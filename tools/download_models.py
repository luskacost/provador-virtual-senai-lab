"""Baixa os modelos do MediaPipe para models/ (pose full + segmentador multiclasse 256)."""

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from provador import paths


def main() -> None:
    paths.MODELS.mkdir(exist_ok=True)
    for dest, url in paths.MODEL_URLS.items():
        if dest.exists() and dest.stat().st_size > 0:
            print(f"ja existe: {dest.name}")
            continue
        print(f"baixando {dest.name} ...")
        tmp = dest.with_suffix(dest.suffix + ".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(dest)
        print(f"  ok ({dest.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
