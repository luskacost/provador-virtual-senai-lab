"""Renderer das peças: GLB na GPU, LBS no vertex shader, projeção alinhada à webcam. Sem readback."""

import moderngl
import numpy as np

from . import paths
from . import skeleton as sk
from .camera import DEFAULT_HFOV, gl_bytes, perspective
from .garment import Garment
from .lighting import DEFAULT_LIGHT, Light

SHADERS = paths.ROOT / "src" / "provador" / "shaders"
GRAIN = 0.02                     # amplitude do grão sobre a peça (0 = sem), combina com o ruído da webcam
INFLATE = 0.012                  # m; dilatação da peça para cobrir a roupa real (T7)


def vertex_source() -> str:
    src = (SHADERS / "garment.vert").read_text(encoding="utf-8")
    head, rest = src.split("\n", 1)            # a linha #version precisa ser a primeira
    return f"{head}\n#define N_JOINTS {sk.N_JOINTS}\n{rest}"


def sh_glsl() -> str:
    """Função sh_eval() do GLSL; exige `uniform float sh[9];` declarado antes."""
    return (SHADERS / "sh.glsl").read_text(encoding="utf-8")


def fragment_source() -> str:
    return (SHADERS / "garment.frag").read_text(encoding="utf-8").replace("// @SH_EVAL@", sh_glsl(), 1)


class GpuGarment:
    """Buffers de uma peça já na GPU (carregar uma vez; trocar de peça é só trocar o objeto — T8)."""

    def __init__(self, ctx: moderngl.Context, prog: moderngl.Program, g: Garment):
        self.name = g.name
        self.base_color = g.base_color
        self.albedo: moderngl.Texture | None = None
        if g.texture is not None:
            h, w = g.texture.shape[:2]
            self.albedo = ctx.texture((w, h), 3, np.ascontiguousarray(g.texture).tobytes())
            self.albedo.swizzle = "BGR1"                      # o OpenCV entrega BGR
            self.albedo.build_mipmaps()
            self.albedo.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            self.albedo.anisotropy = 8.0
            self.albedo.repeat_x = self.albedo.repeat_y = False
        self._bufs = [
            ctx.buffer(g.positions.astype("f4").tobytes()),
            ctx.buffer(g.normals.astype("f4").tobytes()),
            ctx.buffer(g.uvs.astype("f4").tobytes()),
            ctx.buffer(g.joints.astype("u4").tobytes()),
            ctx.buffer(g.weights.astype("f4").tobytes()),
        ]
        self._ibo = ctx.buffer(g.indices.astype("u4").tobytes())
        layout = [("3f", "in_pos"), ("3f", "in_normal"), ("2f", "in_uv"), ("4u4", "in_joints"), ("4f", "in_weights")]
        content = [(buf, fmt, name) for buf, (fmt, name) in zip(self._bufs, layout, strict=True)
                   if name in prog]             # atributos otimizados pelo compilador ficam de fora
        self.vao = ctx.vertex_array(prog, content, index_buffer=self._ibo, index_element_size=4)

    def release(self) -> None:
        if self.albedo is not None:
            self.albedo.release()
        self.vao.release()
        for b in (*self._bufs, self._ibo):
            b.release()


