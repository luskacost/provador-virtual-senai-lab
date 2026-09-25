# Provador Virtual 3D · Plano e tasks

> Plano aprovado em 23/09/2026. Meta: **≥30 FPS** e **<80 ms** de ponta a ponta, navegação simples entre as peças.

## Decisões

| Item | Escolha |
|---|---|
| Plataforma | Desktop + webcam, Windows 11 |
| Hardware | GPU NVIDIA (ver "Hardware desta máquina") |
| Peças | Modelos 3D (template + textura das fotos; imagem→3D por IA para formatos próprios) |
| Abordagem | Híbrida: ajuste geométrico + IA leve (pose + segmentação) |
| Escopo | Protótipo, 5 a 10 peças superiores |
| Foto HD por difusão | v2 |

**Fotos das peças:** frente e costas, peça estendida sem ninguém vestindo, luz uniforme, fundo liso, ≥1024 px.

## Arquitetura

```
Thread de captura (OpenCV, 720p, sempre o frame mais recente)
   ├─► Worker de pose (MediaPipe VIDEO, full) ─► One Euro ─► retarget → rotações dos ossos
   └─► Worker de segmentação (Multiclass 256) ─► máscaras (pele do corpo, cabelo, rosto, roupa)
Loop de render (ModernGL + GLFW):
   textura da webcam (fundo) → peça com LBS na GPU (câmera alinhada à webcam)
   → composição: braços, mãos e cabelo recolocados por cima quando estão à frente (z do landmark)
   → luz: ambiente, SH de ordem 2 estimados na pele, balanço de branco
   → interface (setas, botões e miniaturas em GL) e HUD de métricas
```

Orçamento por frame (~35 ms): captura 5 · pose 15 · segmentação 12 (em paralelo à pose) · render + composição 3.

## Tasks

Status: ✅ feito · 🔄 em andamento · ⬜ a fazer

| # | Prio | Status | Task | Pronto quando |
|---|---|---|---|---|
| T0 | P0 | ✅ | Salvar `docs/relatorio_stack.md`, `relatorio_ia.md` e `tasks.md` | Os arquivos existem com o conteúdo do plano |
| T1 | P0 | ✅ | Ambiente: venv Python 3.11 + mediapipe, opencv-python, moderngl, glfw, pygltflib, trimesh, numpy, psutil, pynvml | `python -m provador.check` mostra versões e a placa usada pelo OpenGL |
| T2 | P0 | ✅ | Captura em thread própria + janela GLFW com a webcam + HUD de FPS | Vídeo 720p com ≥30 FPS |
| T3 | P0 | ✅ | Pose (VIDEO, full) + One Euro, esqueleto no modo debug | Landmarks ≥30 Hz; parado, desvio-padrão dos ombros <2 px |
| T4 | P0 | ✅ | `tools/make_template.py`: camiseta procedural rigada no esqueleto padrão | GLB carrega e deforma ao girar os ossos |
| T5 | P0 | ✅ | Renderer: GLB, LBS no vertex shader, projeção alinhada à webcam | Peça estática sobre o vídeo, MSAA, sem readback para a CPU |
| T6 | P0 | ✅ | Retarget: tronco, ombros, braços; escala por ombros/tronco; torção ±30° | Erro médio <15 px entre articulações da peça e landmarks |
| T7 | P0 | ✅ | Segmentação assíncrona + oclusão do braço + dilatação da peça | Braço cruzado à frente aparece sobre a peça, sem cintilar |
| T7b | P1 | 🔄 | Cenários atrás do usuário (troca de fundo pela máscara), tecla B — ver [`cenarios.md`](cenarios.md) | Troca sem queda de FPS e sem halo visível nos ombros |
| T8 | P0 | ✅ | Navegação: ←/→, teclas 1–9, miniaturas clicáveis, GLBs pré-carregados | Troca entre 5 peças <100 ms, sem queda de FPS |
| T9 | P1 | 🔄 | `tools/garment_from_photos.py`: recorte, projeção na UV do template, `meta.json` | Fotos de uma peça real viram GLB com textura certa no app |
| T10 | P1 | ✅ | Luz: SH ordem 2, exposição, balanço de branco, grão leve, PBR simples | A peça acompanha mudanças de luz do ambiente |
| T11 | P1 | ✅ | Métricas + `tools/benchmark.py` → `docs/desempenho.md` | Relatório gerado numa sessão de 60 s |
| T12 | P2 | ⬜ | `tools/blender_rig.py` + imagem→3D (TRELLIS ou Hunyuan3D) | Jaqueta gerada por IA, rigada, funcionando no app |
| T13 | P2 | ⬜ | Plano B de desempenho: rtmlib RTMW no onnxruntime-gpu (DirectML em AMD) | `--pose-backend rtmw` + benchmark comparativo |
| T14 | P2 | ⬜ | Navegação por gesto (pinça, MediaPipe Hands) | Sem falsos positivos em 1 min |
| T15 | P1 | ⬜ | Passada de realismo clássica: casar a peça com a câmera (desfoque, ruído, cor), molde com gola e manga afunilada, largura pelo tronco medido, normal map de tecido | A peça deixa de parecer "colada" ao lado do vídeo |
| T16 | P2 | ⬜ | IA generativa para o realismo (super-resolução das fotos, normal map, foto HD, refinamento neural) — ver [`roadmap_realismo.md`](roadmap_realismo.md) | Depois de 27/10/2026 |
| v2 | — | ⬜ | Forma do corpo por calibração SMPL, HyperBones, foto HD por CatVTON | — |

## Verificação

- `pytest tests/` — One Euro em sinal sintético, matemática do retarget, carregamento do catálogo.
- `python -m provador.app` — levantar os braços, cruzá-los à frente do peito, girar o tronco ±30°, aproximar/afastar,
  trocar de peça pelas setas e cliques.
- `python tools/benchmark.py --seconds 60` → `docs/desempenho.md`. Metas: média ≥30 FPS, p1 ≥24 FPS, <80 ms ponta a ponta.
- README com captura de tela ou GIF de cada peça.

## Hardware desta máquina

Ver [`docs/hardware.md`](hardware.md) (gerado a partir de `tools/check_hardware.bat`). Ajustes ao plano ficam registrados lá.
