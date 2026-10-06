"use client";

import { useState, useCallback, useRef } from "react";
import { createDecartClient, models, type RealTimeModels } from "@decartai/sdk";

// Versão genérica de hooks/useDecartRealtime.ts só pra app/teste-fundo/ (seção 4.7) — aceita o modelo e o
// stream como parâmetro em vez de fixar "lucy-vton-latest", pra poder alternar entre os dois caminhos
// (A: lucy-2.5, B: lucy-vton-3.5 + fundo local) sem tocar no hook de produção.
type RealtimeClient = Awaited<
  ReturnType<ReturnType<typeof createDecartClient>["realtime"]["connect"]>
>;

export type TestConnectionStatus =
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
  model: RealTimeModels;
  /** Opcional: Caminho A (lucy-2.5) manda o prompt já na conexão. Caminho B (VTON) deixa em branco e
   * aplica a peça depois via clientRef.current.setImage(blob, { prompt, enhance }), igual à produção. */
  prompt?: string;
  onRemoteStream: (stream: MediaStream) => void;
}

export function useDecartTestConnect() {
  const [status, setStatus] = useState<TestConnectionStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const clientRef = useRef<RealtimeClient | null>(null);

  const connect = useCallback(async (options: ConnectOptions) => {
    const { apiKey, stream, model, prompt, onRemoteStream } = options;
    setStatus("connecting");
    setError(null);

    try {
      const client = createDecartClient({ apiKey });

      const rtClient = await client.realtime.connect(stream, {
        model: models.realtime(model),
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
