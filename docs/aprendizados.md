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

## Conflito encontrado: MediaPipe carrega de CDNs externas

`usePersonDetection.ts` baixa o WASM e o modelo do MediaPipe Pose de `cdn.jsdelivr.net` e
`storage.googleapis.com` — a seção 4.4 do CLAUDE.md pede "nada de dependência de recursos externos além da
Decart". **Ainda não resolvido** — decidir com o usuário se self-hosting desses dois arquivos (baixá-los para
`public/mediapipe/`) entra na Fase 1 ou se aceitamos a dependência (a Decart já é uma dependência externa
obrigatória; jsdelivr/Google Storage são infraestrutura muito estável, mas é rede a mais no dia do evento).

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

## Pendente (preenchendo conforme formos testando)

- Custos reais medidos: **ainda não** — falta a chave de API real.
- Peças que funcionam bem/mal no modelo: **ainda não testado**.
- Teste de fundo (seção 4.7, caminhos B e A): **não iniciado**.
- Pedidos/ideias de visitantes e coordenadores: **nenhum ainda** (projeto não foi a campo).
