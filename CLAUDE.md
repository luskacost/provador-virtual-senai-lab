# CLAUDE.md — Provador Virtual em Tempo Real (Exposição)

> Arquivo de contexto para o Claude Code. Leia inteiro antes de qualquer tarefa neste repositório.
> Idioma de trabalho: **português do Brasil** (código e commits podem ser em inglês; comentários e explicações em PT-BR).

---

## 1. Objetivo e prazo

Montar um **provador virtual em tempo real** para uma **exposição em 27/10/2026**. O visitante fica em frente à webcam, escolhe uma peça num catálogo de roupas do laboratório e se vê vestindo a peça **ao vivo**, com aparência fotorrealista. Trocar de peça troca a roupa no vídeo sem reiniciar.

Contexto: laboratório de Engenharia de Produção e Design de Moda. O projeto será apresentado ao público e aos coordenadores — se houver boa aceitação, vira uma aplicação própria no futuro (seção 9).

**Prioridade absoluta: funcionar de forma estável no dia do evento.** Robustez > funcionalidades novas. Código elegante é secundário.

---

## 2. Estratégia em duas etapas

| Etapa | Quando | O que é |
|---|---|---|
| **1 — Exposição** (ESCOPO ATUAL) | agora → 27/10/2026 | Adaptar um **exemplo oficial da Decart** com o catálogo e a identidade do laboratório |
| **2 — Aplicação própria** (FORA DO ESCOPO) | depois do evento, se aprovado | App próprio construído sobre a API da Decart |

Tudo que fizermos agora deve **gerar aprendizado para a Etapa 2** (ver seção 9), mas não comece a Etapa 2 sem pedido explícito.

### ⚠️ Plano anterior

Existe um plano anterior ("Provador Virtual 3D", tarefas T0–T14, baseado em webcam + Python). **Se encontrar arquivos desse plano no repositório, leia-os e aponte ao usuário os conflitos antes de apagar, mover ou sobrescrever qualquer coisa.**

---

## 3. Base técnica (decidida — não reabrir sem falar com o usuário)

- **Modelo:** Decart Lucy VTON (virtual try-on em tempo real via WebRTC).
- **Troca de fundo é outro modelo:** a edição geral por prompt (Lucy 2.1 / 2.5) faz fundo, objetos e estilo; o VTON é especializado em roupa. Ver seção 4.7 — recurso **opcional**, condicionado a teste.
- **Ponto de partida:** repositório oficial https://github.com/DecartAI/tryon-examples (exemplos em Next.js).
- **SDK:** `@decartai/sdk`.
- **Chave de API:** fica apenas no servidor (rota de API do Next.js / `.env.local`); o navegador recebe **token temporário**.

Alternativas descartadas: Higgsfield (assíncrona, não é tempo real); gravar vídeo e reprocessar (latência e custo); overlay 2D com MediaPipe (pouco realista).

**Não troque de framework, não reescreva do zero e não "melhore" a arquitetura do exemplo.** Adapte o mínimo necessário.

O usuário tem Python intermediário e menos experiência com Next.js/TypeScript/WebRTC: explique brevemente as mudanças que não forem óbvias.

---

## 4. Requisitos para o evento

### 4.1 Catálogo
- Peças reais do laboratório, fotografadas pelo usuário.
- Formato da peça (adaptar ao que o exemplo já usa, se houver estrutura própria):
  ```json
  {
    "id": "jaqueta-jeans-01",
    "nome": "Jaqueta Jeans Oversized",
    "categoria": "top",
    "imagem": "/catalog/jaqueta-jeans-01.png",
    "prompt": "Substitute the current top with a light blue denim jacket with an oversized relaxed fit"
  }
  ```
- Prompts em **inglês**, seguindo os padrões *substitute* / *add* do guia de prompts do VTON (ver Referências).
- Imagens JPEG/PNG/WebP, **peça sozinha em fundo neutro**. Mínimo 512x512.
- Adicionar/remover peça deve ser fácil (editar um JSON + colocar imagem numa pasta basta — não precisa de tela de cadastro).
- Campo opcional `"ativo": false` para esconder peças que ficaram ruins nos testes.

