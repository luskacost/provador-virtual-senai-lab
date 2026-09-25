# Roadmap de realismo e IA generativa (futuro aprimoramento)

> Anotado em 25/09/2026 a pedido. **Depois da entrega de 27/10/2026**, salvo folga no cronograma. Nada aqui está
> implementado. Complementa a linha "v2" de [`tasks.md`](tasks.md) (calibração SMPL, HyperBones, foto HD por CatVTON).

## Por que o visual ainda é limitado (hoje)

Forma genérica igual para qualquer corpo · sem dobras, gola ou espessura · textura de mockup pequena (~420 px) com
sombra pintada · luz simples, sem sombras de contato · peça mais nítida e limpa que o vídeo da webcam.
A passada "clássica" (sem IA) está proposta como **T15** em `tasks.md`; este documento cobre o que a IA generativa pode
somar depois dela.

## Restrições que decidem o que cabe

- Máquina: RTX 3060 Laptop com **6 GB de VRAM dedicada**, já dividida com a segmentação (DirectML) e o render.
- Tempo real: 30 FPS e < 80 ms. Difusão completa **não roda** nesse orçamento; só modelos pequenos e pré-computação.
- Privacidade: o vídeo da câmera é do usuário. API na nuvem significa **enviar o rosto para fora**; exige consentimento.
- Licenças: vários modelos de try-on e de imagem→3D são **não comerciais** ou têm restrições. **Verificar a licença de
  cada um antes de adotar** (o projeto vai para um portfólio público).

## Fases

### A. IA offline para melhorar os ativos das peças (encaixa nas ferramentas atuais)
| Ideia | Onde entra | Observação |
|---|---|---|
| Super-resolução da foto da peça (ex.: Real-ESRGAN) | antes de `garment_from_photos.py` | a foto de mockup tem ~420 px; ganho imediato de nitidez |
| Estimar normal map e rugosidade a partir da foto | novo passo em `photos.py` + shader | dá dobras e brilho de tecido sem simular |
| Completar mangas e laterais por inpainting | atlas UV | hoje as vistas laterais da folha não são usadas |
| Imagem → 3D (TRELLIS / Hunyuan3D) + rigging | **T12** | 6 GB de VRAM pode exigir versão quantizada ou rodar em nuvem |

### B. Modo "foto HD" (não é tempo real)
Ao apertar uma tecla, capturar o quadro + a peça e gerar uma imagem realista em segundos (difusão de try-on, ex.:
CatVTON). É o item já previsto na v2. Depende de VRAM (verificar se cabe em 6 GB ou se precisa de nuvem) e de licença.

### C. Refinamento neural leve em tempo real
Rede pequena (ONNX/DirectML, ≤ 5 ms) sobre a camada da peça para casar com a câmera: harmonização de cor/ruído/desfoque
e sombra de contato aprendida. Precisa de dados de treino ou de um modelo pré-treinado de harmonização de imagem.

### D. Tecido aprendido
Rede que prevê dobras (normal map) a partir da pose, ou um simulador simples de tecido. Só depois de A e C.

## Ordem sugerida

1. **T15** (sem IA): casar a peça com a câmera, molde melhor, ajuste ao tronco medido. Maior ganho por esforço.
2. **A**: super-resolução + normal map nas fotos (ferramentas offline, baixo risco).
3. **T12** e **B**, decidindo antes a questão de VRAM/nuvem e licenças.
4. **C** e **D** como pesquisa.

## Perguntas em aberto

- Aceitar nuvem (com consentimento) para o modo foto HD, ou tudo local?
- Uso comercial ou só portfólio? Muda quais modelos podem entrar.
- Qual é o objetivo de realismo: peça convincente ao vivo, ou uma foto final impressionante?
