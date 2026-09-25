# Contexto para agentes (Antigravity / Claude / Codex)

Projeto: **Provador Virtual 3D em tempo real** — webcam + Python sobrepõem peças 3D de roupa ao corpo.

- Leia primeiro `docs/tasks.md` (plano, arquitetura, tasks T0–T14) e `docs/hardware.md` (máquina alvo e ajustes).
- Cenários atrás do usuário (T7b): `docs/cenarios.md`.
- Relatórios de pesquisa: `docs/relatorio_stack.md`, `docs/relatorio_ia.md`.
- Stack: Python 3.11 (MediaPipe não roda em 3.13+), MediaPipe Pose/Segmenter na CPU, ModernGL + GLFW, LBS no shader.
- Metas: ≥30 FPS, <80 ms ponta a ponta. Nada de readback GPU→CPU no loop de render.
- Código em `src/provador/`, ferramentas em `tools/`, testes em `tests/` (`pytest`).
- Ao concluir uma task, atualize o status em `docs/tasks.md`.
- Ambiente: `tools\setup_env.bat` cria `.venv`; `python -m provador.check --camera` valida.
- Desempenho: `python tools/benchmark.py --seconds 60` gera `docs/desempenho.md` (feche outros apps que usem a webcam; com pouca luz a webcam cai para 15 FPS).
- Cenários atrás do usuário: `python tools/make_backgrounds.py` (tecla B no app; ver `docs/cenarios.md`).
- Fotos → peça: `python tools/garment_from_photos.py --sheet folha.jpg --name "Nome"` (ver `docs/fotos.md`; fotos e GLBs `photo_*` ficam fora do git).
- Futuro: realismo e IA generativa em `docs/roadmap_realismo.md` (anotado, não implementado).
