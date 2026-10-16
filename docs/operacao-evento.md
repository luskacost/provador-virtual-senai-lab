# Operação do evento — SENAI Lab Fashion

> Adiantado na Fase 2–4 (o plano original previa isso só na Fase 6, 24/10). Revisar e completar antes do
> congelamento. Pensado para quem vai operar o estande no dia, não só para quem programou.

## Como ligar

1. Abra um terminal na pasta `web/`.
2. Confirme que `.env.local` tem a `DECART_API_KEY` real (não é versionada — se o `.env.local` não existir
   nesta máquina, copie de `.env.example` e cole a chave).
3. Build de produção (mais estável e mais rápido que o modo de desenvolvimento):
   ```
   npm run build
   npm start
   ```
   Isso sobe em `http://localhost:3000` — **pode abrir por esse endereço mesmo**, sem problema (a foto
   agora é impressa direto pelo navegador, não depende mais de rede nem de IP específico).
4. Coloque o navegador em tela cheia (F11) e, se possível, em modo quiosque de verdade (atalho do Chrome:
   `chrome --kiosk http://localhost:3000`) para esconder a barra de endereço e impedir que o visitante
   navegue para outro lugar.
5. Autorize a câmera quando o navegador perguntar (só pergunta na primeira vez por perfil de navegador).
6. **Impressora (Fujifilm ASK-300): use o perfil "FUJIFILM ASK-300 (Copiar 1)"**, na porta USB002, e deixe
   ele como padrão. O perfil sem "(Copiar 1)" (porta USB001) é o da primeira instalação e não imprimiu;
   se o Windows trocar a padrão sozinho, volte para o "(Copiar 1)". Se a impressora ficar em "Erro" com a
   luz "Paper/Ribbon" laranja, confira se papel e fita são do **mesmo kit/tamanho**, cancele os
   trabalhos parados na fila e tente de novo.
   Confirme que há uma **impressora configurada como padrão** no Windows, com papel. O botão "Tirar foto"
   abre o diálogo de impressão do navegador — teste uma vez antes do evento para garantir que a impressora
   certa está selecionada e que o diálogo não fica pedindo confirmação demais (ver "Se algo der errado").

## Escolher a peça pelo teclado (sem mouse)

Durante a sessão, a peça "em foco" tem um anel branco no catálogo.

| Tecla | O que faz |
|---|---|
| **Setas** | Movem o foco para a próxima/anterior peça |
| **Enter** | Veste a peça em foco |
| **Backspace** ou **Delete** | Tira a peça (volta a mostrar a câmera sem a IA) |

| **F** | Tira a foto (só aparece com peça ao vivo, igual ao botão "Tirar foto") |
| Com a prévia da foto aberta: **Enter** | Imprime |
| Com a prévia aberta: **Backspace**, **Delete** ou **Esc** | Fecha a prévia |

Com a prévia aberta, as outras teclas ficam travadas, para não mexer na peça que está por trás.
Tocar/clicar na peça continua funcionando. "Tirar a peça" só esconde a IA na tela; a conexão com a Decart
continua até o fim da sessão (o limite de 50 s controla o custo).

## Atalhos do operador

| Atalho | O que faz |
|---|---|
| `Ctrl+Shift+E` | Encerra a sessão atual imediatamente (libera para o próximo visitante) |
| `Ctrl+Shift+R` | Reseta o app inteiro (recarrega a página — mesmo efeito do botão "Tentar de novo" de erro) |
| `Ctrl+Shift+S` | **Liga/desliga o standby.** Em standby: encerra a sessão em andamento, desliga a câmera (a Canon descansa), pausa a detecção, nada conecta na Decart (custo zero) e a tela fica preta só com o logo. Apertar de novo acorda: religa a câmera (1–2 s) e o quiosque volta ao normal |
| `Esc` (do navegador) | Sai do modo tela cheia, se precisar acessar o terminal |

Esses atalhos exigem um teclado conectado ao quiosque (não aparecem na tela, de propósito — são para o
operador, não para o visitante).

## Se algo der errado

| Sintoma | O que fazer |
|---|---|
| Tela mostra "Algo deu errado. Tente de novo." | Toque no botão (ou `Ctrl+Shift+R`). Se persistir, veja a internet/Wi-Fi do local. |
| "Não conseguimos acessar a câmera" | Confirme que nenhum outro programa está usando a câmera (Teams, outro navegador); recarregue. |
| "Não encontramos uma câmera conectada" | Verifique o cabo/driver da câmera; chame o responsável técnico. |
| Vídeo mostra "Ao vivo" mas a imagem trava | Problema conhecido de rede (ver `docs/aprendizados.md`, "achado técnico" sobre diagnóstico do SDK). Recarregue; se repetir, teste a conexão de internet do local. |
| Botão "Imprimir" abre o diálogo mas nada sai da impressora | Confira a impressora padrão do Windows e se há papel/tinta. Teste a impressão de outro programa para isolar se o problema é do app ou da impressora. |
| Quiosque parece "pulando" visitantes | Pode ser o limite de inatividade curto demais para o ritmo do local — ver "Valores da sessão" abaixo. |

Em qualquer caso que não resolver na hora: `Ctrl+Shift+R` reseta tudo. Se nem isso resolver, feche o
terminal (`Ctrl+C`) e repita "Como ligar".

## Valores da sessão (CLAUDE.md 4.3) — constantes em `web/app/page.tsx`

```ts
const SESSION_LIMIT_SECONDS = 50;      // limite total por visitante
const INACTIVITY_LIMIT_SECONDS = 15;   // sem trocar de peça por esse tempo, encerra
const COOLDOWN_SECONDS = 10;           // pausa antes de reconectar a mesma pessoa
```

**Valores definitivos, decididos em 07/10/2026** (em vez dos 90 s do padrão original): suficientes para o
visitante experimentar e economizam créditos da Decart. Se no evento o ritmo pedir ajuste, é só mudar as
constantes acima e refazer o build — mas não é uma pendência.

## Métricas

`http://localhost:3000/metricas` (não tem link na interface do quiosque — acesse direto por esse
endereço). Mostra total de sessões, duração média, ranking de peças e as últimas 50 sessões. Os dados
ficam em `web/data/metricas.json`, fora do git.

## Antes de ligar no dia do evento (resumo — ver checklist completo em `docs/checklist-estande.md`)

- Testar com a luz real do local (webcams caem de FPS com pouca luz — ver `docs/hardware.md`, do plano
  anterior, que tem a mesma observação para a câmera desta máquina).
- Testar a impressão da foto com a impressora e o papel reais do evento.
- Confirmar que o catálogo (`web/catalog/products.json`) só tem peças aprovadas (`"ativo": true`).
