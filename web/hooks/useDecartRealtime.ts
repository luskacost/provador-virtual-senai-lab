"use client";

import { useState, useCallback, useRef } from "react";
import { createDecartClient, models } from "@decartai/sdk";

type RealtimeClient = Awaited<
  ReturnType<ReturnType<typeof createDecartClient>["realtime"]["connect"]>
>;

export type ConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "generating"
  | "reconnecting"
  | "disconnected"
  | "error";

interface ConnectOptions {
  apiKey: string;
  stream: MediaStream;
  prompt?: string;
  onRemoteStream: (stream: MediaStream) => void;
}

export function useDecartRealtime() {
  const [status, setStatus] = useState<ConnectionStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const clientRef = useRef<RealtimeClient | null>(null);

  const connect = useCallback(async (options: ConnectOptions) => {
    const { apiKey, stream, prompt, onRemoteStream } = options;
    setStatus("connecting");
    setError(null);

    try {
      const client = createDecartClient({ apiKey });
      const model = models.realtime("lucy-vton-latest");

      const rtClient = await client.realtime.connect(stream, {
        model,
        onRemoteStream,
        ...(prompt && {
          initialState: { prompt: { text: prompt, enhance: false } },
        }),
      });

      rtClient.on("connectionChange", (state) => {
        setStatus(state);
      });

      rtClient.on("error", (err) => {
        setError(err.message);
        setStatus("error");
      });

      // DIAGNÓSTICO TEMPORÁRIO (investigando o congelamento do vídeo — remover depois de achar a causa).
      // rtClient.on("stats", ...) dispara ~1x/s com getStats() do WebRTC já em curso: não custa nem uma
      // chamada de rede extra, só lê o que o navegador já sabe sobre a conexão.
      rtClient.on("diagnostic", (evt) => {
        console.log("[decart:diagnostic]", evt.name, evt.data);
      });
      rtClient.on("stats", (s) => {
        const pair = s.connection.selectedCandidatePairs[0];
        console.log("[decart:stats]", {
          rtt_ms: s.connection.currentRoundTripTime != null ? Math.round(s.connection.currentRoundTripTime * 1000) : null,
          candidatoLocal: pair?.local.candidateType,
          candidatoRemoto: pair?.remote.candidateType,
          protocolo: pair?.local.protocol,
          video_fps: s.video?.framesPerSecond,
          video_bitrate_kbps: s.video ? Math.round(s.video.bitrate / 1000) : null,
          video_pacotesPerdidos: s.video?.packetsLost,
          video_congelamentos: s.video?.freezeCount,
          video_duracaoCongelado_s: s.video?.totalFreezesDuration,
          saida_limitadaPor: s.outboundVideo?.qualityLimitationReason,
        });
      });
      rtClient.on("generationEnded", (e) => {
        console.log("[decart:generationEnded]", e);
      });
      rtClient.on("queuePosition", (q) => {
        console.log("[decart:queuePosition]", q);
      });

      clientRef.current = rtClient;
      return rtClient;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Connection failed";
      setError(msg);
      setStatus("error");
      return null;
    }
  }, []);

  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
      clientRef.current = null;
    }
    setStatus("disconnected");
  }, []);

  return { status, error, connect, disconnect, clientRef };
}
