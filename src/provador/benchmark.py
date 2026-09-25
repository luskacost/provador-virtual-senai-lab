"""T11: gravação de uma sessão, estatísticas, veredito contra as metas do plano e relatório em markdown.

O app grava (`SessionRecorder`) enquanto roda; `tools/benchmark.py` orquestra e chama `build_report`.
Estatísticas, veredito e relatório são funções puras (testáveis com dados sintéticos).
"""

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# Metas do plano (docs/tasks.md)
GOALS = {"fps_mean": 30.0, "fps_p1": 24.0, "latency_p95_ms": 80.0}
# A webcam entrega 30 FPS nominais e cada janela de 1 s conta quadros inteiros: ±0,5 FPS é ruído de contagem.
FPS_TOLERANCE = 0.5
WARMUP_S = 3.0                # o início (carregar modelos, primeiros frames) não entra nas estatísticas
MIN_PERSON_FRACTION = 0.8     # abaixo disso a sessão não representa o uso real (ninguém na frente da câmera)
# Orçamento por frame do plano (ms)
PLAN_BUDGET_MS = {"pose": 15.0, "segmentacao": 12.0, "render_cpu": 3.0}

INK, INK_2, SURFACE, SERIES, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#2a78d6", "#e4e3df"


# --- gravação ----------------------------------------------------------------------------------
@dataclass
class SessionRecorder:
    """Séries brutas de uma sessão. Todos os tempos são time.perf_counter() (segundos)."""

    t0: float = 0.0
    t_end: float = 0.0
    loop_ts: list[float] = field(default_factory=list)          # fim de cada iteração do laço de render
    video_ts: list[float] = field(default_factory=list)         # cada quadro de vídeo novo na tela
    pose_ts: list[float] = field(default_factory=list)          # cada pose nova aplicada
    pose_found: list[bool] = field(default_factory=list)
    latency: list[tuple[float, float]] = field(default_factory=list)          # (t, ms) captura → tela
    stages: dict[str, list[tuple[float, float]]] = field(default_factory=dict)  # nome → [(t, ms)]
    system: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def on_loop(self, t: float) -> None:
        self.loop_ts.append(t)

    def on_video(self, t: float, latency_ms: float) -> None:
        self.video_ts.append(t)
        self.latency.append((t, latency_ms))

    def on_pose(self, t: float, found: bool) -> None:
        self.pose_ts.append(t)
        self.pose_found.append(found)

    def stage(self, name: str, ms: float, t: float | None = None) -> None:
        self.stages.setdefault(name, []).append((time.perf_counter() if t is None else t, ms))

    def add_history(self, name: str, history: list[tuple[float, float]] | None) -> None:
        """Incorpora o histórico (t, ms) de um LatencyStats (ex.: a inferência do worker de pose)."""
        if history:
            self.stages.setdefault(name, []).extend(history)


class SystemSampler(threading.Thread):
    """Amostra CPU, RAM e GPU a 1 Hz numa thread própria (NVML ausente → só CPU/RAM)."""

    def __init__(self, rec: SessionRecorder, period: float = 1.0):
        super().__init__(name="sistema", daemon=True)
        self.rec, self.period = rec, period
        self._stop_evt = threading.Event()

    def stop(self) -> None:
        self._stop_evt.set()
        self.join(timeout=2.0)

    def run(self) -> None:
        import psutil

        proc = psutil.Process()
        proc.cpu_percent(None)
        psutil.cpu_percent(None)
        nv = None
        try:
            import pynvml

            pynvml.nvmlInit()
            nv = (pynvml, pynvml.nvmlDeviceGetHandleByIndex(0))
        except Exception:  # noqa: BLE001 — sem NVIDIA/driver: segue sem GPU
            nv = None
        while not self._stop_evt.wait(self.period):
            row = {"t": time.perf_counter(), "proc_cores": proc.cpu_percent(None) / 100.0,
                   "cpu_total": psutil.cpu_percent(None), "rss_mb": proc.memory_info().rss / 1e6}
            if nv:
                lib, h = nv
                try:
                    row["gpu_util"] = float(lib.nvmlDeviceGetUtilizationRates(h).gpu)
                    row["gpu_mem_mb"] = lib.nvmlDeviceGetMemoryInfo(h).used / 1e6
                    row["gpu_temp"] = float(lib.nvmlDeviceGetTemperature(h, lib.NVML_TEMPERATURE_GPU))
                except Exception:  # noqa: BLE001 — leitura pontual falhou: a linha sai sem os campos de GPU
                    row["gpu_error"] = 1.0
            self.rec.system.append(row)


