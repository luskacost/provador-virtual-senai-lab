"""Verificacao do ambiente (T1).

Uso:
    python -m provador.check            # versoes, OpenGL, GPU, modelos
    python -m provador.check --camera   # tambem testa a webcam a 1280x720 por ~3 s

Sai com codigo 1 se algo essencial falhar (Python fora de 3.11/3.12, pacote ausente, sem OpenGL 3.3).
"""

from __future__ import annotations

import argparse
import importlib
import platform
import sys
import time
from importlib import metadata

from provador import paths

REQUIRED = {
    # modulo importado : distribuicao no pip
    "mediapipe": "mediapipe",
    "cv2": "opencv-python",
    "moderngl": "moderngl",
    "glfw": "glfw",
    "pygltflib": "pygltflib",
    "trimesh": "trimesh",
    "numpy": "numpy",
    "psutil": "psutil",
    "pynvml": "nvidia-ml-py",
}
OPTIONAL = {"onnxruntime": "onnxruntime", "pytest": "pytest"}

OK, WARN, FAIL = "[ OK ]", "[AVISO]", "[FALHA]"


def _dist_version(dist: str) -> str | None:
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return None


def check_python() -> bool:
    v = sys.version_info
    good = (v.major, v.minor) in {(3, 11), (3, 12)}
    tag = OK if good else FAIL
    print(f"{tag} Python {platform.python_version()} ({sys.executable})")
    if not good:
        print("       MediaPipe exige Python 3.11 ou 3.12. Recrie o venv com tools\\setup_env.ps1.")
    return good


def check_packages() -> bool:
    all_ok = True
    for mod, dist in REQUIRED.items():
        try:
            importlib.import_module(mod)
            print(f"{OK} {dist:<14} {_dist_version(dist) or '?'}")
        except Exception as exc:  # noqa: BLE001
            all_ok = False
            print(f"{FAIL} {dist:<14} nao importa: {exc}")
    for mod, dist in OPTIONAL.items():
        ver = _dist_version(dist)
        if ver:
            print(f"{OK} {dist:<14} {ver} (opcional)")
    return all_ok


def check_opengl() -> bool:
    """Cria um contexto OpenGL oculto via GLFW (o mesmo caminho do app) e mostra a placa usada."""
    try:
        import glfw
        import moderngl
    except ImportError:
        print(f"{FAIL} OpenGL: glfw/moderngl ausentes")
        return False
    if not glfw.init():
        print(f"{FAIL} OpenGL: glfw.init() falhou")
        return False
    try:
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
        win = glfw.create_window(64, 64, "check", None, None)
        if not win:
            print(f"{FAIL} OpenGL: nao foi possivel criar contexto 3.3 core")
            return False
        glfw.make_context_current(win)
        ctx = moderngl.create_context()
        info = ctx.info
        renderer = info.get("GL_RENDERER", "?")
        print(f"{OK} OpenGL {ctx.version_code // 100}.{ctx.version_code % 100 // 10} | "
              f"{info.get('GL_VENDOR', '?')} | {renderer}")
        print(f"       MSAA max samples: {info.get('GL_MAX_SAMPLES', '?')}")
        low = renderer.lower()
        if "intel" in low or "microsoft basic" in low or "gdi" in low:
            print(f"{WARN} O OpenGL esta usando uma GPU integrada/software. Em notebooks com NVIDIA, "
                  "force a GPU dedicada para python.exe (Painel NVIDIA ou Config. > Sistema > Tela > Graficos).")
        ctx.release()
        glfw.destroy_window(win)
        return True
    finally:
        glfw.terminate()


def check_nvidia() -> None:
    try:
        import pynvml

        pynvml.nvmlInit()
        n = pynvml.nvmlDeviceGetCount()
        drv = pynvml.nvmlSystemGetDriverVersion()
        drv = drv.decode() if isinstance(drv, bytes) else drv
        for i in range(n):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(h)
            name = name.decode() if isinstance(name, bytes) else name
            mem = pynvml.nvmlDeviceGetMemoryInfo(h).total / 1024**3
            print(f"{OK} NVIDIA GPU {i}: {name} | {mem:.1f} GB | driver {drv}")
        pynvml.nvmlShutdown()
    except Exception as exc:  # noqa: BLE001
        print(f"{WARN} NVML indisponivel ({exc.__class__.__name__}): sem GPU NVIDIA ou driver ausente. "
              "Plano B (T13) usa onnxruntime-directml.")


def check_cpu() -> None:
    try:
        import psutil

        freq = psutil.cpu_freq()
        mhz = f"{freq.max:.0f} MHz" if freq else "?"
        print(f"{OK} CPU: {platform.processor() or '?'} | {psutil.cpu_count(logical=False)}c/"
              f"{psutil.cpu_count()}t | {mhz} | RAM {psutil.virtual_memory().total / 1024**3:.1f} GB")
    except Exception as exc:  # noqa: BLE001
        print(f"{WARN} CPU: {exc}")


def check_models() -> None:
    for path in paths.MODEL_URLS:
        if path.exists():
            print(f"{OK} modelo {path.name} ({path.stat().st_size / 1e6:.1f} MB)")
        else:
            print(f"{WARN} modelo {path.name} ausente -> python tools/download_models.py")
    if paths.SEG_ONNX.exists():
        print(f"{OK} modelo {paths.SEG_ONNX.name} ({paths.SEG_ONNX.stat().st_size / 1e6:.1f} MB)")
    else:
        print(f"{WARN} modelo {paths.SEG_ONNX.name} ausente -> python tools/convert_seg_model.py")


def check_camera(index: int = 0, seconds: float = 3.0) -> bool:
    import cv2

    backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        print(f"{FAIL} Webcam {index}: nao abriu")
        return False
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    ok, frame = cap.read()
    if not ok:
        print(f"{FAIL} Webcam {index}: abriu mas nao entregou frames")
        cap.release()
        return False
    n, t0 = 0, time.perf_counter()
    while time.perf_counter() - t0 < seconds:
        ok, frame = cap.read()
        n += ok
    fps = n / (time.perf_counter() - t0)
    h, w = frame.shape[:2]
    tag = OK if fps >= 28 and h >= 720 else WARN
    print(f"{tag} Webcam {index}: {w}x{h} a {fps:.1f} FPS medidos")
    cap.release()
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verifica o ambiente do Provador Virtual 3D")
    ap.add_argument("--camera", action="store_true", help="testa a webcam (1280x720)")
    ap.add_argument("--camera-index", type=int, default=0)
    args = ap.parse_args(argv)

    print(f"Provador Virtual 3D - check | {platform.platform()}\n")
    essentials = [check_python(), check_packages()]
    print()
    essentials.append(check_opengl())
    check_nvidia()
    check_cpu()
    check_models()
    if args.camera:
        check_camera(args.camera_index)
    ok = all(essentials)
    print("\nResultado:", "ambiente pronto" if ok else "corrija os itens [FALHA] acima")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
