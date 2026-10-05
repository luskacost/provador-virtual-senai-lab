"use client";

import { useCapture } from "@/hooks/useCapture";
import { printImage } from "@/lib/print-image";

interface CaptureControlsProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  /** Só mostra o botão quando há uma peça ao vivo (status === "generating") */
  visible: boolean;
}

// Botão "Tirar foto" + prévia com opção de imprimir direto no quiosque (sem rede, sem QR code - ver
// hooks/useCapture.ts e lib/print-image.ts).
export function CaptureControls({ videoRef, visible }: CaptureControlsProps) {
  const cap = useCapture(videoRef);

  if (!visible && cap.state === "idle") return null;

  return (
    <>
      {visible && cap.state === "idle" && (
        <div className="absolute bottom-6 left-1/2 z-40 -translate-x-1/2">
          <button
            onClick={cap.takePhoto}
            className="rounded-full bg-brand-orange px-6 py-3 text-lg font-medium text-white shadow-lg"
          >
            📷 Tirar foto
          </button>
        </div>
      )}

      {cap.state === "erro" && cap.error && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-black/80 px-8 text-center">
          <p className="text-xl text-white">{cap.error}</p>
          <button
            onClick={cap.dismiss}
            className="rounded-full bg-brand-orange px-6 py-3 text-lg font-medium text-white"
          >
            Fechar
          </button>
        </div>
      )}

      {cap.state === "pronto" && cap.photoDataUrl && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-6 bg-black/85 px-8 text-center">
          <h2 className="text-3xl font-bold text-white">Sua foto ficou assim</h2>
          <div className="max-h-[50vh] overflow-hidden rounded-2xl bg-white p-2">
            {/* eslint-disable-next-line @next/next/no-img-element -- prévia de uma data URL gerada no canvas */}
            <img src={cap.photoDataUrl} alt="Prévia da foto capturada" className="max-h-[46vh] rounded-xl" />
          </div>
          <div className="flex gap-4">
            <button
              onClick={() => printImage(cap.photoDataUrl!)}
              className="rounded-full bg-brand-orange px-8 py-3 text-lg font-medium text-white"
            >
              🖨️ Imprimir
            </button>
            <button
              onClick={cap.dismiss}
              className="rounded-full bg-white/20 px-8 py-3 text-lg font-medium text-white"
            >
              Fechar
            </button>
          </div>
        </div>
      )}
    </>
  );
}
