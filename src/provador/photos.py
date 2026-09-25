"""T9: da foto de uma peça para a textura (atlas UV) do template.

Fluxo: recorte da peça do fundo liso → análise da silhueta (tronco × mangas) → "achatar" a foto no molde do
template (tronco por linhas, mangas por retângulo alinhado ao eixo raiz→barra) → atlas com a frente na metade
esquerda e as costas na direita, como o UV planar de template.py.

As vistas laterais da folha (mangas de lado) são reconhecidas mas ainda não usadas.
"""

from dataclasses import dataclass, field

import cv2
import numpy as np

from . import template as tpl

BG_TOL = 6.0                       # distância Lab mínima ao fundo para contar como peça
ERODE_PX = 2                       # tira a franja de mistura com o fundo nas bordas antes de amostrar
MIN_VIEW_AREA = 0.01               # fração da folha para um componente contar como vista
SPLIT_GAP_PX = 3                   # vão mínimo (px) numa linha para dois trechos contarem como separados
ARMPIT_MARGIN = 10                 # linhas abaixo da axila onde a borda do tronco já é confiável
DEFAULT_VIEW_NAMES = ("frente", "costas", "lado_esquerdo", "lado_direito")


# --- recorte -----------------------------------------------------------------------------------
def background_lab(img_bgr: np.ndarray) -> np.ndarray:
    """Cor do fundo (Lab), pela mediana das bordas da imagem."""
    border = np.concatenate([img_bgr[0], img_bgr[-1], img_bgr[:, 0], img_bgr[:, -1]])
    return cv2.cvtColor(np.median(border, axis=0).astype(np.uint8)[None, None], cv2.COLOR_BGR2LAB)[0, 0].astype(np.float32)


def garment_mask(img_bgr: np.ndarray, tol: float = BG_TOL) -> np.ndarray:
    """Máscara bool da peça (tudo que difere do fundo), sem buracos internos."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    m = (np.linalg.norm(lab - background_lab(img_bgr), axis=2) > tol).astype(np.uint8)
    # Sem fechamento morfológico: ele preencheria com fundo as fendas estreitas da axila. Os buracos
    # internos (fundo cercado pela peça) já são tratados pelo floodFill abaixo.
    flood = m.copy()
    h, w = m.shape
    cv2.floodFill(flood, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 2)     # fundo alcançável a partir da borda
    return (m == 1) | (flood == 0)                                          # peça + buracos internos


@dataclass
class View:
    name: str
    bbox: tuple[int, int, int, int]        # x, y, largura, altura na folha
    rgb: np.ndarray                        # recorte BGR (o nome é histórico: é BGR do OpenCV)
    mask: np.ndarray                       # bool, mesmo tamanho do recorte


def split_views(img_bgr: np.ndarray, names=DEFAULT_VIEW_NAMES, pad: int = 4) -> list[View]:
    """Separa as vistas de uma folha (componentes conexos, da esquerda para a direita) e as nomeia."""
    mask = garment_mask(img_bgr)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    min_area = MIN_VIEW_AREA * mask.size
    comps = sorted((i for i in range(1, n) if stats[i][4] >= min_area), key=lambda i: stats[i][0])
    if not comps:
        raise ValueError("nenhuma peça encontrada na imagem (o fundo precisa ser liso e diferente da peça)")
    views = []
    h_img, w_img = mask.shape
    for k, i in enumerate(comps):
        x, y, w, h, _ = stats[i]
        x0, y0, x1, y1 = max(x - pad, 0), max(y - pad, 0), min(x + w + pad, w_img), min(y + h + pad, h_img)
        views.append(View(names[k] if k < len(names) else f"vista{k + 1}", (int(x0), int(y0), int(x1 - x0), int(y1 - y0)),
                          img_bgr[y0:y1, x0:x1].copy(), (labels[y0:y1, x0:x1] == i)))
    return views


def fill_outside(img_bgr: np.ndarray, mask: np.ndarray, erode: int = ERODE_PX) -> tuple[np.ndarray, np.ndarray]:
    """Erode a máscara (tira a franja do fundo) e preenche tudo fora dela com a cor da peça mais próxima.
    Devolve (imagem preenchida, máscara erodida)."""
    core = cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=erode) if erode else mask.astype(np.uint8)
    if not core.any():
        core = mask.astype(np.uint8)
    return nearest_fill(img_bgr, core.astype(bool)), core.astype(bool)


def nearest_fill(img: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Cada pixel inválido recebe o valor do pixel válido mais próximo."""
    if valid.all():
        return img.copy()
    src = np.where(valid, 0, 255).astype(np.uint8)                          # zeros = pixels válidos
    _, labels = cv2.distanceTransformWithLabels(src, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(valid)                                              # rótulos seguem a ordem raster dos zeros
    lookup = np.zeros((len(ys) + 1, 2), np.int32)
    lookup[1:, 0], lookup[1:, 1] = ys, xs
    yy, xx = lookup[labels, 0], lookup[labels, 1]
    return img[yy, xx]


# --- análise da silhueta ------------------------------------------------------------------------
@dataclass
class SleeveFit:
    origin: np.ndarray        # ponto de contato com o tronco (x, y na vista)
    axis: np.ndarray          # unitário, da raiz para a barra
    up: np.ndarray            # unitário, perpendicular, apontando para cima na imagem
    s_range: tuple[float, float]
    t_range: tuple[float, float]

    def point(self, s: np.ndarray, t: np.ndarray) -> np.ndarray:
        """Ponto da foto para (s, t) ∈ [0,1]²: s da raiz à barra, t de baixo para cima. Formato (..., 2)."""
        ds = self.s_range[0] + s * (self.s_range[1] - self.s_range[0])
        dt = self.t_range[0] + t * (self.t_range[1] - self.t_range[0])
        return self.origin + ds[..., None] * self.axis + dt[..., None] * self.up


@dataclass
class ViewAnalysis:
    top: int
    bottom: int
    body_left: np.ndarray          # (h,) borda esquerda do tronco por linha (NaN fora da silhueta)
    body_right: np.ndarray
    armpit_row: int
    sleeves: dict[str, SleeveFit] = field(default_factory=dict)      # "left"/"right" = lado da IMAGEM


def _segments(row: np.ndarray, gap: int = SPLIT_GAP_PX) -> list[tuple[int, int]]:
    cols = np.flatnonzero(row)
    if cols.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(cols) > gap) + 1
    return [(int(s[0]), int(s[-1])) for s in np.split(cols, breaks)]


