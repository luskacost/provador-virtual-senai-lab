"""Barra de navegação em GL: miniaturas (renderizadas na GPU), setas, números e o nome da peça atual."""

import cv2
import moderngl
import numpy as np

from . import paths, ui

SHADERS = paths.ROOT / "src" / "provador" / "shaders"
BORDER = 4        # px da moldura branca da peça selecionada


def _bgra_texture(ctx: moderngl.Context, img: np.ndarray) -> moderngl.Texture:
    h, w = img.shape[:2]
    tex = ctx.texture((w, h), 4, np.ascontiguousarray(img).tobytes())
    tex.swizzle = "BGRA"
    tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
    return tex


def text_image(text: str, scale: float = 0.6, pad: int = 8, min_size: tuple[int, int] = (0, 0)) -> np.ndarray:
    """Texto branco sobre fundo escuro translúcido (BGRA)."""
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    w, h = max(tw + 2 * pad, min_size[0]), max(th + base + 2 * pad, min_size[1])
    img = np.zeros((h, w, 4), np.uint8)
    img[:] = (0, 0, 0, 150)
    cv2.putText(img, text, ((w - tw) // 2, (h + th) // 2), cv2.FONT_HERSHEY_SIMPLEX, scale,
                (255, 255, 255, 255), 1, cv2.LINE_AA)
    return img


def arrow_image(left: bool) -> np.ndarray:
    img = np.zeros((ui.ARROW_H, ui.ARROW_W, 4), np.uint8)
    img[:] = (0, 0, 0, 150)
    cx, cy, s = ui.ARROW_W // 2, ui.ARROW_H // 2, 11
    d = -1 if left else 1
    pts = np.array([[cx - d * s // 2, cy - s * 2], [cx + d * s // 2, cy], [cx - d * s // 2, cy + s * 2]], np.int32)
    cv2.polylines(img, [pts], False, (255, 255, 255, 255), 3, cv2.LINE_AA)
    return img


class GarmentBar:
    def __init__(self, ctx: moderngl.Context, thumbs: list[moderngl.Texture], names: list[str]):
        self.ctx = ctx
        self.thumbs = thumbs
        self.names = names
        self.prog = ctx.program(vertex_shader=(SHADERS / "quad.vert").read_text(encoding="utf-8"),
                                fragment_shader=(SHADERS / "quad.frag").read_text(encoding="utf-8"))
        self.prog["tex"].value = 0
        self.prog["mirror"].value = False
        self.vao = ctx.vertex_array(self.prog, [])
        self.numbers = [_bgra_texture(ctx, text_image(str(i + 1), 0.55, 6, (26, 26))) for i in range(min(len(thumbs), 9))]
        self.arrows = (_bgra_texture(ctx, arrow_image(True)), _bgra_texture(ctx, arrow_image(False)))
        self.white = ctx.texture((1, 1), 4, bytes([255, 255, 255, 255]))
        self.name_tex: moderngl.Texture | None = None
        self._name_for = -1

    def layout(self, fb_w: int, fb_h: int) -> ui.Layout:
        return ui.layout(fb_w, fb_h, len(self.thumbs))

    def _quad(self, tex: moderngl.Texture, rect: ui.Rect, fb_w: int, fb_h: int) -> None:
        self.prog["rect"].value = ui.rect_to_ndc(rect, fb_w, fb_h)
        tex.use(0)
        self.vao.render(moderngl.TRIANGLE_STRIP, vertices=4)

    def _set_name(self, index: int) -> None:
        if index == self._name_for:
            return
        if self.name_tex is not None:
            self.name_tex.release()
        label = f"{index + 1}/{len(self.thumbs)}  {self.names[index]}"
        self.name_tex = _bgra_texture(self.ctx, text_image(label, 0.65, 10))
        self._name_for = index

    def draw(self, fb_w: int, fb_h: int, selected: int) -> None:
        if not self.thumbs or fb_w == 0 or fb_h == 0:
            return
        self.ctx.screen.use()
        self.ctx.viewport = (0, 0, fb_w, fb_h)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        lay = self.layout(fb_w, fb_h)
        for i, (x, y, w, h) in enumerate(lay.thumbs):
            if i == selected:
                self._quad(self.white, (x - BORDER, y - BORDER, w + 2 * BORDER, h + 2 * BORDER), fb_w, fb_h)
            self._quad(self.thumbs[i], (x, y, w, h), fb_w, fb_h)
            if i < len(self.numbers):
                nx, ny = x + 4, y + 4
                self._quad(self.numbers[i], (nx, ny, *self.numbers[i].size), fb_w, fb_h)
        self._quad(self.arrows[0], lay.prev, fb_w, fb_h)
        self._quad(self.arrows[1], lay.next, fb_w, fb_h)
        self._set_name(selected)
        nw, nh = self.name_tex.size
        first = lay.thumbs[0]
        self._quad(self.name_tex, ((fb_w - nw) // 2, first[1] - BORDER - 10 - nh, nw, nh), fb_w, fb_h)
        self.ctx.disable(moderngl.BLEND)

    def release(self) -> None:
        for tex in (*self.thumbs, *self.numbers, *self.arrows, self.white, self.name_tex):
            if tex is not None:
                tex.release()
        self.vao.release()
        self.prog.release()