class GarmentRenderer:
    def __init__(self, ctx: moderngl.Context, hfov: float = DEFAULT_HFOV):
        self.ctx = ctx
        self.hfov = hfov
        self.prog = ctx.program(vertex_shader=vertex_source(), fragment_shader=fragment_source())
        self.prog["mask"].value = 1
        self.prog["albedo_tex"].value = 2
        self.inflate = INFLATE
        self.grain = GRAIN
        self.scene_gain = (1.0, 1.0, 1.0)
        self._light = DEFAULT_LIGHT
        self._frame_no = 0
        self.set_light(DEFAULT_LIGHT)
        self.current: GpuGarment | None = None
        self.set_pose(sk.skin_matrices(sk.world_matrices()), np.eye(4))

    def load(self, g: Garment) -> GpuGarment:
        return GpuGarment(self.ctx, self.prog, g)

    def _bind_albedo(self, garment: GpuGarment) -> None:
        self.prog["has_albedo"].value = garment.albedo is not None
        if garment.albedo is not None:
            garment.albedo.use(2)

    def set_light(self, light: Light) -> None:
        """Luz estimada (lighting.py): SH da forma, exposição e balanço de branco."""
        self._light = light
        self.prog["sh"].value = tuple(float(v) for v in light.sh)
        self.prog["exposure"].value = float(light.exposure)
        self.prog["tint"].value = tuple(float(v) * g for v, g in zip(light.tint, self.scene_gain, strict=True))

    def set_scene_gain(self, gain) -> None:
        """Ganho de cor do cenário (T7b): a peça acompanha a pessoa, que é puxada em direção ao tom do cenário."""
        self.scene_gain = tuple(float(g) for g in gain)
        self.set_light(self._light)

    def set_pose(self, skin_mats: np.ndarray, model: np.ndarray) -> None:
        """skin_mats: (N_JOINTS, 4, 4); model: 4x4 do espaço da peça para o da câmera."""
        self.prog["bones"].write(gl_bytes(skin_mats))
        self.prog["model"].write(gl_bytes(model))

    def render_thumbnail(self, garment: GpuGarment, size: int = 192) -> moderngl.Texture:
        """Miniatura de frente, na pose de repouso, renderizada direto numa textura (sem readback).
        Deixa o framebuffer da tela ativo ao terminar."""
        tex = self.ctx.texture((size, size), 4)
        depth = self.ctx.depth_renderbuffer((size, size))
        fbo = self.ctx.framebuffer([tex], depth)
        fbo.use()
        self.ctx.viewport = (0, 0, size, size)
        fbo.clear(0.46, 0.50, 0.56, 0.95, depth=1.0)
        self.set_pose(sk.skin_matrices(sk.world_matrices()), sk.translation((0.0, -1.22, -1.2)))
        self.prog["proj"].write(gl_bytes(perspective(40.0, 1.0)))
        self.prog["viewport"].value = (0.0, 0.0, float(size), float(size))
        self.prog["use_mask"].value = False
        self.prog["mirror"].value = False
        self.prog["inflate"].value = 0.0
        self.prog["grain"].value = 0.0
        self.set_light(DEFAULT_LIGHT)
        self.prog["base_color"].value = tuple(garment.base_color)
        self._bind_albedo(garment)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.CULL_FACE | moderngl.BLEND)
        garment.vao.render(moderngl.TRIANGLES)
        self.ctx.disable(moderngl.DEPTH_TEST)
        fbo.release()
        depth.release()
        tex.build_mipmaps()
        tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        self.ctx.screen.use()
        return tex

    def draw(self, viewport: tuple[int, int, int, int], mirror: bool, use_mask: bool = False) -> None:
        """Desenha a peça atual. O viewport do GL já deve ser a área (letterbox) do vídeo; com use_mask, a
        máscara da segmentação precisa estar ligada na unidade 1."""
        if self.current is None:
            return
        x, y, w, h = viewport
        self.prog["viewport"].value = (float(x), float(y), float(w), float(h))
        self.prog["use_mask"].value = use_mask
        self.prog["inflate"].value = self.inflate
        self._frame_no += 1
        self.prog["grain"].value = self.grain
        self.prog["grain_seed"].value = float(self._frame_no % 997)
        self.prog["proj"].write(gl_bytes(perspective(self.hfov, w / h)))
        self.prog["mirror"].value = mirror
        self.prog["base_color"].value = tuple(self.current.base_color)
        self._bind_albedo(self.current)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.CULL_FACE)       # casca aberta: o lado de dentro é tratado no shader
        self.ctx.enable(moderngl.BLEND)            # alfa < 1 onde cabelo/rosto passam por cima
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.current.vao.render(moderngl.TRIANGLES)
        self.ctx.disable(moderngl.DEPTH_TEST | moderngl.BLEND)
