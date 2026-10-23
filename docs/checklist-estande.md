# Checklist pré-evento — SENAI Lab Fashion

> Adiantado nas Fases 2–4 (o plano original previa isso na Fase 6). Revisar e completar perto do
> congelamento (24/10) e de novo na manhã do evento (27/10).

## Semana antes

- [ ] Todas as peças do catálogo são reais, sem marca d'água, sem logo de loja, sem imagem gerada por IA
      (ver `docs/aprendizados.md` — critério que usamos para recusar fotos).
- [x] Testar cada peça do catálogo pelo menos uma vez com uma pessoa de verdade (feito pelo usuário em
      15/10/2026, incluindo luvas, capacete e óculos), em condições parecidas com as do evento. Marcar `"ativo": false` em `web/catalog/products.json` para qualquer peça que o
      modelo represente mal.
- [ ] Validar com o usuário a redação final do aviso de LGPD (`web/components/IdleScreen.tsx`).
- [x] Sessão **sem limite de tempo e sem limite de inatividade** (decisão do usuário em 23/10/2026; antes 50 s
      e 15 s). Só termina quando a pessoa sai, pelo operador (`Ctrl+Shift+E`), standby (`Shift+S`) ou aba
      escondida. Custo: $0,02/s por sessão aberta (ver `docs/operacao-evento.md`).
- [ ] Testar uma sessão **longa** de verdade (uns 12 minutos): a documentação cita
      validade de 10 min para o token da Decart, e não sei se isso derruba uma sessão já aberta. Se cair,
      voltar a limitar a sessão (null → segundos em `web/app/page.tsx`).
- [x] (feito em 15/10/2026) Testar numa rede diferente da de casa/trabalho (a rede do evento pode ter proxy/firewall diferente —
      ver o achado sobre diagnóstico de conexão em `docs/aprendizados.md`). A Decart ainda precisa de
      internet; só a foto não depende mais disso.
- [x] Impressora Fujifilm ASK-300 instalada e imprimindo (09/10/2026), pelo perfil **"FUJIFILM ASK-300
      (Copiar 1)"**, que é o padrão. Teste pelo app (F → Enter) feito em 15/10/2026.
- [x] "Permitir que o Windows gerencie minha impressora padrão" desativado em 15/10/2026 (valor
      `LegacyDefaultPrinterMode=1` em HKCU); a padrão continua a "FUJIFILM ASK-300 (Copiar 1)".
- [x] Saldo da chave carregado em 15/10/2026. Conferir o saldo no painel da Decart nocomeço de cada dia do evento.
- [x] Decidir a resposta para a seção 4.7 (cenário de fundo): **decidido em 07/10/2026 — troca de fundo
      por IA fica FORA do evento** (testada e reprovada: fundo que não aparece, peça duplicada, custo alto;
      ver `docs/aprendizados.md`). O estande usa **fundo físico neutro**.
- [x] Teclado: setas movem o anel branco, Enter veste, Backspace tira a peça, F tira a foto (testado em
      15/10/2026). Deixar um teclado ou controle sem fio ao alcance de quem opera.
- [ ] Testar o standby ao vivo com a Canon: `Shift+S` apaga a tela (só logo) e desliga a câmera;
      apertar de novo religa a câmera e o quiosque volta. Fechar o dia em standby e abrir de manhã com
      `Shift+S`.
- [x] Fundo físico neutro do estande montado (liso, sem estampa, sem objetos atrás da pessoa).

## Na véspera

- [ ] `git pull` / confirmar que a máquina do evento está com o código mais recente.
- [ ] `npm install` e `npm run build` na máquina do evento (não só na máquina de desenvolvimento).
- [ ] Rodar `npm start` e o checklist de "Como ligar" de `docs/operacao-evento.md` **na própria máquina e
      rede do evento**, de ponta a ponta: câmera, troca de peça, limite de sessão, foto + impressão, métricas.
- [ ] Testar os atalhos do operador (`Ctrl+Shift+E`, `Ctrl+Shift+R`).
- [ ] Carregar o notebook/máquina 100% e levar o carregador.
- [ ] Confirmar que a câmera está fixada numa posição estável (altura e distância) que enquadre bem a
      maioria das alturas de visitante.
- [ ] Testar a luz real do ambiente do estande (não a luz do laboratório).

## Na manhã do evento

- [ ] Ligar a máquina, conectar na rede do evento (a Decart precisa de internet).
- [ ] Rodar `npm start`, abrir `http://localhost:3000`, tela cheia.
- [ ] Um teste completo com uma pessoa da equipe: câmera → escolher peça → tirar foto → imprimir.
- [ ] Deixar um responsável técnico de prontidão nas primeiras horas (os problemas mais comuns aparecem no
      início: câmera ocupada por outro programa, Wi-Fi instável, luz do estande).
- [ ] Ter este checklist e `docs/operacao-evento.md` impressos ou abertos num celular/tablet separado (se
      o quiosque travar, você não quer depender do próprio quiosque para consultar o que fazer).

## Contato de apoio

_(Preencher: quem chamar se o Wi-Fi do evento cair, se a máquina travar, se precisar de suporte da
Decart.)_
