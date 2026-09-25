import numpy as np

from provador.occlusion import arm_instances, segment_matrix, sphere_matrix
from provador.segment import probabilities_to_rgba, softmax


def test_softmax_e_mascara_rgba():
    logits = np.zeros((2, 2, 6))
    logits[0, 0, 2] = 10          # pele do corpo
    logits[0, 1, 1] = 10          # cabelo
    logits[1, 0, 0] = 10          # fundo
    p = softmax(logits)
    assert np.allclose(p.sum(-1), 1.0)
    m = probabilities_to_rgba(p)
    assert m[0, 0, 0] > 0.99 and m[0, 0, 3] > 0.99       # pele e pessoa
    assert m[0, 1, 1] > 0.99                              # cabelo
    assert m[1, 0, 3] < 0.01                              # fundo não é pessoa


def test_cilindro_unitario_vai_de_a_ate_b_com_o_raio():
    a, b, r = np.array([0.1, 0.2, -1.5]), np.array([0.3, -0.1, -1.4]), 0.05
    m = segment_matrix(a, b, r)
    assert np.allclose((m @ [0, 0, 0, 1])[:3], a)
    assert np.allclose((m @ [0, 1, 0, 1])[:3], b)
    for p in ([1, 0, 0, 1], [0, 0, 1, 1], [1, 0.5, 0, 1]):
        q = (m @ p)[:3]                                   # na superfície: distância r do eixo
        t = np.dot(q - a, b - a) / np.dot(b - a, b - a)
        assert np.isclose(np.linalg.norm(q - (a + t * (b - a))), r)


def test_esfera_e_instancias_dos_bracos():
    assert np.allclose(sphere_matrix(np.array([1.0, 2, 3]), 0.1) @ [1, 0, 0, 1], [1.1, 2, 3, 1])
    pts = np.random.default_rng(1).normal(size=(33, 3)) * 0.3 + [0, 0, -1.5]
    cyl, sph = arm_instances(pts, 1.1)
    assert cyl.shape == (6, 4, 4) and sph.shape == (6, 4, 4)
    assert np.isfinite(cyl).all() and np.isfinite(sph).all()
