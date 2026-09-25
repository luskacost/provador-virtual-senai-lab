import pytest

from provador import ui
from provador.catalog import Selector, find_garments, load_catalog
from provador.template import DEMO_CATALOG, write_demo_catalog


def test_selector_circular_e_limites():
    s = Selector(count=5)
    assert s.step(+1) and s.index == 1
    assert s.step(-1) and s.step(-1) and s.index == 4          # volta pelo início
    assert s.step(+1) and s.index == 0
    assert s.select(3) and s.index == 3
    assert not s.select(3)                                     # já é a atual
    assert not s.select(9) and not s.select(-1) and s.index == 3


def test_selector_com_uma_peca_nao_navega():
    s = Selector(count=1)
    assert not s.step(+1) and s.index == 0
    assert not Selector(count=0).step(+1)


def test_catalogo_demo_carrega_com_nomes_e_ordem(tmp_path):
    write_demo_catalog(tmp_path)
    garments, problems = load_catalog(tmp_path)
    assert not problems
    assert [g.name for g in garments] == [d[1] for d in DEMO_CATALOG]
    assert len({tuple(g.base_color) for g in garments}) == len(DEMO_CATALOG)
    assert garments[3].positions[:, 0].max() < garments[2].positions[:, 0].max()     # manga curta × longa


def test_catalogo_pula_glb_invalido_sem_derrubar(tmp_path):
    write_demo_catalog(tmp_path)
    (tmp_path / "quebrada.glb").write_bytes(b"isto nao e um glb")
    garments, problems = load_catalog(tmp_path)
    assert len(garments) == len(DEMO_CATALOG)
    assert len(problems) == 1 and "quebrada.glb" in problems[0]


def test_find_garments_arquivo_unico_e_pasta_vazia(tmp_path):
    path = write_demo_catalog(tmp_path)[0]
    assert find_garments(path) == [path]
    assert find_garments(tmp_path / "vazia") == []


def test_layout_centralizado_e_cabe_na_janela():
    lay = ui.layout(1280, 720, 5)
    assert len(lay.thumbs) == 5
    left, right = lay.prev[0], lay.next[0] + lay.next[2]
    assert abs(left - (1280 - right)) <= 1                     # simétrico
    for x, y, w, h in [*lay.thumbs, lay.prev, lay.next]:
        assert x >= 0 and x + w <= 1280 and y >= 0 and y + h <= 720


def test_layout_encolhe_miniaturas_em_janela_estreita():
    lay = ui.layout(500, 400, 9)
    assert lay.thumbs[0][2] < ui.THUMB
    assert lay.prev[0] >= 0 and lay.next[0] + lay.next[2] <= 500


def test_hit_test():
    lay = ui.layout(1280, 720, 5)
    x, y, w, h = lay.thumbs[2]
    assert ui.hit(lay, x + w / 2, y + h / 2) == ("piece", 2)
    assert ui.hit(lay, x + w + ui.GAP / 2, y + h / 2) is None          # vão entre miniaturas
    assert ui.hit(lay, lay.prev[0] + 5, lay.prev[1] + 5) == ("prev", 0)
    assert ui.hit(lay, lay.next[0] + 5, lay.next[1] + 5) == ("next", 0)
    assert ui.hit(lay, 10, 10) is None


def test_rect_para_ndc():
    assert ui.rect_to_ndc((0, 0, 1280, 720), 1280, 720) == (-1.0, -1.0, 1.0, 1.0)
    x0, y0, x1, y1 = ui.rect_to_ndc((640, 360, 640, 360), 1280, 720)      # quadrante inferior direito
    assert (x0, y0, x1, y1) == (0.0, -1.0, 1.0, 0.0)
    assert pytest.approx(ui.rect_to_ndc((320, 180, 640, 360), 1280, 720)[0]) == -0.5
