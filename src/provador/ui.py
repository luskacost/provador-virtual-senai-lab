"""Layout e hit-test da interface (setas + miniaturas), em pixels da janela com origem no canto superior
esquerdo. Sem GL: o app só desenha os retângulos calculados aqui e usa `hit` nos cliques."""

from dataclasses import dataclass

Rect = tuple[int, int, int, int]      # x, y, largura, altura

THUMB = 96
GAP = 12
ARROW_W, ARROW_H = 44, 64
MARGIN_BOTTOM = 18


@dataclass(frozen=True)
class Layout:
    thumbs: list[Rect]
    prev: Rect
    next: Rect


def layout(win_w: int, win_h: int, n: int) -> Layout:
    """Faixa centralizada no rodapé: seta ← · miniaturas · seta →. Se não couber, encolhe as miniaturas."""
    n = max(n, 0)
    avail = max(win_w - 2 * (ARROW_W + GAP) - 24, 1)
    size = min(THUMB, max((avail - GAP * max(n - 1, 0)) // max(n, 1), 24))
    strip_w = n * size + GAP * max(n - 1, 0)
    x0 = (win_w - strip_w) // 2
    y = win_h - MARGIN_BOTTOM - size
    thumbs = [(x0 + i * (size + GAP), y, size, size) for i in range(n)]
    ay = y + (size - ARROW_H) // 2
    return Layout(thumbs, (x0 - GAP - ARROW_W, ay, ARROW_W, ARROW_H), (x0 + strip_w + GAP, ay, ARROW_W, ARROW_H))


def _inside(r: Rect, x: float, y: float) -> bool:
    return r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]


def hit(lay: Layout, x: float, y: float) -> tuple[str, int] | None:
    """O que há sob o ponto: ("piece", i), ("prev", 0), ("next", 0) ou None."""
    for i, r in enumerate(lay.thumbs):
        if _inside(r, x, y):
            return "piece", i
    if _inside(lay.prev, x, y):
        return "prev", 0
    if _inside(lay.next, x, y):
        return "next", 0
    return None


def rect_to_ndc(r: Rect, win_w: int, win_h: int) -> tuple[float, float, float, float]:
    """Retângulo em pixels (origem no topo) → (x0, y0, x1, y1) em NDC com y para cima, como o quad.vert espera."""
    x, y, w, h = r
    return (2.0 * x / win_w - 1.0, 1.0 - 2.0 * (y + h) / win_h,
            2.0 * (x + w) / win_w - 1.0, 1.0 - 2.0 * y / win_h)
