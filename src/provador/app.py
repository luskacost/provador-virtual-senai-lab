"""App do Provador Virtual 3D: webcam + peça 3D rigada (LBS na GPU) + HUD.

Uso:  python -m provador.app [--camera-index 0] [--no-mirror] [--debug] [--garment x.glb] [--hfov 70]
Teclas: Esc/Q sai · H HUD · M espelho · G peça · S sincronia vídeo/pose · A animação de teste do LBS
        K esqueleto (--debug)
A peça segue o corpo pela pose (retarget.py). --debug mostra o esqueleto e as métricas de pose/jitter.
"""

import argparse
import sys
import time

import cv2
import glfw
import moderngl
import numpy as np

from . import paths
from . import skeleton as sk
from .capture import CameraThread
from .debug_draw import SkeletonOverlay
from .garment import load_glb
from .garment_render import GarmentRenderer
from .gl_sync import finish_without_gil
from .metrics import JitterStats, LatencyStats, RateCounter, RunningMean
from .pose import L_SHOULDER, R_SHOULDER, PoseResult, PoseWorker
from .retarget import Retarget, joint_error_px, retarget
from .viewport import letterbox

SHADERS = paths.ROOT / "src" / "provador" / "shaders"
FULLSCREEN = (-1.0, -1.0, 1.0, 1.0)
HUD_WIDTH = 560
HUD_LINE_H = 26
HUD_REFRESH_S = 0.25         # o texto muda pouco: reenviar a textura só 4x/s
MSAA_SAMPLES = 4
# Posição fixa usada só pela animação de teste (tecla A); no uso normal o retarget posiciona a peça.
STATIC_MODEL = sk.translation((0.0, -1.25, -1.7))


def _read_shader(name: str) -> str:
    return (SHADERS / name).read_text(encoding="utf-8")


def render_hud(lines: list[str]) -> np.ndarray:
    """Desenha o HUD numa imagem BGRA pequena (a textura sobe à GPU; nunca há readback)."""
    img = np.zeros((HUD_LINE_H * len(lines) + 12, HUD_WIDTH, 4), np.uint8)
    img[:] = (0, 0, 0, 150)
    for i, text in enumerate(lines):
        cv2.putText(img, text, (10, 26 + i * HUD_LINE_H), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255, 255), 1, cv2.LINE_AA)
    return img


