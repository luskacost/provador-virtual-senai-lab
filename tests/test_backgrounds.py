import json

import cv2
import numpy as np
import pytest

from provador import backgrounds as bgm
from provador.backgrounds import BackgroundSelector, cover_scale, load_background, load_backgrounds


def make_scene(root, name, meta=None, color=(120, 130, 140), size=(64, 48), image_name="background.jpg"):
    folder = root / name
    folder.mkdir(parents=True)
    if image_name:
        cv2.imwrite(str(folder / image_name), np.full((size[1], size[0], 3), color, np.uint8))
    if meta is not None:
        (folder / "meta.json").write_text(meta if isinstance(meta, str) else json.dumps(meta), encoding="utf-8")
    return folder


def test_catalogo_carrega_e_ordena_por_pasta(tmp_path):
    make_scene(tmp_path, "b_loja", {"name": "Loja", "color_match": 0.5})
    make_scene(tmp_path, "a_estudio", {"name": "Estudio"})
    loaded, problems = load_backgrounds(tmp_path)
    assert not problems
    assert [b.id for b in loaded] == ["a_estudio", "b_loja"]
    assert [b.name for b in loaded] == ["Estudio", "Loja"]
    assert loaded[0].color_match == bgm.DEFAULT_COLOR_MATCH and loaded[1].color_match == 0.5


def test_meta_e_opcional_e_o_id_vira_nome(tmp_path):
    make_scene(tmp_path, "sem_meta", meta=None)
    bg = load_background(tmp_path / "sem_meta")
    assert bg.name == "sem_meta" and bg.color_match == bgm.DEFAULT_COLOR_MATCH


@pytest.mark.parametrize(("meta", "trecho"), [
    ("{isto nao e json", "meta.json inválido"),
    ("[1, 2]", "objeto JSON"),
    ({"type": "video"}, "não suportado"),
    ({"color_match": 1.5}, "entre 0 e 1"),
    ({"color_match": "muito"}, "entre 0 e 1"),
    ({"name": ""}, "texto não vazio"),
])
def test_meta_invalido_da_erro_claro(tmp_path, meta, trecho):
    make_scene(tmp_path, "ruim", meta)
    with pytest.raises(ValueError, match=trecho):
        load_background(tmp_path / "ruim")


def test_cenario_ruim_e_pulado_sem_derrubar_os_outros(tmp_path):
    make_scene(tmp_path, "ok", {"name": "Ok"})
    make_scene(tmp_path, "sem_imagem", {"name": "X"}, image_name=None)
    make_scene(tmp_path, "json_ruim", "{{")
    (tmp_path / "corrompida").mkdir()
    (tmp_path / "corrompida" / "background.jpg").write_bytes(b"nao e imagem")
    make_scene(tmp_path, "_ignorada", {"name": "Y"})              # pastas com _ ou . no início não entram
    loaded, problems = load_backgrounds(tmp_path)
    assert [b.id for b in loaded] == ["ok"]
    assert len(problems) == 3
    assert any("sem_imagem" in p and "sem imagem" in p for p in problems)
    assert any("corrompida" in p and "ler" in p for p in problems)


def test_pasta_inexistente_da_lista_vazia(tmp_path):
    assert load_backgrounds(tmp_path / "nao_existe") == ([], [])


def test_imagem_grande_e_reduzida_e_media_linear(tmp_path):
    make_scene(tmp_path, "grande", size=(3000, 1500), color=(128, 128, 128))
    bg = load_background(tmp_path / "grande")
    assert bg.image.shape[1] == bgm.MAX_WIDTH and bg.image.shape[0] == 960
    assert bg.mean_lin == pytest.approx([0.2158, 0.2158, 0.2158], abs=0.003)     # sRGB 128 ≈ 0,216 linear


def test_cover_scale():
    assert cover_scale(1920, 1080, 1280, 720) == (1.0, 1.0)
    sx, sy = cover_scale(2000, 1000, 1280, 720)                    # cenário mais largo: corta dos lados
    assert sx == pytest.approx((1280 / 720) / 2.0) and sy == 1.0
    sx, sy = cover_scale(1000, 1000, 1280, 720)                    # mais alto: corta em cima e embaixo
    assert sx == 1.0 and sy == pytest.approx(1.0 / (1280 / 720))
    assert cover_scale(0, 10, 100, 100) == (1.0, 1.0)


