# Provador Virtual 3D

Webcam + Python sobrepõem peças 3D de roupa ao corpo do usuário em tempo real (meta: ≥30 FPS, <80 ms).
Plano completo e tasks em [`docs/tasks.md`](docs/tasks.md).

## Começando (Windows)

1. **Hardware:** dê dois cliques em `tools\check_hardware.bat` → gera `docs/hardware_raw.txt`.
2. **Ambiente:** dê dois cliques em `tools\setup_env.bat`. Ele:
   - cria `.venv` com Python **3.11** (via `uv`, ou `py -3.11`/`py -3.12`; o MediaPipe não roda em 3.13+);
   - instala `requirements-dev.txt` e o pacote em modo editável;
   - baixa os modelos do MediaPipe para `models/`;
   - roda `python -m provador.check --camera`.
3. **Antigravity:** *File → Open Folder…* nesta pasta. O interpretador `.venv` já está configurado em
   `.vscode/settings.json` e há configurações de execução em *Run and Debug*.

Sem Python 3.11/3.12 instalado: `winget install -e --id astral-sh.uv` (recomendado) ou
`winget install -e --id Python.Python.3.11`.

## Comandos

```powershell
.venv\Scripts\activate
python -m provador.check --camera   # T1: versões, placa usada pelo OpenGL, webcam
pytest                               # testes
python -m provador.app               # (a partir da T2)
```

## Estrutura

```
src/provador/   código do app (check, capture, pose, segmentation, renderer, ...)
tools/          setup, verificação de hardware, geração de peças, benchmark
assets/         garments/<id>/{garment.glb, meta.json, thumb.png} e templates/
models/         modelos do MediaPipe (baixados, fora do git)
docs/           plano, relatórios, hardware e desempenho
tests/          pytest
```
