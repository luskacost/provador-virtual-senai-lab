# Relatório 1 · Stack tecnológico

> Pesquisa feita em 23/09/2026 (subagente de stack). Fonte: plano aprovado do Provador Virtual 3D.

## Recomendação

MediaPipe **Pose Landmarker** (world landmarks 3D) e **Multiclass Selfie Segmenter** na CPU. A peça fica rigada num
esqueleto humanoide padrão (Mixamo), com a rotação dos ossos calculada a partir dos landmarks, **sem SMPL**. A renderização
usa **ModernGL + GLFW**, com skinning LBS no shader e a composição inteira na GPU. **One Euro** suaviza os pontos e
**slerp** suaviza as rotações. Todas as licenças são Apache ou MIT.

## Comparativo

| Componente | Opção | Latência | Realismo | Complexidade | Licença |
|---|---|---|---|---|---|
| Pose | MediaPipe Pose (full, CPU) | 10–25 ms | Bom, 3D | Baixa | Apache-2.0 |
| Pose | RTMW/RTMPose (rtmlib, ORT-CUDA) | 3–8 ms | Muito bom em 2D; 3D limitado | Média | Apache-2.0 |
| Pose | YOLO11/26-pose | 2–5 ms | Só 2D, 17 pontos | Baixa | AGPL-3.0 |
| Corpo 3D | ROMP/BEV | ~20 ms | Médio | Média | SMPL não comercial |
| Corpo 3D | Multi-HMR-S / SAT-HMR | 25–40 ms | Alto | Alta | Não comercial |
| Corpo 3D | Landmarks → ossos (sem SMPL) | <1 ms | Médio | Média | Livre |
| Segmentação | MP Multiclass 256 | 8–15 ms | Bom, com classe pele | Baixa | Apache-2.0 |
| Segmentação | RVM (ONNX/CUDA) | 3–6 ms | Bordas muito boas | Baixa | GPL-3.0 |
| Segmentação | SAM2 / BiRefNet | >30–100 ms | Excelente | Alta | Apache/MIT |
| Render | ModernGL + skinning em shader | 1–3 ms | Alto | Média | MIT |
| Render | pyrender | 5–15 ms | Bom | Baixa | MIT |
| Tecido | LBS (+ offset/jiggle) | <1 ms | Médio-bom | Baixa | — |
| Tecido | Warp VBD / Taichi | >30 ms | Alto | Muito alta | Apache |
| Tecido | HOOD / SNUG | exige treino | Alto | Muito alta | Pesquisa |

*As latências são estimativas para uma RTX de consumo a 720p e precisam ser medidas no hardware alvo.*

## Pontos importantes

- O MediaPipe 1.0.1 (agosto de 2026) tem wheels para Windows com Python 3.9–3.12, mas no Windows **não usa a GPU**
  ("GPU Delegate is not yet supported for Windows").
- O ModernGL dá controle total de FBOs, MSAA e profundidade. A skinning cabe em ~20 linhas de vertex shader, e o glTF é
  carregado com pygltflib ou trimesh.
- O pyrender não faz skinning e está sem manutenção. O Panda3D faz, mas integrar o fundo da webcam e a oclusão é mais
  trabalhoso. O nvdiffrast é difícil de compilar no Windows.
- Tecido: LBS com pesos suavizados, pequeno offset na normal (para o corpo não atravessar a peça) e ossos com mola na barra
  da jaqueta, se preciso.
- Interface: botões desenhados no próprio OpenGL, com teclado e mouse. Gestos custam +5–10 ms e ficam para a fase 2.
- Rig: manequim em A-pose, ajustar a peça, *Parent → With Automatic Weights* ou *Data Transfer* no Blender, limpar os pesos
  das axilas e exportar em GLB. Todas as peças usam o mesmo esqueleto.
- Fontes de assets: Sketchfab (conferir licença de cada peça), Meshy (algumas peças CC0), Marvelous Designer ou Blender
  Cloth. O CLOTH3D é não comercial.

## Riscos e mitigações

1. **MediaPipe só na CPU** — numa CPU fraca o orçamento estoura. Mitigação: modelo lite, segmentação em frames alternados,
   ou trocar por rtmlib + RVM na GPU (T13).
2. **Profundidade (z) ruidosa** — a peça gira errado. Mitigação: limitar a torção a ±30°, One Euro e confiar mais no 2D.
3. **Sem a forma do corpo** — vãos ou o corpo atravessa a peça. Mitigação: escala por osso e ajuste pela máscara de roupa.
4. **Artefatos de LBS** (cotovelo "embrulho de bala"). Mitigação: dual-quaternion skinning e pesos bem pintados.
5. **Qualidade e licença dos assets.**
6. **Peça com cara de "colada"** — resolver com luz ambiente e sombra de contato simples.

## Fontes

- https://pypi.org/project/mediapipe/ · https://github.com/google/mediapipe/issues/5126 · https://github.com/google-ai-edge/mediapipe/issues/5385
- https://pypi.org/project/rtmlib · https://arxiv.org/pdf/2407.08634 · https://docs.ultralytics.com/models/yolo11
- https://github.com/Arthur151/ROMP · https://arxiv.org/html/2411.19824v3 · https://github.com/isarandi/nlf · https://smpl.is.tue.mpg.de/modellicense.html
- https://ai.google.dev/edge/mediapipe/solutions/vision/image_segmenter · https://github.com/PeterL1n/RobustVideoMatting
- https://github.com/moderngl/moderngl · https://github.com/highfestiva/gltf-skin-anim-viewer · https://pyrender.readthedocs.io/
- https://github.com/casiez/OneEuroFilter
