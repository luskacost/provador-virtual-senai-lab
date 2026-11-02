# Provador virtual com ID da peça: a ideia, as possibilidades e os detalhes

> Documento enviado pelo usuário em 02/11/2026 (arquivo original: `ideia-id-da-peca-provador-virtual.md`),
> guardado aqui sem alterações para o estudo da Etapa 2.

## 1. A ideia em uma frase

Em vez de liberar o catálogo inteiro para qualquer pessoa experimentar, **cada peça física ou digital carrega um ID único**. O provador só é acionado quando o consumidor, ao demonstrar interesse real, **apresenta esse ID** (escaneando, tocando ou digitando). Assim, o provador deixa de ser uma atração aberta e passa a ser uma **ferramenta de venda ligada a uma peça específica**.

## 2. Por que isso resolve problemas reais

| Problema | Como o ID ajuda |
|---|---|
| **Custo por segundo de IA** (ex.: US$ 0,02/s) | Cada sessão tem peça, duração e orçamento definidos. O gasto passa a ser previsível e atribuível a uma venda ou não venda. |
| **Curiosos que só querem brincar** | Para provar, é preciso ter a peça na mão ou estar numa página de produto. Isso filtra quem não tem intenção. |
| **Catálogo inteiro disponível = custo sem controle** | Só as peças elegíveis (ex.: lançamentos, ticket alto, tamanho em estoque) ficam habilitadas. |
| **Falta de dados sobre intenção** | Cada prova vira um evento "peça X provada, por quanto tempo, por qual perfil, com qual resultado". |
| **Atribuição de venda** | Prova → compra fica rastreável pelo mesmo ID, o que sustenta cobrança por performance. |
| **Experiência confusa** | O consumidor não precisa navegar por centenas de itens; a peça que ele tem em mãos já abre o provador. |

## 3. Como o ID pode chegar ao consumidor

### 3.1 Opções de suporte físico e digital

| Mecanismo | Como funciona | Vantagens | Limitações |
|---|---|---|---|
| **QR code na etiqueta/cabide** | Cliente escaneia com o celular e abre uma URL com o ID | Barato, funciona em qualquer celular, fácil de imprimir | Precisa de câmera e de boa luz; pode ser fotografado e reutilizado |
| **NFC na etiqueta** | Cliente encosta o celular e abre a URL | Experiência fluida, difícil de copiar à distância | Custo por etiqueta maior; nem todo celular antigo lê |
| **RFID (UHF)** | Leitor no provador/cabine identifica a peça sozinha | Ótimo para provador físico automatizado, sem ação do cliente | Infraestrutura mais cara; faz sentido para redes maiores |
| **Código de barras/EAN já existente** | Aproveita o código da etiqueta atual | Zero custo de etiqueta nova | EAN identifica o produto/variante, não a unidade; exige leitor |
| **ID digital (página de produto/app)** | Botão "Experimentar" no e-commerce, o ID vem da página | Totalmente digital, sem etiqueta | Perde o filtro de "ter a peça na mão" |
| **Código curto digitável** | Código de 6 a 8 caracteres impresso na etiqueta | Funciona sem câmera e sem NFC | Atrito de digitação; sujeito a erro |
| **Cartão/QR do vendedor** | Vendedor libera a peça para o cliente | Une provador e abordagem de venda | Depende de pessoal disponível |

### 3.2 Granularidade do ID: o que ele identifica?

| Nível | Exemplo | Quando usar |
|---|---|---|
| **Modelo** | Sutiã "Renda Clássica" | Catálogo geral, dados de interesse por modelo |
| **Variante (SKU)** | Renda Clássica, preto, tamanho 42C | Estoque e recomendação de tamanho |
| **Unidade individual (serial)** | Peça física nº 000123 | Controle antifraude, vínculo com estoque físico, link de uso único |

Recomendação para o protótipo: **ID de modelo + variante (SKU)**, com um **token de sessão** separado para controlar uso e custo (ver seção 5).

## 4. Fluxos possíveis

### 4.1 Loja física (cabine ou espelho inteligente)

