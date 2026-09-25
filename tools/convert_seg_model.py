"""Converte o segmentador multiclasse do MediaPipe (.tflite) para ONNX, para rodar na GPU via DirectML.

Por quê: no MediaPipe (CPU) o modelo leva ~82 ms por frame nesta máquina; em ONNX Runtime + DirectML na
NVIDIA leva ~4 ms, com 99,8% de concordância nas classes. A conversão precisa de TensorFlow + tf2onnx, que
NÃO entram no .venv do app: este script cria um ambiente temporário com o uv, converte e o apaga.

Uso:  python tools/convert_seg_model.py        (uma vez; o setup_env chama sozinho se o .onnx faltar)
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from provador import paths

PACKAGES = ["tensorflow-cpu==2.15.1", "tf2onnx==1.16.1", "numpy<2", "protobuf<4"]


def main() -> int:
    if paths.SEG_ONNX.exists():
        print(f"já existe: {paths.SEG_ONNX}")
        return 0
    if not paths.SEG_MODEL.exists():
        print("baixe os modelos antes: python tools/download_models.py")
        return 1
    uv = shutil.which("uv")
    if not uv:
        print("o uv não foi encontrado (winget install -e --id astral-sh.uv)")
        return 1
    tmp = Path(tempfile.mkdtemp(prefix="provador_conv_"))
    try:
        env = tmp / "venv"
        py = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        print("criando ambiente temporário com TensorFlow + tf2onnx (~300 MB, só nesta etapa)...")
        subprocess.run([uv, "venv", "-q", "--python", "3.11", str(env)], check=True)
        subprocess.run([uv, "pip", "install", "-q", "--python", str(py), *PACKAGES], check=True)
        print("convertendo...")
        subprocess.run([str(py), "-m", "tf2onnx.convert", "--tflite", str(paths.SEG_MODEL),
                        "--output", str(paths.SEG_ONNX), "--opset", "17"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"ok: {paths.SEG_ONNX} ({paths.SEG_ONNX.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
