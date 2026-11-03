# Provador Virtual em Tempo Real — SENAI Lab Fashion

Quiosque de provador virtual feito para o laboratório **SENAI Lab Fashion** (Engenharia de Produção e Design de
Moda) e usado numa exposição de 27 a 29/10/2026. O visitante fica em frente à câmera, escolhe uma peça do
catálogo e se vê vestindo a peça ao vivo, com aparência fotorrealista gerada por IA.

## Resultados do evento

- 99 sessões em 3 dias, cerca de 3,5 horas de vídeo gerado ao vivo.
- Em 87% das sessões a pessoa experimentou pelo menos uma peça; 641 trocas de peça no total.
- Peças mais procuradas: jaquetas de combate a incêndio, vestido e macacões; as camisetas lisas foram as menos usadas.

Detalhes em [`docs/aprendizados.md`](docs/aprendizados.md) (seção "Métricas reais do evento").

## Como funciona

- **Next.js 16 + React 19 + TypeScript + Tailwind CSS v4**, em [`web/`](web/).
- **Decart Lucy VTON** (prova virtual em tempo real via WebRTC, SDK `@decartai/sdk`). A chave da API fica só no
  servidor; o navegador recebe um token temporário.
- **MediaPipe Pose**, auto-hospedado, para detectar se há alguém na frente da câmera: a sessão com a IA (cobrada
  por segundo) só abre com uma pessoa presente e fecha quando ela sai.
- Catálogo em JSON (`web/catalog/products.json`): cada peça tem imagem e um prompt em inglês.
- Foto do resultado impressa direto pela impressora do estande, sem passar por rede.
- Métricas locais por sessão (sem guardar vídeo nem imagem das pessoas) e uma página de resumo em `/metricas`.
- Atalhos do operador: encerrar sessão, resetar e modo standby; navegação do catálogo pelo teclado.

## Rodando localmente

```
cd web
cp .env.example .env.local   # coloque sua DECART_API_KEY
npm install                  # também baixa os arquivos do MediaPipe
npm run dev                  # http://localhost:3000
```

Guias de operação: [`docs/operacao-evento.md`](docs/operacao-evento.md) e
[`docs/checklist-estande.md`](docs/checklist-estande.md).

## Histórico do projeto

1. **Plano inicial em Python** (webcam + roupas 3D sobrepostas ao corpo, MediaPipe e OpenGL), em `src/`,
   `tools/` e `tests/`. Descrito em [`docs/plano-python-3d.md`](docs/plano-python-3d.md).
2. **Quiosque com a Decart** (o que foi para o evento), em `web/`, partindo do exemplo oficial
   [DecartAI/tryon-examples](https://github.com/DecartAI/tryon-examples).
3. **Estudo da próxima etapa** (uso comercial, ID da peça e nichos), em [`docs/etapa2/`](docs/etapa2/).

As decisões, testes e aprendizados de cada fase estão em [`docs/aprendizados.md`](docs/aprendizados.md).

## Sobre as imagens

O logo é do SENAI Lab Fashion. As fotos de roupas do catálogo foram usadas só para demonstração no estande; os
direitos pertencem aos seus autores e marcas.
