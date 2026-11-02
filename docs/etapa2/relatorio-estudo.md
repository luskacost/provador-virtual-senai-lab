# Estudo para a próxima etapa do Provador Virtual

**SENAI Lab Fashion · 02/11/2026**

Estudo feito depois da exposição de 27 a 29/10/2026 para avaliar o uso profissional e comercial do provador.
Duas frentes: (1) a viabilidade de acionar o provador por um **ID da peça** (proposta em
`docs/etapa2/ideia-id-da-peca.md`) e (2) a expansão para **nichos específicos**. Cada frente foi pesquisada
por um agente separado; as afirmações sobre a Decart (SDK, guia de prompts, política de uso) foram conferidas
por mim nas fontes oficiais. Itens marcados "(hipótese)" não têm fonte.

---

## 1. Resumo executivo

- **O ID da peça é tecnicamente viável hoje.** A Decart já permite emitir, por sessão, um token com prazo,
  modelos permitidos, origens permitidas e **teto de duração aplicado por ela**. O que falta construir é nosso:
  cotas, orçamento, IDs assinados, banco de dados e, no celular do cliente, nuvem com HTTPS.
- **O risco principal é econômico, não técnico.** Com a sessão média do evento (127 s), cada sessão custa
  US$ 2,54 e o custo por venda fica entre US$ 10 e US$ 51. A conta só fecha com sessões de até 20–30 s e
  conversão de 10% ou mais, e nada ainda comprova esses números. **O teto de duração pesa mais que o ID.**
- **Nichos mais promissores:** EPI e uniformes profissionais (B2B), que foi o destaque do evento e é o público
  natural do SENAI, e festa/aluguel de trajes. **Evitar por ora:** lingerie/praia e moda infantil, pelo risco
  legal e de uso indevido.
- **Recomendação:** um piloto pequeno de **EPI/uniformes em quiosque**, com a peça aberta pelo código da
  etiqueta e teto de 30 s, medindo segundos reais e interesse do comprador. Em paralelo, manter um "modo
  vitrine" sem ID para eventos.

---

## 2. ID da peça

### Veredito
Viável e com base técnica pronta na Decart. Controla e atribui o custo, mas **não garante, sozinho, mais
conversão**. Os números da proposta (sessões de 15–20 s, conversão de 10–25%) são otimistas e precisam
ser medidos em piloto.

### Pontos positivos
- **Teto de custo aplicado pela Decart:** `constraints.realtime.maxSessionDuration` no token (confirmado no
  SDK). Hoje o limite fica só no nosso código, no navegador.
- **Muito do quiosque atual é reaproveitado:** token emitido no servidor, catálogo com `id` por peça, métricas
  por sessão e por peça, detecção de presença e o controle de sessão (com limite hoje desligado).
- **QR e código digitável custam quase zero;** EAN e RFID muitas vezes já existem nas grandes redes.
- **Gera dados que hoje não existem:** qual peça foi provada, quanto tempo e, com integração, se virou venda.
- **Medição de custo mais precisa:** o SDK emite `generationTick` e `generationEnded` (confirmado), que hoje o
  app não usa.

### Pontos negativos e riscos
| Risco | Mitigação |
|---|---|
| Sessões de 15–20 s são otimistas: no evento foram 127 s e 7,5 trocas por sessão | Piloto com teto de 30 s e registro dos segundos reais |
| Conversão de 10–25% sem fonte | Grupo de controle no piloto |
| O filtro do ID tira o efeito "atração": no evento o público preferiu peças chamativas e ignorou as camisetas lisas, que são as de compra do dia a dia | Separar **modo vitrine** (marketing, orçamento fixo) de **modo venda** (por ID) |
| O token da Decart **não é de uso único**: inicia conexões até expirar; QR copiado segue valendo nesse prazo | Token curto (~30 s), um por clique, `allowedOrigins` e cota no nosso servidor |
| **Não há teto de gasto na Decart** (só limite de sessões simultâneas por chave) | Orçamento diário controlado no nosso gateway |
| Fluxo no celular do cliente exige o que hoje está fora do escopo: nuvem, HTTPS, banco de dados | Começar no quiosque da loja |
| LGPD: com cupom ou WhatsApp, os dados de intenção viram dado pessoal | Consentimento antes da câmera, sessão anônima, retenção curta, parecer jurídico |
| O que acontece quando o teto de duração é atingido **não está documentado** | Testar antes do piloto |