1. Cliente pega a peça (com QR/NFC/RFID).
2. Aproxima do leitor ou escaneia.
3. O sistema valida: a peça está elegível? Há orçamento? A cota do cliente permite?
4. Inicia a sessão com tempo máximo (ex.: 15 a 20 s por peça).
5. Ao final, oferece compra no balcão ou por link, com o mesmo ID.

### 4.2 Loja física com celular do próprio cliente

1. Cliente escaneia o QR da etiqueta.
2. Abre uma página web (sem instalar app) com o ID na URL.
3. Aceita o consentimento, libera a câmera e testa a peça.
4. Pode salvar a peça numa lista de desejos ou finalizar a compra online.

### 4.3 E-commerce

1. Na página do produto, botão "Experimentar" (o ID vem da própria página).
2. O sistema aplica cota por visitante e por dia.
3. A sessão é curta e termina com chamada para compra (adicionar ao carrinho).

### 4.4 Showroom B2B (indústria para lojistas)

1. O lojista acessa o portal com login.
2. Cada peça do mostruário tem ID; o lojista experimenta as que está avaliando comprar.
3. Os dados de prova alimentam o planejamento de coleção.

### 4.5 Eventos e ativações (feiras, desfiles, lançamentos)

1. Modo demonstração com **orçamento fixo** e peças pré-selecionadas.
2. O custo entra como marketing, não como custo de venda.
3. QR em totens e convites para controle de fila.

## 5. Controle de uso, custo e abuso

O ID sozinho filtra bastante, mas pode ser copiado (um QR pode ser fotografado). Camadas adicionais:

| Camada | Descrição |
|---|---|
| **Token de sessão** | O ID abre uma sessão com token único e prazo de validade (ex.: 10 minutos). O token expira e não pode ser reutilizado. |
| **Cota por cliente** | Ex.: 3 provas gratuitas por dia, por dispositivo ou por contato verificado (WhatsApp). |
| **Cota por peça** | Limite de provas por dia para cada peça, evitando que uma única peça consuma o orçamento. |
| **Teto de duração** | Encerramento automático (ex.: 10 a 20 s) com aviso visual de tempo. |
| **Orçamento diário por loja** | Limite de gasto em segundos de IA por loja/dia, com alerta ao chegar a 80%. |
| **Elegibilidade por peça** | Só peças marcadas como habilitadas (lançamentos, ticket alto, estoque disponível no tamanho). |
| **Presença física opcional** | Para NFC/RFID, a leitura só vale perto da peça; para QR, pode-se rotacionar o código ou usar token dinâmico. |
| **Detecção de pessoa** | Cobrar só quando há uma pessoa na câmera; pausar quando ela sai. |
| **Limitação de taxa (rate limit)** | Impede varredura automática de IDs (enumeração) e uso por robôs. |
| **IDs não previsíveis** | Evitar IDs sequenciais públicos; usar identificadores aleatórios ou assinados para que ninguém descubra outras peças por tentativa. |

### Equilíbrio entre filtro e experiência

Atrito demais mata o encanto. Sugestão de gradação:

- **Fluxo normal:** escanear e provar, com cota diária generosa.
- **Prova prolongada ou extra:** exige login rápido ou liberação do vendedor.
- **Modo demonstração:** tratado à parte, com orçamento próprio.

## 6. Incentivar a compra com o ID

O ID permite ligar a prova a uma ação comercial:

- **Cupom pós-prova:** quem provou ganha um desconto válido por 24 h para aquela peça.
- **Lista de desejos:** peça provada vira item salvo, com lembrete.
- **Aviso de estoque:** "seu tamanho está disponível nesta loja".
- **Venda cruzada:** após provar, sugerir peças complementares (também com ID).
- **Abordagem do vendedor:** o evento de prova avisa a equipe de que há um cliente interessado naquela peça.

## 7. Dados gerados pelo ID (e o valor deles)

Com o ID, cada prova gera um evento estruturado:

| Campo | Utilidade |
|---|---|
| `product_id` / `sku` | Quais peças despertam interesse |
| `session_id` anônimo | Funil prova → compra sem identificar a pessoa |
| Duração da prova | Engajamento e custo por peça |
| Resultado (comprou, devolveu, abandonou) | Taxa de conversão e de devolução por peça |
| Canal (loja, e-commerce, evento) | Onde o provador rende mais |
| Horário e loja | Planejamento de equipe e de estoque |
| Tamanho provado vs. comprado | Ajuste de tabelas de medidas e recomendação |

