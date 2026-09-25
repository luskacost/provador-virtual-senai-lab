"""Filtro One Euro (Casiez et al., 2012) vetorizado com numpy.

Suaviza o jitter quando o sinal está parado (cutoff baixo) e reduz o atraso quando ele se move
depressa (cutoff cresce com a velocidade). Aceita arrays de qualquer forma, ex.: (33, 3).
"""

import math

import numpy as np


def _alpha(cutoff: np.ndarray | float, dt: float) -> np.ndarray | float:
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    """min_cutoff: Hz de corte com o sinal parado (menor = mais suave). beta: quanto o corte sobe com
    a velocidade (maior = menos atraso em movimentos rápidos). d_cutoff: suavização da derivada.

    Os parâmetros valem para as unidades do sinal; se ele estiver em pixels, min_cutoff≈1 e beta≈0.01
    são um bom começo. Para outras unidades, escale o sinal antes (ex.: metros × 1000 → mm).
    """

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.01, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x: np.ndarray | None = None
        self._dx: np.ndarray | None = None
        self._t: float | None = None

    def reset(self) -> None:
        self._x = self._dx = self._t = None

    def __call__(self, x: np.ndarray, t: float) -> np.ndarray:
        """Filtra a amostra x (em qualquer forma) medida no instante t (segundos)."""
        x = np.asarray(x, dtype=np.float64)
        if self._x is None or self._t is None or x.shape != self._x.shape or t <= self._t:
            self._x, self._dx, self._t = x.copy(), np.zeros_like(x), t
            return x.copy()
        dt = t - self._t
        dx = (x - self._x) / dt
        a_d = _alpha(self.d_cutoff, dt)
        self._dx = a_d * dx + (1.0 - a_d) * self._dx
        cutoff = self.min_cutoff + self.beta * np.abs(self._dx)
        a = _alpha(cutoff, dt)
        self._x = a * x + (1.0 - a) * self._x
        self._t = t
        return self._x.copy()
