# Checklist pré-evento — SENAI Lab Fashion

> Adiantado nas Fases 2–4 (o plano original previa isso na Fase 6). Revisar e completar perto do
> congelamento (24/10) e de novo na manhã do evento (27/10).

## Semana antes

- [ ] Todas as peças do catálogo são reais, sem marca d'água, sem logo de loja, sem imagem gerada por IA
      (ver `docs/aprendizados.md` — critério que usamos para recusar fotos).
- [ ] Testar cada peça do catálogo pelo menos uma vez com uma pessoa de verdade, em condições parecidas
      com as do evento. Marcar `"ativo": false` em `web/catalog/products.json` para qualquer peça que o
      modelo represente mal.
- [ ] Validar com o usuário a redação final do aviso de LGPD (`web/components/IdleScreen.tsx`).
- [ ] Decidir os valores finais de `SESSION_LIMIT_SECONDS` / `INACTIVITY_LIMIT_SECONDS` /
      `COOLDOWN_SECONDS` (hoje estão em valores de teste — ver `docs/operacao-evento.md`).
- [ ] Testar numa rede diferente da de casa/trabalho (a rede do evento pode ter proxy/firewall diferente —
      ver o achado sobre diagnóstico de conexão em `docs/aprendizados.md`).
- [ ] Testar o fluxo de QR code (foto e vídeo) com o Wi-Fi e os celulares que mais se parecem com o que os
      visitantes vão usar (incluindo pelo menos um iPhone, por causa da limitação do `.webm`).
- [ ] Confirmar que `DECART_API_KEY` tem saldo/limite suficiente para o dia (checar o painel da Decart).
- [ ] Decidir a resposta para a seção 4.7 (cenário de fundo): ficou de fora do escopo, ou foi testado e
      aprovado? Se ficou de fora, confirmar que o fundo físico do estande é neutro.

## Na véspera

- [ ] `git pull` / confirmar que a máquina do evento está com o código mais recente.
- [ ] `npm install` e `npm run build` na máquina do evento (não só na máquina de desenvolvimento).
- [ ] Rodar `npm start` e o checklist de "Como ligar" de `docs/operacao-evento.md` **na própria máquina e
      rede do evento**, de ponta a ponta: câmera, troca de peça, limite de sessão, foto, vídeo, métricas.
- [ ] Testar os atalhos do operador (`Ctrl+Shift+E`, `Ctrl+Shift+R`).
- [ ] Carregar o notebook/máquina 100% e levar o carregador.
- [ ] Confirmar que a câmera está fixada numa posição estável (altura e distância) que enquadre bem a
      maioria das alturas de visitante.
- [ ] Testar a luz real do ambiente do estande (não a luz do laboratório).

## Na manhã do evento

- [ ] Ligar a máquina, conectar na rede do evento, confirmar o IP (`ipconfig`).
- [ ] Rodar `npm start`, abrir o navegador pelo IP (não `localhost`), tela cheia.
- [ ] Um teste completo com uma pessoa da equipe: câmera → escolher peça → tirar foto → escanear o QR code
      com um celular de verdade, no Wi-Fi do evento.
- [ ] Deixar um responsável técnico de prontidão nas primeiras horas (os problemas mais comuns aparecem no
      início: câmera ocupada por outro programa, Wi-Fi instável, luz do estande).
- [ ] Ter este checklist e `docs/operacao-evento.md` impressos ou abertos num celular/tablet separado (se
      o quiosque travar, você não quer depender do próprio quiosque para consultar o que fazer).

## Contato de apoio

_(Preencher: quem chamar se o Wi-Fi do evento cair, se a máquina travar, se precisar de suporte da
Decart.)_
