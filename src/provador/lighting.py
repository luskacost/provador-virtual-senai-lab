"""Estimativa de luz do ambiente a partir da própria pessoa (harmônicos esféricos de ordem 2).

Ideia: a pele visível tem normais que conhecemos aproximadamente. O rosto é uma esfera (centro e raio pelos
landmarks das orelhas/olhos) e cada braço é um cilindro (eixo ombro→cotovelo→pulso). Cada pixel de pele
(escolhido pela máscara da segmentação) vira uma amostra (normal, luminância) e um ajuste por mínimos
quadrados regularizado dá a "forma" da irradiância E(n) em SH9. Só o hemisfério voltado à câmera é
observado, então o ajuste é puxado para uma luz padrão (prior) nos termos mal determinados.

- Forma: SH9 da luminância normalizada (média 1) → direção e contraste da luz.
- Exposição: luminância média do quadro (independe do tom de pele), suavizada.
- Balanço de branco: cromaticidade da pele contra uma pele nominal, com força limitada (`wb_strength`),
  porque o tom de pele varia entre pessoas. É uma heurística e tem chave para ligar/desligar (tecla L).
Tudo em numpy, em espaço linear, a ~10 Hz sobre a máscara 256x256 (custo ~1 ms).
"""

from dataclasses import dataclass, field

import numpy as np

# Base real de SH até l=2, na ordem [1, y, z, x, xy, yz, 3z²-1, xz, x²-y²] (a mesma do shader, sh.glsl)
SH_CONST = np.array([0.282095, 0.488603, 0.488603, 0.488603, 1.092548, 1.092548, 0.315392, 1.092548, 0.546274])
SH_LEVEL = np.array([0, 1, 1, 1, 2, 2, 2, 2, 2])

# Luz padrão (prior): ambiente com um pouco de luz de cima e da frente. E(n) = 1 + 0.25 y + 0.25 z
PRIOR_SH = np.array([1.0 / SH_CONST[0], 0.25 / SH_CONST[1], 0.25 / SH_CONST[2], 0, 0, 0, 0, 0, 0])

LUMA = np.array([0.2126, 0.7152, 0.0722])
NOMINAL_SKIN_SRGB = np.array([198.0, 150.0, 128.0]) / 255.0
FRAME_REF_LIN = 0.22          # luminância linear média de um quadro "bem exposto"
EXPOSURE_RANGE = (0.45, 1.8)
EXPOSURE_POWER = 0.6          # amortece: a câmera já compensa parte da variação
TINT_RANGE = (0.75, 1.3)
MIN_SAMPLES = 150
MASK_SIZE = 256
RIDGE = np.array([0.002, 0.008, 0.008, 0.008, 0.25, 0.25, 0.25, 0.25, 0.25])   # relativo ao nº de amostras
# l=0,1 (ambiente e direção) são bem observados na metade voltada à câmera; l=2 quase não é: fica contido.

# Landmarks do MediaPipe Pose
NOSE, L_EYE_OUT, R_EYE_OUT, L_EAR, R_EAR = 0, 3, 6, 7, 8
ARM_SEGMENTS = ((11, 13), (13, 15), (12, 14), (14, 16))


def sh_basis(n: np.ndarray) -> np.ndarray:
    """(N, 3) normais unitárias (x, y, z) → (N, 9) base de SH."""
    x, y, z = n[:, 0], n[:, 1], n[:, 2]
    b = np.stack([np.ones_like(x), y, z, x, x * y, y * z, 3 * z * z - 1, x * z, x * x - y * y], axis=1)
    return b * SH_CONST


