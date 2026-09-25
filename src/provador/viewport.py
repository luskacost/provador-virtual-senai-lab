"""Geometria de viewport (sem GL), para poder testar sem janela."""


def letterbox(win_w: int, win_h: int, img_w: int, img_h: int) -> tuple[int, int, int, int]:
    """Maior retângulo (x, y, w, h) com a proporção da imagem, centralizado na janela."""
    if min(win_w, win_h, img_w, img_h) <= 0:
        return 0, 0, max(win_w, 0), max(win_h, 0)
    scale = min(win_w / img_w, win_h / img_h)
    w, h = round(img_w * scale), round(img_h * scale)
    return (win_w - w) // 2, (win_h - h) // 2, w, h
