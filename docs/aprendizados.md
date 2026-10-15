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

## Foto/vídeo do visitante, 30/09/2026

Pedido do usuário depois de ver o Anywear (referência do CLAUDE.md, seção 10): botões "Tirar foto" e
"Gravar vídeo" do resultado ao vivo. Isso conflitava com duas frases explícitas do CLAUDE.md ("não
gravar nem armazenar vídeo ou imagem dos visitantes" na 4.5, e "gravação/compartilhamento de vídeo dos
visitantes" na lista de fora de escopo da seção 8) — parei, expliquei o conflito e a diferença entre
"gravar e guardar no servidor do estande" vs. "gerar uma cópia efêmera que só o próprio visitante leva
no celular por QR code", e o usuário aprovou o segundo caminho. Atualizei o CLAUDE.md (seção 4.5b) para
documentar a decisão em vez de deixar o documento contradizendo o que foi construído.

Implementação: captura fica só na memória do processo Node (nunca em disco), expira em 10 minutos, é
entregue via QR code que aponta para `/api/capture/<token>`. Testado de ponta a ponta por API (upload,
download idêntico ao original, QR decodificável, link inválido devolve página amigável) — a parte de
câmera real (espelhamento no canvas, MediaRecorder) só o usuário pode testar.

**Ponto operacional que vai precisar de atenção na Fase 6:** o link do QR code usa o host que o
navegador do quiosque usou para abrir a página. Se abrir por `localhost`, o QR não funciona no celular
de ninguém — o quiosque precisa abrir pelo IP da máquina na rede do evento.

## Foto/vídeo, parte 2: QR code abandonado por impressão local, 05/10/2026

Usuário testou o QR code em `localhost` — não funcionou, como esperado (celular não alcança
`localhost`). Antes de simplesmente trocar para o IP da rede (a correção óbvia), levantei um risco mais
sério: muitas redes de evento/feira têm **isolamento entre dispositivos** (client/AP isolation), um
recurso de segurança comum em Wi-Fi público que impede um celular de alcançar outro aparelho na mesma
rede — quebraria o QR code no dia do evento mesmo com tudo certo em teste doméstico, sem aviso prévio.
Dei 4 alternativas (hotspot do próprio notebook, túnel público, impressão local, remover a
funcionalidade); o usuário escolheu **impressão local** e pediu para remover o que não serviria mais
(gravação de vídeo, já que não há solução de entrega sem rede que valha o esforço agora).

Resultado: `window.print()` com CSS de `@media print` isolando só a foto (sem biblioteca nova) — a foto
não sai mais da máquina nem passa por rede ou servidor, então **o aviso sobre abrir por IP/localhost não
vale mais** (era só por causa do QR code). Removido: as rotas `/api/capture`, o armazenamento efêmero em
memória, a dependência `qrcode`, e toda a parte de vídeo (botão, `MediaRecorder`, `canvas.captureStream`).
CLAUDE.md atualizado (seção 4.5b reescrita com o histórico; "gravação de vídeo" volta à lista de fora de
escopo da seção 8).

**Lição para a Etapa 2:** qualquer recurso que dependa de dois dispositivos na mesma rede local (QR code,
cast, etc.) precisa ser testado na rede real de destino antes de confiar nele — redes domésticas quase
nunca têm isolamento entre dispositivos, mas redes de evento/escritório/convidado frequentemente têm.

## Trabalho sem supervisão, 01/10/2026

O usuário não pôde validar em tempo real por um dia; pediu prioridades. Escolhi só trabalho seguro e
reversível (documentação + revisão de código), nada que gaste sessão real da Decart ou precise do
julgamento dele:
- `docs/operacao-evento.md` e `docs/checklist-estande.md` (Fase 6, adiantados).
- `docs/como-adicionar-peca.md` — guia prático para cadastrar peça sem mim, com a tabela de "a foto
  serve?" que já vínhamos usando na prática.
- `docs/aviso-lgpd-opcoes.md` — 3 opções de redação para ele escolher; **não aplicada nenhuma mudança de
  código** (a seção 4.6 pede validação explícita da redação, não é decisão minha).
- `web/README.md` reescrito — ainda descrevia o exemplo genérico da Decart (`lib/products.ts`,
  `public/products/`, link para `../standalone/`, nada disso existe/se aplica mais aqui).
- Revisão de robustez do código já existente (sessão, captura, conexão) — não achei bugs reais; só um
  comentário explicativo a mais em `capture-store.ts`.
- Confirmei `npm audit` com 0 vulnerabilidades depois do `qrcode`.
- **Não toquei:** teste de fundo (seção 4.7, precisa de aprovação explícita + pessoa real na câmera),
  catálogo (sem fotos novas para processar), redação final de LGPD (esperando a escolha dele).

## Pendente (preenchendo conforme formos testando)

- Custos reais medidos: **ainda não** — falta checar o painel de cobrança da conta Decart depois de alguns
  testes reais.
- Peças que funcionam bem/mal no modelo: só uma peça testada até agora (Camiseta SESI, resultado bom).
- Teste de ponta a ponta do limite de 90s e dos atalhos do operador: **não feito** (ver Fase 3 acima).
- Métricas locais (seção 4.5): **não iniciado** (é a Fase 4).
- Teste de fundo (seção 4.7, caminhos B e A): **não iniciado**.

## Lote de peças de 05/10 — roupas formais/sociais + EPI testadas antes no Anywear

O usuário enviou 7 fotos já testadas por ele na ferramenta Anywear (da própria Decart) e pediu para
colocarmos todas. Mantive o critério de vetagem de sempre (marca d'água, logo/etiqueta de loja visível,
aparência de gerado por IA) mesmo com a aprovação prévia no Anywear, porque esse critério é sobre direito
de imagem da fotografia do produto, não sobre qualidade do try-on.

**Adicionadas (5):**
- `vestido-off-white-babados` — vestido sem manga, barra de babados em camadas, cinto preto.
- `macacao-xadrez-marrom` e `macacao-verde-militar` — mesmo macacão (decote drapeado, perna larga), duas
  cores. Observação: por terem exatamente a mesma silhueta/pose, duas cores diferentes, podem ser
  variações de cor do mesmo anúncio de loja (comum em e-commerce) **ou** o mesmo gerado duas vezes por IA
  com cor alterada — não dá para confirmar só pela imagem. Sem marca/logo visível, então deixei entrar;
  se algum coordenador reconhecer a origem, reavaliar.
- `conjunto-listrado-preto-branco` — camisa risca de giz preta/branca + minissaia preta.
- `jaqueta-epi-azul-marinho` — jaqueta EPI azul-marinho com fitas refletivas; só tem uma etiqueta pequena
  de gola (padrão em qualquer peça real, ilegível na foto), sem logo de marca em destaque — critério
  diferente de uma etiqueta de peito grande e legível.

**Rejeitadas (2) — marca legível em destaque, mesmo problema das 9 fotos da Zara/H&M/Massimo
Dutti/PIECES recusadas antes:**
- Macacão laranja: bolso do peito traz o texto "Dickies" bem legível.
- Camisa cinza EPI com fita amarela: patch de marca costurado na manga direita (ilegível de tão pequeno
  na foto, mas reconhecível como etiqueta de fabricante — mesmo risco de direito de imagem do produto).

**Lição para a Etapa 2:** vale documentar no cadastro de peça *de onde* a foto veio (print de loja, foto
própria, ferramenta de IA) — teria resolvido a dúvida sobre o macacão em duas cores sem precisar
adivinhar.

## Mais 2 peças de 05/10 — também testadas antes no Anywear

- `camisa-popover-azul-marinho` — sem marca d'água nem logo. **Diferença em relação ao resto do
  catálogo:** é foto de modelo vestindo a peça, não peça isolada/manequim-fantasma como a seção 4.1 do
  CLAUDE.md pede ("peça sozinha em fundo neutro"). Deixei entrar porque o usuário já validou o resultado
  do try-on no Anywear com essa mesma foto; se aparecer problema de pose/enquadramento durante os testes
  de campo (Fase 5), essa é a primeira peça a revisar.
- `jaqueta-bombeiro-turnout` — jaqueta de bombeiro (turnout gear), manequim-fantasma, sem logo/marca
  legível visível (só um clipe metálico e um bolso sem texto).

**Rejeitada:** jaqueta de bombeiro vermelha (1ª versão) — texto "Xtreme®" bem legível no peito, mais um
logo "X" bordado no ombro. Mesmo critério de marca comercial em destaque das rejeições anteriores
(Dickies, patch da camisa EPI cinza). O usuário enviou outra foto do mesmo tipo de peça sem marca visível
— entrou como `jaqueta-bombeiro-vermelha`.

## Primeira peça de mão: `luvas-protecao-azul`

Luvas de proteção/solda azuis com reforço de couro marrom na palma, sem marca/logo visível. **Categoria
nova para o catálogo (`epi-maos`)** — até aqui só tínhamos EPI de tronco (colete, jaquetas). Usei o padrão
"add" do prompt (em vez de "substitute") porque é um acessório que normalmente não está presente na
imagem original, diferente de um top que troca outro top.

**Risco não testado:** mãos se movem muito mais rápido e saem de quadro com muito mais frequência que o
torso — não sei se o VTON acompanha bem. Prioridade alta para o teste "uma peça, uma pessoa real" do
`docs/checklist-estande.md` antes de confiar nela no evento.
- Pedidos/ideias de visitantes e coordenadores: **nenhum ainda** (projeto não foi a campo).

## Primeira peça de cabeça: `capacete-seguranca-laranja`

Capacete de segurança laranja, testado antes pelo usuário no Anywear. Sem marca/logo visível. **Categoria
nova (`epi-cabeca`)** — mesma lógica das luvas: cabeça é território ainda mais crítico que mão pro VTON
(é onde o rosto está, foco principal do modelo) — prioridade de teste com pessoa real antes do evento.

## Primeira peça de rosto: `oculos-esportivo-preto`

Óculos esportivo preto, lente única escura, sem marca/logo visível. **Categoria nova (`acessorio`)** — não
é EPI certificado (é estilo esportivo, não proteção), por isso não entrou em `epi-cabeca`. Mesmo risco das
luvas/capacete, só que ainda mais sensível: fica direto no rosto, onde a identidade da pessoa é mais
evidente — prioridade alta de teste com pessoa real.

## Renomeação do catálogo, 06/10/2026

A pedido do usuário, todos os nomes (`nome`) do catálogo foram trocados de descrição literal de cor/tecido
pra nome de produto de loja (tipo + estilo, cor por último) — ex.: "Camiseta Preta Oversized" →
"Camiseta Oversized Preta"; "Macacão Xadrez Marrom" → "Macacão Pied-de-Poule Marrom" (nome correto do
estampado). Só o campo `nome` mudou; `id`/`categoria`/`prompt`/`imagem` ficaram intactos.

## Teste de fundo, 1ª rodada — 06/10/2026 (Fase 1b, seção 4.7)

Ferramenta: `web/app/teste-fundo/` (isolada, ver commit `176a92b`). Testado pelo próprio usuário, sozinho,
na própria luz/webcam — ainda falta testar com outras pessoas e na luz do evento (critério da seção 4.7).

**Caminho B (VTON + fundo local, cor sólida laranja):**
- Bordas aguentaram bem no geral.
- **Achado importante:** o tom da cor laranja do fundo **mudava visivelmente** conforme o usuário se
  movimentava com a roupa trocada no corpo. Isso indica que o VTON **não está só compositando por cima**
  do fundo que mandamos — ele resintetiza o frame inteiro e aparentemente ajusta cor/luz global frame a
  frame, inclusive onde não devia ter nada pra "corrigir". **Isso invalida parcialmente a hipótese da
  seção 4.7** ("será que o VTON preserva um fundo já trocado?") — a resposta, por este teste, é: não
  perfeitamente, pelo menos não com cor sólida.
- Achado secundário: o movimento da cadeira (objeto, não corpo) fazia o fundo "desaparecer" num ponto
  específico — provável confusão do segmentador (o `selfie_segmenter` é treinado pra pessoa, não pra
  objetos/mobília ao redor). Usuário avaliou como pouco relevante no geral.

**Caminho A (lucy-2.5, cenário "praia"):**
- Performance aceitável, sem detalhe ainda sobre se a cor/luz do fundo também deriva com o movimento
  (não comparado lado a lado com o mesmo tipo de fundo do Caminho B) nem sobre a qualidade da roupa
  comparada ao VTON dedicado.

## Teste de fundo, 2ª rodada — 06/10/2026: Caminho A com o mesmo fundo laranja sólido

Objetivo: isolar se a deriva de cor do fundo (vista no Caminho B) é um problema do VTON especificamente
ou dos modelos Lucy em geral. Testado com a Camiseta Preta Oversized + preset "Laranja sólido" (mesma cor
do teste B, `#ff6123`, mas pedida por texto ao `lucy-2.5`, não compositada localmente).

**Resultado: a cor do fundo e a qualidade da roupa ficaram "muito boas" — sem a deriva de tom que apareceu
no Caminho B.** Isso aponta pra deriva de cor ser um problema **específico do VTON** (`lucy-vton-3.5`
resintetizando o frame todo, inclusive o fundo que já mandamos pronto) — não um problema geral da família
Lucy. Até aqui, isso favorece o **Caminho A** sobre o B no critério de estabilidade do fundo.

**Ainda em aberto antes de decidir:**
- Repetir o teste do Caminho A em cenários realistas (não só cor sólida) pra confirmar que a roupa continua
  boa com um fundo fotográfico de verdade (praia/rua/vitrine), não só com cor lisa.
- Testar com mais gente, não só o usuário, e na luz do ambiente do evento.
- Ainda não comparamos a borda (cabelo, mãos, movimento rápido) do Caminho A especificamente — só a cor e
  a roupa. Vale repetir a observação de bordas que foi feita no B.

## Teste de fundo, 3ª rodada e decisão final — 07/10/2026: troca de fundo FORA do evento

Caminho A (`lucy-2.5`) com cenários fotográficos, testado pelo usuário:
- Jaqueta de Combate a Incêndio + fundo "passarela": **o fundo não apareceu**, e a jaqueta ficou muito
  desalinhada com o corpo e com aspecto superficial.
- Camiseta Esportiva SESI + fundo "praia": o fundo apareceu, mas a camiseta ficou muito artificial e
  **duplicada** (uma segunda camiseta aparecia onde deveria estar o próprio usuário).
- Custo alto para o pouco que rendeu.

**Falha do meu lado no teste (registrar para não repetir):** no Caminho A a página mandava ao `lucy-2.5`
só o texto do prompt, **sem a foto da peça** (o modelo aceita `reference_image`, mas não foi usado). Com a
camiseta preta lisa da 2ª rodada, o texto bastava; com peça cheia de detalhe (logo SESI, faixas e bolsos
da jaqueta) o modelo inventou a peça a partir da descrição. Ou seja: **a qualidade da roupa no Caminho A
ficou subavaliada por causa da ferramenta de teste**. Já o fundo que não aparece e a peça duplicada são
instabilidade do próprio modelo, e bastam para reprovar pelos critérios da seção 4.7.

**Decisão do usuário (07/10/2026):** a troca de fundo por IA **sai do evento**. Usar **fundo físico
neutro** no estande, como o CLAUDE.md prevê para o caso de não estar estável até 16/10. O código do teste
(`web/app/teste-fundo/`, `hooks/useBackgroundReplace.ts`, `hooks/useDecartTestConnect.ts` e o download do
`selfie_segmenter.tflite`) foi **apagado** — continua no histórico do git (commits `176a92b` e `72e071e`)
se a Etapa 2 quiser retomar. A atualização do SDK para 0.2.5 **ficou**: o quiosque já roda nela e foi
validado.

**Para a Etapa 2, se a ideia de cenário voltar:**
- Caminho B (VTON + fundo local) tem bordas boas, mas o VTON altera a cor de um fundo que já chega pronto.
  Vale testar com fundo fotográfico (não só cor sólida) antes de descartar de vez.
- Caminho A precisa ser testado de novo **mandando a foto da peça** como referência, antes de qualquer
  conclusão sobre a qualidade da roupa.
- Mesmo preço por segundo do VTON ($0,02/s), mas cada rodada de teste é gasto sem retorno até funcionar:
  planejar testes curtos e com roteiro fechado.

## Marca d'água no vídeo da Decart, 07/10/2026 — deixada como está

O usuário notou uma marca d'água no vídeo ao vivo. Não é do nosso código (só desenhamos o logo do SENAI Lab
Fashion na foto impressa). O changelog da Decart (maio/2026) cita "server-baked pixels (watermarks,
overlays)": a marca é gravada pelo servidor deles nos pixels do vídeo gerado. Não há opção no
`@decartai/sdk` 0.2.5 nem menção na documentação do VTON para removê-la. **Decisão do usuário: não remover.**
Em aberto para a Etapa 2: se a marca depende do plano da conta (perguntar ao suporte da Decart) — não foi
verificado se ela já aparecia com a chave antiga. Vale lembrar que a foto impressa também leva a marca.

