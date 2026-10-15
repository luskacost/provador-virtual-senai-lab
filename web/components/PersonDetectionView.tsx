"use client";

import { useRef, useEffect } from "react";
import { ConnectionStatus } from "@/hooks/useDecartRealtime";
import { friendlyErrorMessage } from "@/lib/errors";
import { IdleScreen } from "@/components/IdleScreen";
import { CaptureControls } from "@/components/CaptureControls";

interface PersonDetectionViewProps {
  localStream: MediaStream | null;
  status: ConnectionStatus;
  error: string | null;
  personPresent: boolean;
  detectionReady: boolean;
  onRemoteStream: (ref: React.RefObject<HTMLVideoElement | null>) => void;
  onLocalVideo?: (ref: React.RefObject<HTMLVideoElement | null>) => void;
  /** Segundos restantes da sessão (CLAUDE.md 4.3); null quando não há sessão ativa. */
  sessionSecondsLeft?: number | null;
  /** true durante o resfriamento pós-encerramento forçado (limite, inatividade, operador). */
  cooling?: boolean;
  /** true depois de "tirar a peça": mostra a câmera sem a IA, mesmo com a conexão ainda aberta. */
  showOriginal?: boolean;
  /** Conteúdo extra por cima do vídeo (legenda dos gestos). */
  overlay?: React.ReactNode;
}

function getDetectionLabel(
  detectionReady: boolean,
  personPresent: boolean,
  status: ConnectionStatus
): { text: string; className: string; pulse: boolean } {
  if (!detectionReady) {
    return {
      text: "Carregando detecção...",
      className: "bg-black/60 text-white",
      pulse: false,
    };
  }

  if (status === "generating") {
    return {
      text: "Ao vivo",
      className: "bg-green-500/90 text-white",
      pulse: true,
    };
  }

  if (status === "connecting") {
    return {
      text: "Pessoa detectada - conectando...",
      className: "bg-blue-500/90 text-white",
      pulse: true,
    };
  }

  if (status === "connected") {
    return {
      text: "Conectado - toque numa peça para experimentar",
      className: "bg-blue-500/90 text-white",
      pulse: false,
    };
  }

  if (personPresent) {
    return {
      text: "Pessoa detectada",
      className: "bg-blue-500/90 text-white",
      pulse: true,
    };
  }

  return {
    text: "Aguardando...",
    className: "bg-black/60 text-white",
    pulse: false,
  };
}

export function PersonDetectionView({
  localStream,
  status,
  error,
  personPresent,
  detectionReady,
  onRemoteStream,
  onLocalVideo,
  sessionSecondsLeft = null,
  cooling = false,
  showOriginal = false,
  overlay,
}: PersonDetectionViewProps) {
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    if (localVideoRef.current && localStream) {
      localVideoRef.current.srcObject = localStream;
    }
  }, [localStream]);

  useEffect(() => {
    onRemoteStream(remoteVideoRef);
  }, [onRemoteStream]);

  useEffect(() => {
    onLocalVideo?.(localVideoRef);
  }, [onLocalVideo]);

  const isGenerating = status === "generating" && !showOriginal;
  const label = getDetectionLabel(detectionReady, personPresent, status);
  const friendlyError = friendlyErrorMessage(error);

  return (
    <div className="relative flex-1 bg-black">
      {/* Câmera local */}
      <video
        ref={localVideoRef}
        autoPlay
        playsInline
        muted
        className={`absolute inset-0 w-full h-full object-cover transition-opacity ${
          isGenerating ? "opacity-20" : "opacity-100"
        }`}
        style={{ transform: "scaleX(-1)" }}
      />

      {/* Vídeo com a IA da Decart */}
      <video
        ref={remoteVideoRef}
        autoPlay
        playsInline
        muted
        className={`absolute inset-0 w-full h-full object-cover transition-opacity ${
          isGenerating ? "opacity-100" : "opacity-0"
        }`}
        style={{ transform: "scaleX(-1)" }}
      />

      {/* Tela de espera (CLAUDE.md 4.2) por cima do vídeo, some quando alguém é detectado */}
      <IdleScreen visible={!personPresent || cooling} cooling={cooling} />

      {/* Contagem regressiva da sessão (CLAUDE.md 4.3) */}
      {sessionSecondsLeft != null && (
        <div className="absolute top-6 right-6 z-40 rounded-full bg-black/60 px-4 py-2 text-base font-medium text-white">
          Tempo restante: {sessionSecondsLeft}s
        </div>
      )}

      {/* Selo de status (para quem está de olho no funcionamento; o texto grande fica na tela de espera) */}
      <div className="absolute top-6 left-6 z-40">
        <div
          className={`flex items-center gap-2 text-base font-medium px-4 py-2 rounded-full ${label.className}`}
        >
          {label.pulse && (
            <span className="w-2.5 h-2.5 bg-white rounded-full animate-pulse" />
          )}
          {label.text}
        </div>
      </div>

      {/* Tirar foto / gravar vídeo (a pedido do usuário) - efêmero, ver hooks/useCapture.ts */}
      <CaptureControls videoRef={remoteVideoRef} visible={isGenerating} />

      {overlay}

      {friendlyError && (
        <div className="absolute bottom-6 left-6 right-6 z-40 flex items-center justify-between gap-4 rounded-xl bg-red-600/90 px-6 py-4 text-white">
          <span className="text-lg">{friendlyError}</span>
          <button
            onClick={() => window.location.reload()}
            className="shrink-0 rounded-lg bg-white/20 px-5 py-3 text-lg font-medium hover:bg-white/30"
          >
            Tentar de novo
          </button>
        </div>
      )}
    </div>
  );
}
