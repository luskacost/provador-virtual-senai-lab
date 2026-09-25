import cv2
import numpy as np
import pytest

from provador import lighting
from provador.lighting import DEFAULT_LIGHT, LightEstimator, fit_sh, sh_basis, skin_samples

IMG = (1280, 720)


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def random_normals(n=500, seed=0):
    rng = np.random.default_rng(seed)
    v = rng.normal(size=(n, 3))
    v[:, 2] = np.abs(v[:, 2])                       # hemisfério voltado à câmera
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_base_sh_e_ortonormal_na_esfera():
    rng = np.random.default_rng(1)
    v = rng.normal(size=(200000, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    y = sh_basis(v)
    gram = y.T @ y * (4 * np.pi / len(v))
    assert np.allclose(gram, np.eye(9), atol=0.03)


def test_fit_recupera_luz_de_baixa_ordem_sem_ruido():
    n = random_normals(2000)
    sh_true = lighting.PRIOR_SH.copy()
    sh_true[3] = 0.9                                 # luz vinda da direita (+x)
    lum = sh_basis(n) @ sh_true
    sh_fit = fit_sh(n, lum)
    e_true, e_fit = sh_basis(n) @ sh_true, sh_basis(n) @ sh_fit
    assert np.corrcoef(e_true, e_fit)[0, 1] > 0.995
    assert abs(sh_fit[3] - sh_true[3]) < 0.25


def test_fit_com_poucas_amostras_fica_perto_do_prior():
    n = random_normals(8)
    sh_fit = fit_sh(n, np.ones(8))
    assert np.abs(sh_fit[4:]).max() < 0.5             # termos de ordem 2 ficam contidos


def synthetic_scene(light_dir, ambient=0.25, gain=1.0, rgb_gain=(1.0, 1.0, 1.0)):
    """Rosto (esfera) iluminado por uma luz direcional, na máscara 256x256 e no quadro reduzido."""
    size = 256
    mask = np.zeros((size, size, 4), np.uint8)
    cx, cy, r = 128.0, 90.0, 30.0
    ys, xs = np.mgrid[0:size, 0:size]
    dx, dy = (xs - cx) / r, (ys - cy) / r
    inside = dx * dx + dy * dy < 1.0
    mask[inside, 2] = 255                            # pele do rosto
    mask[inside, 3] = 255
    n = np.stack([dx, -dy, np.sqrt(np.clip(1 - dx * dx - dy * dy, 0, 1))], -1)
    lam = np.clip(n @ unit(light_dir), 0, None)
    skin = lighting.srgb_to_linear(lighting.NOMINAL_SKIN_SRGB * 255.0)          # pele nominal × cor da luz
    lin = (ambient + 0.75 * lam)[..., None] * gain * np.array(rgb_gain) * skin / (skin @ lighting.LUMA)
    bg = 0.18 * gain * np.array(rgb_gain)                                        # fundo cinza sob a mesma luz
    lin = np.where(inside[..., None], lin * 0.35, bg)
    srgb = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.clip(lin, 0, 1) ** (1 / 2.4) - 0.055)
    frame = np.clip(srgb * 255, 0, 255).astype(np.uint8)
    px = np.zeros((33, 3))
    px[:9] = [cx, cy, 0]                             # nariz, olhos, orelhas (centro)
    px[lighting.L_EAR] = [cx - r, cy, 0]
    px[lighting.R_EAR] = [cx + r, cy, 0]
    px[:, :2] *= np.array([IMG[0] / size, IMG[1] / size])      # landmarks em pixels da imagem cheia
    vis = np.zeros(33)
    vis[:9] = 1.0
    return frame[..., ::-1].copy(), mask, px, vis


def run_estimator(scene, n=25, **kw):
    est = LightEstimator(smoothing=0.4, **kw)
    frame, mask, px, vis = scene
    for _ in range(n):
        light = est.update(frame, mask, px, vis, IMG)
    return light


@pytest.mark.parametrize("direction", [(-1, 0.2, 0.6), (1, 0.2, 0.6), (0, 1, 0.5)])
def test_estimador_acha_a_direcao_da_luz(direction):
    light = run_estimator(synthetic_scene(direction))
    assert light.n_samples > 500
    assert light.direction @ unit(direction) > 0.75
    left, right = light.eval(np.array([[-0.7, 0, 0.7]])), light.eval(np.array([[0.7, 0, 0.7]]))
    assert (left > right)[0] == (direction[0] < 0) or direction[0] == 0


def test_exposicao_acompanha_o_brilho():
    bright = run_estimator(synthetic_scene((0, 0, 1), gain=1.0))
    dark = run_estimator(synthetic_scene((0, 0, 1), gain=0.25))
    assert dark.exposure < bright.exposure * 0.85


def test_balanco_de_branco_segue_a_cor_da_luz():
    warm = run_estimator(synthetic_scene((0, 0, 1), rgb_gain=(1.3, 1.0, 0.7)), wb_strength=0.8)
    cool = run_estimator(synthetic_scene((0, 0, 1), rgb_gain=(0.75, 1.0, 1.3)), wb_strength=0.8)
    assert warm.tint[0] > warm.tint[2] and cool.tint[2] > cool.tint[0]
    assert warm.tint[0] / warm.tint[2] > cool.tint[0] / cool.tint[2]
    neutral = run_estimator(synthetic_scene((0, 0, 1)), wb_strength=0.8)
    assert np.allclose(neutral.tint, 1.0, atol=0.05)                   # luz neutra → sem tinta
    off = run_estimator(synthetic_scene((0, 0, 1), rgb_gain=(1.3, 1.0, 0.7)), wb_strength=0.0)
    assert np.allclose(off.tint, 1.0, atol=1e-6)                       # força 0 desliga


def test_sem_amostras_mantem_a_luz_anterior():
    est = LightEstimator()
    frame, mask, px, vis = synthetic_scene((1, 0, 1))
    est.update(frame, mask, px, vis, IMG)
    before = est.light
    assert est.update(frame, np.zeros_like(mask), px, vis, IMG) is before      # máscara vazia
    est.reset()
    assert est.light is DEFAULT_LIGHT


def test_amostras_de_braco_tem_normais_de_cilindro():
    mask = np.zeros((256, 256, 4), np.uint8)
    cv2.line(mask, (40, 128), (200, 128), (255, 0, 0, 255), 30)              # braço horizontal, pele
    px = np.zeros((33, 3))
    px[11, :2], px[13, :2] = [40 * 5, 128 * 2.8125], [200 * 5, 128 * 2.8125]
    vis = np.zeros(33)
    vis[[11, 13]] = 1.0
    coords, normals = skin_samples(mask, px, vis, IMG)
    assert len(normals) > 300
    assert np.allclose(np.linalg.norm(normals, axis=1), 1.0, atol=1e-6)
    above = normals[coords[:, 1] < 128 - 4]
    below = normals[coords[:, 1] > 128 + 4]
    assert above[:, 1].mean() > 0.2 and below[:, 1].mean() < -0.2          # acima olha para cima (y da câmera)


def test_paridade_glsl_numpy():
    """A função sh_eval() do shader tem de bater com sh_basis() do numpy."""
    moderngl = pytest.importorskip("moderngl")
    from provador.garment_render import sh_glsl

    try:
        ctx = moderngl.create_standalone_context(require=330)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"sem contexto OpenGL: {exc}")
    src = ("#version 330\nuniform float sh[9];\n" + sh_glsl()
           + "\nin vec3 n;\nout float e;\nvoid main() { e = sh_eval(normalize(n)); }\n")
    prog = ctx.program(vertex_shader=src, varyings=["e"])
    rng = np.random.default_rng(3)
    coeffs = rng.normal(size=9)
    prog["sh"].value = tuple(coeffs)
    v = rng.normal(size=(64, 3)).astype("f4")
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    vao = ctx.vertex_array(prog, [(ctx.buffer(v.tobytes()), "3f", "n")])
    out = ctx.buffer(reserve=64 * 4)
    vao.transform(out, 0, vertices=64)
    gpu = np.frombuffer(out.read(), np.float32)
    assert np.abs(gpu - sh_basis(v.astype(float)) @ coeffs).max() < 1e-4
    ctx.release()