## Gestos para escolher/tirar peça sem tocar na TV, 15/10/2026

Pedido do usuário: o visitante fica a 1,5–2 m da TV e não depende do operador para escolher peça. Feito com
a pose do MediaPipe que já detecta presença (local, sem custo na Decart): mão direita/esquerda levantada =
próxima/anterior, duas mãos acima da cabeça por 1,5 s = escolher; com peça escolhida, esse mesmo gesto é a
**única** opção e tira a peça (evita troca por engano). Setas + Enter + Backspace como reserva.

- Lógica pura em `web/lib/gesture-engine.ts`, testada com 12 cenários de poses simuladas (repetição,
  tempo mínimo, "soltar antes de repetir", pulso fora do quadro, modo vestindo ignora mão única).
  **Não testada com pessoa real** — depende de enquadramento da Canon e da distância; ver checklist.
- Durante a sessão a leitura da pose sobe de 1 para ~8 por segundo (precisa para gestos); em espera
  continua 1 por segundo. O tempo para considerar "pessoa saiu" segue em 3 s.
- "Tirar a peça" só esconde a IA na tela (volta a câmera crua). O SDK tem `setImage(null)`, mas não
  verifiquei o que o modelo faz com o prompt antigo, e testar gasta crédito; o limite de 30 s já
  controla o custo. Para a Etapa 2: testar `set({ prompt, image: null })` de verdade.
- Interruptor: `GESTURES_ENABLED` em `web/app/page.tsx`.

**Atualização 15/10/2026: gestos retirados a pedido do usuário.** Ficou só a navegação por teclado
(setas, Enter, Backspace/Delete), para não depender do mouse. A detecção de presença voltou a 1 leitura por
segundo. O código dos gestos (lógica testada com poses simuladas) continua no histórico do git, commit
`ad7dfc5`, se a Etapa 2 quiser retomar.
