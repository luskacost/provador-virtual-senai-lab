"""Benchmark de uma sessão real: roda o app por N segundos gravando métricas e gera docs/desempenho.md.

Uso:  python tools/benchmark.py [--seconds 60] [--cycle 5] [--out docs/desempenho.md]

Fique de frente para a câmera (ombros e cintura visíveis). Primeiros 20 s parado; depois mova os braços e
gire o tronco. A peça troca sozinha a cada --cycle segundos, para incluir o custo da troca.
Feche outros apps que usem a webcam. Os dados brutos vão para benchmarks/ (fora do git).
"""

import argparse
import datetime
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from provador import paths
from provador.app import App, build_parser
from provador.benchmark import (
    SessionRecorder,
    build_report,
    compute_stats,
    make_charts,
    save_raw,
    verdicts,
)


def environment(app: App) -> dict:
    import importlib.metadata as md

    import psutil

    env = {
        "Máquina": platform.node() or "?",
        "SO": platform.platform(),
        "CPU": f"{platform.processor()} ({psutil.cpu_count(logical=False)}c/{psutil.cpu_count()}t)",
        "RAM": f"{psutil.virtual_memory().total / 1024**3:.1f} GB",
        "OpenGL (renderer)": app.gl_renderer,
        "Python": platform.python_version(),
    }
    try:
        import pynvml

        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(h)
        drv = pynvml.nvmlSystemGetDriverVersion()
        env["GPU"] = (f"{name.decode() if isinstance(name, bytes) else name}, "
                      f"{pynvml.nvmlDeviceGetMemoryInfo(h).total / 1024**3:.0f} GB, "
                      f"driver {drv.decode() if isinstance(drv, bytes) else drv}")
    except Exception:  # noqa: BLE001 — sem NVIDIA/driver
        env["GPU"] = "NVML indisponível"
    for pkg in ("mediapipe", "onnxruntime-directml", "moderngl", "glfw", "opencv-python", "numpy"):
        try:
            env[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            pass
    return env


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")     # o console do Windows usa cp1252
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seconds", type=float, default=60.0, help="duração da sessão medida (sem o aquecimento)")
    ap.add_argument("--cycle", type=float, default=5.0, help="troca de peça a cada N s (0 = não troca)")
    ap.add_argument("--out", default=str(paths.DOCS / "desempenho.md"))
    ap.add_argument("--charts-dir", default=str(paths.DOCS / "img"), help="pasta dos PNG dos gráficos")
    ap.add_argument("--no-charts", action="store_true")
    ap.add_argument("--camera-index", type=int, default=0)
    args = ap.parse_args()

    warmup = 3.0
    app_args = build_parser().parse_args([
        "--seconds", str(args.seconds + warmup), "--cycle", str(args.cycle),
        "--camera-index", str(args.camera_index)])
    app = App(app_args)
    app.recorder = SessionRecorder()
    print(f"Benchmark de {args.seconds:.0f} s (+{warmup:.0f} s de aquecimento). Fique de frente para a câmera.")
    code = app.run()
    if code != 0:
        return code
    rec = app.recorder
    stats = compute_stats(rec, warmup)

    fit_error = rec.meta.get("fit_error_px", 0.0)
    meta = {
        "date": datetime.datetime.now().astimezone().strftime("%d/%m/%Y %H:%M"),
        "camera_fps": 30,
        "environment": environment(app),
        "config": {
            "Resolução da câmera": f"{app_args.width}x{app_args.height}",
            "Peças no catálogo": app.selector.count,
            "Troca de peça automática": f"a cada {args.cycle:g} s" if args.cycle else "desligada",
            "Segmentação": app.seg.provider if app.seg else "desligada",
            "Luz adaptativa": "ligada" if app.adaptive_light else "fixa",
            "FOV horizontal": f"{app_args.hfov:g}°",
            "Erro médio das articulações": f"{fit_error:.1f} px",
        },
    }
    stamp = datetime.datetime.now().astimezone().strftime("%Y%m%d_%H%M")
    raw = save_raw(rec, stats, meta, paths.ROOT / "benchmarks" / f"{stamp}.json")
    charts = {} if args.no_charts else make_charts(rec, stats, args.charts_dir)
    out = Path(args.out)
    out.write_text(build_report(stats, meta, charts, raw_file=str(raw.relative_to(paths.ROOT)).replace("\\", "/")),
                   encoding="utf-8")

    print(f"\nRelatório: {out}")
    for v in verdicts(stats):
        print(f"  {'OK   ' if v['ok'] else 'FALHA'} {v['name']}: {v['value']} (meta {v['goal']})")
    return 0 if all(v["ok"] for v in verdicts(stats)) else 2


if __name__ == "__main__":
    raise SystemExit(main())
