"""Retarget: landmarks do MediaPipe → matrizes dos ossos da peça no espaço da câmera.

Ideia: o 2D precisa bater com o vídeo, então cada articulação é colocada exatamente sobre o landmark
desprojetado (pixel + profundidade). A profundidade vem de ajustar o esqueleto métrico do MediaPipe
(world landmarks, em metros) aos pixels. As rotações saem de frames do tronco (peito e quadril separados,
o que dá a torção) e de "swing" mínimo para clavícula, braço e antebraço. A escala vem da largura dos
ombros e do comprimento do tronco.

Convenções: câmera do OpenGL (camera.py). World landmarks do MediaPipe: origem no centro do quadril,
x para a direita da imagem, y para baixo, z maior = mais longe → no espaço da câmera: (x, -y, -z).
O landmark "left" do MediaPipe é o lado esquerdo da PESSOA, que é o +X do esqueleto padrão.
"""

from dataclasses import dataclass

import numpy as np

from . import skeleton as sk
from .camera import focal_px, perspective, project, unproject

# Landmarks do MediaPipe Pose
L_SH, R_SH, L_EL, R_EL, L_WR, R_WR, L_HIP, R_HIP = 11, 12, 13, 14, 15, 16, 23, 24

# Medidas do esqueleto padrão (skeleton.py)
_HIPS_Y = sk.REST_WORLD[sk.INDEX["hips"]][1]
_SHOULDER_Y = sk.REST_WORLD[sk.INDEX["L_upper_arm"]][1]
TEMPLATE_TORSO = _SHOULDER_Y - _HIPS_Y                                   # 0,45 m
TEMPLATE_SHOULDERS = 2.0 * sk.REST_WORLD[sk.INDEX["L_upper_arm"]][0]     # 0,38 m
_CLAV_FRAC = sk.REST_WORLD[sk.INDEX["L_clavicle"]][0] / sk.REST_WORLD[sk.INDEX["L_upper_arm"]][0]

SCALE_RANGE = (0.6, 1.6)
ASPECT_RANGE = (0.75, 1.35)      # altura/largura do tronco em relação ao template
MAX_TWIST_DEG = 40.0             # torção peito × quadril (a meta é ±30°)
HIP_VIS_MIN = 0.5                # abaixo disso o quadril (fora do quadro) não entra no ajuste de profundidade

# Pares (osso da peça, landmark) usados na métrica de alinhamento
ERROR_PAIRS = [("L_upper_arm", L_SH), ("R_upper_arm", R_SH), ("L_forearm", L_EL), ("R_forearm", R_EL),
               ("L_hand", L_WR), ("R_hand", R_WR)]


@dataclass(frozen=True)
class Retarget:
    skin: np.ndarray          # (N, 4, 4) matrizes de skinning (mundo × inversa do bind), espaço da câmera
    world: np.ndarray         # (N, 4, 4) matrizes de mundo dos ossos
    depth: float              # distância do quadril à câmera (m)
    scale: tuple[float, float]  # (largura, altura) do tronco relativas ao template
    yaw_deg: float            # giro do peito em torno do eixo vertical (0 = de frente)
    twist_deg: float          # torção peito × quadril
    points: np.ndarray        # (33, 3) landmarks no espaço da câmera (para a oclusão)