# --- estatísticas ------------------------------------------------------------------------------
def summarize(values) -> dict:
    """n, média, p50, p95, p99, mínimo e máximo. Vazio → zeros."""
    v = np.asarray(list(values), float)
    if v.size == 0:
        return dict.fromkeys(("mean", "p50", "p95", "p99", "min", "max"), 0.0) | {"n": 0}
    return {"n": int(v.size), "mean": float(v.mean()), "p50": float(np.percentile(v, 50)),
            "p95": float(np.percentile(v, 95)), "p99": float(np.percentile(v, 99)),
            "min": float(v.min()), "max": float(v.max())}


def fps_per_second(timestamps, start: float, end: float) -> np.ndarray:
    """Eventos por segundo em janelas inteiras de 1 s entre start e end (a última janela parcial é descartada)."""
    n = int(np.floor(end - start))
    if n <= 0:
        return np.zeros(0)
    ts = np.asarray(timestamps, float)
    counts, _ = np.histogram(ts, bins=np.arange(n + 1) + start)
    return counts.astype(float)


def _fps_stats(timestamps, start: float, end: float) -> dict:
    series = fps_per_second(timestamps, start, end)
    if series.size == 0:
        return {"series": [], "mean": 0.0, "p1": 0.0, "min": 0.0}
    return {"series": series.tolist(), "mean": float(series.mean()),
            "p1": float(np.percentile(series, 1)), "min": float(series.min())}


def _after(pairs, start: float) -> list[float]:
    return [v for t, v in pairs if t >= start]


def compute_stats(rec: SessionRecorder, warmup_s: float = WARMUP_S) -> dict:
    """Todas as estatísticas da sessão (sem o aquecimento inicial)."""
    start, end = rec.t0 + warmup_s, rec.t_end
    loop = np.asarray([t for t in rec.loop_ts if t >= start])
    dt = np.diff(loop) if loop.size > 1 else np.zeros(0)
    found = [f for t, f in zip(rec.pose_ts, rec.pose_found, strict=True) if t >= start]
    sysrows = [r for r in rec.system if r["t"] >= start]

    def col(name):
        return [r[name] for r in sysrows if name in r]

    return {
        "duration_s": float(max(end - start, 0.0)),
        "warmup_s": warmup_s,
        "fps_video": _fps_stats(rec.video_ts, start, end),
        "fps_pose": _fps_stats(rec.pose_ts, start, end),
        "fps_render": {**_fps_stats(rec.loop_ts, start, end),
                       "p1_frame": float(1.0 / np.percentile(dt, 99)) if dt.size else 0.0},
        "latency_ms": summarize(_after(rec.latency, start)),
        "stages_ms": {name: summarize(_after(pairs, start)) for name, pairs in sorted(rec.stages.items())},
        "person_fraction": float(np.mean(found)) if found else 0.0,
        "system": {
            "proc_cores": summarize(col("proc_cores")), "cpu_total": summarize(col("cpu_total")),
            "rss_mb": summarize(col("rss_mb")), "gpu_util": summarize(col("gpu_util")),
            "gpu_mem_mb": summarize(col("gpu_mem_mb")), "gpu_temp": summarize(col("gpu_temp")),
        },
    }


