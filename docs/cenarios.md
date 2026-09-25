# Cenários atrás do usuário (troca de fundo) · T7b

> Contexto para o agente. Decidido em 25/09/2026 como extensão do plano aprovado. Prioridade **P1**, depois da T7.

## Objetivo

Substituir o fundo real da webcam por um cenário (loja, passarela, estúdio…), mantendo a pessoa, a peça 3D e a
oclusão dos braços. Sem impacto perceptível no FPS (meta geral: ≥30 FPS, <80 ms ponta a ponta).

## Por que é barato

A T7 já roda o **MediaPipe Multiclass Selfie Segmenter (256×256)**. A classe `0 = background` dá a máscara de fundo
em todo frame. A troca de fundo é só mais um passo no shader de composição (`composite.frag`) → custo **<1 ms**.
Nada de readback GPU→CPU: máscara e cenário vivem como texturas.

## Ordem de composição (composite.frag)

```
1. cenário (textura)                        ← novo
2. pessoa da webcam, recortada pela máscara (alpha = 1 − background, com bordas suaves)
3. peça 3D com LBS (renderer, FBO com MSAA)
4. braços, mãos e cabelo por cima quando estão à frente (oclusão da T7)
5. HUD / interface
```

Com o cenário desligado (modo "fundo real"), o passo 1–2 volta a ser o frame da webcam inteiro, como na T7.

## Tipos de cenário

| Tipo | Esforço | Observação |
|---|---|---|
| Imagem fixa (`.jpg/.png`) | Baixo | **Escopo da T7b** |
| Vídeo em loop (`.mp4`) | Baixo–médio | Decodificar em thread própria (mesmo padrão da captura); fase 2 |
| Cena 3D no ModernGL com paralaxe pela posição da cabeça | Médio–alto | v2 |

## Problemas conhecidos e mitigação

1. **Halo nas bordas** (máscara 256×256 ampliada; cabelo e dedos): refinar a máscara com *guided filter* usando o
   frame da webcam como guia (pode ser no shader ou `cv2.ximgproc` se disponível), feather de 2–4 px e leve erosão.
   Plano B com GPU NVIDIA: **RVM** (Robust Video Matting, ONNX/CUDA, 3–6 ms, bordas muito melhores) — licença
   **GPL-3.0**, avaliar antes de adotar.
2. **Atraso da máscara** (segmentação assíncrona → borda "arrasta" em movimento rápido): suavização temporal da máscara
   (EMA por pixel) e registrar o timestamp do frame de cada máscara; opção `--sync-seg` que espera a máscara do mesmo
   frame (custa alguns ms).
3. **Luz incoerente** (pessoa iluminada pela sala real parece recortada): ajuste leve de cor da pessoa em direção à
   média/tom do cenário (casamento de média e desvio em Lab, intensidade 0,2–0,4). A iluminação da peça (T10) pode usar
   SH estimados **do cenário** quando ele estiver ativo.
4. **Escala e chão:** para enquadramento de busto, preferir cenários sem chão aparente. Guardar em `meta.json` do cenário
   um ponto de horizonte/escala para uso futuro.

## Especificação da T7b

- **Assets:** `assets/backgrounds/<id>/{background.jpg, meta.json}` — `meta.json`: `{"name": "...", "color_match": 0.3,
  "type": "image"}`. Pré-carregar todas as texturas na inicialização.
- **Código:**
  - `src/provador/backgrounds.py` — catálogo e carregamento (mesmo padrão de `garments.py`).
  - `src/provador/segmentation.py` — expor máscara de fundo refinada + suavização temporal.
  - `src/provador/shaders/composite.frag` — uniforms `u_background`, `u_bg_enabled`, `u_color_match`.
  - `src/provador/app.py` — tecla **B** alterna fundo real → cenário 1 → cenário 2 → …; **Shift+B** volta.
  - `src/provador/ui.py` — indicador do cenário ativo no HUD.
- **Testes:** `tests/test_backgrounds.py` (catálogo, meta.json inválido) e teste do refinamento de máscara num sinal
  sintético (borda degrau → feather monotônico).
- **Pronto quando:** trocar de cenário não derruba o FPS (diferença <1 FPS no `benchmark.py`), sem halo visível no
  contorno dos ombros e sem cintilação da borda com a pessoa parada.

## Fora do escopo agora

Vídeo em loop, cena 3D com paralaxe, sombras da pessoa projetadas no cenário, relighting completo da pessoa.
