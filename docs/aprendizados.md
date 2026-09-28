# Aprendizados (Etapa 1 → insumo para a Etapa 2)

> Atualizado ao longo do trabalho, como pede o `CLAUDE.md` (seção 9). Não é um plano; é registro do que fomos
> descobrindo na prática.

## Como a integração com a Decart funciona (confirmado no código real do exemplo, não só na doc)

- SDK: `import { createDecartClient, models } from "@decartai/sdk"`.
- Token (servidor): `client.tokens.create()` sem argumentos no exemplo mais simples; a doc descreve também
  `expiresIn`, `allowedModels`, `allowedOrigins`, `constraints` para produção. TTL citado pela doc: 10 minutos.
- Conexão (navegador): `client.realtime.connect(stream, { model: models.realtime("lucy-vton-latest"), onRemoteStream })`.
- Troca de peça: `rtClient.setImage(garmentBlob, { prompt, enhance })`. **Sempre os dois juntos** (imagem + prompt);
  bate com a regra 2 do CLAUDE.md sobre `set()` substituir o estado inteiro.
- Evento de status: `rtClient.on("connectionChange", state => ...)` — estados vistos no exemplo: `idle`,
  `connecting`, `connected`, `generating`, `reconnecting`, `disconnected`, `error`.
- **Cuidado com buscas na documentação por ferramenta automática (WebFetch):** numa primeira rodada, ela devolveu
  com muita confiança um endpoint (`wss://api3.decart.ai/v1/stream?...`) e um nome de modelo (`lucy-vton-3.5`) que
  **não aparecem no código real do repositório**. O nome real é `lucy-vton-latest`. Sempre confirmar contra o
  código-fonte de um exemplo antes de aceitar um detalhe técnico específico vindo de resumo de página.

## Escolha do exemplo-base

Entre os 7 exemplos do `DecartAI/tryon-examples`, usamos **Person Detection**: tela única, só precisa da
`DECART_API_KEY`, e já resolve a abertura/fechamento de sessão por presença (economiza créditos — parte da
seção 4.3). Alternativas descartadas: *Standalone* e *Full-Featured* exigem `OPENAI_API_KEY` obrigatória para
gerar prompt por IA (não precisamos disso — nosso catálogo já tem prompt escrito à mão); *E-commerce* é um modal
sobre página de produto, não uma tela de quiosque; *Digital Mirror* exige um segundo aparelho (celular via QR).

## Conflito encontrado e resolvido: MediaPipe carregava de CDNs externas

`usePersonDetection.ts` baixava o WASM e o modelo do MediaPipe Pose de `cdn.jsdelivr.net` e
`storage.googleapis.com` — a seção 4.4 do CLAUDE.md pede "nada de dependência de recursos externos além da
Decart". **Resolvido em 28/09/2026** (`web/scripts/setup-mediapipe.mjs`, hook `postinstall`):
- O WASM já vem dentro do pacote `@mediapipe/tasks-vision` (node_modules) — só copiar, sem rede.
- O modelo `pose_landmarker_lite.task` (~5,8 MB) é baixado do Google Storage **uma vez**, na configuração
  (`npm install`), não em cada carregamento de página.
- Os dois ficam em `web/public/mediapipe/` (~28 MB, fora do git — mesmo padrão do `models/*.task` do plano
  Python anterior).
- Depois disso, em tempo de execução, o único serviço externo do quiosque é a própria Decart.

## Segurança: Next.js do exemplo tinha uma CVE crítica

O exemplo oficial vem fixado em `next@15.1.0`, com **RCE não autenticada em servidores Windows**
(GHSA-p293-qw3h-jr36) entre outras ~30 falhas do `npm audit` (a máquina do evento é Windows). Corrigido para
`^15.5.26` com `npm audit fix --force` (dentro da mesma major version, sem quebra); build de produção e dev
server testados depois da correção, sem problemas. Sobrou 1 vulnerabilidade alta de PostCSS aninhada dentro do
próprio Next — corrigi-la pediria salto para o Next 16 (major, risco de quebrar o exemplo); não fiz isso sem
confirmar com o usuário.

## Catálogo do exemplo: schema mais simples que o do plano

`lib/products.ts` do exemplo usa `{ name, image, prompt, price }`. O CLAUDE.md pede também `id`, `categoria`,
`ativo`. Vamos estender o schema na Fase 2, ao trocar os produtos de demonstração da Decart pelas peças reais do
laboratório.

## Chave de API real (28/09/2026)

O usuário forneceu a `DECART_API_KEY` real. Ela só existe em `web/.env.local` (fora do git; confirmado com
`git check-ignore`). Testei **apenas** a criação de token (`POST /api/tokens`, que chama `client.tokens.create()`
no servidor) — não abri uma sessão de vídeo em tempo real, que é a parte cobrada por segundo de geração ativa.
Resultado: **200 OK**, token JWT válido, `expiresAt` de fato ~10 minutos no futuro (confirma o TTL da doc), e o
payload do token mostra `dataRetention: false` — bate com o aviso de LGPD da seção 4.6 ("não é armazenado pelo
estande" — e, por este campo, também não pela Decart nesta conta).

**Ainda não testado:** uma conexão WebRTC real (câmera → Decart → vídeo de volta). Isso é a parte que custa
dinheiro e precisa de uma pessoa de verdade na frente da câmera; fica para o teste do usuário no navegador.

## Pendente (preenchendo conforme formos testando)

- Custos reais medidos: **ainda não** — falta medir uma sessão real de geração (a criação de token, testada, não
  deve contar como geração ativa).
- Peças que funcionam bem/mal no modelo: **ainda não testado**.
- Teste de fundo (seção 4.7, caminhos B e A): **não iniciado**.
- Pedidos/ideias de visitantes e coordenadores: **nenhum ainda** (projeto não foi a campo).
