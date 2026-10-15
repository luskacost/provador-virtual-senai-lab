"use client";

import type { GestureMode, HoldKind } from "@/lib/gesture-engine";

interface GestureOverlayProps {
  mode: GestureMode;
  hold: { kind: HoldKind; progress: number } | null;
  focusedName: string | null;
}

const HOLD_LABEL: Record<HoldKind, string> = {
  next: "Próxima peça",
  prev: "Peça anterior",
  confirm: "Segure...",
};

// Legenda grande (legível a 1,5-2 m, CLAUDE.md 4.2) dos gestos. Fica na parte de baixo do vídeo e muda
// conforme há ou não uma peça escolhida: com peça, só existe a opção de tirá-la.
export function GestureOverlay({ mode, hold, focusedName }: GestureOverlayProps) {
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-30 flex flex-col items-center gap-3 bg-gradient-to-t from-black/80 to-transparent px-6 pb-24 pt-16 text-center text-white">
      {mode === "browsing" ? (
        <>
          {focusedName && (
            <p className="text-3xl font-bold text-brand-orange portrait:text-4xl">{focusedName}</p>
          )}
          <p className="text-2xl font-semibold portrait:text-3xl">
            Mão direita: próxima &nbsp;·&nbsp; Mão esquerda: anterior
          </p>
          <p className="text-2xl font-semibold portrait:text-3xl">
            Duas mãos acima da cabeça: escolher
          </p>
        </>
      ) : (
        <p className="text-2xl font-semibold portrait:text-3xl">
          Duas mãos acima da cabeça (segure) para tirar a peça
        </p>
      )}

      <div className="h-4 w-80 max-w-full overflow-hidden rounded-full bg-white/20">
        <div
          className="h-full rounded-full bg-brand-orange transition-[width] duration-100"
          style={{ width: `${Math.round((hold?.progress ?? 0) * 100)}%` }}
        />
      </div>
      <p className="h-8 text-xl font-medium text-white/90">{hold ? HOLD_LABEL[hold.kind] : ""}</p>
    </div>
  );
}
