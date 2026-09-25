import cv2
import numpy as np
import pytest

from provador import garment, photos
from provador import template as tpl

BG = (244, 226, 219)                  # BGR, o lilás da foto real
WHITE = (250, 250, 250)


def shirt_view(canvas_w=500, canvas_h=420, marker=None, sleeve_tip_marker=None, sleeves=True):
    """Camiseta sintética vista de frente: tronco 200 px de largura, ombros inclinados e mangas em diagonal."""
    img = np.full((canvas_h, canvas_w, 3), BG, np.uint8)
    body = [(200, 60), (300, 60), (350, 100), (350, 380), (150, 380), (150, 100)]
    cv2.fillPoly(img, [np.array(body, np.int32)], WHITE)
    if sleeves:
        left = [(150, 100), (60, 170), (90, 225), (150, 160)]
        right = [(350, 100), (440, 170), (410, 225), (350, 160)]
        cv2.fillPoly(img, [np.array(left, np.int32), np.array(right, np.int32)], WHITE)
    if marker:
        (x, y), color = marker
        cv2.rectangle(img, (x - 12, y - 12), (x + 12, y + 12), color, -1)
    if sleeve_tip_marker:
        (x, y), color = sleeve_tip_marker
        cv2.circle(img, (x, y), 8, color, -1)
    return img


def sheet_of(*views, gap=60):
    h = max(v.shape[0] for v in views)
    parts = []
    for v in views:
        parts += [np.pad(v, ((0, h - v.shape[0]), (0, 0), (0, 0)), constant_values=0), np.full((h, gap, 3), BG, np.uint8)]
    sheet = np.hstack(parts[:-1])
    sheet[(sheet == 0).all(axis=2)] = BG
    return sheet


RED, GREEN, BLUE = (40, 40, 220), (60, 190, 60), (220, 60, 40)


@pytest.fixture(scope="module")
def sheet():
    front = shirt_view(marker=((250, 170), RED), sleeve_tip_marker=((80, 205), BLUE))
    back = shirt_view(marker=((250, 250), GREEN))
    return sheet_of(front, back)


def test_recorte_separa_e_ordena_as_vistas(sheet):
    views = photos.split_views(sheet)
    assert [v.name for v in views] == ["frente", "costas"]
    assert views[0].bbox[0] < views[1].bbox[0]
    assert all(v.mask.sum() > 20000 for v in views)


def test_fundo_liso_e_erosao_nao_deixam_franja():
    img = shirt_view()
    mask = photos.garment_mask(img)
    assert mask[200, 250] and not mask[5, 5] and not mask[400, 20]
    filled, _core = photos.fill_outside(img, mask)
    dist = np.abs(filled.astype(int) - np.array(BG)).sum(axis=2)
    assert (dist < 30).sum() == 0                       # nenhum pixel com a cor do fundo depois do preenchimento


def test_nearest_fill():
    img = np.zeros((5, 5, 3), np.uint8)
    img[2, 2] = (10, 20, 30)
    valid = np.zeros((5, 5), bool)
    valid[2, 2] = True
    assert (photos.nearest_fill(img, valid) == (10, 20, 30)).all()
    img2 = np.zeros((1, 6, 3), np.uint8)
    img2[0, 0], img2[0, 5] = 50, 200
    valid2 = np.array([[True, False, False, False, False, True]])
    out = photos.nearest_fill(img2, valid2)
    assert out[0, 1, 0] == 50 and out[0, 4, 0] == 200


def test_analise_acha_axila_bordas_e_mangas(sheet):
    front = photos.split_views(sheet)[0]
    an = photos.analyze_view(photos.fill_outside(front.rgb, front.mask)[1])
    x0 = front.bbox[0]
    assert set(an.sleeves) == {"left", "right"}
    r_armpit = an.armpit_row
    assert 60 < r_armpit - (front.bbox[1] - 0) + 60 and r_armpit < 200
    mid = (an.top + an.bottom) // 2 + 40
    body_w = an.body_right[mid] - an.body_left[mid]
    assert body_w == pytest.approx(200, abs=6)
    right = an.sleeves["right"]
    assert right.axis[0] > 0.3 and right.axis[1] > 0.3                      # desce para fora
    assert right.up[1] < 0                                                    # "cima" aponta para cima na imagem
    assert x0 >= 0


def test_sem_mangas_soltas_nao_quebra():
    img = shirt_view(sleeves=False)
    views = photos.split_views(img)
    assert len(views) == 1
    an = photos.analyze_view(photos.fill_outside(views[0].rgb, views[0].mask)[1])
    assert an.sleeves == {}
    mesh = tpl.build_tshirt()
    geo = photos.template_geometry(mesh, 0.33, 0.95)
    flat, cover = photos.flatten_view(views[0].rgb, views[0].mask, geo, 256, 240)
    assert cover.mean() > 0.3 and flat.shape == (240, 256, 3)


def centroid(img, color, tol=60):
    ys, xs = np.nonzero(np.abs(img.astype(int) - np.array(color)).sum(axis=2) < tol)
    return (xs.mean(), ys.mean(), len(xs)) if len(xs) else None


