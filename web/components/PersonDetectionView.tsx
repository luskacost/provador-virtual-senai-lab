"use client";

import { useRef, useEffect } from "react";
import { ConnectionStatus } from "@/hooks/useDecartRealtime";
import { friendlyErrorMessage } from "@/lib/errors";
import { IdleScreen } from "@/components/IdleScreen";

interface PersonDetectionViewProps {
  localStream: MediaStream | null;
  status: ConnectionStatus;
  error: string | null;
  personPresent: boolean;
  detectionReady: boolean;
  onRemoteStream: (ref: React.RefObject<HTMLVideoElement | null>) => void;
  onLocalVideo?: (ref: React.RefObject<HTMLVideoElement | null>) => void;
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

  const isGenerating = status === "generating";
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
      <IdleScreen visible={!personPresent} />

      {/* Selo de status (para quem está de olho no funcionamento; o texto grande fica na tela de espera) */}
      <div className="absolute top-4 left-4 z-40">
        <div
          className={`flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-full ${label.className}`}
        >
          {label.pulse && (
            <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
          )}
          {label.text}
        </div>
      </div>

      {friendlyError && (
        <div className="absolute bottom-4 left-4 right-4 z-40 flex items-center justify-between gap-4 rounded-lg bg-red-600/90 px-4 py-3 text-white">
          <span className="text-sm">{friendlyError}</span>
          <button
            onClick={() => window.location.reload()}
            className="shrink-0 rounded-md bg-white/20 px-3 py-1.5 text-sm font-medium hover:bg-white/30"
          >
            Tentar de novo
          </button>
        </div>
      )}
    </div>
  );
}
