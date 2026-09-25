"""glFinish chamado via ctypes, que LIBERA o GIL enquanto espera a GPU.

Por quê: com vsync, o driver da NVIDIA bloqueia a thread de render na primeira chamada GL do frame
seguinte até haver um back buffer livre. O ModernGL segura o GIL durante as chamadas GL, então essa
espera (~5 ms por frame, a 165 Hz) travava as threads de pose/segmentação: a inferência ia de 15 para
33 ms. Esperando aqui, logo após o swap, a espera acontece sem o GIL.
"""

import ctypes
import ctypes.util
import sys


def _load():
    try:
        if sys.platform == "win32":
            return ctypes.windll.opengl32.glFinish
        name = ctypes.util.find_library("OpenGL" if sys.platform == "darwin" else "GL")
        return ctypes.CDLL(name).glFinish if name else None
    except (OSError, AttributeError):
        return None


_gl_finish = _load()


def finish_without_gil() -> None:
    """Espera a GPU terminar o frame sem segurar o GIL (no-op se a biblioteca GL não for achada)."""
    if _gl_finish is not None:
        _gl_finish()
