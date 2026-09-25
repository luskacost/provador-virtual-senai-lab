"""Catálogo de peças: descoberta dos GLBs, carregamento tolerante a falhas e seleção circular."""

from dataclasses import dataclass
from pathlib import Path

from . import paths
from .garment import Garment, load_glb


def find_garments(source: str | Path | None = None) -> list[Path]:
    """GLBs de uma pasta (ordenados pelo nome) ou o próprio arquivo. Sem argumento: assets/garments/ e,
    se estiver vazia, o template procedural."""
    if source is not None:
        p = Path(source)
        return [p] if p.is_file() else sorted(p.glob("*.glb"))
    found = sorted(paths.GARMENTS.glob("*.glb"))
    fallback = paths.TEMPLATES / "tshirt.glb"
    return found or ([fallback] if fallback.exists() else [])


def load_catalog(source: str | Path | None = None) -> tuple[list[Garment], list[str]]:
    """Carrega as peças; um GLB inválido é pulado e vira uma mensagem (não derruba o app)."""
    garments, problems = [], []
    for path in find_garments(source):
        try:
            garments.append(load_glb(path))
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            problems.append(f"{path.name}: {exc}")
    return garments, problems


@dataclass
class Selector:
    """Índice da peça atual, com volta circular."""

    count: int
    index: int = 0

    def select(self, i: int) -> bool:
        """Vai para a peça i (0-based). Devolve False se não existir ou já for a atual."""
        if not 0 <= i < self.count or i == self.index:
            return False
        self.index = i
        return True

    def step(self, delta: int) -> bool:
        if self.count < 2:
            return False
        self.index = (self.index + delta) % self.count
        return True
