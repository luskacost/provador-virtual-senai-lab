"""Métricas leves de desempenho (FPS e latência), sem dependências de GL ou câmera."""

import time
from collections import deque


class RateCounter:
    """Taxa de eventos por segundo numa janela deslizante de tempo."""

    def __init__(self, window: float = 1.0, clock=time.perf_counter):
        self._window = window
        self._clock = clock
        self._stamps: deque[float] = deque()

    def tick(self) -> None:
        now = self._clock()
        self._stamps.append(now)
        self._trim(now)

    def _trim(self, now: float) -> None:
        limit = now - self._window
        while self._stamps and self._stamps[0] < limit:
            self._stamps.popleft()

    @property
    def rate(self) -> float:
        """Eventos/s. Precisa de ao menos 2 eventos na janela; senão, 0."""
        self._trim(self._clock())
        n = len(self._stamps)
        if n < 2:
            return 0.0
        span = self._stamps[-1] - self._stamps[0]
        return (n - 1) / span if span > 0 else 0.0


class LatencyStats:
    """Média e máximo (em ms) das últimas N amostras."""

    def __init__(self, size: int = 120):
        self._samples: deque[float] = deque(maxlen=size)

    def add(self, seconds: float) -> None:
        self._samples.append(seconds * 1000.0)

    @property
    def mean_ms(self) -> float:
        return sum(self._samples) / len(self._samples) if self._samples else 0.0

    @property
    def max_ms(self) -> float:
        return max(self._samples) if self._samples else 0.0