def verdicts(stats: dict) -> list[dict]:
    """Compara com as metas. Cada item: nome, meta (texto), medido (texto) e ok (bool)."""
    fps, lat = stats["fps_video"], stats["latency_ms"]
    return [
        {"name": "FPS efetivo médio (vídeo + peça atualizados)", "goal": f"≥ {GOALS['fps_mean']:.0f}",
         "value": f"{fps['mean']:.1f}", "ok": fps["mean"] >= GOALS["fps_mean"] - FPS_TOLERANCE},
        {"name": "FPS efetivo p1 (janelas de 1 s)", "goal": f"≥ {GOALS['fps_p1']:.0f}",
         "value": f"{fps['p1']:.1f}", "ok": fps["p1"] >= GOALS["fps_p1"]},
        {"name": "Latência captura → tela p95", "goal": f"< {GOALS['latency_p95_ms']:.0f} ms",
         "value": f"{lat['p95']:.0f} ms", "ok": 0 < lat["p95"] < GOALS["latency_p95_ms"]},
        {"name": "Sessão válida (pessoa detectada)", "goal": f"≥ {MIN_PERSON_FRACTION:.0%}",
         "value": f"{stats['person_fraction']:.0%}", "ok": stats["person_fraction"] >= MIN_PERSON_FRACTION},
    ]


