# SENAI Lab Fashion — Provador Virtual

Quiosque de provador virtual em tempo real para uma exposição do laboratório (SENAI, Sistema FIEG). O
visitante fica em frente à webcam; quando detectado, conecta ao modelo de try-on em tempo real da Decart
(`lucy-vton-latest`) e pode trocar entre as peças do catálogo, vendo o resultado ao vivo.

Baseado no exemplo oficial [`person-detection`](https://github.com/DecartAI/tryon-examples) da Decart,
bastante adaptado para este evento. Veja `docs/aprendizados.md` (na raiz do repositório) para o histórico
completo de decisões — este README é só o essencial para rodar e entender o código.

> Este projeto segue `CLAUDE.md` (na raiz do repositório). Leia-o antes de qualquer mudança.

## Rodando localmente

```bash
npm install                  # também baixa/copia os arquivos do MediaPipe (scripts/setup-mediapipe.mjs)
cp .env.example .env.local   # cole sua DECART_API_KEY
npm run dev                  # http://localhost:3000
```

Para o dia do evento (quiosque de verdade): `docs/operacao-evento.md` e `docs/checklist-estande.md`, na
raiz do repositório — inclui o motivo pelo qual o navegador do quiosque **não pode** abrir por `localhost`.

## Como funciona

```
Página carrega → câmera inicia (getUserMedia)
  → MediaPipe PoseLandmarker (auto-hospedado, scripts/setup-mediapipe.mjs) detecta presença no navegador
    → pessoa detectada → token em /api/tokens → conecta à Decart (WebRTC)
      → visitante escolhe uma peça → garmentBlob + prompt → setImage()
      → "Tirar foto" / "Gravar vídeo" → captura efêmera, QR code para o celular (lib/capture-store.ts)
    → limite de tempo, inatividade, aba escondida ou atalho do operador → desconecta (hooks/useSessionTimer.ts)
      → registra a sessão em data/metricas.json (lib/metrics.ts) — nunca vídeo/imagem
    → pessoa sai → desconecta (para de cobrar) → volta a escanear
```

## Estrutura

| Caminho | O que é |
|---|---|
| `catalog/products.json` + `public/catalog/*.jpg` | **O catálogo.** Adicionar/remover peça é só editar o JSON e a imagem — ver `lib/catalog.ts` para o schema. |
| `lib/catalog.ts` | Carrega e tipa o catálogo (`ativo: false` esconde sem apagar). |
| `app/page.tsx` | Orquestração principal: detecção → conexão → sessão → métricas. |
| `hooks/usePersonDetection.ts` | MediaPipe Pose no navegador; vira `personPresent`. |
| `hooks/useDecartRealtime.ts` | Conecta/desconecta da Decart; loga `diagnostic`/`stats` do SDK no console (achado útil se o vídeo travar — ver `docs/aprendizados.md`). |
| `hooks/useSessionTimer.ts` | Limite de sessão, inatividade, cooldown (CLAUDE.md 4.3). |
| `hooks/useCapture.ts` + `components/CaptureControls.tsx` | Foto/vídeo efêmero por QR code (CLAUDE.md 4.5b). |
| `lib/metrics.ts` + `app/api/metrics/` + `app/metricas/` | Métricas locais e a página de resumo para os coordenadores. |
| `lib/errors.ts` | Traduz erros técnicos para mensagens amigáveis (CLAUDE.md 4.4). |
| `components/IdleScreen.tsx` | Tela de espera + aviso de LGPD. |
| `public/brand/` | Logo do SENAI Lab Fashion; cores em `app/globals.css` (`--color-brand-*`). |

## Variáveis de ambiente

| Variável | Obrigatória | Para quê |
|---|---|---|
| `DECART_API_KEY` | Sim | Cria os tokens de cliente para a conexão WebRTC (só no servidor — nunca chega ao navegador). |

## Scripts

| Comando | O que faz |
|---|---|
| `npm run dev` | Servidor de desenvolvimento |
| `npm run build` / `npm start` | Build e execução de produção (use no quiosque de verdade) |
| `npm run setup:mediapipe` | Re-gera `public/mediapipe/` se precisar (já roda sozinho no `npm install`) |