def _smooth(v: np.ndarray, k: int = 9) -> np.ndarray:
    """Mediana + média móvel, ignorando NaN nas pontas (interpola)."""
    ok = ~np.isnan(v)
    if ok.sum() < 3:
        return v
    x = np.arange(len(v))
    filled = np.interp(x, x[ok], v[ok])
    med = cv2.medianBlur(filled.astype(np.float32).reshape(-1, 1), 5 if k >= 5 else 3).ravel()
    ker = np.ones(k) / k
    pad = np.pad(med, k // 2, mode="edge")
    out = np.convolve(pad, ker, mode="valid")
    out[~ok] = np.nan
    return out


def analyze_view(mask: np.ndarray) -> ViewAnalysis:
    """Acha a axila, as bordas do tronco e o eixo de cada manga numa vista frontal ou traseira."""
    h, w = mask.shape
    rows = np.flatnonzero(mask.any(axis=1))
    top, bottom = int(rows[0]), int(rows[-1])
    segs = [_segments(mask[r]) for r in range(h)]

    # Axila: primeira linha (abaixo de 15% da altura) em que a manga se separa do tronco
    armpit = next((r for r in range(top + int(0.15 * (bottom - top)), bottom) if len(segs[r]) >= 3), None)
    sleeves_detached = armpit is not None
    if armpit is None:                                     # manga colada ao tronco (ou sem manga): estima
        armpit = top + int(0.42 * (bottom - top))

    left = np.full(h, np.nan)
    right = np.full(h, np.nan)
    for r in range(top, bottom + 1):
        if not segs[r]:
            continue
        if r >= armpit + ARMPIT_MARGIN or not sleeves_detached:
            body = max(segs[r], key=lambda s: s[1] - s[0]) if r >= armpit else None
        else:
            body = None
        if body is not None:
            left[r], right[r] = body[0], body[1]
    ref = slice(armpit + ARMPIT_MARGIN, min(armpit + ARMPIT_MARGIN + 25, bottom))
    xl0 = float(np.nanmedian(left[ref])) if not np.isnan(left[ref]).all() else float(np.nanmin(left))
    xr0 = float(np.nanmedian(right[ref])) if not np.isnan(right[ref]).all() else float(np.nanmax(right))
    for r in range(top, armpit + ARMPIT_MARGIN):           # acima da axila: silhueta cortada nas colunas do tronco
        if segs[r]:
            left[r] = max(segs[r][0][0], xl0)
            right[r] = min(segs[r][-1][1], xr0)
    analysis = ViewAnalysis(top, bottom, _smooth(left), _smooth(right), armpit)

    cols = np.arange(w)[None, :]
    body_l = np.where(np.isnan(left), np.inf, left)[:, None]
    body_r = np.where(np.isnan(right), -np.inf, right)[:, None]
    for side, region, contact_x, direction in (("left", mask & (cols < body_l - 1), xl0, -1.0),
                                               ("right", mask & (cols > body_r + 1), xr0, 1.0)):
        region = region.copy()
        region[armpit + int(0.35 * (bottom - armpit)):] = False        # a manga não desce abaixo disso
        n, labels, stats, _ = cv2.connectedComponentsWithStats(region.astype(np.uint8))
        if n < 2:
            continue
        region = labels == 1 + int(np.argmax(stats[1:, 4]))
        analysis.sleeves[side] = _fit_sleeve(region, contact_x, direction)
    return analysis


def _fit_sleeve(region: np.ndarray, contact_x: float, direction: float) -> SleeveFit:
    ys, xs = np.nonzero(region)
    pts = np.stack([xs, ys], 1).astype(np.float64)
    near = np.abs(pts[:, 0] - contact_x) <= 3                        # pixels encostados na linha do tronco
    contact = pts[near] if near.any() else pts[np.argsort(np.abs(pts[:, 0] - contact_x))[:20]]
    origin = np.array([contact_x, (contact[:, 1].min() + contact[:, 1].max()) / 2.0])
    dist = np.linalg.norm(pts - origin, axis=1)
    tip = pts[dist >= np.percentile(dist, 90)].mean(axis=0)
    axis = (tip - origin) / max(np.linalg.norm(tip - origin), 1e-6)
    if axis[0] * direction < 0:
        axis = np.array([-axis[0], axis[1]])
    up = np.array([-axis[1], axis[0]])
    if up[1] > 0:
        up = -up
    rel = pts - origin
    s, t = rel @ axis, rel @ up
    return SleeveFit(origin, axis, up, (float(s.min()), float(s.max())), (float(t.min()), float(t.max())))


# --- geometria do template no espaço da vista ---------------------------------------------------
@dataclass
class TemplateGeometry:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    ring_y: np.ndarray             # do barrado à gola (crescente)
    ring_half_width: np.ndarray
    sleeve_start: float
    sleeve_end: float
    sleeve_cy: float
    sleeve_radius: tuple[float, float]


def template_geometry(mesh: tpl.Mesh3D, sleeve_end: float, hem: float) -> TemplateGeometry:
    """Medidas do template (as mesmas que geraram a malha); as extensões do UV vêm dos vértices."""
    pos = mesh.positions
    ys = np.array([r[0] for r in tpl.TORSO_RINGS])
    ys[0] = hem
    return TemplateGeometry(float(pos[:, 0].min()), float(pos[:, 0].max()), float(pos[:, 1].min()),
                            float(pos[:, 1].max()), ys, np.array([r[1] for r in tpl.TORSO_RINGS]),
                            tpl.SLEEVE_X[0], sleeve_end, tpl.SLEEVE_CENTER_Y, tpl.SLEEVE_RADIUS)


# --- achatar a foto no molde ---------------------------------------------------------------------
def flatten_view(photo_bgr: np.ndarray, mask: np.ndarray, geo: TemplateGeometry, width: int, height: int
                 ) -> tuple[np.ndarray, np.ndarray]:
    """Metade do atlas (height × width): a foto deformada para o molde. Devolve (imagem BGR, cobertura bool).

    O molde é a vista frontal ortográfica do template: x de x_min a x_max (esquerda → direita da imagem) e
    y de y_max (topo) a y_min. Frente e costas usam a mesma função (a vista de trás já é "vista por trás").
    """
    filled, core = fill_outside(photo_bgr, mask)
    an = analyze_view(core)

    xs = geo.x_min + (np.arange(width) + 0.5) / width * (geo.x_max - geo.x_min)
    ys = geo.y_max - (np.arange(height) + 0.5) / height * (geo.y_max - geo.y_min)
    map_x = np.zeros((height, width), np.float32)
    map_y = np.zeros((height, width), np.float32)
    cover = np.zeros((height, width), bool)

    # Tronco: cada linha do molde estica sobre a linha correspondente do tronco na foto
    top_y, hem_y = float(geo.ring_y[-1]), float(geo.ring_y[0])
    a_y = np.interp(ys, geo.ring_y, geo.ring_half_width)
    torso_rows = (ys >= hem_y) & (ys <= top_y)
    v_n = np.clip((top_y - ys) / (top_y - hem_y), 0.0, 1.0)
    photo_row = an.top + v_n * (an.bottom - an.top)
    r_idx = np.arange(len(an.body_left))
    bl = np.interp(photo_row, r_idx, np.where(np.isnan(an.body_left), np.nanmean(an.body_left), an.body_left))
    br = np.interp(photo_row, r_idx, np.where(np.isnan(an.body_right), np.nanmean(an.body_right), an.body_right))
    scale = (br - bl) / np.maximum(2.0 * a_y, 1e-6)                      # px da foto por metro do molde
    map_x[:] = ((bl + br) / 2.0)[:, None] + xs[None, :] * scale[:, None]
    map_y[:] = photo_row[:, None]
    cover |= torso_rows[:, None] & (np.abs(xs)[None, :] <= a_y[:, None])

    # Mangas: (s, t) do tubo do template → retângulo da manga na foto (lado da imagem = sinal de x da vista)
    for side, sign in (("right", 1.0), ("left", -1.0)):
        fit = an.sleeves.get(side)
        if fit is None:
            continue
        s = (np.abs(xs) - geo.sleeve_start) / (geo.sleeve_end - geo.sleeve_start)
        radius = geo.sleeve_radius[0] + np.clip(s, 0, 1) * (geo.sleeve_radius[1] - geo.sleeve_radius[0])
        t = (ys[:, None] - (geo.sleeve_cy - radius[None, :])) / (2.0 * radius[None, :])
        region = (xs * sign > 0)[None, :] & (s[None, :] >= 0) & (s[None, :] <= 1) & (t >= 0) & (t <= 1)
        region &= ~cover                                                 # o tronco tem prioridade na sobreposição
        pts = fit.point(np.broadcast_to(s[None, :], t.shape), t)
        map_x[region], map_y[region] = pts[..., 0][region], pts[..., 1][region]
        cover |= region

    flat = cv2.remap(filled, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return nearest_fill(flat, cover), cover


def build_atlas(front: View, back: View, mesh: tpl.Mesh3D, sleeve_end: float, hem: float,
                size: int = 1024) -> tuple[np.ndarray, dict]:
    """Atlas (size/2 × size, BGR): frente na metade esquerda, costas na direita. Devolve (imagem, info)."""
    geo = template_geometry(mesh, sleeve_end, hem)
    half_w = size // 2
    half_h = round(half_w * (geo.y_max - geo.y_min) / (geo.x_max - geo.x_min) * 1.15)   # texel um pouco mais fino em y
    f_img, f_cov = flatten_view(front.rgb, front.mask, geo, half_w, half_h)
    b_img, b_cov = flatten_view(back.rgb, back.mask, geo, half_w, half_h)
    info = {"atlas_px": [size, half_h], "front_sleeves": sorted(analyze_view(fill_outside(front.rgb, front.mask)[1]).sleeves),
            "back_sleeves": sorted(analyze_view(fill_outside(back.rgb, back.mask)[1]).sleeves),
            "front_coverage": float(f_cov.mean()), "back_coverage": float(b_cov.mean())}
    return np.hstack([f_img, b_img]), info