class App:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.mirror = not args.no_mirror
        self.show_hud = True
        self.show_skeleton = True
        self.pose: PoseWorker | None = None
        self.skeleton: SkeletonOverlay | None = None
        self.jitter_raw = JitterStats()
        self.jitter_filtered = JitterStats()
        self.person_found = False
        self.garments: GarmentRenderer | None = None
        self.show_garment = True
        self.demo_anim = args.demo
        self.sync_video = True
        self.fit: Retarget | None = None
        self.fit_error = RunningMean()
        self.render_rate = RateCounter()
        self.latency = LatencyStats()
        self.win = None
        self.ctx = None

    # --- janela e GL -------------------------------------------------------------------------
    def _init_window(self) -> None:
        if not glfw.init():
            raise RuntimeError("glfw.init() falhou")
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
        self.win = glfw.create_window(self.args.width, self.args.height, "Provador Virtual 3D", None, None)
        if not self.win:
            raise RuntimeError("não foi possível criar a janela OpenGL 3.3 core")
        glfw.make_context_current(self.win)
        glfw.swap_interval(1)
        glfw.set_key_callback(self.win, self._on_key)

        self.ctx = moderngl.create_context()
        renderer = self.ctx.info.get("GL_RENDERER", "?")
        print(f"OpenGL: {renderer}")
        if "intel" in renderer.lower():
            print("[AVISO] OpenGL na GPU integrada; veja docs/hardware.md (ajuste 1).")

        self.prog = self.ctx.program(vertex_shader=_read_shader("quad.vert"),
                                     fragment_shader=_read_shader("quad.frag"))
        self.vao = self.ctx.vertex_array(self.prog, [])      # sem buffers: vértices vêm de gl_VertexID
        self.prog["tex"].value = 0
        self.video_tex = None
        self.hud_tex = None
        self.msaa: moderngl.Framebuffer | None = None
        if self.args.debug:
            self.skeleton = SkeletonOverlay(self.ctx)
        self._init_garment()

    def _init_garment(self) -> None:
        self.garments = GarmentRenderer(self.ctx, hfov=self.args.hfov)
        path = self.args.garment
        try:
            self.garments.current = self.garments.load(load_glb(path))
        except (OSError, ValueError) as exc:
            print(f"[AVISO] peça não carregada ({exc}). Gere o template: python tools/make_template.py")
            return
        print(f"Peça: {self.garments.current.name}")

    def _demo_pose(self, t: float) -> None:
        """Anima os ossos (sem pose da webcam) para conferir o LBS na GPU."""
        rots = np.broadcast_to(np.eye(3), (sk.N_JOINTS, 3, 3)).copy()
        s = np.sin(t * 2.0)
        rots[sk.INDEX["L_upper_arm"]] = sk.rotation_axis_angle((0, 0, 1), -35 + 55 * s)
        rots[sk.INDEX["R_upper_arm"]] = sk.rotation_axis_angle((0, 0, 1), 35 + 55 * s)
        rots[sk.INDEX["spine"]] = sk.rotation_axis_angle((0, 1, 0), 25 * np.sin(t * 0.9))
        self.garments.set_pose(sk.skin_matrices(sk.world_matrices(rots)), STATIC_MODEL)

    def _on_key(self, win, key, scancode, action, mods) -> None:
        if action != glfw.PRESS:
            return
        if key in (glfw.KEY_ESCAPE, glfw.KEY_Q):
            glfw.set_window_should_close(win, True)
        elif key == glfw.KEY_H:
            self.show_hud = not self.show_hud
        elif key == glfw.KEY_M:
            self.mirror = not self.mirror
        elif key == glfw.KEY_K:
            self.show_skeleton = not self.show_skeleton
        elif key == glfw.KEY_G:
            self.show_garment = not self.show_garment
        elif key == glfw.KEY_A and self.garments:
            self.demo_anim = not self.demo_anim
        elif key == glfw.KEY_S:
            self.sync_video = not self.sync_video

    def _upload_hud(self, image: np.ndarray) -> None:
        h, w = image.shape[:2]
        if self.hud_tex is None or self.hud_tex.size != (w, h):
            if self.hud_tex is not None:
                self.hud_tex.release()
            self.hud_tex = self.ctx.texture((w, h), 4)
            self.hud_tex.swizzle = "BGRA"
            self.hud_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.hud_tex.write(image, alignment=1)

    def _upload_frame(self, image: np.ndarray) -> None:
        h, w = image.shape[:2]
        if self.video_tex is None or self.video_tex.size != (w, h):
            if self.video_tex is not None:
                self.video_tex.release()
            self.video_tex = self.ctx.texture((w, h), 3)
            self.video_tex.swizzle = "BGR1"                 # o OpenCV entrega BGR; troca no sampler
            self.video_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.video_tex.write(image, alignment=1)

    # --- desenho -----------------------------------------------------------------------------
    def _msaa_target(self, size: tuple[int, int]) -> moderngl.Framebuffer:
        """Framebuffer MSAA (cor + profundidade) do tamanho da janela; recriado só quando ela muda."""
        if self.msaa is None or self.msaa.size != size:
            if self.msaa is not None:
                for att in (*self.msaa.color_attachments, self.msaa.depth_attachment):
                    att.release()
                self.msaa.release()
            self.msaa = self.ctx.framebuffer(
                color_attachments=[self.ctx.renderbuffer(size, 4, samples=MSAA_SAMPLES)],
                depth_attachment=self.ctx.depth_renderbuffer(size, samples=MSAA_SAMPLES),
            )
            print(f"MSAA {self.msaa.samples}x em {size[0]}x{size[1]}")
        return self.msaa

    def _draw_scene(self) -> None:
        """Vídeo + peça + esqueleto no framebuffer MSAA, resolvido na tela por blit (tudo na GPU)."""
        fb_w, fb_h = glfw.get_framebuffer_size(self.win)
        self.ctx.screen.use()
        self.ctx.viewport = (0, 0, fb_w, fb_h)
        self.ctx.clear(0.0, 0.0, 0.0)
        if fb_w == 0 or fb_h == 0:
            return
        target = self._msaa_target((fb_w, fb_h))
        target.use()
        self.ctx.viewport = (0, 0, fb_w, fb_h)
        target.clear(0.0, 0.0, 0.0, 1.0, depth=1.0)
        self._draw_video(fb_w, fb_h)
        self.ctx.copy_framebuffer(self.ctx.screen, target)
        self.ctx.screen.use()

    def _draw_video(self, fb_w: int, fb_h: int) -> None:
        if self.video_tex is None:
            return
        x, y, w, h = letterbox(fb_w, fb_h, *self.video_tex.size)
        self.ctx.viewport = (x, y, w, h)
        self.ctx.disable(moderngl.BLEND)
        self.prog["rect"].value = FULLSCREEN
        self.prog["mirror"].value = self.mirror
        self.video_tex.use(0)
        self.vao.render(moderngl.TRIANGLE_STRIP, vertices=4)
        if self.garments and self.show_garment and (self.fit is not None or self.demo_anim):
            self.garments.draw((w, h), self.mirror)
        if self.skeleton and self.show_skeleton:
            self.skeleton.draw((w, h), self.mirror)

    def _draw_hud(self) -> None:
        fb_w, fb_h = glfw.get_framebuffer_size(self.win)
        self.ctx.screen.use()
        if fb_w == 0 or fb_h == 0 or self.hud_tex is None:
            return
        hud_w, hud_h = self.hud_tex.size
        self.ctx.viewport = (0, 0, fb_w, fb_h)
        margin = 12
        x0 = -1.0 + 2.0 * margin / fb_w
        y1 = 1.0 - 2.0 * margin / fb_h
        rect = (x0, y1 - 2.0 * hud_h / fb_h, x0 + 2.0 * hud_w / fb_w, y1)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.prog["rect"].value = rect
        self.prog["mirror"].value = False
        self.hud_tex.use(0)
        self.vao.render(moderngl.TRIANGLE_STRIP, vertices=4)

    def _hud_lines(self, cam: CameraThread) -> list[str]:
        if cam.error:
            return ["SEM SINAL DA WEBCAM", cam.error]
        lines = [
            f"FPS render  {self.render_rate.rate:5.1f}",
            f"FPS camera  {cam.capture_rate.rate:5.1f}",
            f"Latencia captura->tela  {self.latency.mean_ms:4.0f} ms (max {self.latency.max_ms:.0f})",
        ]
        if self.fit is not None:
            lines.append(f"Ajuste: {self.fit.depth:.2f} m | escala {self.fit.scale[0]:.2f}/{self.fit.scale[1]:.2f}"
                         f" | giro {self.fit.yaw_deg:+.0f} torcao {self.fit.twist_deg:+.0f} | "
                         f"erro {self.fit_error.mean:.1f} px")
        if self.pose and self.pose.error:
            lines.append(f"POSE: {self.pose.error}")
        elif self.pose:
            lines.append(f"Pose {self.pose.rate.rate:5.1f} Hz | inferencia {self.pose.inference.mean_ms:4.1f} ms"
                         f" | {'pessoa OK' if self.person_found else 'SEM PESSOA'}")
            if self.args.debug:
                lines.append(f"Jitter ombros (desvio-padrao px): cru {self.jitter_raw.std_max:.2f}"
                             f" -> filtrado {self.jitter_filtered.std_max:.2f}")
        if self.garments and self.garments.current:
            lines.append(f"Peca: {self.garments.current.name} | hFOV {self.garments.hfov:.0f} | "
                         f"G: peca | S: sincronia {'ON' if self.sync_video else 'OFF'} | "
                         f"A: animacao {'ON' if self.demo_anim else 'OFF'}")
        lines.append(f"Espelho {'ON' if self.mirror else 'OFF'} | H: HUD | M: espelho | K: esqueleto | Esc: sair")
        return lines

    def _update_pose(self, frame_id: int, result: PoseResult | None) -> None:
        """Aplica um resultado de pose novo: retarget da peça, overlay e métricas."""
        self.person_found = result is not None
        if result is None:
            self.fit = None
            if self.skeleton:
                self.skeleton.clear()
            self.jitter_raw.reset()
            self.jitter_filtered.reset()
            return
        self.fit = retarget(result.px, result.world, result.visibility, result.image_size, self.args.hfov)
        self.fit_error.add(joint_error_px(self.fit, result.px_raw, self.args.hfov, result.image_size))
        if self.garments and not self.demo_anim:
            self.garments.set_pose(self.fit.skin, np.eye(4))
        if self.skeleton:
            self.skeleton.update(result.px, result.visibility, result.image_size)
        shoulders = (L_SHOULDER, R_SHOULDER)
        self.jitter_raw.add(result.px_raw[shoulders, :2].ravel())
        self.jitter_filtered.add(result.px[shoulders, :2].ravel())

    def _save_screenshot(self, path: str) -> None:
        fb_w, fb_h = glfw.get_framebuffer_size(self.win)
        img = np.frombuffer(self.ctx.screen.read(viewport=(0, 0, fb_w, fb_h), components=3), np.uint8)
        cv2.imwrite(path, cv2.cvtColor(img.reshape(fb_h, fb_w, 3)[::-1], cv2.COLOR_RGB2BGR))
        print(f"screenshot: {path}")

    # --- loop --------------------------------------------------------------------------------
    def run(self) -> int:
        try:
            cam = CameraThread(self.args.camera_index, self.args.width, self.args.height).start()
        except RuntimeError as exc:
            print(f"[ERRO] {exc}")
            return 1
        try:
            self._init_window()
            self.pose = PoseWorker(cam).start()
            return self._loop(cam)
        except RuntimeError as exc:
            print(f"[ERRO] {exc}")
            return 1
        finally:
            if self.pose:
                self.pose.stop()
            cam.stop()
            if self.win:
                glfw.destroy_window(self.win)
            glfw.terminate()

    def _loop(self, cam: CameraThread) -> int:
        last_id = -1
        last_pose_id = -1
        last_hud = 0.0
        t_start = time.perf_counter()
        shot_done = False
        while not glfw.window_should_close(self.win):
            glfw.poll_events()
            if self.args.seconds and time.perf_counter() - t_start >= self.args.seconds:
                break

            frame = None
            pose_id, pose_result = self.pose.latest() if self.pose else (-1, None)
            if pose_id != last_pose_id:
                self._update_pose(pose_id, pose_result)
                last_pose_id = pose_id
                if self.sync_video and pose_result is not None and pose_id > last_id:
                    frame = cam.get(pose_id)                    # o frame que gerou a pose: peça e vídeo juntos
            if frame is None and not (self.sync_video and self.person_found):
                frame = cam.latest(last_id)                     # sem pessoa (ou sem sincronia): o mais recente
            if frame is not None:
                self._upload_frame(frame.image)
                last_id = frame.id
            if self.demo_anim:
                self._demo_pose(time.perf_counter() - t_start)

            self._draw_scene()
            now = time.perf_counter()
            if self.show_hud:
                if now - last_hud >= HUD_REFRESH_S:
                    self._upload_hud(render_hud(self._hud_lines(cam)))
                    last_hud = now
                self._draw_hud()

            if (self.args.screenshot and not shot_done
                    and time.perf_counter() - t_start >= max(self.args.seconds - 0.2, 0.5)):
                self._save_screenshot(self.args.screenshot)     # readback único, só para depuração
                shot_done = True
            glfw.swap_buffers(self.win)
            finish_without_gil()                            # espera o vsync sem o GIL (gl_sync.py)
            self.render_rate.tick()
            if frame is not None:
                self.latency.add(time.perf_counter() - frame.t_capture)
        if self.args.seconds:
            print(f"FPS render {self.render_rate.rate:.1f} | FPS camera {cam.capture_rate.rate:.1f} | "
                  f"latencia {self.latency.mean_ms:.0f} ms (max {self.latency.max_ms:.0f})")
            if self.fit is not None:
                print(f"Ajuste {self.fit.depth:.2f} m | escala {self.fit.scale[0]:.2f}/{self.fit.scale[1]:.2f} | "
                      f"giro {self.fit.yaw_deg:+.0f} | torcao {self.fit.twist_deg:+.0f} | "
                      f"erro articulacoes {self.fit_error.mean:.1f} px")
            if self.pose:
                print(f"Pose {self.pose.rate.rate:.1f} Hz | inferencia {self.pose.inference.mean_ms:.1f} ms | "
                      f"pessoa {'sim' if self.person_found else 'NAO'} | jitter ombros px: "
                      f"cru {self.jitter_raw.std_max:.2f} -> filtrado {self.jitter_filtered.std_max:.2f}")
        return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Provador Virtual 3D")
    ap.add_argument("--camera-index", type=int, default=0)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--no-mirror", action="store_true", help="não espelha a imagem")
    ap.add_argument("--seconds", type=float, default=0, help="fecha sozinho após N s e imprime as métricas")
    ap.add_argument("--garment", default=str(paths.TEMPLATES / "tshirt.glb"), help="GLB da peça")
    ap.add_argument("--hfov", type=float, default=70.0, help="FOV horizontal da webcam em graus")
    ap.add_argument("--demo", action="store_true", help="começa com a animação de teste do LBS ligada")
    ap.add_argument("--screenshot", help="salva um PNG da tela perto do fim (use com --seconds)")
    ap.add_argument("--debug", action="store_true", help="liga a pose: esqueleto e métricas de pose/jitter")
    args = ap.parse_args(argv)
    return App(args).run()


if __name__ == "__main__":
    sys.exit(main())
