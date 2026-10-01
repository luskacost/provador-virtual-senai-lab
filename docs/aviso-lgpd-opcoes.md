# Opções de redação — aviso de LGPD na tela de espera

CLAUDE.md (seção 4.6) pede que **você** valide a redação exata. Três opções, do mais curto ao mais
completo. Nenhuma foi aplicada ainda além da opção A, que é o texto atual (provisório) em
`web/components/IdleScreen.tsx`. Me diga qual prefere (ou peça ajustes) e eu aplico.

## Opção A — atual (curta, informal)

> Seu vídeo é processado em tempo real por um serviço externo, só para gerar a prévia da roupa. Se você
> tocar em "Tirar foto" ou "Gravar vídeo", a captura fica disponível por alguns minutos só para você
> baixar por QR code no seu celular — não fica guardada por nós depois disso.

**A favor:** curta, cabe bem na tela de espera, linguagem simples.
**Contra:** não nomeia o serviço externo (Decart) nem menciona LGPD explicitamente.

## Opção B — mais curta ainda (para quem prioriza legibilidade a 1,5–2 m)

> Seu vídeo vira uma prévia da roupa ao vivo, processada por um serviço externo (Decart), e não é
> guardada por nós. Fotos e vídeos que você escolher tirar vão só para o seu celular, por QR code.

**A favor:** mais direta, uma frase por ideia, boa para leitura rápida.
**Contra:** omite detalhes (tempo de expiração do QR code, por exemplo).

## Opção C — mais completa (menciona LGPD e dados tratados)

> Em conformidade com a LGPD: seu vídeo é processado **em tempo real** pela Decart (serviço de terceiro)
> só para gerar a prévia da roupa, e não é armazenado por nós nem por eles além do tempo da sessão. Se você
> tocar em "Tirar foto" ou "Gravar vídeo", geramos uma cópia temporária (apagada em poucos minutos) para
> você baixar no seu celular por QR code — essa cópia nunca fica no nosso servidor depois de gerada.

**A favor:** mais transparente, nomeia a Decart e a base legal, cobre o caso de dúvida de um coordenador
ou visitante mais atento.
**Contra:** mais longa — pode precisar de fonte menor ou quebrar em duas linhas na tela de espera.

## Observação técnica importante

Nenhuma dessas opções afirma algo que eu possa garantir sobre o que a **Decart** faz com o vídeo do lado
dela (retenção, treinamento de modelo etc.) — isso depende dos termos de serviço da Decart, que não
conferi a fundo. Se quiser uma afirmação mais forte sobre o que a Decart faz ou não com os dados, é
preciso checar os termos de uso/política de privacidade dela antes (posso fazer isso se pedir).
