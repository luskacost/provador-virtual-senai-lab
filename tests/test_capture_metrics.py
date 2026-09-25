from provador.capture import CameraThread
from provador.metrics import LatencyStats, RateCounter
from provador.viewport import letterbox


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_rate_counter_30hz():
    clock = FakeClock()
    rc = RateCounter(window=1.0, clock=clock)
    for _ in range(60):
        rc.tick()
        clock.t += 1 / 30
    assert abs(rc.rate - 30.0) < 0.5


def test_rate_counter_vazio_e_expira():
    clock = FakeClock()
    rc = RateCounter(window=1.0, clock=clock)
    assert rc.rate == 0.0
    rc.tick()
    clock.t += 0.1
    rc.tick()
    clock.t += 5.0          # tudo saiu da janela
    assert rc.rate == 0.0


def test_latency_stats():
    ls = LatencyStats(size=3)
    assert ls.mean_ms == 0.0 and ls.max_ms == 0.0
    for s in (0.010, 0.020, 0.030, 0.040):   # a de 10 ms sai da janela de 3
        ls.add(s)
    assert abs(ls.mean_ms - 30.0) < 1e-6
    assert abs(ls.max_ms - 40.0) < 1e-6


def test_letterbox_mantem_proporcao():
    assert letterbox(1280, 720, 1280, 720) == (0, 0, 1280, 720)
    assert letterbox(1920, 1080, 1280, 720) == (0, 0, 1920, 1080)
    x, y, w, h = letterbox(1000, 1000, 1280, 720)      # barras em cima e embaixo
    assert (x, w) == (0, 1000) and h == 562 and y == 219
    x, y, w, h = letterbox(500, 1000, 1280, 720)
    assert w == 500 and x == 0


def test_letterbox_degenerado():
    assert letterbox(0, 0, 1280, 720) == (0, 0, 0, 0)


def test_latest_so_entrega_frame_novo():
    cam = CameraThread()
    assert cam.latest() is None
    import numpy as np

    from provador.capture import Frame

    cam._frame = Frame(5, np.zeros((2, 2, 3), np.uint8), 0.0)
    assert cam.latest(4).id == 5
    assert cam.latest(5) is None


def test_jitter_stats():
    from provador.metrics import JitterStats

    js = JitterStats()
    for _ in range(5):
        js.add((100.0, 200.0))
    assert js.std_max == 0.0                      # poucas amostras
    for i in range(20):
        js.add((100.0 + (2.0 if i % 2 else -2.0), 200.0))
    assert 1.5 < js.std_max < 2.5                 # pior canal é o x, com oscilação de ±2
    js.reset()
    assert js.std_max == 0.0
