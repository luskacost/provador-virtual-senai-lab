import numpy as np

from provador.oneeuro import OneEuroFilter

FPS = 30.0


def _run(f, signal):
    return np.array([f(x, i / FPS) for i, x in enumerate(signal)])


def test_reduz_jitter_com_sinal_parado():
    rng = np.random.default_rng(0)
    noisy = 500 + rng.normal(0, 2.0, size=(300, 5))          # 5 canais parados com ruído de 2 px
    out = _run(OneEuroFilter(min_cutoff=1.0, beta=0.01), noisy)
    assert out[60:].std(axis=0).max() < 0.5 * noisy[60:].std(axis=0).min()


def test_acompanha_movimento_rapido_com_pouco_atraso():
    t = np.arange(150) / FPS
    ramp = 300.0 * t                                          # 300 px/s, movimento rápido
    out = _run(OneEuroFilter(min_cutoff=1.0, beta=0.05), ramp)
    assert abs(out[-1] - ramp[-1]) < 12                       # < 12 px (~40 ms) de atraso em regime


def test_beta_maior_reduz_atraso():
    t = np.arange(90) / FPS
    ramp = 200.0 * t
    lag = lambda b: abs(_run(OneEuroFilter(1.0, b), ramp)[-1] - ramp[-1])
    assert lag(0.1) < lag(0.0)


def test_aceita_arrays_multidimensionais():
    f = OneEuroFilter()
    x = np.ones((33, 3))
    assert f(x, 0.0).shape == (33, 3)
    assert f(x * 2, 1 / FPS).shape == (33, 3)


def test_primeira_amostra_passa_direto_e_reset():
    f = OneEuroFilter()
    assert np.allclose(f(np.array([10.0, 20.0]), 0.0), [10.0, 20.0])
    f.reset()
    assert np.allclose(f(np.array([99.0, 99.0]), 5.0), [99.0, 99.0])


def test_timestamp_nao_crescente_reinicia_sem_dividir_por_zero():
    f = OneEuroFilter()
    f(np.array([1.0]), 1.0)
    assert np.isfinite(f(np.array([2.0]), 1.0)).all()
