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
   Isso sobe em `http://localhost:3000` — **mas não abra por esse endereço** (ver aviso abaixo sobre o QR
   code). Em desenvolvimento/teste rápido, `npm run dev` também funciona.
4. Abra o navegador (Chrome ou Edge) **pelo IP da máquina na rede do evento**, não por `localhost`:
   - Descubra o IP: `ipconfig` (Windows), procure "Endereço IPv4" na placa de rede Wi-Fi/Ethernet em uso.
   - Abra `http://<esse-ip>:3000` no navegador do quiosque.
5. Coloque o navegador em tela cheia (F11) e, se possível, em modo quiosque de verdade (atalho do Chrome:
   `chrome --kiosk http://<ip>:3000`) para esconder a barra de endereço e impedir que o visitante navegue
   para outro lugar.
6. Autorize a câmera quando o navegador perguntar (só pergunta na primeira vez por perfil de navegador).

### ⚠️ Por que não pode ser `localhost`

A funcionalidade de **tirar foto / gravar vídeo** mostra um QR code que o celular do visitante escaneia
para baixar a captura. Esse QR code aponta para o mesmo endereço que o navegador do quiosque usou para
abrir a página. Se for `localhost`, o link só funciona dentro da própria máquina do quiosque — o celular do
visitante nunca vai conseguir abrir. **O celular do visitante também precisa estar na mesma rede Wi-Fi.**

Teste isso **antes** do evento: abra pelo IP, escaneie o QR code com o seu próprio celular (no Wi-Fi do
local) e confirme que baixa.

## Atalhos do operador

| Atalho | O que faz |
|---|---|
| `Ctrl+Shift+E` | Encerra a sessão atual imediatamente (libera para o próximo visitante) |
| `Ctrl+Shift+R` | Reseta o app inteiro (recarrega a página — mesmo efeito do botão "Tentar de novo" de erro) |
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
| QR code da foto/vídeo não abre no celular | Confirme que o navegador do quiosque foi aberto pelo IP da rede (não `localhost`) e que o celular está na mesma Wi-Fi. |
| Vídeo baixado pelo QR code não abre no iPhone | Limitação conhecida: o vídeo é `.webm`; alguns iPhones não tocam nativamente. A foto (`.jpg`) não tem esse problema. |
| Quiosque parece "pulando" visitantes | Pode ser o limite de inatividade curto demais para o ritmo do local — ver "Valores da sessão" abaixo. |

Em qualquer caso que não resolver na hora: `Ctrl+Shift+R` reseta tudo. Se nem isso resolver, feche o
terminal (`Ctrl+C`) e repita "Como ligar".

## Valores da sessão (CLAUDE.md 4.3) — constantes em `web/app/page.tsx`

```ts
const SESSION_LIMIT_SECONDS = 30;      // limite total por visitante
const INACTIVITY_LIMIT_SECONDS = 15;   // sem trocar de peça por esse tempo, encerra
const COOLDOWN_SECONDS = 10;           // pausa antes de reconectar a mesma pessoa
```

**Esses são valores de teste** (o padrão do CLAUDE.md pede 90 s de limite). Decidir com o usuário os
valores finais antes do evento — 30 s pode ser curto demais para alguém realmente escolher e ver a peça.

## Métricas

`http://<ip-do-quiosque>:3000/metricas` (não tem link na interface do quiosque — acesse direto por esse
endereço, só na rede local). Mostra total de sessões, duração média, ranking de peças e as últimas 50
sessões. Os dados ficam em `web/data/metricas.json`, fora do git.

## Antes de ligar no dia do evento (resumo — ver checklist completo em `docs/checklist-estande.md`)

- Testar com a luz real do local (webcams caem de FPS com pouca luz — ver `docs/hardware.md`, do plano
  anterior, que tem a mesma observação para a câmera desta máquina).
- Testar o QR code de foto/vídeo com o Wi-Fi real do evento.
- Confirmar que o catálogo (`web/catalog/products.json`) só tem peças aprovadas (`"ativo": true`).