def _norm(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def rotation_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Menor rotação 3x3 que leva a direção a na direção b."""
    a, b = _norm(a), _norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if c < -0.999999:                                  # opostos: 180° em torno de um eixo perpendicular
        axis = _norm(np.cross(a, [1.0, 0, 0]) if abs(a[0]) < 0.9 else np.cross(a, [0, 1.0, 0]))
        return 2.0 * np.outer(axis, axis) - np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1.0 + c)


def _yaw_deg(x_axis: np.ndarray) -> float:
    """Giro em torno do Y da câmera, medido pelo eixo +X do corpo (0 = de frente para a câmera)."""
    return float(np.degrees(np.arctan2(-x_axis[2], x_axis[0])))


def _rot_y(deg: float) -> np.ndarray:
    return sk.rotation_axis_angle((0, 1, 0), deg)


def mp_world_to_camera(world: np.ndarray) -> np.ndarray:
    return world * np.array([1.0, -1.0, -1.0])


def estimate_depth(px: np.ndarray, world: np.ndarray, vis: np.ndarray, hfov: float,
                   size: tuple[int, int], iters: int = 6) -> float:
    """Distância do centro do quadril que faz o esqueleto métrico, projetado, ter o tamanho observado."""
    w, h = size
    idx = [L_SH, R_SH] + ([L_HIP, R_HIP] if min(vis[L_HIP], vis[R_HIP]) >= HIP_VIS_MIN else [])
    if len(idx) == 2:
        idx += [L_EL, R_EL] if min(vis[L_EL], vis[R_EL]) >= HIP_VIS_MIN else []
    obs = px[idx, :2]
    spread_obs = np.linalg.norm(obs - obs.mean(0), axis=1).sum()
    offsets = mp_world_to_camera(world[idx])
    hip_px = (px[L_HIP, :2] + px[R_HIP, :2]) / 2.0
    proj = perspective(hfov, w / h)
    # chute inicial pela largura dos ombros
    f = focal_px(hfov, w)
    sh_perp = np.linalg.norm((world[L_SH] - world[R_SH])[:2])
    depth = float(np.clip(f * sh_perp / max(np.linalg.norm(px[L_SH, :2] - px[R_SH, :2]), 1.0), 0.3, 10.0))
    for _ in range(iters):
        root = unproject(hip_px[None], np.array([depth]), hfov, w, h)[0]
        pts = project(root + offsets, proj, w, h)
        spread = np.linalg.norm(pts - pts.mean(0), axis=1).sum()
        if spread <= 1e-6:
            break
        depth = float(np.clip(depth * spread / spread_obs, 0.3, 10.0))
    return depth


def retarget(px: np.ndarray, world: np.ndarray, vis: np.ndarray, image_size: tuple[int, int],
             hfov: float) -> Retarget:
    """px: (33, ≥2) pixels da imagem crua; world: (33, 3) world landmarks (m); vis: (33,)."""
    w, h = image_size
    depth = estimate_depth(px, world, vis, hfov, image_size)
    # profundidade por landmark: a do quadril + o z métrico relativo ao quadril
    hip_world_z = (world[L_HIP, 2] + world[R_HIP, 2]) / 2.0
    P = unproject(px[:, :2].astype(np.float64), depth + (world[:, 2] - hip_world_z), hfov, w, h)

    sh_mid, hip_mid = (P[L_SH] + P[R_SH]) / 2.0, (P[L_HIP] + P[R_HIP]) / 2.0
    x_chest = _norm(P[L_SH] - P[R_SH])
    up = sh_mid - hip_mid
    y = _norm(up - x_chest * np.dot(x_chest, up))
    r_chest = np.column_stack([x_chest, y, np.cross(x_chest, y)])

    x_hip = P[L_HIP] - P[R_HIP]
    x_hip = _norm(x_hip - y * np.dot(y, x_hip))
    r_hips = np.column_stack([x_hip, y, np.cross(x_hip, y)])
    twist = _yaw_deg(r_hips.T @ x_chest)                  # giro do peito visto no frame do quadril
    if abs(twist) > MAX_TWIST_DEG:                        # quadril mal estimado: limita a torção
        twist = float(np.clip(twist, -MAX_TWIST_DEG, MAX_TWIST_DEG))
        r_hips = r_chest @ _rot_y(-twist)
    r_spine = r_hips @ _rot_y(twist * 0.5)

    sx = np.clip(np.linalg.norm(P[L_SH] - P[R_SH]) / TEMPLATE_SHOULDERS, *SCALE_RANGE)
    sy = np.clip(np.linalg.norm(up) / TEMPLATE_TORSO, sx * ASPECT_RANGE[0], sx * ASPECT_RANGE[1])
    s_torso = np.diag([sx, sy, sx])
    s_limb = np.eye(3) * sx

    def along(y_rest: float) -> np.ndarray:            # ponto do eixo quadril→ombros na altura do template
        return hip_mid + (y_rest - _HIPS_Y) / TEMPLATE_TORSO * up

    pos = np.zeros((sk.N_JOINTS, 3))
    rot = np.zeros((sk.N_JOINTS, 3, 3))
    scl = np.zeros((sk.N_JOINTS, 3, 3))
    for name, r in (("hips", r_hips), ("spine", r_spine), ("chest", r_chest), ("neck", r_chest), ("head", r_chest)):
        j = sk.INDEX[name]
        pos[j], rot[j], scl[j] = along(sk.REST_WORLD[j][1]), r, s_torso

    for side, sh, el, wr, sign in (("L", L_SH, L_EL, L_WR, 1.0), ("R", R_SH, R_EL, R_WR, -1.0)):
        rest_dir = np.array([sign, 0.0, 0.0])
        clav, upper, fore, hand = (sk.INDEX[f"{side}_{b}"] for b in ("clavicle", "upper_arm", "forearm", "hand"))
        pos[clav] = sh_mid + _CLAV_FRAC * (P[sh] - sh_mid)
        rot[clav] = rotation_between(r_chest @ rest_dir, P[sh] - pos[clav]) @ r_chest
        pos[upper] = P[sh]
        rot[upper] = rotation_between(rot[clav] @ rest_dir, P[el] - P[sh]) @ rot[clav]
        pos[fore] = P[el]
        rot[fore] = rotation_between(rot[upper] @ rest_dir, P[wr] - P[el]) @ rot[upper]
        pos[hand], rot[hand] = P[wr], rot[fore]
        for j in (clav, upper, fore, hand):
            scl[j] = s_limb

    world_m = np.tile(np.eye(4), (sk.N_JOINTS, 1, 1))
    world_m[:, :3, :3] = rot @ scl
    world_m[:, :3, 3] = pos
    return Retarget(
        skin=sk.skin_matrices(world_m),
        world=world_m,
        depth=depth,
        scale=(float(sx), float(sy)),
        yaw_deg=_yaw_deg(x_chest),
        twist_deg=float(twist),
        points=P,
    )


def joint_error_px(result: Retarget, px_ref: np.ndarray, hfov: float, image_size: tuple[int, int]) -> float:
    """Erro médio (px) entre as articulações da peça projetadas e os landmarks de referência."""
    w, h = image_size
    joints = np.array([result.world[sk.INDEX[name], :3, 3] for name, _ in ERROR_PAIRS])
    got = project(joints, perspective(hfov, w / h), w, h)
    ref = px_ref[[lm for _, lm in ERROR_PAIRS], :2]
    return float(np.linalg.norm(got - ref, axis=1).mean())
