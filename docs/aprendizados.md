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

## Catálogo do exemplo: schema mais simples que o do plano — resolvido na Fase 2

`lib/products.ts` do exemplo usava `{ name, image, prompt, price }`. Trocado por `catalog/products.json` +
`lib/catalog.ts`, no schema exato do CLAUDE.md (`id`, `nome`, `categoria`, `imagem`, `prompt`, `ativo`). Os 10
produtos de demonstração da Decart (com a marca deles) foram removidos; só a Camiseta SESI real ficou.

## Chave de API real (28/09/2026)

O usuário forneceu a `DECART_API_KEY` real. Ela só existe em `web/.env.local` (fora do git; confirmado com
`git check-ignore`). Testei **apenas** a criação de token (`POST /api/tokens`, que chama `client.tokens.create()`
no servidor) — não abri uma sessão de vídeo em tempo real, que é a parte cobrada por segundo de geração ativa.
Resultado: **200 OK**, token JWT válido, `expiresAt` de fato ~10 minutos no futuro (confirma o TTL da doc), e o
payload do token mostra `dataRetention: false` — bate com o aviso de LGPD da seção 4.6 ("não é armazenado pelo
estande" — e, por este campo, também não pela Decart nesta conta).

**Testado pelo usuário em 28/09/2026:** conexão WebRTC real, câmera → Decart → vídeo de volta, com a Camiseta
SESI (primeira peça real). Resultado: funcionou. Na primeira tentativa a imagem "ficou Live mas travou" — para
investigar, liguei os eventos de diagnóstico do próprio SDK (`rtClient.on("stats"/"diagnostic", ...)`, achados
em `node_modules/@decartai/sdk/dist/realtime/observability/`; não documentados na página pública, só nos tipos
TypeScript do pacote instalado). No teste seguinte funcionou perfeitamente — não chegamos a capturar o log do
travamento, então a causa exata ficou sem confirmação (suspeita: rede/Wi-Fi instável no primeiro handshake). O
log de diagnóstico ficou no código (`useDecartRealtime.ts`), sem custo extra, para o caso de o problema voltar.

## Fase 2 (catálogo + visual), em andamento — 29/09/2026

- Catálogo migrado para `catalog/products.json` (ver acima).
- Adicionado: tela de espera em tela cheia (`components/IdleScreen.tsx`) com o aviso de LGPD da seção 4.6,
  mensagens de erro amigáveis + botão "Tentar de novo" (seção 4.4 — o exemplo original mostrava o erro técnico
  bruto do SDK), e toda a interface visível ao visitante traduzida para português.
- Next.js elevado para a versão 16 (major) a pedido do usuário, para zerar a última vulnerabilidade do
  `npm audit`; build e testes manuais OK depois do salto.
- **Provisório, esperando o usuário:** nome do projeto ("Provador Virtual"), texto da tela de espera e a
  redação exata do aviso de LGPD — o CLAUDE.md pede validação explícita dessa redação. Identidade visual
  (logo, cores do laboratório) ainda não entrou; a interface está num tema escuro neutro.
- **Ainda não feito:** dimensionar a interface para toque a 1,5–2 m (botões/textos maiores, seção 4.2); isso
  é o próximo passo natural dentro da própria Fase 2.

## Fase 3 (sessão e robustez), 29/09/2026

- `hooks/useSessionTimer.ts`: limite de 90 s por visitante com contagem regressiva visível, encerramento por
  45 s de inatividade (sem trocar de peça — não conta contra o limite total), encerramento ao esconder a
  aba, e um "cooldown" de 5 s pós-encerramento forçado para a mesma pessoa não ser reconectada na hora pela
  detecção de presença. Os três números são constantes no topo de `app/page.tsx` (fácil de ajustar).
- Atalhos do operador: `Ctrl+Shift+E` encerra a sessão atual, `Ctrl+Shift+R` reseta o app.
- **Não testado de ponta a ponta:** o cronômetro só é validável com uma sessão real de câmera+Decart, e
  90 s de espera real; ficou para o teste do usuário (pode reduzir `SESSION_LIMIT_SECONDS` temporariamente
  para testar mais rápido).

## Identidade visual, 29/09/2026: resolvida

O laboratório é do **SENAI** (o logo diz "SENAI lab FASHION"); a camiseta SESI já no catálogo continua
válida como peça real (é a marca impressa na peça, não a marca do app — as duas coisas são independentes).
Cores extraídas por amostragem de pixel do arquivo real do logo (não estimadas visualmente): navy `#164092`,
laranja `#ff6123`. O logo tem "FASHION" em preto, por isso aparece numa placa branca sobre o fundo escuro do
quiosque (senão o texto desapareceria). Aplicado em `globals.css` (tokens Tailwind v4), na tela de espera e
no topo da barra de peças. Título da página agora é "SENAI Lab Fashion".

## Direção do catálogo, 29/09/2026: do vestuário formal ao EPI

O usuário quer que o catálogo reflita a realidade da indústria, não só camisetas — de roupa formal a
Equipamento de Proteção Individual (capacete, luvas, colete, macacão etc.). Tem o logo do laboratório e as
cores (laranja e azul marinho) para a identidade visual do app.

**Risco técnico por categoria (avaliação, ainda sem teste real):** o VTON da Decart já prova bem "top"
(camiseta/jaqueta/blazer, inclusive no próprio catálogo de exemplo) e "headwear" (boné/gorro no exemplo —
capacete deve seguir o mesmo padrão). Óculos de proteção (peça pequena, precisa encaixar exatamente nos
olhos) e luvas (mãos se movem muito e são um ponto fraco conhecido de modelos de vídeo generativos) são mais
arriscados — tratar como experimental antes de investir em mais fotos dessas categorias. Macacão/traje
completo pode precisar de um prompt diferente ("substitute the current outfit" em vez de "...top") — testar.

## Fase 4 (métricas locais), 30/09/2026 — feita

`data/metricas.json` (fora do git) grava início/fim, duração, motivo do encerramento e peças
experimentadas de cada sessão — nunca vídeo/imagem. `/api/metrics` recebe o registro (envio best-effort
do cliente: falha de rede/disco nunca quebra a experiência do visitante). Página `/metricas` (não
linkada no quiosque; só quem souber o endereço acessa) resume para os coordenadores: total de sessões,
duração média, ranking de peças, motivos de encerramento, últimas 50 sessões. Testado de ponta a ponta
com sessões falsas antes do commit (removidas depois).

Achado de doc: no Next 16, `export const dynamic = "force-dynamic"` só foi removido quando o novo
"Cache Components" está habilitado (`next.config.ts` com a flag `cacheComponents`) — este projeto não
habilita, então a forma clássica continua funcionando (confirmado na doc local antes de usar, não só
lembrado do treinamento — é exatamente o tipo de mudança que o aviso do Next 16 alertou).

## Pendente (preenchendo conforme formos testando)

- Custos reais medidos: **ainda não** — falta checar o painel de cobrança da conta Decart depois de alguns
  testes reais.
- Peças que funcionam bem/mal no modelo: só uma peça testada até agora (Camiseta SESI, resultado bom).
- Teste de ponta a ponta do limite de 90s e dos atalhos do operador: **não feito** (ver Fase 3 acima).
- Métricas locais (seção 4.5): **não iniciado** (é a Fase 4).
- Teste de fundo (seção 4.7, caminhos B e A): **não iniciado**.
- Pedidos/ideias de visitantes e coordenadores: **nenhum ainda** (projeto não foi a campo).