### 4.2 Interface (modo quiosque)
- Tela cheia, legível a 1,5–2 m de distância: botões grandes, pouco texto.
- Identidade visual do laboratório (cores, logo, nome do projeto — o usuário fornecerá).
- Vídeo grande; catálogo em grade ao lado ou embaixo.
- Estados visíveis e amigáveis: `pronto para começar` → `conectando` → `ao vivo` → `algo deu errado, tente de novo`.
- Tela inicial de espera ("Toque para experimentar") quando ninguém está usando.

### 4.3 Controle de sessão e custo (obrigatório — cobrança por segundo de geração ativa)
- Sessão com a Decart **só abre** quando o visitante inicia.
- Limite por visitante (configurável) com contagem regressiva visível. **Decidido em 07/10/2026: 30 s de limite, 15 s de inatividade e 10 s de pausa entre visitantes** (em vez dos 90 s do padrão original) — suficiente para o visitante e economiza créditos da Decart.
- Encerrar automaticamente por inatividade, ao trocar de aba e ao chegar no limite; voltar para a tela de espera.
- Atalho de teclado do operador para **encerrar sessão imediatamente** e **resetar** a aplicação.
- Usar modo padrão (não usar `speed: "fast"`, que custa o dobro).

### 4.4 Robustez
- Se a conexão cair: mensagem amigável + botão de tentar de novo; nunca tela branca ou erro técnico.
- Se a câmera falhar: mensagem clara para o operador.
- Nada de dependência de recursos externos além da Decart (fontes, imagens e scripts locais).

### 4.5 Métricas do evento (para apresentar aos coordenadores)
- Registrar **localmente** em JSON (ex: `data/metricas.json` via rota de API): início/fim de cada sessão, duração, peças experimentadas.
- **O estande não grava nem guarda vídeo/imagem para si** (métricas são só texto/números). A exceção é a
  seção 4.5b: uma foto/vídeo que o próprio visitante pediu para levar, e que não fica retida depois.
- Script ou página simples que resume: total de sessões, duração média, ranking de peças.

### 4.5b Foto do visitante para ele levar (decidido em 30/09/2026, mecanismo trocado em 05/10/2026)

Pedido do usuário, inspirado no Anywear (seção 10): botão "Tirar foto" do resultado ao vivo.

**Primeira tentativa (30/09, abandonada em 05/10):** QR code para o visitante baixar no próprio celular,
com a captura guardada só na memória do processo por um tempo curto. Funcionou em testes, mas foi
abandonada: exige o navegador do quiosque abrir pelo IP da rede local (não `localhost`) **e** depende da
rede Wi-Fi do evento não ter isolamento entre dispositivos (muitas redes de evento/feira têm esse
isolamento por segurança, o que quebraria o recurso sem aviso no dia) — risco grande demais para testar
só no dia.

**Mecanismo atual:** a foto é capturada no navegador (canvas, espelhada como o visitante vê na tela, com
o logo do SENAI Lab Fashion marcado no canto) e impressa **direto pela impressora do quiosque**
(`window.print()`). Nunca passa por rede, nunca toca um servidor — mais simples e mais robusto que o QR
code. Exige uma impressora configurada e conectada ao quiosque.

**Gravação de vídeo foi testada e removida em 05/10/2026** (sem solução de entrega aceitável sem rede) —
volta a valer o item "gravação de vídeo dos visitantes" da seção 8 como fora de escopo.

### 4.6 Privacidade (LGPD)
- Aviso na tela inicial: o vídeo é processado em tempo real por um serviço externo, só para gerar a
  prévia da roupa; não é armazenado pelo estande. Ao usar "Tirar foto", a imagem vai direto para a
  impressora do estande e não fica guardada por nós. Texto curto; o usuário valida a redação.

### 4.7 Troca de fundo / cenário (OPCIONAL — só entra se o teste da Fase 1b for aprovado)