def srgb_to_linear(u8: np.ndarray) -> np.ndarray:
    c = u8.astype(np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


@dataclass(frozen=True)
class Light:
    sh: np.ndarray                       # (9,) forma da irradiância (média ~1 sobre a pele visível)
    exposure: float = 1.0
    tint: np.ndarray = field(default_factory=lambda: np.ones(3))
    n_samples: int = 0

    def eval(self, n: np.ndarray) -> np.ndarray:
        """Irradiância relativa (forma × exposição) para normais (N, 3)."""
        return sh_basis(n) @ self.sh * self.exposure

    @property
    def direction(self) -> np.ndarray:
        """Direção dominante da luz no espaço da câmera (x direita, y cima, z para a câmera) e sua força."""
        v = np.array([self.sh[3], self.sh[1], self.sh[2]]) * SH_CONST[1]
        n = np.linalg.norm(v)
        return v / n if n > 1e-9 else np.array([0.0, 0.0, 1.0])

    @property
    def contrast(self) -> float:
        """Quanto a luz é direcional (0 = totalmente difusa)."""
        ambient = self.sh[0] * SH_CONST[0]
        return float(np.linalg.norm(np.array([self.sh[3], self.sh[1], self.sh[2]]) * SH_CONST[1]) / max(ambient, 1e-6))


DEFAULT_LIGHT = Light(sh=PRIOR_SH)


def skin_samples(mask: np.ndarray, px: np.ndarray, vis: np.ndarray, image_size: tuple[int, int],
                 vis_min: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    """Coordenadas (N, 2, em pixels da máscara: x, y) e normais (N, 3) das amostras de pele.

    mask: (256, 256, 4) uint8 (R pele do corpo, G cabelo, B rosto, A pessoa). px: (33, ≥2) pixels da imagem.
    Normais no espaço da câmera: x direita, y cima, z para a câmera.
    """
    w, h = image_size
    p = px[:, :2] * np.array([MASK_SIZE / w, MASK_SIZE / h])
    skin = np.maximum(mask[..., 0], mask[..., 2]) >= 128
    not_hair = mask[..., 1] < 80
    valid = skin & not_hair
    coords, normals = [], []

    def add(xs: np.ndarray, ys: np.ndarray, n: np.ndarray) -> None:
        keep = valid[ys, xs]
        coords.append(np.stack([xs[keep], ys[keep]], 1))
        normals.append(n[keep])

    # Rosto: esfera
    if min(vis[L_EAR], vis[R_EAR]) >= vis_min or min(vis[L_EYE_OUT], vis[R_EYE_OUT]) >= vis_min:
        center = p[:9].mean(axis=0)
        r = max(np.linalg.norm(p[L_EAR] - p[R_EAR]) / 2.0, np.linalg.norm(p[L_EYE_OUT] - p[R_EYE_OUT]) * 1.3)
        if r >= 4:
            x0, x1 = int(max(center[0] - r, 0)), int(min(center[0] + r, MASK_SIZE - 1))
            y0, y1 = int(max(center[1] - r, 0)), int(min(center[1] + r, MASK_SIZE - 1))
            if x1 > x0 and y1 > y0:
                ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
                xs, ys = xs.ravel(), ys.ravel()
                dx, dy = (xs - center[0]) / r, (ys - center[1]) / r
                inside = dx * dx + dy * dy < 0.85
                xs, ys, dx, dy = xs[inside], ys[inside], dx[inside], dy[inside]
                add(xs, ys, np.stack([dx, -dy, np.sqrt(np.clip(1 - dx * dx - dy * dy, 0, 1))], 1))

    # Braços: cilindros
    for a_i, b_i in ARM_SEGMENTS:
        if min(vis[a_i], vis[b_i]) < vis_min:
            continue
        a, b = p[a_i], p[b_i]
        length = np.linalg.norm(b - a)
        if length < 12:
            continue
        u = (b - a) / length
        perp = np.array([-u[1], u[0]])
        r = float(np.clip(0.16 * length, 4, 30))
        lo = np.floor(np.minimum(a, b) - r).clip(0, MASK_SIZE - 1).astype(int)
        hi = np.ceil(np.maximum(a, b) + r).clip(0, MASK_SIZE - 1).astype(int)
        ys, xs = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
        xs, ys = xs.ravel(), ys.ravel()
        rel = np.stack([xs, ys], 1) - a
        s = rel @ u / length
        t = (rel @ perp) / r
        inside = (s > 0.1) & (s < 0.9) & (np.abs(t) < 0.9)
        xs, ys, t = xs[inside], ys[inside], t[inside]
        nxy = t[:, None] * np.array([perp[0], -perp[1]])            # y da imagem cresce para baixo
        add(xs, ys, np.column_stack([nxy, np.sqrt(np.clip(1 - t * t, 0, 1))]))

    if not coords:
        return np.zeros((0, 2), int), np.zeros((0, 3))
    return np.concatenate(coords), np.concatenate(normals)


def fit_sh(normals: np.ndarray, luminance: np.ndarray, prior: np.ndarray = PRIOR_SH) -> np.ndarray:
    """SH9 da luminância relativa (média 1) por mínimos quadrados regularizados em direção ao prior."""
    y = sh_basis(normals)
    target = luminance / max(luminance.mean(), 1e-6)
    lam = RIDGE * len(normals)
    a = y.T @ y + np.diag(lam)
    rhs = y.T @ target + lam * prior
    return np.linalg.solve(a, rhs)


class LightEstimator:
    def __init__(self, wb_strength: float = 0.35, smoothing: float = 0.2):
        self.wb_strength = wb_strength
        self.smoothing = smoothing              # peso da estimativa nova (10 Hz → constante de tempo ~0,5 s)
        self.light = DEFAULT_LIGHT
        self._nominal_chroma = self._chroma(srgb_to_linear(NOMINAL_SKIN_SRGB * 255.0))

    @staticmethod
    def _chroma(rgb_lin: np.ndarray) -> np.ndarray:
        return rgb_lin / max(float(rgb_lin @ LUMA), 1e-6)

    def reset(self) -> None:
        self.light = DEFAULT_LIGHT

    def update(self, frame_small_bgr: np.ndarray, mask: np.ndarray, px: np.ndarray, vis: np.ndarray,
               image_size: tuple[int, int]) -> Light:
        """frame_small_bgr: o quadro reduzido para 256x256 (uint8 BGR, sem espelho). Devolve a luz suavizada;
        sem amostras suficientes, mantém a anterior."""
        coords, normals = skin_samples(mask, px, vis, image_size)
        if len(normals) < MIN_SAMPLES:
            return self.light
        rgb_lin = srgb_to_linear(frame_small_bgr[coords[:, 1], coords[:, 0], ::-1])
        lum = rgb_lin @ LUMA
        if lum.mean() < 1e-3:
            return self.light
        sh_new = fit_sh(normals, lum)

        frame_lin = srgb_to_linear(frame_small_bgr[::4, ::4, ::-1]) @ LUMA
        exposure = float(np.clip((frame_lin.mean() / FRAME_REF_LIN) ** EXPOSURE_POWER, *EXPOSURE_RANGE))

        tint = (self._chroma(rgb_lin.mean(axis=0)) / self._nominal_chroma) ** self.wb_strength
        tint = np.clip(tint / max(float(tint @ LUMA), 1e-6), *TINT_RANGE)

        k = self.smoothing
        old = self.light
        self.light = Light(sh=(1 - k) * old.sh + k * sh_new, exposure=(1 - k) * old.exposure + k * exposure,
                           tint=(1 - k) * old.tint + k * tint, n_samples=len(normals))
        return self.light