### O que a Decart permite (conferido)
| Item | Situação | Fonte |
|---|---|---|
| Token com `expiresIn`, `allowedModels`, `allowedOrigins`, `metadata` | Confirmado | SDK `dist/tokens/client.d.ts` |
| Teto por sessão: `constraints.realtime.maxSessionDuration` | Confirmado | SDK `dist/tokens/client.d.ts` |
| Eventos `generationTick` / `generationEnded`; fim por `insufficient_credits`, `session_limit`, `moderation_violation` | Confirmado | SDK `dist/realtime/*` |
| Token de uso único | Não existe | doc client-tokens (agente) |
| Teto de gasto por token ou por chave | Não encontrado | SDK + doc |
| Preço VTON: US$ 0,02/s padrão, US$ 0,04/s fast | Confirmado | doc de preços |

### Conta de custo (US$ 0,02/s; custo por venda = custo por sessão ÷ conversão)
| Sessão | Custo/sessão | Conv. 5% | Conv. 10% | Conv. 25% |
|---|---|---|---|---|
| 127 s (média do evento) | US$ 2,54 | US$ 50,80 | US$ 25,40 | US$ 10,16 |
| 30 s (teto) | US$ 0,60 | US$ 12,00 | US$ 6,00 | US$ 2,40 |
| 20 s | US$ 0,40 | US$ 8,00 | US$ 4,00 | US$ 1,60 |
| 15 s | US$ 0,30 | US$ 6,00 | US$ 3,00 | US$ 1,20 |

Com câmbio de ~R$ 5,5 e margem de 30–50% (hipótese): peças acima de R$ 400 fecham a partir de 30 s com 10%;
peças de ~R$ 200 só com ≤20 s e ≥10%; camisetas de R$ 60–80 só com 15 s e 25%.

### Mecanismo do ID para começar
**QR impresso ou o EAN que a etiqueta já tem**, lido por um leitor USB no quiosque. NFC (~R$ 2,40 por
etiqueta, segundo o agente) e RFID ficam para depois, ou só para redes que já usam RFID.

### Esforço estimado (1 desenvolvedor; hipótese)
| Entrega | Esforço |
|---|---|
| Token com teto e restrições + registro dos segundos reais | ~3 dias |
| Rota por peça com ID assinado | ~1 semana |
| Cotas, orçamento diário e banco de dados | 3–4 semanas |
| Nuvem com HTTPS + fluxo no celular do cliente | 2–3 semanas |
| Painel de custo por peça/loja | ~1 semana |
| Integração com PDV/e-commerce | 3–8 semanas |

**Piloto no quiosque, sem PDV: ~2–3 semanas.** No celular do cliente: ~6–9 semanas. Com PDV: +1–2 meses.

---

## 3. Nichos específicos

### Comparação
| Nicho | Viabilidade técnica | Risco | Prioridade |
|---|---|---|---|
| **EPI e uniformes (B2B)** | Alta no tronco; média em mãos e cabeça | Baixo | **1** |
| **Festa / noiva / aluguel** | Alta | Baixo a médio | **1–2** |
| Esportivo / fitness | Alta | Médio (roupa justa) | 2 |
| Acessórios grandes (chapéu, bolsa, colar) | Média (o guia da Decart tem padrão) | Baixo | 2 |
| Calçados | Média (hipótese: pés no quadro, câmera baixa) | Médio (operação) | 2 |
| Acessórios pequenos (joias finas, relógio, óculos) | Baixa a média | Médio | 3 |
| Plus size | Depende de teste | Médio (viés do modelo) | Teste em todos os nichos |
| Lingerie / praia | Média (hipótese) | **Alto** | 3 |
| Infantil | Desconhecida | **Alto** | 3 |

### Pontos positivos
- **EPI/uniformes:** jaquetas de bombeiro foram as peças mais usadas do evento (83 e 52 aplicações).
  Encaixe direto com a indústria atendida pelo SENAI: showroom para compradores compararem modelos, cores e
  faixas refletivas antes de um pedido em lote. Já existem soluções B2B no exterior.
- **Festa/aluguel:** vestido e macacões foram dos mais usados. Peças caras e pouco provadas, então a prévia
  economiza prova física. O guia da Decart tem o padrão "Substitute the outfit with…".
- **Acessórios grandes e calçados:** o guia oficial tem padrões próprios para calçado, chapéu e colar, e cita
  bolsa como exemplo de "Add … to the outfit".

