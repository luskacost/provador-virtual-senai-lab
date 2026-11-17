# Provador Virtual em Tempo Real — SENAI Lab Fashion

> Quiosque em que o visitante fica diante de uma câmera, escolhe uma peça num catálogo e **se vê vestindo a peça
> ao vivo**, com aparência fotorrealista gerada por IA. Trocar de peça troca a roupa no vídeo, sem reiniciar.

Projeto do laboratório **SENAI Lab Fashion** (Engenharia de Produção e Design de Moda), apresentado ao público
na exposição de **27 a 29/10/2026**. Este documento resume o projeto para quem **decide** (coordenação, gestão,
parceiros). A parte técnica está no final, em [Para a equipe técnica](#para-a-equipe-técnica).

---

## Resumo para gestores

| | |
|---|---|
| **O que é** | Provador virtual em tempo real: câmera + catálogo de peças + IA que veste a peça no vídeo ao vivo. |
| **Situação** | Concluído e **usado em evento real** (27 a 29/10/2026). Código congelado desde 24/10, só correções. |
| **Resultado** | 99 sessões em 3 dias; 87% dos visitantes experimentaram pelo menos uma peça. |
| **Tecnologia de IA** | Modelo *Lucy VTON* da Decart, serviço externo contratado por uso. |
| **Principal risco** | Custo por segundo de IA e dependência de internet (ver [Custo e riscos](#custo-e-riscos)). |
| **Próximo passo possível** | Piloto comercial em EPI e uniformes (ver [Próxima etapa](#próxima-etapa-estudo-de-uso-comercial)). |

---

## Resultados do evento (27 a 29/10/2026)

| Indicador | Valor |
|---|---|
| Sessões no evento | **99** (27/10: 48, 28/10: 40, 29/10: 11) |
| Vídeo gerado ao vivo | cerca de **3,5 horas** (12.610 s) |
| Duração média / mediana / maior | 127 s / 101 s / 373 s |
| Sessões em que a pessoa experimentou alguma peça | **87%** (86 de 99) |
| Trocas de peça | **641** no total, média de 7,5 por sessão com peça |
| Horário de pico | 14h (22 sessões); funcionamento das 13h às 19h |

**O que o público escolheu:** peças marcantes. As mais procuradas foram as jaquetas de combate a incêndio, o
vestido e os macacões; as camisetas lisas, inclusive a do próprio SENAI, foram as menos usadas. Isso sugere um
catálogo futuro com menos básicos e mais peças com personalidade.

**Como ler a duração:** o operador encerrou a maioria das sessões (75 de 99) para atender a pessoa seguinte.
Por isso a duração média reflete o ritmo do estande, **não** o interesse do visitante.

**O que o sistema não mede:** quantas fotos foram impressas, quantas pessoas diferentes participaram (uma pessoa
pode ter várias sessões) e erros de conexão. Detalhes na seção "Métricas reais do evento" de
[`docs/aprendizados.md`](docs/aprendizados.md).

---

## Como funciona (sem jargão)

1. O quiosque fica em **espera**, com a câmera ligada mas sem usar a IA e sem custo.
2. Quando **alguém aparece** na frente da câmera, o sistema abre uma sessão com o serviço de IA.
3. O visitante **toca numa peça** do catálogo e se vê vestindo a peça, ao vivo, na tela grande.
4. Pode **tirar uma foto**, que é impressa direto na impressora do estande.
5. Quando a pessoa **sai da frente da câmera**, a sessão fecha sozinha e o quiosque volta à espera.

O **operador** do estande tem atalhos de teclado para encerrar a sessão, reiniciar tudo ou colocar o quiosque em
*standby* (câmera desligada, nenhum custo). Veja [`docs/operacao-evento.md`](docs/operacao-evento.md).

---

## Privacidade (LGPD)

- O vídeo do visitante é enviado em tempo real a um **serviço externo** (Decart), **apenas** para gerar a prévia
  da roupa.
- **O estande não grava nem guarda vídeo ou imagem.** As métricas são só texto e números: horário, duração e peças
  experimentadas, sem identificar ninguém.
- A **foto** é montada no navegador e vai direto para a impressora, sem passar por servidor nem rede. Não fica
  guardada.
- Um **aviso** é exibido na tela de espera. A redação final deve ser validada pelo responsável; as opções
  discutidas estão em [`docs/aviso-lgpd-opcoes.md`](docs/aviso-lgpd-opcoes.md).
- A chave de acesso ao serviço de IA fica **somente no servidor**; o navegador recebe apenas um token temporário.

---

## Custo e riscos

**Custo.** A Decart cobra por segundo de IA ativa: **US$ 0,02 por segundo** no modo padrão, cerca de US$ 72 por
hora com a sessão aberta (valor de referência; confirme no [preço oficial](https://docs.platform.decart.ai/getting-started/pricing)).
O quiosque reduz o gasto de três formas: só abre sessão quando há alguém, fecha quando a pessoa sai e tem modo
*standby* para os intervalos.

| Risco | Efeito | Como foi tratado |
|---|---|---|
| Queda de internet | A IA para de funcionar | Mensagem amigável e botão "tentar de novo"; testado em rede diferente |
| Objeto detectado como pessoa (cartaz, manequim) | Sessão aberta gastando sem ninguém | Operador encerra com atalho ou usa o standby |
| Sessão sem limite de tempo (decisão de 23/10) | Gasto maior se alguém ficar parado | Limites continuam implementados e reativáveis em `web/app/page.tsx` |
| Peças que o modelo representa mal | Resultado estranho ao vivo | Campo `"ativo": false` esconde a peça sem apagar |
| Dependência de um fornecedor | Preço ou regras podem mudar | Estudo da Etapa 2 avalia a dependência |

**O que foi testado e descartado:** a troca de **fundo/cenário** por IA (passarela, rua, praia) foi testada e
**reprovada** em 07/10/2026 (fundo que não aparecia, peça duplicada, custo alto). O estande usou fundo físico
neutro. Registro completo em [`docs/aprendizados.md`](docs/aprendizados.md).

---

## Próxima etapa: estudo de uso comercial

Depois do evento foi feito um estudo (02/11/2026) sobre transformar o quiosque num produto. Relatório completo em
[`docs/etapa2/relatorio-estudo.md`](docs/etapa2/relatorio-estudo.md); proposta técnica em
[`docs/etapa2/ideia-id-da-peca.md`](docs/etapa2/ideia-id-da-peca.md).

- **ID da peça:** abrir o provador já na peça certa, a partir de um código (QR ou etiqueta). É **tecnicamente viável**
  com a Decart de hoje.
- **A conta econômica é o ponto crítico:** com a sessão média do evento (127 s) o custo por venda fica alto. A conta só
  fecha com sessões curtas (20 a 30 s) e boa conversão, e **nada disso foi comprovado ainda**. O teto de duração pesa
  mais que o ID.
- **Nichos mais promissores:** **EPI e uniformes profissionais** (B2B, destaque do evento e público natural do SENAI)
  e festa/aluguel de trajes.
- **Evitar por ora:** lingerie, moda praia e infantil, por risco legal e de uso indevido.
- **Recomendação:** piloto pequeno de EPI/uniformes em quiosque, com teto de 30 s, medindo segundos reais e
  interesse do comprador.

Nada da Etapa 2 foi implementado; o repositório contém só o estudo.

---

## Para a equipe técnica

### Tecnologia

- **Next.js 16 + React 19 + TypeScript + Tailwind CSS v4**, em [`web/`](web/).
- **Decart Lucy VTON** (prova virtual em tempo real via WebRTC, SDK `@decartai/sdk`). Parte do exemplo oficial
  [DecartAI/tryon-examples](https://github.com/DecartAI/tryon-examples), bastante adaptado.
- **MediaPipe Pose**, auto-hospedado, para detectar presença: a sessão cobrada só abre com alguém na frente da câmera.
- Catálogo em JSON (`web/catalog/products.json`): cada peça tem imagem e um prompt em inglês.
- Métricas locais por sessão em `web/data/metricas.json` (fora do git) e página de resumo em `/metricas`.

### Rodando localmente

Requisitos: Node.js, uma webcam e uma chave de API da Decart (<https://platform.decart.ai>).

```bash
cd web
cp .env.example .env.local   # coloque sua DECART_API_KEY
npm install                  # também baixa os arquivos do MediaPipe
npm run dev                  # http://localhost:3000
```

Para o evento use `npm run build` e `npm start`. A chave **nunca** deve ir para o código nem para o git
(`.env.local` e `data/` já estão no `.gitignore`).

### Estrutura do repositório

| Caminho | Conteúdo |
|---|---|
| [`web/`](web/) | **O quiosque que foi ao evento** (Next.js). |
| [`web/catalog/products.json`](web/catalog/products.json) | Catálogo de peças. Adicionar ou remover peça é editar o JSON e a imagem. |
| [`docs/`](docs/) | Operação, checklist, aprendizados, estudo da Etapa 2. |
| `src/`, `tools/`, `tests/`, `assets/` | **Plano inicial em Python** (roupas 3D sobrepostas ao corpo), substituído pela abordagem com a Decart. Mantido como histórico. |
| [`CLAUDE.md`](CLAUDE.md) | Requisitos, decisões e regras de trabalho do projeto. |

### Documentação

| Documento | Para quê |
|---|---|
| [`docs/operacao-evento.md`](docs/operacao-evento.md) | Como ligar o quiosque, atalhos do operador, o que fazer se algo falhar |
| [`docs/checklist-estande.md`](docs/checklist-estande.md) | Checklist de montagem e testes antes do evento |
| [`docs/como-adicionar-peca.md`](docs/como-adicionar-peca.md) | Como incluir uma peça no catálogo |
| [`docs/aprendizados.md`](docs/aprendizados.md) | Decisões, testes, o que funcionou e o que não funcionou, métricas reais |
| [`docs/aviso-lgpd-opcoes.md`](docs/aviso-lgpd-opcoes.md) | Opções de redação do aviso de privacidade |
| [`docs/etapa2/`](docs/etapa2/) | Estudo de uso comercial (ID da peça e nichos) |

### Limitações conhecidas

- Depende de internet e de um serviço externo pago por segundo.
- Peças em fotos com modelo, ou muito detalhadas, podem ser representadas com menos fidelidade.
- Acessórios de mão, cabeça e rosto (luvas, capacete, óculos) são mais sensíveis a movimento rápido.
- A foto depende de uma impressora configurada no quiosque (no evento, uma Fujifilm ASK-300).

---

## Sobre as imagens

- O **logo** é do SENAI Lab Fashion.
- No evento o catálogo teve mais peças do que as incluídas neste repositório. As fotos que podiam ter direitos de
  terceiros **foram removidas** da versão publicada. Ficaram **10 peças** de aparência sintética, sem origem
  comprovada: a ausência de direitos autorais nelas **não foi verificada**.
- Para usar o projeto, adicione fotos **próprias** ou com licença que permita o uso, seguindo
  [`docs/como-adicionar-peca.md`](docs/como-adicionar-peca.md).
