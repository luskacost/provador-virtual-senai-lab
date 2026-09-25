"""Esqueleto padrão das peças (parte superior do corpo) e cinemática direta.

Convenção (a mesma do glTF): metros, Y para cima, o corpo olha para +Z, o lado ESQUERDO do corpo fica em +X.
Pose de repouso em T. Os ossos aparecem em ordem topológica (pai antes do filho).
Qualquer GLB rigado com estes nomes de nós funciona no app (peças de T9 e T12 incluídas).
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Joint:
    name: str
    parent: int                          # índice do pai; -1 = raiz
    rest: tuple[float, float, float]     # posição no mundo na pose de repouso (m)


def _arm(side: str, s: float) -> list[tuple[str, str, tuple[float, float, float]]]:
    """(nome, pai, posição) do braço; s = +1 (esquerdo, +X) ou -1 (direito, -X)."""
    return [
        (f"{side}_clavicle", "chest", (0.06 * s, 1.45, 0.0)),
        (f"{side}_upper_arm", f"{side}_clavicle", (0.19 * s, 1.45, 0.0)),
        (f"{side}_forearm", f"{side}_upper_arm", (0.47 * s, 1.45, 0.0)),
        (f"{side}_hand", f"{side}_forearm", (0.75 * s, 1.45, 0.0)),
    ]


_SPEC = [
    ("hips", "", (0.0, 1.00, 0.0)),
    ("spine", "hips", (0.0, 1.10, 0.0)),
    ("chest", "spine", (0.0, 1.30, 0.0)),
    ("neck", "chest", (0.0, 1.50, 0.0)),
    ("head", "neck", (0.0, 1.58, 0.0)),
    *_arm("L", +1.0),
    *_arm("R", -1.0),
]

NAMES: tuple[str, ...] = tuple(n for n, _, _ in _SPEC)
INDEX: dict[str, int] = {n: i for i, n in enumerate(NAMES)}
JOINTS: tuple[Joint, ...] = tuple(
    Joint(n, INDEX[p] if p else -1, pos) for n, p, pos in _SPEC
)
N_JOINTS = len(JOINTS)
PARENT = np.array([j.parent for j in JOINTS], np.int32)
REST_WORLD = np.array([j.rest for j in JOINTS], np.float64)                       # (n, 3)
REST_LOCAL = REST_WORLD - np.where(PARENT[:, None] >= 0, REST_WORLD[PARENT], 0.0)  # (n, 3)

assert all(j.parent < i for i, j in enumerate(JOINTS)), "ossos precisam estar em ordem topológica"


def translation(t) -> np.ndarray:
    m = np.eye(4)
    m[:3, 3] = t
    return m


def inverse_bind() -> np.ndarray:
    """(n, 4, 4) — inversa da matriz de mundo de cada osso na pose de repouso (só translação)."""
    return np.stack([translation(-p) for p in REST_WORLD])


def world_matrices(local_rot: np.ndarray | None = None, root_offset=(0.0, 0.0, 0.0)) -> np.ndarray:
    """Cinemática direta: (n, 4, 4) matrizes de mundo dos ossos.

    local_rot: (n, 3, 3) rotação de cada osso RELATIVA à pose de repouso, no espaço local do osso
    (None = repouso). root_offset: deslocamento do quadril (m).
    """
    rot = np.broadcast_to(np.eye(3), (N_JOINTS, 3, 3)) if local_rot is None else local_rot
    world = np.empty((N_JOINTS, 4, 4))
    for i, j in enumerate(JOINTS):
        local = translation(REST_LOCAL[i])
        local[:3, :3] = rot[i]
        if j.parent < 0:
            local[:3, 3] += root_offset
            world[i] = local
        else:
            world[i] = world[j.parent] @ local
    return world


def skin_matrices(world: np.ndarray) -> np.ndarray:
    """Matrizes de skinning (n, 4, 4) = mundo do osso × inversa do bind. Repouso → identidade."""
    return world @ inverse_bind()


def rotation_axis_angle(axis, degrees: float) -> np.ndarray:
    """Matriz 3x3 (fórmula de Rodrigues)."""
    axis = np.asarray(axis, np.float64)
    axis = axis / np.linalg.norm(axis)
    a = np.radians(degrees)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(a) * k + (1 - np.cos(a)) * (k @ k)