Esses dados têm valor próprio para a indústria: **peças muito provadas e pouco compradas**, **tamanhos mais procurados**, **interesse por região**. Podem virar um dashboard ou relatório vendido como serviço adicional.

Importante: tratar os dados de forma **agregada e anônima**, sem vincular a imagem ou o corpo de uma pessoa ao ID (ver seção 9).

## 8. Arquitetura técnica sugerida

```
Etiqueta (QR/NFC/RFID/código) ──► URL com ID assinado
                                      │
                                      ▼
                            Gateway de sessão
        (valida ID, elegibilidade, cota, orçamento, rate limit)
                                      │
                      emite token de sessão (curta duração)
                                      │
                                      ▼
                          Provador (provedor de IA)
              (tempo máximo, cobrança por segundo, encerramento)
                                      │
                                      ▼
                   Eventos (prova, duração, resultado)
                                      │
                                      ▼
               Painel de métricas / integração com PDV e e-commerce
```

Componentes principais:

| Componente | Responsabilidade |
|---|---|
| **Catálogo de IDs** | Relaciona ID ↔ modelo/variante ↔ marca ↔ regras de elegibilidade |
| **Gateway de sessão** | Valida o ID, aplica cotas e orçamento e emite o token temporário |
| **Controle de custo** | Contabiliza segundos usados por sessão, peça, loja e dia, e corta quando atinge o limite |
| **Registro de eventos** | Guarda provas e resultados de forma anônima |
| **Integração com PDV/e-commerce** | Fecha o ciclo "prova → compra" usando o mesmo ID |
| **Painel** | Mostra custo por venda, conversão por peça, uso por loja |

### Formato da URL (exemplo)

`https://provador.exemplo.com/p/{id_assinado}`

O ID na URL deve ser **opaco** (não sequencial) e, idealmente, **assinado** (com HMAC) para impedir que alguém forje IDs válidos.

## 9. Privacidade e segurança

- O ID identifica a **peça**, nunca a **pessoa**. Não vincule imagem ou corpo do cliente ao ID da peça de forma identificável.
- **Sessões anônimas** e processamento efêmero: sem gravar vídeo ou imagem, sem botão de print ou compartilhar, salvo opção explícita e consentida.
- **Consentimento explícito** antes de ligar a câmera, com finalidade única (LGPD).
- Uso de câmera ao vivo (e não de foto enviada) reduz o risco de alguém usar a imagem de terceiros.
- **Categorias sensíveis** (como roupas íntimas) pedem salvaguardas extras, detalhadas na conversa anterior: barreira de idade, filtro de conteúdo na saída, ambiente privado e preferência por abordagens sem câmera (questionário de medidas e avatar) no início.
- Proteja a API contra enumeração de IDs, abuso de cotas e vazamento de dados de uso.
- Registre o mínimo necessário e defina prazo de retenção.

## 10. Modelos de negócio com o ID

| Modelo | Como cobrar | Observação |
|---|---|---|
| **SaaS com franquia** | Mensalidade com X minutos incluídos; excedente com margem sobre o custo por segundo | Previsível para o cliente, margem protegida |
| **Performance** | Comissão sobre vendas atribuídas via ID | Requer integração com PDV/e-commerce; alinha incentivos |
| **Por ativação** | Preço fechado por evento, feira ou lançamento | Bom para entrada e para demonstrações |
| **B2B showroom** | Licença por indústria/coleção | Argumento: economia em amostras físicas e fotos de catálogo |
| **Dados e relatórios** | Assinatura de insights de intenção por peça | Produto complementar; exige dados agregados e anonimizados |
| **Híbrido** | Mensalidade base + comissão por venda | Reduz risco para a loja e garante receita mínima |

## 11. Conta de viabilidade (modelo simples)

**Custo por venda = (custo por sessão) ÷ (taxa de conversão)**

Com custo de US$ 0,02 por segundo (valor de referência; confirme os valores atuais com o provedor):