def test_seletor_em_ciclo_com_fundo_real():
    s = BackgroundSelector(count=3)
    assert s.real
    assert [s.step(+1) for _ in range(5)] == [0, 1, 2, -1, 0]
    assert s.step(-1) == -1 and s.step(-1) == 2 and not s.real
    vazio = BackgroundSelector(count=0)
    assert vazio.step(+1) == -1 and vazio.step(-1) == -1


# --- refinamento da borda na GPU ---------------------------------------------------------------
@pytest.fixture(scope="module")
def gl():
    moderngl = pytest.importorskip("moderngl")
    try:
        ctx = moderngl.create_standalone_context(require=330)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"sem contexto OpenGL: {exc}")
    yield ctx
    ctx.release()


def render_alpha(gl, video_bgr, mask_alpha_lowres):
    """Roda o composite.frag: pessoa branca sobre cenário azul → o canal R do resultado é o alfa refinado."""
    import moderngl

    from provador.composite import Compositor, texture_from_bgr

    h, w = video_bgr.shape[:2]
    mh, mw = mask_alpha_lowres.shape
    mask = np.zeros((mh, mw, 4), np.uint8)
    mask[..., 3] = np.round(mask_alpha_lowres * 255)
    mask_tex = gl.texture((mw, mh), 4, mask.tobytes())
    mask_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
    guide = cv2.resize(video_bgr, (mw, mh), interpolation=cv2.INTER_AREA)
    video_tex = texture_from_bgr(gl, video_bgr, mipmaps=False)
    guide_tex = texture_from_bgr(gl, guide, mipmaps=False, nearest=True)
    bg_tex = texture_from_bgr(gl, np.full((4, 4, 3), (255, 0, 0), np.uint8), mipmaps=False)       # azul (BGR)
    fbo = gl.framebuffer([gl.texture((w, h), 4)])
    fbo.use()
    gl.viewport = (0, 0, w, h)
    Compositor(gl).draw(video_tex, mask_tex, guide_tex, bg_tex, mirror=False, bg_scale=(1.0, 1.0))
    img = np.frombuffer(fbo.read(components=3), np.uint8).reshape(h, w, 3)[::-1]
    return img[..., 0].astype(float) / 255.0                        # canal R = alfa da pessoa


def test_borda_refinada_segue_a_imagem_e_nao_a_mascara_borrada(gl):
    w, h, mw, mh = 512, 256, 256, 128
    edge = 300                                                       # borda REAL: pessoa branca à esquerda
    video = np.zeros((h, w, 3), np.uint8)
    video[:, :edge] = 255
    tx = np.arange(mw) + 0.5
    ramp = np.clip(0.5 - (tx - 151.5) / 8.0, 0.0, 1.0)              # máscara do modelo: rampa larga e 3 px deslocada
    mask = np.tile(ramp, (mh, 1))
    alpha = render_alpha(gl, video, mask)[h // 2]

    assert (np.diff(alpha[250:350]) <= 1e-6).all()                   # feather monotônico (sem halo nem cintilação)
    assert alpha[:296].min() > 0.95 and alpha[312:].max() < 0.05    # pessoa inteira / fundo inteiro fora da borda
    cross = np.flatnonzero(alpha < 0.5)[0]
    bilinear = np.interp(np.arange(w) + 0.5, tx * (w / mw), ramp)   # ampliação simples da mesma máscara
    cross_bilinear = np.flatnonzero(bilinear < 0.5)[0]
    assert abs(cross - edge) <= 1.5
    assert abs(cross - edge) < abs(cross_bilinear - edge)            # o refinamento é melhor que só ampliar


def test_sem_pessoa_o_quadro_vira_so_cenario(gl):
    video = np.full((64, 128, 3), 255, np.uint8)
    alpha = render_alpha(gl, video, np.zeros((32, 64)))
    assert alpha.max() < 0.02
    pessoa = render_alpha(gl, video, np.ones((32, 64)))
    assert pessoa.min() > 0.98
