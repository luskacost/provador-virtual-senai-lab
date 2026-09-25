"""Overlay de debug: esqueleto da pose desenhado em GL (sem readback)."""

import moderngl
import numpy as np

from . import paths

SHADERS = paths.ROOT / "src" / "provador" / "shaders"

_BONES = None


def bone_indices() -> np.ndarray:
    """Pares (a, b) de landmarks a ligar. Ignora o rosto (índices 1-10) para o esqueleto ficar limpo."""
    global _BONES
    if _BONES is None:
        from mediapipe.tasks.python import vision

        pairs = [(c.start, c.end) for c in vision.PoseLandmarksConnections.POSE_LANDMARKS]
        _BONES = np.array([p for p in pairs if p[0] > 10 and p[1] > 10] + [(0, 11), (0, 12)], np.int32)
    return _BONES


def _shader(name: str) -> str:
    return (SHADERS / name).read_text(encoding="utf-8")


class SkeletonOverlay:
    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        frag = _shader("skeleton.frag")
        self.bone_prog = ctx.program(vertex_shader=_shader("skeleton_bone.vert"), fragment_shader=frag)
        self.point_prog = ctx.program(vertex_shader=_shader("skeleton_point.vert"), fragment_shader=frag)
        self.bones = bone_indices()
        self.bone_buf = ctx.buffer(reserve=len(self.bones) * 6 * 4, dynamic=True)
        self.point_buf = ctx.buffer(reserve=33 * 3 * 4, dynamic=True)
        self.bone_vao = ctx.vertex_array(self.bone_prog, [(self.bone_buf, "3f 3f/i", "a", "b")])
        self.point_vao = ctx.vertex_array(self.point_prog, [(self.point_buf, "3f", "p")])
        self._has_data = False

    def update(self, px: np.ndarray, visibility: np.ndarray, image_size: tuple[int, int]) -> None:
        """px: (33, 3) em pixels da imagem; visibility: (33,)."""
        w, h = image_size
        pts = np.column_stack([px[:, 0] / w, px[:, 1] / h, visibility]).astype(np.float32)
        self.point_buf.write(pts.tobytes())
        self.bone_buf.write(np.hstack([pts[self.bones[:, 0]], pts[self.bones[:, 1]]]).tobytes())
        self._has_data = True

    def clear(self) -> None:
        self._has_data = False

    def draw(self, viewport_px: tuple[int, int], mirror: bool) -> None:
        """Desenha por cima do vídeo; o viewport do GL já deve ser a área (letterbox) do vídeo."""
        if not self._has_data:
            return
        self.ctx.enable(moderngl.BLEND | moderngl.PROGRAM_POINT_SIZE)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        prog = self.bone_prog
        prog["viewport_px"].value = viewport_px
        prog["mirror"].value = mirror
        prog["thickness"].value = 4.0
        prog["rgb"].value = (0.1, 1.0, 0.4)
        prog["round_point"].value = False
        self.bone_vao.render(moderngl.TRIANGLE_STRIP, vertices=4, instances=len(self.bones))

        prog = self.point_prog
        prog["mirror"].value = mirror
        prog["point_size"].value = 10.0
        prog["rgb"].value = (1.0, 0.85, 0.1)
        prog["round_point"].value = True
        self.point_vao.render(moderngl.POINTS, vertices=33)
        self.ctx.disable(moderngl.BLEND)