### Pontos negativos e riscos
- **Luvas, capacete e óculos** foram usados no evento sem avaliação formal. O guia da Decart **não fala de mãos
  nem de óculos**. No EPI, o cliente pode achar que a imagem "certifica" a peça: avisar que é só visualização,
  sem validar ajuste nem certificado (CA).
- **Calçados:** os pés precisam aparecer, o que pede câmera baixa ou um segundo enquadramento; os concorrentes
  usam AR com modelos 3D, não geração por IA. O guia não documenta enquadramento.
- **Joias e relógios:** peças pequenas tendem a se perder no vídeo (hipótese); concorrentes de AR são mais
  precisos.
- **Plus size:** a literatura aponta viés de corpo em modelos de try-on; não há dado sobre o modelo da Decart.
  Testar com corpos diversos antes de oferecer comercialmente, e não prometer caimento nem tamanho.
- **Lingerie/praia:** gera imagem quase nua de uma pessoa real ao vivo. A política da Decart proíbe imagem
  íntima não consentida (conferido); num quiosque público, alguém pode "vestir" quem passa. Só em formato
  privado, com consentimento e parecer jurídico.
- **Infantil:** a LGPD (art. 14) exige consentimento específico de um dos pais; a política da Decart proíbe
  conteúdo sugestivo envolvendo menores (conferido). Não vale o risco agora.

### Achado sobre os nossos prompts
O guia oficial usa "Substitute the **upper body garment**…" e "Add … **to the outfit**"; o nosso catálogo usa
"Substitute the **current top**…" e "to the hands/head/face". Vale testar se o padrão oficial melhora as peças
de mão, cabeça e rosto (não muda nada no quiosque atual).

---

## 4. Recomendações e próximos passos

1. **Piloto B2B de EPI/uniformes no quiosque** (une as duas frentes): 5 peças de uma empresa parceira
   fotografadas em fundo neutro; peça aberta pelo EAN/QR da etiqueta; token com teto de 30 s; 5 pessoas de
   biotipos diferentes; cada peça testada com o prompt atual e com o padrão oficial; notas de fidelidade
   (faixa refletiva, bolsos, cor), estabilidade e mãos/cabeça; ao final, perguntar ao comprador se isso
   ajudaria a decidir um pedido. Custo de geração estimado: ~US$ 12 (hipótese).
2. **Primeiro ajuste técnico, barato e útil para qualquer caminho:** token com `maxSessionDuration`,
   `expiresIn` curto e `allowedOrigins`, e registro dos segundos reais via `generationTick` (~3 dias).
3. **Manter o modo vitrine** para eventos, separado do modo venda.
4. **Festa/aluguel** como segundo nicho, com uma loja parceira.
5. **Calçados e acessórios grandes** depois de um teste de enquadramento.
6. **Lingerie/praia e infantil** só depois de parecer jurídico e em formato privado.

## 5. Perguntas em aberto
1. Qual o foco inicial: indústria (B2B), loja física, e-commerce ou eventos?
2. Há uma empresa parceira de EPI/uniformes para o piloto?
3. Qual o ticket médio das peças do piloto? Ele define se o custo por segundo cabe na margem.
4. A loja ou empresa tem equipe para acompanhar a prova?
5. Haverá integração com PDV para medir a conversão de ponta a ponta?
6. O SENAI tem jurídico para avaliar LGPD antes de um piloto com cupom ou contato do cliente?

## 6. Fontes e método
- **Conferido por mim:** SDK `@decartai/sdk` 0.2.5 instalado (`dist/tokens/client.d.ts`, `dist/realtime/*`);
  guia de prompts do VTON (https://docs.platform.decart.ai/models/realtime/vton-3.5-prompting.md); política de
  uso (https://docs.platform.decart.ai/resources/aup, atualizada em 12/02/2026); métricas do evento
  (`web/data/metricas.json`, resumidas em `docs/aprendizados.md`).
- **Trazido pelos agentes, não conferido por mim:** preços de etiquetas NFC (KaBuM), RFID na Renner, ticket
  médio do Natal 2025 nos shoppings (R$ 221), exemplos de mercado (Kimberly-Clark Symbiosis Man, TRICORP
  TriFit, Threekit, Perfect Corp/YouCam, Wanna Kicks, Gucci, apps de try-on do Shopify) e a literatura sobre
  viés de corpo (arXiv 1912.06697, 2408.02803). Os links estão nos relatórios dos agentes.
- **LGPD, art. 14:** citado de memória pelo agente; confirmar o texto oficial.
