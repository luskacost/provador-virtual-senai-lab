"""Métricas leves de desempenho (FPS e latência), sem dependências de GL ou câmera."""

import statistics
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
    """Média e máximo (em ms) das últimas N amostras. Com keep_history(), guarda também todas como (t, ms)."""

    def __init__(self, size: int = 120):
        self._samples: deque[float] = deque(maxlen=size)
        self.history: list[tuple[float, float]] | None = None

    def keep_history(self) -> None:
        if self.history is None:
            self.history = []

    def add(self, seconds: float) -> None:
        ms = seconds * 1000.0
        self._samples.append(ms)
        if self.history is not None:
            self.history.append((time.perf_counter(), ms))

    @property
    def mean_ms(self) -> float:
        return sum(self._samples) / len(self._samples) if self._samples else 0.0

    @property
    def max_ms(self) -> float:
        return max(self._samples) if self._samples else 0.0


class JitterStats:
    """Desvio-padrão (na unidade da amostra) de um vetor de coordenadas nas últimas N amostras.

    Com a pessoa parada, mede o tremor: usa-se o pior canal (ex.: x e y de cada ombro).
    """

    def __init__(self, size: int = 90):
        self._samples: deque[tuple[float, ...]] = deque(maxlen=size)

    def add(self, values) -> None:
        self._samples.append(tuple(float(v) for v in values))

    def reset(self) -> None:
        self._samples.clear()

    @property
    def std_max(self) -> float:
        """Pior desvio-padrão entre os canais. Precisa de ao menos 10 amostras; senão, 0."""
        if len(self._samples) < 10:
            return 0.0
        cols = list(zip(*self._samples, strict=True))
        return max(statistics.pstdev(c) for c in cols)


class RunningMean:
    """Média das últimas N amostras (unidade livre)."""

    def __init__(self, size: int = 90):
        self._samples: deque[float] = deque(maxlen=size)

    def add(self, value: float) -> None:
        self._samples.append(float(value))

    @property
    def mean(self) -> float:
        return sum(self._samples) / len(self._samples) if self._samples else 0.0