# --- gráficos ----------------------------------------------------------------------------------
def _style(ax) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def make_charts(rec: SessionRecorder, stats: dict, out_dir: str | Path) -> dict[str, str]:
    """Dois PNG (série única, cor 1 da paleta; metas em tracejado neutro com rótulo direto). Devolve nome → arquivo."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = {}

    series = stats["fps_video"]["series"]
    if series:
        fig, ax = plt.subplots(figsize=(8, 3.2), facecolor=SURFACE)
        _style(ax)
        x = np.arange(len(series)) + 1
        ax.plot(x, series, color=SERIES, linewidth=2, solid_capstyle="round")
        for y, label in ((GOALS["fps_mean"], "meta média 30"), (GOALS["fps_p1"], "meta p1 24")):
            ax.axhline(y, color=INK_2, linewidth=1, linestyle=(0, (4, 3)))
            ax.text(x[-1], y + 0.5, label, ha="right", va="bottom", fontsize=8.5, color=INK_2)
        ax.set_ylim(0, max(36, max(series) + 3))
        ax.set_xlim(x[0], x[-1])
        ax.set_xlabel("segundos de sessão (após o aquecimento)", color=INK_2, fontsize=9)
        ax.set_ylabel("quadros por segundo", color=INK_2, fontsize=9)
        ax.set_title(f"FPS efetivo por segundo: média {stats['fps_video']['mean']:.1f}, p1 {stats['fps_video']['p1']:.0f}",
                     loc="left", fontsize=11, color=INK)
        fig.tight_layout()
        files["fps"] = "desempenho_fps.png"
        fig.savefig(out / files["fps"], dpi=150, facecolor=SURFACE)
        plt.close(fig)

    lat = np.asarray(_after(rec.latency, rec.t0 + stats["warmup_s"]))
    if lat.size:
        fig, ax = plt.subplots(figsize=(8, 3.2), facecolor=SURFACE)
        _style(ax)
        top = max(GOALS["latency_p95_ms"] * 1.15, float(np.percentile(lat, 99.5)) * 1.1)
        bins = np.linspace(0, top, 41)
        counts, edges = np.histogram(np.clip(lat, 0, top), bins=bins)
        ax.bar(edges[:-1], counts, width=np.diff(edges), align="edge", color=SERIES, edgecolor=SURFACE, linewidth=1.5)
        ax.axvline(GOALS["latency_p95_ms"], color=INK_2, linewidth=1, linestyle=(0, (4, 3)))
        ymax = ax.get_ylim()[1]
        ax.text(GOALS["latency_p95_ms"] - top * 0.01, ymax * 0.95, "meta p95 < 80 ms", ha="right", va="top",
                fontsize=8.5, color=INK_2)
        p95 = stats["latency_ms"]["p95"]
        ax.axvline(p95, color=INK, linewidth=1.2)
        ax.text(p95 + top * 0.01, ymax * 0.80, f"p95 {p95:.0f} ms", ha="left", va="top", fontsize=8.5, color=INK)
        ax.set_xlim(0, top)
        ax.set_xlabel("latência captura → tela (ms)", color=INK_2, fontsize=9)
        ax.set_ylabel("quadros", color=INK_2, fontsize=9)
        ax.set_title(f"Latência: mediana {stats['latency_ms']['p50']:.0f} ms, p99 {stats['latency_ms']['p99']:.0f} ms",
                     loc="left", fontsize=11, color=INK)
        fig.tight_layout()
        files["latency"] = "desempenho_latencia.png"
        fig.savefig(out / files["latency"], dpi=150, facecolor=SURFACE)
        plt.close(fig)
    return files


# --- relatório ---------------------------------------------------------------------------------
STAGE_LABELS = {
    "pose": ("Pose (MediaPipe, CPU)", "inferência"), "segmentacao": ("Segmentação (ONNX, GPU)", "inferência"),
    "retarget": ("Retarget + oclusor", "CPU, thread principal"), "luz": ("Estimativa de luz", "CPU, a 10 Hz"),
    "upload_video": ("Envio do quadro à GPU", "CPU"), "render_cpu": ("Render (envio dos comandos)", "CPU"),
    "swap_wait": ("Espera do vsync", "bloqueado, sem GIL"), "troca_peca": ("Troca de peça (tecla → tela)", "evento"),
}


def _row(cells) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def build_report(stats: dict, meta: dict, charts: dict[str, str] | None = None, raw_file: str | None = None) -> str:
    """Markdown do relatório (docs/desempenho.md)."""
    checks = verdicts(stats)
    valid = checks[-1]["ok"]
    all_ok = all(c["ok"] for c in checks)
    fps_v, fps_p, fps_r = stats["fps_video"], stats["fps_pose"], stats["fps_render"]
    lat = stats["latency_ms"]
    s = ["# Desempenho", "",
         (f"Sessão de **{stats['duration_s']:.0f} s** (mais {stats['warmup_s']:.0f} s de aquecimento "
          f"descartados) em {meta.get('date', '?')}. Gerado por `python tools/benchmark.py`."), ""]
    if not valid:
        s += [("> ⚠️ **Sessão inválida:** a pessoa foi detectada em apenas "
               f"{stats['person_fraction']:.0%} do tempo. Fique em frente à câmera, com ombros e cintura visíveis, "
               "e rode de novo."), ""]
    s += ["## Resultado contra as metas", "", _row(["Métrica", "Meta", "Medido", "Resultado"]), _row(["---"] * 4)]
    s += [_row([c["name"], c["goal"], c["value"], "✅ passou" if c["ok"] else "❌ falhou"]) for c in checks]
    verdict = "Todas as metas foram atingidas." if all_ok else "Há metas não atingidas (veja acima)."
    s += ["", (f"**{verdict}** O FPS efetivo é o ritmo em que vídeo e peça se atualizam juntos; é limitado pela "
               f"webcam ({meta.get('camera_fps', 30)} FPS nominais), por isso a média tem tolerância de "
               f"±{FPS_TOLERANCE} FPS (cada janela de 1 s conta quadros inteiros)."), ""]
    if charts:
        for key, title in (("fps", "FPS efetivo por segundo"), ("latency", "Distribuição da latência")):
            if key in charts:
                s += [f"![{title}](img/{charts[key]})", ""]

    s += ["## Taxas", "", _row(["Fluxo", "Média", "p1 (janelas de 1 s)", "Mínimo"]), _row(["---"] * 4),
          _row(["Vídeo + peça na tela", f"{fps_v['mean']:.1f}", f"{fps_v['p1']:.0f}", f"{fps_v['min']:.0f}"]),
          _row(["Pose (landmarks novos)", f"{fps_p['mean']:.1f}", f"{fps_p['p1']:.0f}", f"{fps_p['min']:.0f}"]),
          _row(["Laço de render (vsync)", f"{fps_r['mean']:.0f}", f"{fps_r['p1']:.0f}", f"{fps_r['min']:.0f}"]), "",
          (f"Pior 1% dos quadros do laço de render: {fps_r['p1_frame']:.0f} FPS equivalentes "
           "(o render roda muito acima da câmera, então não é o gargalo)."), ""]

    s += ["## Latência captura → tela", "", _row(["Média", "p50", "p95", "p99", "Máx."]), _row(["---"] * 5),
          _row([f"{lat['mean']:.0f} ms", f"{lat['p50']:.0f} ms", f"{lat['p95']:.0f} ms", f"{lat['p99']:.0f} ms",
                f"{lat['max']:.0f} ms"]), "",
          ("Medida do instante em que o driver entrega o quadro até o fim do desenho na tela (inclui a pose "
           "desse quadro, o retarget e a espera do vsync, porque o vídeo exibido é o quadro que gerou a pose). "
           "**Não inclui a latência interna da webcam** (sensor → driver), que não é observável por software."), ""]

    s += ["## Orçamento por estágio", "", _row(["Estágio", "Onde", "Média", "p95", "Máx.", "Plano"]), _row(["---"] * 6)]
    for key, st in stats["stages_ms"].items():
        label, where = STAGE_LABELS.get(key, (key, ""))
        plan = PLAN_BUDGET_MS.get(key)
        s.append(_row([label, where, f"{st['mean']:.1f} ms", f"{st['p95']:.1f} ms", f"{st['max']:.1f} ms",
                       f"{plan:.0f} ms" if plan else "-"]))
    s += ["", ("Pose e segmentação rodam em threads paralelas, então o custo por quadro é o do estágio mais "
               "lento, não a soma."), ""]

    sysm = stats["system"]
    s += ["## Recursos", "", _row(["Recurso", "Média", "Máx."]), _row(["---"] * 3),
          _row(["CPU do processo (núcleos equivalentes)", f"{sysm['proc_cores']['mean']:.1f}", f"{sysm['proc_cores']['max']:.1f}"]),
          _row(["CPU total do sistema", f"{sysm['cpu_total']['mean']:.0f}%", f"{sysm['cpu_total']['max']:.0f}%"]),
          _row(["RAM do processo", f"{sysm['rss_mb']['mean']:.0f} MB", f"{sysm['rss_mb']['max']:.0f} MB"])]
    if sysm["gpu_util"]["n"]:
        s += [_row(["GPU (utilização)", f"{sysm['gpu_util']['mean']:.0f}%", f"{sysm['gpu_util']['max']:.0f}%"]),
              _row(["VRAM usada (toda a GPU)", f"{sysm['gpu_mem_mb']['mean']:.0f} MB", f"{sysm['gpu_mem_mb']['max']:.0f} MB"]),
              _row(["Temperatura da GPU", f"{sysm['gpu_temp']['mean']:.0f} °C", f"{sysm['gpu_temp']['max']:.0f} °C"])]
    s += [""]

    s += ["## Ambiente", ""]
    s += [f"- **{k}:** {v}" for k, v in meta.get("environment", {}).items()]
    s += ["", "## Configuração da sessão", ""]
    s += [f"- **{k}:** {v}" for k, v in meta.get("config", {}).items()]
    s += ["", "## Como reproduzir", "", "```",
          "python tools/benchmark.py --seconds 60", "```", "",
          ("Fique de frente para a câmera, com ombros e cintura visíveis. Nos primeiros 20 s, parado; depois mova "
           "os braços e gire o tronco. O benchmark troca de peça sozinho a cada 5 s. Feche outros apps que usem a "
           "webcam (eles a dividem e derrubam o FPS).")]
    if raw_file:
        s += ["", f"Dados brutos: `{raw_file}` (fora do git)."]
    return "\n".join(s) + "\n"


def save_raw(rec: SessionRecorder, stats: dict, meta: dict, path: str | Path) -> Path:
    """JSON com as estatísticas e as séries por segundo (as séries por quadro ficam de fora, pelo tamanho)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"meta": meta, "stats": stats, "system": rec.system}, indent=1, default=float),
                 encoding="utf-8")
    return p