**Contexto.** A Decart oferece edição de fundo em tempo real por prompt de texto (ex: `"Change the background to a sandy beach with clear blue water."`), sem imagem de referência, nos modelos de edição geral (Lucy 2.1 / 2.5). O VTON é um modelo separado, com endpoint e preço próprios. O Lucy 2.5 cobre roupa e fundo num único prompt, mas **não está verificado** se a qualidade da roupa iguala a do VTON dedicado, e o preço dele pode ser o dobro (confirmar no painel).

**Caminhos a testar** (nesta ordem, parando no primeiro que atender aos critérios):

| Caminho | Como | Observação |
|---|---|---|
| **B. VTON + fundo local** | VTON veste a roupa; o fundo é trocado **antes** de enviar o vídeo, por segmentação local (ex: MediaPipe selfie segmentation), ou é um fundo físico | Hipótese não testada: depende de o VTON preservar o fundo já trocado. Custo extra zero |
| **A. Lucy 2.5 sozinho** | Um prompt pede roupa **e** fundo na mesma conexão | Comparar a roupa lado a lado com o VTON |
| ~~C. Encadear dois modelos~~ | Saída de um vira entrada do outro | **Não fazer**: dobra custo e latência e degrada a imagem |

**Critérios de aprovação** (o usuário decide; você apresenta evidências):
- Bordas (cabelo, mãos, movimento rápido) sem tremor ou "recorte" visível.
- Qualidade da roupa igual ou muito próxima à do VTON dedicado.
- Latência percebida aceitável e custo por sessão compatível com a seção 4.3.
- Testar com pessoas diferentes, na luz do ambiente do evento (não só com o usuário).

**Regras:**
- Não integre nada ao quiosque antes de o usuário aprovar o resultado do teste.
- Só entra no evento se estiver **estável até 16/10**. Caso contrário, use **fundo físico neutro** e registre isso em `docs/checklist-estande.md`.
- Se aprovado, a interface é um seletor simples de cenários (ex: passarela, rua, vitrine), com opção "sem cenário" como padrão.

**Decidido em 07/10/2026: REPROVADO, fora do evento.** Testados os caminhos B e A (fundo que não aparecia,
peça duplicada, cor do fundo mudando com o movimento, custo alto). O estande usa fundo físico neutro
(registrado em `docs/checklist-estande.md`). Código do teste apagado; resultados e o que refazer na Etapa 2
estão em `docs/aprendizados.md`. Não retomar antes do evento sem pedido explícito do usuário.

---

## 5. Segurança

- Chave `DECART_API_KEY` só em `.env.local` (servidor). Nunca no código do navegador, nunca em commit.
- `.env.example` sem valor real; `.env.local` e `data/` no `.gitignore` **antes** do primeiro commit.

---

## 6. Plano de execução

Execute em ordem. **Ao final de cada fase: pare, resuma o que foi feito, diga como testar e peça confirmação.**

| Fase | Conteúdo | Meta |
|---|---|---|
| **0 — Reconhecimento** | Ver o que existe no repo; checar plano antigo; clonar/analisar `tryon-examples`; listar os exemplos disponíveis e **recomendar ao usuário qual usar como base** (o mais simples que tenha câmera + troca de peça por imagem); ler a documentação atual da Decart e confirmar nomes de modelo (VTON **e** edição geral Lucy 2.1/2.5), métodos do SDK, fluxo de token e preços atuais | até 02/10 |
| **1 — Rodando** | Exemplo escolhido rodando localmente com a chave do usuário e 3–5 peças dele | até 02/10 |
| **1b — Teste de fundo (opcional)** | Seção 4.7: testar os caminhos B e A **fora do quiosque** (playground ou script isolado), gravar resultados e custos em `docs/aprendizados.md` e apresentar ao usuário para decisão | até 05/10 |
| **2 — Catálogo + visual** | Catálogo em JSON, peças do laboratório, identidade visual, modo quiosque; se a 1b foi aprovada, seletor de cenários | até 09/10 |
| **3 — Sessão e robustez** | Seção 4.3 e 4.4 completas, atalhos do operador | até 09/10 |
| **4 — Métricas + aviso LGPD** | Seções 4.5 e 4.6 | até 16/10 |
| **5 — Testes de campo** | Ajustes após testes em outra rede, outra luz, outras pessoas; desativar peças ruins | até 23/10 |
| **6 — Congelamento** | A partir de 24/10: **só correções de bugs**. Gerar `docs/operacao-evento.md` (como ligar, atalhos, o que fazer se cair) e `docs/checklist-estande.md` | 24/10 |

