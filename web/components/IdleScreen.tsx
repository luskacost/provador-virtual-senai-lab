"use client";

// Tela inicial de espera (CLAUDE.md 4.2: "Toque para experimentar" quando ninguém está usando) + aviso de
// LGPD (4.6). O texto do convite reflete o mecanismo real deste app (conecta por presença, não por toque —
// ver hooks/usePersonDetection.ts); ajuste se o quiosque ganhar um botão físico/touch de início.
//
// TEXTO PROVISÓRIO: nome do projeto, cores e a redação do aviso de LGPD ainda não foram validados pelo
// usuário (CLAUDE.md pede validação explícita da redação). Trocar quando a identidade visual do laboratório
// chegar.
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
      {cooling ? (
        <>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Sessão encerrada</h1>
          <p className="max-w-2xl text-xl text-white/90 sm:text-2xl">
            Preparando para a próxima pessoa...
          </p>
        </>
      ) : (
        <>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Provador Virtual</h1>
          <p className="max-w-2xl text-xl text-white/90 sm:text-2xl">
            Fique em frente à câmera para começar a experimentar as peças
          </p>
          <p className="mt-8 max-w-xl text-sm text-white/60">
            Seu vídeo é processado em tempo real por um serviço externo, só para gerar a prévia da roupa, e
            não é gravado nem armazenado pelo estande.
          </p>
        </>
      )}
    </div>
  );
}
