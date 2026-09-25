"""Cenários atrás do usuário (T7b): catálogo em assets/backgrounds/<id>/{background.jpg, meta.json}.

meta.json (opcional): {"name": "Passarela", "color_match": 0.3, "type": "image"}. Sem meta.json valem os padrões
(nome = id da pasta, color_match 0,3). Um cenário inválido é pulado com uma mensagem, sem derrubar o app.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from . import paths

MAX_WIDTH = 1920                     # cenários maiores são reduzidos ao carregar (VRAM e tempo de upload)
DEFAULT_COLOR_MATCH = 0.3
IMAGE_NAMES = ("background.jpg", "background.jpeg", "background.png")


@dataclass
class Background:
    id: str
    name: str
    image: np.ndarray            # (H, W, 3) BGR uint8
    color_match: float           # 0 = pessoa intacta; 1 = média de cor da pessoa igual à do cenário
    mean_lin: np.ndarray         # (3,) média RGB linear do cenário (para o casamento de cor)


def _srgb_to_linear(u8: np.ndarray) -> np.ndarray:
    c = u8.astype(np.float32) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def load_background(folder: str | Path) -> Background:
    """Carrega um cenário; ValueError com mensagem clara se algo estiver errado."""
    folder = Path(folder)
    meta = {}
    meta_path = folder / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"meta.json inválido ({exc})") from exc
        if not isinstance(meta, dict):
            raise ValueError("meta.json precisa ser um objeto JSON")
    kind = meta.get("type", "image")
    if kind != "image":
        raise ValueError(f"tipo '{kind}' ainda não suportado (só 'image')")
    color_match = meta.get("color_match", DEFAULT_COLOR_MATCH)
    if isinstance(color_match, bool) or not isinstance(color_match, (int, float)) or not 0.0 <= color_match <= 1.0:
        raise ValueError("color_match precisa ser um número entre 0 e 1")
    name = meta.get("name", folder.name)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name precisa ser um texto não vazio")

    image_path = next((folder / n for n in IMAGE_NAMES if (folder / n).exists()), None)
    if image_path is None:
        raise ValueError(f"sem imagem ({' ou '.join(IMAGE_NAMES)})")
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"não foi possível ler {image_path.name}")
    if image.shape[1] > MAX_WIDTH:
        scale = MAX_WIDTH / image.shape[1]
        image = cv2.resize(image, (MAX_WIDTH, round(image.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    mean_lin = _srgb_to_linear(image[::4, ::4, ::-1]).reshape(-1, 3).mean(axis=0)
    return Background(folder.name, name.strip(), image, float(color_match), mean_lin)


def find_backgrounds(root: str | Path | None = None) -> list[Path]:
    """Pastas de cenário (as que têm uma imagem ou meta.json), em ordem alfabética."""
    root = Path(root) if root is not None else paths.BACKGROUNDS
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))


def load_backgrounds(root: str | Path | None = None) -> tuple[list[Background], list[str]]:
    loaded, problems = [], []
    for folder in find_backgrounds(root):
        try:
            loaded.append(load_background(folder))
        except ValueError as exc:
            problems.append(f"{folder.name}: {exc}")
    return loaded, problems


def cover_scale(img_w: int, img_h: int, view_w: int, view_h: int) -> tuple[float, float]:
    """Escala do uv da tela para o uv do cenário no modo "cobrir" (preenche a tela e corta o excesso, centrado)."""
    if min(img_w, img_h, view_w, view_h) <= 0:
        return 1.0, 1.0
    img_aspect, view_aspect = img_w / img_h, view_w / view_h
    if img_aspect > view_aspect:           # cenário mais largo: corta dos lados
        return view_aspect / img_aspect, 1.0
    return 1.0, img_aspect / view_aspect   # mais alto: corta em cima e embaixo


@dataclass
class BackgroundSelector:
    """Fundo real (índice -1) e os cenários (0..count-1), em ciclo."""

    count: int
    index: int = -1

    def step(self, delta: int) -> int:
        """Avança (+1) ou volta (-1) no ciclo real → 0 → 1 … → real. Devolve o novo índice."""
        if self.count == 0:
            return self.index
        self.index = (self.index + 1 + delta) % (self.count + 1) - 1
        return self.index

    @property
    def real(self) -> bool:
        return self.index < 0