| Duração da sessão | Custo por sessão | Conversão 10% | Conversão 25% |
|---|---|---|---|
| 15 s | US$ 0,30 | US$ 3,00 por venda | US$ 1,20 por venda |
| 30 s | US$ 0,60 | US$ 6,00 por venda | US$ 2,40 por venda |
| 60 s | US$ 1,20 | US$ 12,00 por venda | US$ 4,80 por venda |

O ID melhora essa conta de duas formas: **aumenta a conversão** (a prova acontece com intenção real) e **limita os segundos** (sessão com teto e peça definida). Em peças de ticket médio ou alto, o custo por venda tende a caber na margem; em itens muito baratos, só fecha com conversão alta ou sessões muito curtas.

## 12. Riscos e pontos de atenção

| Risco | Mitigação |
|---|---|
| QR/ID copiado e reutilizado | Token de sessão com validade curta; ID assinado; NFC/RFID onde fizer sentido |
| Fricção excessiva reduz uso | Gradação de filtros; cota diária generosa; modo demonstração separado |
| Custo de etiquetas (NFC/RFID) | Começar com QR; migrar para NFC/RFID em lojas de maior volume |
| Peça sem dados de ajuste/medidas | Marcar como não elegível até a marca fornecer os dados |
| Dependência do provedor de IA e do preço por segundo | Camada de abstração para trocar de provedor; monitorar custo |
| Privacidade e dados sensíveis | Anonimização, consentimento, retenção mínima, avaliação jurídica (LGPD) |
| Operação em loja (treinar equipe, manter etiquetas) | Processo simples, material de apoio e projeto-piloto acompanhado |
| Peças indisponíveis no estoque | Integração de estoque para só habilitar provas com tamanho disponível |

## 13. Como validar a ideia (piloto)

1. **Escolher 1 loja e 1 marca** com 20 a 50 peças com ID (QR na etiqueta).
2. **Duração:** 30 dias.
3. **Grupos de comparação:** com provador por ID vs. sem provador (ou antes/depois).
4. **Métricas:**
   - taxa de conversão (prova → compra);
   - segundos médios por prova e por venda;
   - custo de IA por venda;
   - ticket médio;
   - taxa de devolução;
   - proporção de provas "curiosas" (sem compra) com e sem o filtro do ID;
   - satisfação do cliente e da equipe de vendas.
5. **Decisão:** se o custo por venda ficar abaixo da margem de contribuição e a conversão subir, partir para mais lojas e para o modelo comercial.

## 14. Roadmap sugerido

| Fase | Entrega |
|---|---|
| **1. Fundação** | Catálogo de IDs, URLs assinadas, gateway de sessão com token e teto de duração |
| **2. Controle de custo** | Cotas por cliente/peça/loja, orçamento diário, painel básico |
| **3. Piloto** | QR em etiquetas numa loja, coleta de métricas, ajustes de fluxo |
| **4. Conversão** | Cupom pós-prova, lista de desejos, integração com PDV/e-commerce |
| **5. Escala** | NFC/RFID onde compensar, showroom B2B, relatórios de intenção |

## 15. Perguntas em aberto (para decidir a seguir)

1. O foco inicial é **loja física, e-commerce, indústria (B2B) ou eventos**?
2. A marca parceira já tem **etiquetas com código** (EAN/QR) que possam ser reaproveitadas?
3. Qual é o **ticket médio** das peças? Isso define a viabilidade do custo por segundo.
4. A loja tem **equipe de vendas** que possa liberar a prova e abordar o cliente?
5. O provador será usado em **categorias sensíveis** (como íntimas)? Se sim, aplicar as salvaguardas e os níveis sem câmera primeiro.
6. Haverá **integração com PDV ou e-commerce** para medir a conversão de ponta a ponta?
7. Qual será o **modelo de cobrança** preferido: mensalidade, comissão, por evento ou híbrido?

## 16. Resumo

O ID da peça transforma o provador virtual de **vitrine aberta e cara** em **funil controlado e mensurável**: filtra curiosos, limita e atribui o custo de IA, liga a prova à venda e gera dados de intenção valiosos. A implementação pode começar simples (QR + token de sessão + teto de duração) e evoluir para NFC/RFID, cotas inteligentes e integração com PDV conforme o piloto comprovar a viabilidade.
