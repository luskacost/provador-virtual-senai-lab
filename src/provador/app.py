"""App do Provador Virtual 3D. T2: webcam em thread + janela GLFW/ModernGL + HUD de FPS.

Uso:  python -m provador.app [--camera-index 0] [--no-mirror] [--debug]
Teclas: Esc/Q sai · H liga/desliga o HUD · M espelha/desespelha · K liga/desliga o esqueleto (--debug)
--debug liga a pose (T3): esqueleto sobre o vídeo e métricas de pose e jitter no HUD.
"""

import argparse
import sys
import time

import cv2
import glfw
import moderngl
import numpy as np

from . import paths
from .capture import CameraThread
from .debug_draw import SkeletonOverlay
from .metrics import JitterStats, LatencyStats, RateCounter
from .pose import L_SHOULDER, R_SHOULDER, PoseWorker
from .viewport import letterbox

SHADERS = paths.ROOT / "src" / "provador" / "shaders"
FULLSCREEN = (-1.0, -1.0, 1.0, 1.0)
HUD_WIDTH = 560
HUD_LINE_H = 26
HUD_REFRESH_S = 0.25         # o texto muda pouco: reenviar a textura só 4x/s


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
        if self.args.debug:
            self.skeleton = SkeletonOverlay(self.ctx)

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
    def _draw_video(self) -> None:
        fb_w, fb_h = glfw.get_framebuffer_size(self.win)
        self.ctx.viewport = (0, 0, fb_w, fb_h)
        self.ctx.clear(0.0, 0.0, 0.0)
        if self.video_tex is None or fb_w == 0 or fb_h == 0:
            return
        x, y, w, h = letterbox(fb_w, fb_h, *self.video_tex.size)
        self.ctx.viewport = (x, y, w, h)
        self.ctx.disable(moderngl.BLEND)
        self.prog["rect"].value = FULLSCREEN
        self.prog["mirror"].value = self.mirror
        self.video_tex.use(0)
        self.vao.render(moderngl.TRIANGLE_STRIP, vertices=4)
        if self.skeleton and self.show_skeleton:
            self.skeleton.draw((w, h), self.mirror)

    def _draw_hud(self) -> None:
        fb_w, fb_h = glfw.get_framebuffer_size(self.win)
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
        if self.pose:
            if self.pose.error:
                lines.append(f"POSE: {self.pose.error}")
            else:
                lines += [
                    (f"Pose {self.pose.rate.rate:5.1f} Hz | inferencia {self.pose.inference.mean_ms:4.1f} ms"
                     f" | {'pessoa OK' if self.person_found else 'SEM PESSOA'}"),
                    (f"Jitter ombros (desvio-padrao px): cru {self.jitter_raw.std_max:.2f}"
                     f" -> filtrado {self.jitter_filtered.std_max:.2f}"),
                ]
        lines.append(f"Espelho {'ON' if self.mirror else 'OFF'} | H: HUD | M: espelho | K: esqueleto | Esc: sair")
        return lines

    def _update_pose(self, last_pose_id: int) -> int:
        """Puxa o resultado de pose mais novo para o overlay e as métricas. Devolve o id consumido."""
        frame_id, result = self.pose.latest()
        if frame_id == last_pose_id:
            return last_pose_id
        self.person_found = result is not None
        if result is None:
            self.skeleton.clear()
            self.jitter_raw.reset()
            self.jitter_filtered.reset()
            return frame_id
        self.skeleton.update(result.px, result.visibility, result.image_size)
        shoulders = (L_SHOULDER, R_SHOULDER)
        self.jitter_raw.add(result.px_raw[shoulders, :2].ravel())
        self.jitter_filtered.add(result.px[shoulders, :2].ravel())
        return frame_id

    # --- loop --------------------------------------------------------------------------------
    def run(self) -> int:
        try:
            cam = CameraThread(self.args.camera_index, self.args.width, self.args.height).start()
        except RuntimeError as exc:
            print(f"[ERRO] {exc}")
            return 1
        try:
            self._init_window()
            if self.args.debug:
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
        while not glfw.window_should_close(self.win):
            glfw.poll_events()
            if self.args.seconds and time.perf_counter() - t_start >= self.args.seconds:
                break

            frame = cam.latest(last_id)
            if frame is not None:
                self._upload_frame(frame.image)
                last_id = frame.id
            if self.pose:
                last_pose_id = self._update_pose(last_pose_id)

            self._draw_video()
            now = time.perf_counter()
            if self.show_hud:
                if now - last_hud >= HUD_REFRESH_S:
                    self._upload_hud(render_hud(self._hud_lines(cam)))
                    last_hud = now
                self._draw_hud()

            glfw.swap_buffers(self.win)
            self.render_rate.tick()
            if frame is not None:
                self.latency.add(time.perf_counter() - frame.t_capture)
        if self.args.seconds:
            print(f"FPS render {self.render_rate.rate:.1f} | FPS camera {cam.capture_rate.rate:.1f} | "
                  f"latencia {self.latency.mean_ms:.0f} ms (max {self.latency.max_ms:.0f})")
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
    ap.add_argument("--debug", action="store_true", help="liga a pose: esqueleto e métricas de pose/jitter")
    args = ap.parse_args(argv)
    return App(args).run()


if __name__ == "__main__":
    sys.exit(main())
