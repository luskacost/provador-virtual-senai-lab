"""Renderer das peças: GLB na GPU, LBS no vertex shader, projeção alinhada à webcam. Sem readback."""

import moderngl
import numpy as np

from . import paths
from . import skeleton as sk
from .camera import DEFAULT_HFOV, gl_bytes, perspective
from .garment import Garment

SHADERS = paths.ROOT / "src" / "provador" / "shaders"
LIGHT_DIR = (0.35, 0.6, 1.0)     # de cima, levemente à direita, vindo da câmera
INFLATE = 0.012                  # m; dilatação da peça para cobrir a roupa real (T7)


def vertex_source() -> str:
    src = (SHADERS / "garment.vert").read_text(encoding="utf-8")
    head, rest = src.split("\n", 1)            # a linha #version precisa ser a primeira
    return f"{head}\n#define N_JOINTS {sk.N_JOINTS}\n{rest}"


def fragment_source() -> str:
    return (SHADERS / "garment.frag").read_text(encoding="utf-8")


class GpuGarment:
    """Buffers de uma peça já na GPU (carregar uma vez; trocar de peça é só trocar o objeto — T8)."""

    def __init__(self, ctx: moderngl.Context, prog: moderngl.Program, g: Garment):
        self.name = g.name
        self.base_color = g.base_color
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
        self.vao.release()
        for b in (*self._bufs, self._ibo):
            b.release()


class GarmentRenderer:
    def __init__(self, ctx: moderngl.Context, hfov: float = DEFAULT_HFOV):
        self.ctx = ctx
        self.hfov = hfov
        self.prog = ctx.program(vertex_shader=vertex_source(), fragment_shader=fragment_source())
        self.prog["light_dir"].value = LIGHT_DIR
        self.prog["mask"].value = 1
        self.inflate = INFLATE
        self.current: GpuGarment | None = None
        self.set_pose(sk.skin_matrices(sk.world_matrices()), np.eye(4))

    def load(self, g: Garment) -> GpuGarment:
        return GpuGarment(self.ctx, self.prog, g)

    def set_pose(self, skin_mats: np.ndarray, model: np.ndarray) -> None:
        """skin_mats: (N_JOINTS, 4, 4); model: 4x4 do espaço da peça para o da câmera."""
        self.prog["bones"].write(gl_bytes(skin_mats))
        self.prog["model"].write(gl_bytes(model))

    def draw(self, viewport: tuple[int, int, int, int], mirror: bool, use_mask: bool = False) -> None:
        """Desenha a peça atual. O viewport do GL já deve ser a área (letterbox) do vídeo; com use_mask, a
        máscara da segmentação precisa estar ligada na unidade 1."""
        if self.current is None:
            return
        x, y, w, h = viewport
        self.prog["viewport"].value = (float(x), float(y), float(w), float(h))
        self.prog["use_mask"].value = use_mask
        self.prog["inflate"].value = self.inflate
        self.prog["proj"].write(gl_bytes(perspective(self.hfov, w / h)))
        self.prog["mirror"].value = mirror
        self.prog["base_color"].value = tuple(self.current.base_color)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.CULL_FACE)       # casca aberta: o lado de dentro é tratado no shader
        self.ctx.enable(moderngl.BLEND)            # alfa < 1 onde cabelo/rosto passam por cima
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.current.vao.render(moderngl.TRIANGLES)
        self.ctx.disable(moderngl.DEPTH_TEST | moderngl.BLEND)
