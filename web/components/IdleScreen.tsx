"use client";

import Image from "next/image";

// Tela inicial de espera (CLAUDE.md 4.2: "Toque para experimentar" quando ninguém está usando) + aviso de
// LGPD (4.6). O texto do convite reflete o mecanismo real deste app (conecta por presença, não por toque —
// ver hooks/usePersonDetection.ts); ajuste se o quiosque ganhar um botão físico/touch de início.
//
// O logo (web/public/brand/senai-lab-fashion.png) tem a palavra "FASHION" em preto — some num fundo escuro
// — por isso fica numa placa branca, prática comum para logos com texto escuro sobre UI dark.
//
// Redação do aviso de LGPD validada pelo usuário em 05/10/2026 (opção A de docs/aviso-lgpd-opcoes.md); a
// frase sobre a foto foi ajustada no mesmo dia, quando a entrega por QR code virou impressão local — tom
// e tamanho iguais ao que já foi validado, mas a troca de mecanismo não voltou a passar por aprovação
// explícita frase por frase.
interface IdleScreenProps {
  visible: boolean;
  /** true logo depois de um encerramento forçado (limite de tempo, inatividade, operador) — troca o
   * convite normal por um aviso de transição, para a mesma pessoa não achar que travou (CLAUDE.md 4.3). */
  cooling?: boolean;
}

export function IdleScreen({ visible, cooling = false }: IdleScreenProps) {
  return (
    <div
      aria-hidden={!visible}
      className={`absolute inset-0 z-30 flex flex-col items-center justify-center gap-6 bg-black/70 px-8 text-center backdrop-blur-sm transition-opacity duration-500 ${
        visible ? "opacity-100" : "pointer-events-none opacity-0"
      }`}
    >
      <div className="rounded-2xl bg-white px-8 py-5 shadow-lg">
        <Image
          src="/brand/senai-lab-fashion.png"
          alt="SENAI Lab Fashion"
          width={430}
          height={124}
          className="h-auto w-[280px] sm:w-[380px]"
          priority
        />
      </div>

      {cooling ? (
        <>
          <h1 className="text-4xl font-bold tracking-tight text-brand-orange sm:text-5xl">
            Sessão encerrada
          </h1>
          <p className="max-w-2xl text-xl text-white/90 sm:text-2xl">
            Preparando para a próxima pessoa...
          </p>
        </>
      ) : (
        <>
          <p className="text-2xl font-semibold text-brand-orange sm:text-3xl">Provador Virtual</p>
          <p className="max-w-2xl text-xl text-white/90 sm:text-2xl">
            Fique em frente à câmera para começar a experimentar as peças
          </p>
          <p className="mt-8 max-w-xl text-sm text-white/60">
            Seu vídeo é processado em tempo real por um serviço externo, só para gerar a prévia da roupa. Se
            você tocar em &quot;Tirar foto&quot;, a imagem vai direto para a impressora do estande — não
            fica guardada por nós.
          </p>
        </>
      )}
    </div>
  );
}
