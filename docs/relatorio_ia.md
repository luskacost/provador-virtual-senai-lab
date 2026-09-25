# Relatório 2 · Necessidade de IA

> Pesquisa feita em 23/09/2026 (subagente de IA). Fonte: plano aprovado do Provador Virtual 3D.

## Conclusão

A IA é **essencial apenas na forma leve** — pose e segmentação. SMPL, tecido neural, rede de harmonização e foto por
difusão são opcionais. Difusão e GAN são dispensáveis no vídeo ao vivo. O realismo em tempo real depende de três coisas:
**oclusão por máscara**, **iluminação coerente (SH)** e **estabilidade temporal**.

## Classificação por etapa

| Etapa | Classificação | Custo de latência | Ganho de realismo |
|---|---|---|---|
| Segmentação corporal por DL | **ESSENCIAL** | ~1–3 ms | Alto: coloca os braços à frente e esconde a borda da roupa real |
| Keypoints 2D/3D | **ESSENCIAL** | ~3–8 ms | Alto: é a base do ajuste |
| Malha SMPL/SMPL-X | OPCIONAL (v2) | ~30 ms | Médio: forma do corpo e oclusão por profundidade |
| Difusão em imagem (CatVTON, IDM-VTON…) | DISPENSÁVEL ao vivo · OPCIONAL como foto | 2,6–13 s | Muito alto em foto; nenhum em vídeo |
| Difusão em vídeo (SwiftTry, LiveVVT) | DISPENSÁVEL | 2–22 FPS | Alto, mas não é interativo |
| GAN (VITON-HD, HR-VITON…) | DISPENSÁVEL | ~2,5 FPS | Médio; só 2D e oscila entre frames |
| Tecido neural (HyperBones, HOOD) | OPCIONAL | 5–50 ms | Baixo a médio em peças justas |
| Harmonização de luz (SH analítico) | OPCIONAL, muito recomendada | <1 ms | Médio a alto |
| Foto HD assíncrona | OPCIONAL (v2) | 2–13 s, sem afetar o FPS | Alto para a foto final |

## Discussão

- **SMPL ou keypoints:** keypoints 3D com One Euro chegam a ~80% do resultado. Meio-termo: estimar a forma do corpo (β)
  uma vez, numa calibração com a pessoa parada, e animar por keypoints no resto do tempo.
- **Difusão e GAN:** nenhum método é tempo real numa GPU de consumo. Esses modelos recebem uma imagem 2D da peça, não um
  modelo 3D, e em vídeo a textura cintila.
- **Luz:** melhor relação custo-benefício. SH de ordem 2 (9 coeficientes) estimados sobre a pele segmentada, casamento de
  exposição e balanço de branco, e ruído/desfoque de câmera.
- **Pipeline híbrido:** render 3D ao vivo e, na v2, um botão "foto HD" que roda CatVTON num processo separado.

## Fontes

- https://github.com/Zheng-Chong/CatVTON · https://www.alphaxiv.org/abs/2407.15886 · https://replicate.com/cuuupid/idm-vton
- https://www.alphaxiv.org/abs/2608.26714 · https://arxiv.org/html/2412.10178v1 · https://arxiv.org/pdf/2308.13798 · https://arxiv.org/pdf/2312.15861
- https://arxiv.org/html/2605.20460 · https://arxiv.org/html/2606.14841v1
- https://github.com/zhkkke/harmonizer · https://openaccess.thecvf.com/content/CVPR2023/papers/Guerreiro_PCT-Net_Full_Resolution_Image_Harmonization_Using_Pixel-Wise_Color_Transformations_CVPR_2023_paper.pdf