def test_atlas_poe_cada_marcador_no_lugar_certo(sheet):
    front, back = photos.split_views(sheet)
    mesh = tpl.build_tshirt()
    atlas, info = photos.build_atlas(front, back, mesh, 0.33, 0.95, size=1024)
    h, w = atlas.shape[:2]
    assert w == 1024 and info["front_coverage"] > 0.5 and info["front_sleeves"] == ["left", "right"]

    red = centroid(atlas, RED)                      # quadrado no centro do peito, só na frente
    assert red and red[2] > 200
    assert red[0] == pytest.approx(w * 0.25, abs=w * 0.03)                  # centro da metade esquerda
    assert 0.2 * h < red[1] < 0.65 * h

    green = centroid(atlas, GREEN)                  # marcador das costas, só na metade direita
    assert green and green[0] == pytest.approx(w * 0.75, abs=w * 0.03) and green[2] > 200
    assert centroid(atlas[:, : w // 2], GREEN) is None and centroid(atlas[:, w // 2:], RED) is None

    blue = centroid(atlas, BLUE)                    # ponta da manga esquerda da IMAGEM = x negativo do molde
    assert blue is not None
    assert blue[0] < w * 0.25 and blue[1] < 0.35 * h                       # metade esquerda da frente, na altura das mangas


def test_atlas_sem_franja_do_fundo(sheet):
    front, back = photos.split_views(sheet)
    atlas, _ = photos.build_atlas(front, back, tpl.build_tshirt(), 0.33, 0.95, size=512)
    dist = np.abs(atlas.astype(int) - np.array(BG)).sum(axis=2)
    assert (dist < 25).mean() < 0.001


def test_glb_com_textura_faz_roundtrip_e_entra_no_catalogo(tmp_path, sheet):
    from provador.catalog import load_catalog

    front, back = photos.split_views(sheet)
    mesh = tpl.build_tshirt()
    atlas, _ = photos.build_atlas(front, back, mesh, 0.33, 0.95, size=512)
    ok, png = cv2.imencode(".png", atlas)
    assert ok
    tpl.write_glb(mesh, tmp_path / "photo_teste.glb", name="Camiseta Teste", color=(1, 1, 1, 1),
                  texture_png=png.tobytes())
    tpl.write_glb(mesh, tmp_path / "01_lisa.glb", name="Lisa")
    garments, problems = load_catalog(tmp_path)
    assert not problems and [g.name for g in garments] == ["Lisa", "Camiseta Teste"]
    assert garments[0].texture is None
    tex = garments[1].texture
    assert tex.shape == atlas.shape and np.abs(tex.astype(int) - atlas.astype(int)).max() == 0     # PNG sem perdas
    assert garment.load_glb(tmp_path / "photo_teste.glb").uvs.shape == (len(mesh.positions), 2)


def test_folha_sem_peca_da_erro_claro():
    with pytest.raises(ValueError, match="nenhuma peça"):
        photos.split_views(np.full((200, 300, 3), BG, np.uint8))


def test_texture_gpu_e_amostrada_no_shader(tmp_path, sheet):
    """Com textura, o shader lê o atlas: um atlas vermelho produz uma peça avermelhada na tela."""
    moderngl = pytest.importorskip("moderngl")
    try:
        ctx = moderngl.create_standalone_context(require=330)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"sem contexto OpenGL: {exc}")
    from provador import skeleton as sk
    from provador.camera import gl_bytes, perspective
    from provador.garment_render import GarmentRenderer

    mesh = tpl.build_tshirt()
    red = np.full((128, 256, 3), RED, np.uint8)
    _ok, png = cv2.imencode(".png", red)
    tpl.write_glb(mesh, tmp_path / "vermelha.glb", texture_png=png.tobytes(), color=(1, 1, 1, 1))
    r = GarmentRenderer(ctx)
    r.current = r.load(garment.load_glb(tmp_path / "vermelha.glb"))
    size = 200
    tex = ctx.texture((size, size), 4)
    fbo = ctx.framebuffer([tex], ctx.depth_renderbuffer((size, size)))
    fbo.use()
    ctx.viewport = (0, 0, size, size)
    fbo.clear(0.0, 0.0, 0.0, 1.0, depth=1.0)
    r.set_pose(sk.skin_matrices(sk.world_matrices()), sk.translation((0, -1.22, -1.5)))
    r.prog["proj"].write(gl_bytes(perspective(38.0, 1.0)))
    r.prog["viewport"].value = (0.0, 0.0, float(size), float(size))
    r.prog["use_mask"].value = False
    r.prog["mirror"].value = False
    r.prog["inflate"].value = 0.0
    r.prog["grain"].value = 0.0
    r.prog["base_color"].value = (1.0, 1.0, 1.0, 1.0)
    r._bind_albedo(r.current)
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.disable(moderngl.CULL_FACE | moderngl.BLEND)
    r.current.vao.render(moderngl.TRIANGLES)
    px = np.frombuffer(fbo.read(components=3), np.uint8).reshape(size, size, 3).astype(int)
    lit = px[px.sum(axis=2) > 60]
    assert len(lit) > 2000
    assert lit[:, 0].mean() > 2.0 * lit[:, 2].mean() and lit[:, 0].mean() > 2.0 * lit[:, 1].mean()     # RGB: vermelho domina
    ctx.release()
