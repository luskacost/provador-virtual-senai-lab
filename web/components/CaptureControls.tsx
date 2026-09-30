"use client";

import { useCapture } from "@/hooks/useCapture";

interface CaptureControlsProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  /** Só mostra os botões quando há uma peça ao vivo (status === "generating") */
  visible: boolean;
}

// Botões "Tirar foto" / "Gravar vídeo" + o modal com o QR code para o visitante levar a captura no
// próprio celular (nada fica guardado pelo estande — ver hooks/useCapture.ts e lib/capture-store.ts).
export function CaptureControls({ videoRef, visible }: CaptureControlsProps) {
  const cap = useCapture(videoRef);

  if (!visible && cap.state === "idle") return null;

  return (
    <>
      <div className="absolute bottom-6 left-1/2 z-40 flex -translate-x-1/2 gap-4">
        {cap.state === "recording" ? (
          <button
            onClick={cap.stopRecording}
            className="flex items-center gap-2 rounded-full bg-red-600 px-6 py-3 text-lg font-medium text-white shadow-lg"
          >
            <span className="h-3 w-3 animate-pulse rounded-full bg-white" />
            Parar ({cap.maxRecordSeconds - cap.recordingSeconds}s)
          </button>
        ) : (
          visible && (
            <>
              <button
                onClick={cap.takePhoto}
                disabled={cap.state === "enviando"}
                className="rounded-full bg-brand-orange px-6 py-3 text-lg font-medium text-white shadow-lg disabled:opacity-50"
              >
                📷 Tirar foto
              </button>
              <button
                onClick={cap.startRecording}
                disabled={cap.state === "enviando"}
                className="rounded-full bg-white px-6 py-3 text-lg font-medium text-gray-900 shadow-lg disabled:opacity-50"
              >
                🎥 Gravar vídeo
              </button>
            </>
          )
        )}
      </div>

      {cap.state === "enviando" && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/70">
          <p className="text-xl text-white">Preparando...</p>
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

      {cap.state === "pronto" && cap.result && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-6 bg-black/85 px-8 text-center">
          <h2 className="text-3xl font-bold text-white">
            Escaneie para levar {cap.result.kind === "foto" ? "sua foto" : "seu vídeo"}
          </h2>
          <div className="rounded-2xl bg-white p-4">
            {/* eslint-disable-next-line @next/next/no-img-element -- data URL, next/image não se aplica */}
            <img src={cap.result.qrDataUrl} alt="QR code para baixar sua captura" width={320} height={320} />
          </div>
          <p className="max-w-md text-white/70">
            Aponte a câmera do seu celular para o código. O link funciona por {Math.round(cap.result.expiresInSeconds / 60)}{" "}
            minutos e não fica guardado depois disso.
          </p>
          <button
            onClick={cap.dismiss}
            className="rounded-full bg-brand-orange px-8 py-3 text-lg font-medium text-white"
          >
            Fechar
          </button>
        </div>
      )}
    </>
  );
}
