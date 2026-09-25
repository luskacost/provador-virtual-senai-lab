import numpy as np
import pytest

from provador import benchmark as bm
from provador.metrics import LatencyStats


def fake_session(fps=30.0, seconds=20.0, latency_ms=45.0, person=True, stall=None):
    """Sessão sintética: câmera regular de `fps`, render a 165 Hz, `stall` = (início, duração) sem quadros."""
    rec = bm.SessionRecorder(t0=100.0, t_end=100.0 + seconds)
    t = 100.0
    while t < rec.t_end:
        if not (stall and stall[0] <= t - 100.0 < stall[0] + stall[1]):
            rec.on_video(t, latency_ms)
            rec.on_pose(t, person)
        t += 1.0 / fps
    for k in range(int(seconds * 165)):
        rec.on_loop(100.0 + k / 165.0)
    for k in range(int(seconds * 30)):
        rec.stage("pose", 15.0 + (k % 5) * 0.5, 100.0 + k / 30.0)
        rec.stage("swap_wait", 5.5, 100.0 + k / 30.0)
    rec.system = [{"t": 100.0 + i, "proc_cores": 3.2, "cpu_total": 40.0, "rss_mb": 900.0, "gpu_util": 30.0,
                   "gpu_mem_mb": 2000.0, "gpu_temp": 60.0} for i in range(int(seconds))]
    return rec


def test_summarize():
    s = bm.summarize(range(1, 101))
    assert s["n"] == 100 and s["mean"] == pytest.approx(50.5) and s["p50"] == pytest.approx(50.5)
    assert s["p95"] == pytest.approx(95.05) and s["max"] == 100 and s["min"] == 1
    empty = bm.summarize([])
    assert empty["n"] == 0 and empty["mean"] == 0.0


def test_fps_por_segundo_conta_janelas_inteiras():
    ts = np.arange(0, 5.0, 1 / 30)                      # 30 FPS por 5 s
    series = bm.fps_per_second(ts, 0.0, 4.5)            # a janela parcial [4, 4.5) é descartada
    assert len(series) == 4 and (np.abs(series - 30) <= 1).all()
    assert bm.fps_per_second(ts, 3.0, 3.5).size == 0


def test_estatisticas_de_sessao_saudavel():
    rec = fake_session()
    stats = bm.compute_stats(rec, warmup_s=3.0)
    assert stats["duration_s"] == pytest.approx(17.0)
    assert stats["fps_video"]["mean"] == pytest.approx(30.0, abs=0.6)
    assert stats["fps_render"]["mean"] == pytest.approx(165.0, abs=2)
    assert stats["latency_ms"]["p95"] == pytest.approx(45.0)
    assert stats["stages_ms"]["pose"]["mean"] == pytest.approx(16.0, abs=0.2)
    assert stats["person_fraction"] == 1.0
    assert stats["system"]["gpu_util"]["mean"] == 30.0
    assert all(v["ok"] for v in bm.verdicts(stats))


def test_aquecimento_e_descartado():
    rec = fake_session()
    rec.latency = [(t, 500.0 if t < 102.9 else ms) for t, ms in rec.latency]       # latência alta só no início
    stats = bm.compute_stats(rec, warmup_s=3.0)
    assert stats["latency_ms"]["max"] == pytest.approx(45.0)


def test_veredito_pega_fps_baixo_e_latencia_alta():
    slow = bm.verdicts(bm.compute_stats(fake_session(fps=22.0), 3.0))
    assert not slow[0]["ok"] and not slow[1]["ok"]                                  # média e p1
    laggy = bm.verdicts(bm.compute_stats(fake_session(latency_ms=95.0), 3.0))
    assert not laggy[2]["ok"] and laggy[0]["ok"]


def test_travada_derruba_o_p1_mas_nao_a_media_alta():
    stats = bm.compute_stats(fake_session(seconds=40.0, stall=(20.0, 1.5)), 3.0)
    assert stats["fps_video"]["min"] < 24                                           # uma janela quase vazia
    assert stats["fps_video"]["p1"] < bm.GOALS["fps_p1"]
    assert not bm.verdicts(stats)[1]["ok"]


def test_sessao_sem_pessoa_e_invalida():
    stats = bm.compute_stats(fake_session(person=False), 3.0)
    assert not bm.verdicts(stats)[3]["ok"]
    assert "Sessão inválida" in bm.build_report(stats, {})


def test_relatorio_tem_as_secoes_e_o_veredito():
    rec = fake_session()
    stats = bm.compute_stats(rec, 3.0)
    meta = {"date": "25/09/2026 15:00", "environment": {"CPU": "teste"}, "config": {"Peças": 5}}
    md = bm.build_report(stats, meta, {"fps": "a.png", "latency": "b.png"}, raw_file="benchmarks/x.json")
    for trecho in ("# Desempenho", "## Resultado contra as metas", "✅ passou", "## Latência captura → tela",
                   "## Orçamento por estágio", "Pose (MediaPipe, CPU)", "## Recursos", "**CPU:** teste",
                   "![FPS efetivo por segundo](img/a.png)", "benchmarks/x.json", "Todas as metas foram atingidas"):
        assert trecho in md, trecho
    assert "❌" not in md


def test_graficos_sao_gerados(tmp_path):
    pytest.importorskip("matplotlib")
    rec = fake_session()
    files = bm.make_charts(rec, bm.compute_stats(rec, 3.0), tmp_path)
    assert set(files) == {"fps", "latency"}
    assert all((tmp_path / f).stat().st_size > 2000 for f in files.values())


def test_latency_stats_guarda_historico_so_quando_pedido():
    ls = LatencyStats()
    ls.add(0.010)
    assert ls.history is None
    ls.keep_history()
    ls.add(0.020)
    assert len(ls.history) == 1 and ls.history[0][1] == pytest.approx(20.0)


def test_sampler_roda_sem_nvml(monkeypatch):
    import sys
    import time

    monkeypatch.setitem(sys.modules, "pynvml", None)              # simula ausência do NVML
    rec = bm.SessionRecorder()
    sampler = bm.SystemSampler(rec, period=0.05)
    sampler.start()
    time.sleep(0.3)
    sampler.stop()
    assert len(rec.system) >= 2 and "gpu_util" not in rec.system[0] and rec.system[0]["rss_mb"] > 0


def test_diagnostico_aponta_a_webcam_quando_o_processamento_da_conta():
    lenta = bm.compute_stats(fake_session(fps=15.0), 3.0)          # pose ~16 ms → comporta ~60 FPS
    diag = bm.diagnosis(lenta)
    assert diag and "webcam" in diag and "pouca luz" in diag
    assert bm.diagnosis(bm.compute_stats(fake_session(fps=30.0), 3.0)) is None
    assert "Diagnóstico" in bm.build_report(lenta, {})


def test_diagnostico_aponta_o_processamento_quando_ele_e_o_gargalo():
    rec = fake_session(fps=15.0)
    rec.stages["pose"] = [(100.0 + k / 30.0, 60.0) for k in range(600)]       # pose a 60 ms: só ~16 FPS
    diag = bm.diagnosis(bm.compute_stats(rec, 3.0))
    assert diag and "não comporta" in diag
