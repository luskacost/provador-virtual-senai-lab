"""Oclusão dos braços: cápsulas 3D (cilindros + esferas) nos braços, desenhadas DEPOIS da peça com teste de
profundidade. Onde o braço está à frente da peça, a cápsula repinta o próprio pixel do vídeo, recortado pela
máscara da segmentação. Resultado: a ordem (frente/atrás) vem da geometria 3D do retarget e o contorno vem da
máscara, sem readback. Onde não há peça, repintar o vídeo com ele mesmo não muda nada.
"""

import moderngl
import numpy as np

from . import paths
from .camera import gl_bytes, perspective
from .retarget import L_EL, L_SH, L_WR, R_EL, R_SH, R_WR

SHADERS = paths.ROOT / "src" / "provador" / "shaders"
L_PINKY, R_PINKY, L_INDEX, R_INDEX = 17, 18, 19, 20

# Raios (m) para escala 1,0. Um pouco menores que um braço real: a borda fina fica por conta da máscara.
R_UPPER, R_FORE, R_HAND = 0.050, 0.042, 0.050


def _cylinder(seg: int = 16) -> tuple[np.ndarray, np.ndarray]:
    """Cilindro unitário (raio 1, de y=0 a y=1) como TRIANGLES: posições e normais (N, 3)."""
    a = np.linspace(0, 2 * np.pi, seg + 1)
    pos, nor = [], []
    for i in range(seg):
        c0, s0, c1, s1 = np.cos(a[i]), np.sin(a[i]), np.cos(a[i + 1]), np.sin(a[i + 1])
        quad = [(c0, 0, s0), (c1, 0, s1), (c1, 1, s1), (c0, 0, s0), (c1, 1, s1), (c0, 1, s0)]
        pos += quad
        nor += [(x, 0, z) for x, _, z in quad]
    return np.array(pos, np.float32), np.array(nor, np.float32)


def _sphere(seg: int = 12, rings: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """Esfera unitária como TRIANGLES (normal = posição)."""
    th = np.linspace(0, np.pi, rings + 1)
    ph = np.linspace(0, 2 * np.pi, seg + 1)

    def p(t, f):
        return (np.sin(t) * np.cos(f), np.cos(t), np.sin(t) * np.sin(f))

    tris = []
    for i in range(rings):
        for j in range(seg):
            a, b, c, d = p(th[i], ph[j]), p(th[i], ph[j + 1]), p(th[i + 1], ph[j + 1]), p(th[i + 1], ph[j])
            tris += [a, b, c, a, c, d]
    pos = np.array(tris, np.float32)
    return pos, pos.copy()


def segment_matrix(a: np.ndarray, b: np.ndarray, radius: float) -> np.ndarray:
    """Matriz 4x4 que leva o cilindro unitário para o segmento a→b com o raio dado."""
    axis = b - a
    y = axis / max(np.linalg.norm(axis), 1e-9)
    ref = np.array([1.0, 0, 0]) if abs(y[0]) < 0.9 else np.array([0, 0, 1.0])
    x = np.cross(y, ref)
    x /= np.linalg.norm(x)
    z = np.cross(x, y)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x * radius, axis, z * radius, a
    return m


def sphere_matrix(c: np.ndarray, radius: float) -> np.ndarray:
    m = np.eye(4)
    m[:3, :3] *= radius
    m[:3, 3] = c
    return m


def arm_instances(points: np.ndarray, scale: float) -> tuple[np.ndarray, np.ndarray]:
    """Pontos 3D (33, 3) no espaço da câmera → matrizes (cilindros, esferas) dos dois braços e mãos."""
    cyl, sph = [], []
    for sh, el, wr, pk, ix in ((L_SH, L_EL, L_WR, L_PINKY, L_INDEX), (R_SH, R_EL, R_WR, R_PINKY, R_INDEX)):
        hand = (points[wr] + points[pk] + points[ix]) / 3.0
        cyl += [segment_matrix(points[sh], points[el], R_UPPER * scale),
                segment_matrix(points[el], points[wr], R_FORE * scale),
                segment_matrix(points[wr], hand, R_FORE * scale)]
        sph += [sphere_matrix(points[el], R_FORE * scale), sphere_matrix(points[wr], R_FORE * scale),
                sphere_matrix(hand, R_HAND * scale)]
    return np.stack(cyl), np.stack(sph)


class ArmOccluder:
    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self.prog = ctx.program(vertex_shader=(SHADERS / "occluder.vert").read_text(encoding="utf-8"),
                                fragment_shader=(SHADERS / "occluder.frag").read_text(encoding="utf-8"))
        self.prog["video"].value = 0
        self.prog["mask"].value = 1
        self._vaos = []
        for mesh in (_cylinder(), _sphere()):
            pos, nor = mesh
            inst = ctx.buffer(reserve=6 * 64, dynamic=True)
            vao = ctx.vertex_array(self.prog, [
                (ctx.buffer(pos.tobytes()), "3f", "in_pos"),
                (ctx.buffer(nor.tobytes()), "3f", "in_normal"),
                (inst, "16f/i", "inst"),
            ])
            self._vaos.append([vao, inst, len(pos), 0])
        self.visible = False

    def update(self, points: np.ndarray | None, scale: float = 1.0) -> None:
        if points is None:
            self.visible = False
            return
        for slot, mats in zip(self._vaos, arm_instances(points, scale), strict=True):
            slot[1].write(gl_bytes(mats))      # column-major: cada instância vira 4 colunas vec4
            slot[3] = len(mats)
        self.visible = True

    def draw(self, hfov: float, viewport: tuple[int, int, int, int], mirror: bool, debug: bool = False) -> None:
        """Depois da peça, com o buffer de profundidade dela. video/mask já ligados nas unidades 0 e 1."""
        if not self.visible:
            return
        x, y, w, h = viewport
        self.prog["proj"].write(gl_bytes(perspective(hfov, w / h)))
        self.prog["viewport"].value = (float(x), float(y), float(w), float(h))
        self.prog["mirror"].value = mirror
        self.prog["debug"].value = debug
        self.ctx.enable(moderngl.DEPTH_TEST | moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.ctx.depth_mask = False                    # não atrapalha a profundidade da peça
        for vao, _, n_vert, n_inst in self._vaos:
            vao.render(moderngl.TRIANGLES, vertices=n_vert, instances=n_inst)
        self.ctx.depth_mask = True
        self.ctx.disable(moderngl.DEPTH_TEST | moderngl.BLEND)
