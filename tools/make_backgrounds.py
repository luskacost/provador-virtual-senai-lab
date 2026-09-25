"""Gera cenários procedurais de demonstração em assets/backgrounds/<id>/{background.jpg, meta.json}.

Uso:  python tools/make_backgrounds.py [--width 1920] [--out assets/backgrounds]

São 4 cenários (estúdio, passarela, loja, cidade ao entardecer) desenhados com numpy/OpenCV, sem chão de
perspectiva forte, para enquadramento de busto. Para usar suas próprias imagens, crie uma pasta em
assets/backgrounds/<id>/ com background.jpg e (opcional) meta.json {"name": "...", "color_match": 0.3}.
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from provador import paths


def bgr(r: int, g: int, b: int) -> np.ndarray:
    return np.array([b, g, r], np.float32)


def vgrad(h: int, w: int, top, bottom) -> np.ndarray:
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    return np.broadcast_to(top * (1 - t) + bottom * t, (h, w, 3)).copy()


def glow(img: np.ndarray, cx: float, cy: float, radius: float, color, strength: float) -> None:
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / radius
    img += np.exp(-d * d * 2.0)[..., None] * color * strength


def bokeh(shape, rng, n: int, y_range, radius_range, palette, alpha: float = 0.5) -> np.ndarray:
    h, w = shape[:2]
    layer = np.zeros(shape, np.float32)
    for _ in range(n):
        c = palette[rng.integers(len(palette))]
        cv2.circle(layer, (int(rng.uniform(0, w)), int(rng.uniform(*y_range) * h)),
                   int(rng.uniform(*radius_range)), tuple(float(v) for v in c * alpha), -1, cv2.LINE_AA)
    return cv2.GaussianBlur(layer, (0, 0), 5)


def finish(img: np.ndarray, rng, vignette: float = 0.3, grain: float = 3.0, blur: float = 0.0) -> np.ndarray:
    h, w = img.shape[:2]
    if blur:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xs - w / 2) / (w / 2)) ** 2 + ((ys - h / 2) / (h / 2)) ** 2)
    img = img * (1.0 - vignette * np.clip(d - 0.4, 0, 1)[..., None])
    img = img + rng.normal(0, grain, img.shape).astype(np.float32)
    return np.clip(img, 0, 255).astype(np.uint8)


def studio(h: int, w: int, rng) -> np.ndarray:
    horizon = int(h * 0.64)
    img = np.zeros((h, w, 3), np.float32)
    img[:horizon] = vgrad(horizon, w, bgr(148, 158, 176), bgr(206, 212, 224))
    img[horizon:] = vgrad(h - horizon, w, bgr(196, 200, 210), bgr(112, 118, 130))
    glow(img, w * 0.5, h * 0.34, w * 0.55, bgr(255, 250, 240), 0.22)
    img[horizon - 3:horizon + 3] = cv2.GaussianBlur(img[horizon - 20:horizon + 20], (0, 0), 8)[17:23]   # linha do fundo infinito suave
    return finish(img, rng, vignette=0.35, grain=2.5, blur=1.5)


def runway(h: int, w: int, rng) -> np.ndarray:
    img = vgrad(h, w, bgr(14, 10, 26), bgr(30, 20, 44))
    # cones de luz do teto
    cones = np.zeros_like(img)
    for cx in (0.18, 0.5, 0.82):
        pts = np.array([[cx * w - 25, 0], [cx * w + 25, 0], [cx * w + 0.16 * w, 0.75 * h], [cx * w - 0.16 * w, 0.75 * h]], np.int32)
        cv2.fillPoly(cones, [pts], (255.0 * 0.20, 240.0 * 0.20, 215.0 * 0.20))
    img += cv2.GaussianBlur(cones, (0, 0), 38)
    # passarela: trapézio brilhante e reflexo
    floor = np.zeros_like(img)
    poly = np.array([[0.40 * w, 0.58 * h], [0.60 * w, 0.58 * h], [0.94 * w, h], [0.06 * w, h]], np.int32)
    cv2.fillPoly(floor, [poly], (130, 120, 118))
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    floor *= 0.35 + 0.75 * np.clip((ys - 0.58) / 0.42, 0, 1)
    img = np.where(floor > 0, floor, img)
    cv2.line(img, (int(0.5 * w), int(0.58 * h)), (int(0.5 * w), h), (200, 200, 205), 3, cv2.LINE_AA)
    for a, b in (((0.40, 0.58), (0.06, 1.0)), ((0.60, 0.58), (0.94, 1.0))):
        cv2.line(img, (int(a[0] * w), int(a[1] * h)), (int(b[0] * w), int(b[1] * h)), (255, 235, 200), 5, cv2.LINE_AA)
    warm, cool = bgr(255, 200, 120), bgr(140, 170, 255)
    img += bokeh(img.shape, rng, 70, (0.12, 0.55), (10, 30), [warm, cool, bgr(255, 120, 160)], 0.45)
    glow(img, w * 0.5, h * 0.6, w * 0.3, bgr(255, 235, 210), 0.25)
    return finish(img, rng, vignette=0.4, grain=3.0, blur=2.0)


def store(h: int, w: int, rng) -> np.ndarray:
    img = vgrad(h, w, bgr(226, 210, 184), bgr(200, 178, 148))
    palette = [bgr(240, 240, 238), bgr(30, 50, 100), bgr(170, 40, 45), bgr(214, 196, 160), bgr(96, 110, 70),
               bgr(90, 120, 165), bgr(40, 40, 44), bgr(210, 150, 60)]
    for k, y in enumerate((0.30, 0.52, 0.74)):
        board_y = int(y * h)
        x = int(0.03 * w)
        while x < 0.97 * w:
            bw = int(rng.uniform(95, 150))
            color = palette[rng.integers(len(palette))]
            layers = int(rng.integers(3, 7))
            for i in range(layers):
                shade = color * (0.85 + 0.15 * (i % 2))
                y0 = board_y - (i + 1) * 26
                cv2.rectangle(img, (x, y0), (x + bw, y0 + 24), tuple(float(v) for v in shade), -1)
                cv2.line(img, (x, y0 + 24), (x + bw, y0 + 24), tuple(float(v) * 0.6 for v in shade), 2)
            x += bw + int(rng.uniform(14, 40))
        cv2.rectangle(img, (0, board_y), (w, board_y + 16), (55, 82, 112), -1)
        cv2.rectangle(img, (0, board_y + 16), (w, board_y + 22), (35, 52, 78), -1)
    img[int(0.9 * h):] = vgrad(h - int(0.9 * h), w, bgr(120, 84, 56), bgr(80, 54, 36))
    img += bokeh(img.shape, rng, 26, (0.02, 0.14), (16, 34), [bgr(255, 226, 170), bgr(255, 240, 210)], 0.5)
    glow(img, w * 0.5, h * 0.05, w * 0.5, bgr(255, 236, 200), 0.18)
    return finish(img, rng, vignette=0.3, grain=2.5, blur=7.0)          # desfoque de profundidade de campo


def sunset(h: int, w: int, rng) -> np.ndarray:
    horizon = int(h * 0.68)
    img = np.zeros((h, w, 3), np.float32)
    img[:horizon] = vgrad(horizon, w, bgr(62, 44, 120), bgr(252, 158, 96))
    glow(img, w * 0.72, horizon, w * 0.32, bgr(255, 190, 110), 0.55)
    for layer, (color, top, bottom) in enumerate(((bgr(92, 66, 118), 0.30, 0.16), (bgr(30, 24, 52), 0.42, 0.20))):
        x = -40
        while x < w:
            bw = int(rng.uniform(60, 170))
            bh = int(rng.uniform(bottom, top) * h * (0.9 + 0.3 * layer))
            cv2.rectangle(img, (x, horizon - bh), (x + bw, horizon + 2), tuple(float(v) for v in color), -1)
            if layer == 1:
                for wy in range(horizon - bh + 14, horizon - 6, 26):
                    for wx in range(x + 10, x + bw - 12, 22):
                        if rng.random() < 0.28:
                            cv2.rectangle(img, (wx, wy), (wx + 9, wy + 13), (120.0, 205.0, 255.0), -1)
            x += bw + int(rng.uniform(-10, 14))
    img[horizon:] = vgrad(h - horizon, w, bgr(22, 18, 40), bgr(12, 10, 26))
    return finish(img, rng, vignette=0.3, grain=3.0, blur=2.5)


SCENES = [
    ("estudio", "Estudio", 0.25, studio),
    ("passarela", "Passarela", 0.35, runway),
    ("loja", "Loja", 0.30, store),
    ("cidade_entardecer", "Cidade ao entardecer", 0.30, sunset),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--out", default=str(paths.BACKGROUNDS))
    args = ap.parse_args()
    w = args.width
    h = round(w * 9 / 16)
    for k, (slug, name, color_match, fn) in enumerate(SCENES):
        folder = Path(args.out) / slug
        folder.mkdir(parents=True, exist_ok=True)
        img = fn(h, w, np.random.default_rng(100 + k))
        cv2.imwrite(str(folder / "background.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        (folder / "meta.json").write_text(json.dumps({"name": name, "type": "image", "color_match": color_match},
                                                     indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{folder / 'background.jpg'} ({(folder / 'background.jpg').stat().st_size / 1e3:.0f} kB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