Se uma fase atrasar, avise e proponha o que cortar — nunca comprometa as fases 3 e 6.

---

## 7. Regras de trabalho para o Claude Code

1. **Verifique a documentação atual da Decart antes de mexer na integração.** Não invente métodos, parâmetros ou endpoints; se não encontrar, pergunte.
2. Na documentação, `set()` **substitui o estado inteiro** — campos omitidos são limpos. Ao trocar de peça, envie sempre imagem **e** prompt.
3. Mudanças pequenas e testáveis. Commits frequentes com mensagens claras.
4. Não adicione dependências sem justificar.
5. Não apague nem sobrescreva arquivos existentes sem confirmar.
6. Se algo das seções 2–4 parecer errado na prática, **pare e explique** em vez de mudar por conta própria.
7. Seja direto sobre limitações e riscos (custo, rede, peças que o modelo representa mal).
8. Após o congelamento (24/10), recuse refatorações e features novas; apenas correções.
9. Troca de fundo: seguir estritamente a seção 4.7. Teste isolado primeiro, integração só com aprovação explícita do usuário.

---

## 8. Fora do escopo agora

Extensão de navegador para sites de terceiros · login · banco de dados · deploy em nuvem · app mobile · modo offline com MediaPipe (exceto a segmentação local usada no teste opcional da 4.7) · troca de fundo por IA no quiosque (exceto se aprovada na Fase 1b) · backend Python · **gravação/compartilhamento de vídeo dos visitantes**.

(Esse último item saiu da lista em 30/09/2026 a pedido do usuário, foi implementado e testado, e **voltou
a entrar** em 05/10/2026: sem rede disponível no app, dependência de rede do evento não ter isolamento
entre dispositivos era risco demais para testar só no dia — ver seção 4.5b. **Foto** do visitante
continua no escopo, via impressão local, sem essa dependência de rede.)

---

## 9. Preparando a Etapa 2 (aplicação própria)

Não implementar agora. Mas, durante o trabalho, **mantenha `docs/aprendizados.md` atualizado** com:
- Como a integração com a Decart funciona de fato (token, conexão, troca de peça, erros encontrados).
- Que tipo de peça/foto funciona bem e mal no modelo.
- Custos reais medidos nos testes e no evento.
- Partes do exemplo oficial que seriam reaproveitáveis e partes que seriam refeitas.
- Ideias e pedidos que surgirem dos visitantes e coordenadores.
- Resultados do teste de fundo (qual caminho foi testado, qualidade das bordas, latência, custo) e ideias de cenários para o produto (passarela, rua, vitrine).

Direção provável da Etapa 2 (apenas referência): aplicação própria sobre a API da Decart, possivelmente com backend Python (FastAPI) para tokens e gestão de catálogo, cadastro de peças via interface, e uso em consultorias com empresas de moda.

---

## 10. Referências

- Exemplos oficiais: https://github.com/DecartAI/tryon-examples
- Documentação — Virtual Try-On realtime: https://docs.platform.decart.ai/models/realtime/virtual-try-on
- Guia de prompts do VTON (link a partir da página acima)
- Preços: https://docs.platform.decart.ai/getting-started/pricing
- Modelo de edição geral em tempo real (fundo, objetos): https://docs.platform.decart.ai/models/realtime/lucy-2.1
- Lucy 2.5 na fal (prompt único para fundo/roupa/VFX): https://fal.ai/models/decart/lucy-2-5/realtime
- Chave de API: https://platform.decart.ai
- Referência de experiência (produto da Decart): https://anywear.decart.ai/virtual-try-on
