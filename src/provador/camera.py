"""Câmera virtual alinhada à webcam (pinhole), em numpy.

Convenção de câmera do OpenGL: câmera na origem olhando para -Z, Y para cima, X para a direita da imagem
NÃO espelhada. Como a peça olha para +Z (skeleton.py), o lado esquerdo do corpo (+X) aparece à direita da
imagem crua — igual a uma pessoa real de frente para a webcam. O espelho é aplicado só na exibição.
"""

import math

import numpy as np

DEFAULT_HFOV = 70.0      # graus; típico de webcam de notebook. Ajustável por --hfov (calibrar na T6).


def focal_px(hfov_deg: float, width: int) -> float:
    """Distância focal em pixels para um FOV horizontal."""
    return (width / 2.0) / math.tan(math.radians(hfov_deg) / 2.0)


def perspective(hfov_deg: float, aspect: float, near: float = 0.05, far: float = 20.0) -> np.ndarray:
    """Matriz de projeção (4x4, row-major) com FOV horizontal; aspect = largura / altura."""
    sx = 1.0 / math.tan(math.radians(hfov_deg) / 2.0)
    m = np.zeros((4, 4))
    m[0, 0] = sx
    m[1, 1] = sx * aspect
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = 2.0 * far * near / (near - far)
    m[3, 2] = -1.0
    return m


def project(points: np.ndarray, proj: np.ndarray, width: int, height: int) -> np.ndarray:
    """Pontos (N, 3) no espaço da câmera → pixels (N, 2) da imagem crua (x para a direita, y para baixo)."""
    p = np.concatenate([points, np.ones((len(points), 1))], axis=1) @ proj.T
    ndc = p[:, :2] / p[:, 3:4]
    return np.stack([(ndc[:, 0] + 1.0) * 0.5 * width, (1.0 - ndc[:, 1]) * 0.5 * height], axis=1)


def unproject(px: np.ndarray, depth: np.ndarray, hfov_deg: float, width: int, height: int) -> np.ndarray:
    """Pixels (N, 2) + distância ao longo de -Z (N,) → pontos (N, 3) no espaço da câmera. Inversa de project."""
    f = focal_px(hfov_deg, width)
    x = (px[:, 0] - width / 2.0) / f * depth
    y = -(px[:, 1] - height / 2.0) / f * depth
    return np.stack([x, y, -depth], axis=1)


def gl_bytes(m: np.ndarray) -> bytes:
    """Matriz(es) row-major do numpy → bytes column-major float32 para uniforms do GLSL."""
    return np.ascontiguousarray(np.swapaxes(m, -1, -2), dtype=np.float32).tobytes()
