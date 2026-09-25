"""Compositor do cenário (T7b): desenha o quad de vídeo com o fundo trocado pela máscara da pessoa."""

import moderngl
import numpy as np

from . import paths

SHADERS = paths.ROOT / "src" / "provador" / "shaders"
RANGE_SIGMA = 0.10        # tolerância de cor do refinamento (0-1): menor = borda mais colada à imagem, mais ruído
EDGE_LO, EDGE_HI = 0.35, 0.75   # curva da máscara; o corte acima de 0,5 come o halo de fundo


def texture_from_bgr(ctx: moderngl.Context, image: np.ndarray, mipmaps: bool = True,
                     nearest: bool = False) -> moderngl.Texture:
    """Textura RGB a partir de uma imagem BGR do OpenCV (o swizzle troca R e B na amostragem)."""
    h, w = image.shape[:2]
    tex = ctx.texture((w, h), 3, np.ascontiguousarray(image).tobytes())
    tex.swizzle = "BGR1"
    tex.repeat_x = tex.repeat_y = False
    if nearest:
        tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    elif mipmaps:
        tex.build_mipmaps()
        tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        tex.anisotropy = 4.0
    else:
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
    return tex


class Compositor:
    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.prog = ctx.program(vertex_shader=(SHADERS / "quad.vert").read_text(encoding="utf-8"),
                                fragment_shader=(SHADERS / "composite.frag").read_text(encoding="utf-8"))
        self.vao = ctx.vertex_array(self.prog, [])
        for name, unit in (("video", 0), ("mask", 1), ("background", 3), ("guide", 4)):
            self.prog[name].value = unit
        self.prog["rect"].value = (-1.0, -1.0, 1.0, 1.0)
        self.prog["range_sigma"].value = RANGE_SIGMA
        self.prog["edge_lo"].value = EDGE_LO
        self.prog["edge_hi"].value = EDGE_HI

    def draw(self, video: moderngl.Texture, mask: moderngl.Texture, guide: moderngl.Texture,
             background: moderngl.Texture, mirror: bool, bg_scale: tuple[float, float],
             person_gain=(1.0, 1.0, 1.0)) -> None:
        """Desenha no viewport atual (a área letterbox do vídeo)."""
        self.prog["mirror"].value = mirror
        self.prog["bg_scale"].value = bg_scale
        self.prog["person_gain"].value = tuple(float(g) for g in person_gain)
        video.use(0)
        mask.use(1)
        background.use(3)
        guide.use(4)
        self.ctx.disable(moderngl.BLEND | moderngl.DEPTH_TEST)
        self.vao.render(moderngl.TRIANGLE_STRIP, vertices=4)
