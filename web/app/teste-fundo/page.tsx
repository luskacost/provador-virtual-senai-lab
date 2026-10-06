"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { PRODUCTS } from "@/lib/catalog";
import { useCamera } from "@/hooks/useCamera";
import { useDecartTestConnect } from "@/hooks/useDecartTestConnect";
import { useBackgroundReplace } from "@/hooks/useBackgroundReplace";
import { urlToImageBlob, resizeImageBlob } from "@/lib/image-utils";

// Página de teste ISOLADA da seção 4.7 do CLAUDE.md — compara os dois caminhos de troca de fundo, FORA do
// quiosque (app/page.tsx não importa nada deste arquivo, e esta página não aparece em nenhum menu). Nada
// aqui é usado em produção até o usuário aprovar um dos dois caminhos.
//
// Caminho A: lucy-2.5 (edição geral) — um prompt só pede roupa E fundo, no vídeo bruto da câmera.
// Caminho B: lucy-vton-3.5 (VTON) — a roupa fica com a Decart; o fundo é trocado AQUI no navegador
//   (segmentação local via MediaPipe, hooks/useBackgroundReplace.ts) antes do vídeo sair da máquina.
//
// Preço confirmado na documentação (platform.decart.ai/getting-started/pricing) em 06/10/2026: os dois
// modelos custam $0.02/s no modo padrão (nunca usamos "fast", que custa o dobro).
const COST_PER_SECOND = 0.02;

const BACKGROUND_PRESETS = [
  {
    label: "Laranja sólido (comparar com Caminho B)",
    value: "a solid flat orange (#ff6123) background, no texture, no gradient, like a seamless photography backdrop",
  },
  { label: "Estúdio cinza claro", value: "a plain light grey photography studio backdrop" },
  { label: "Praia (exemplo da doc)", value: "a sandy beach with clear blue water" },
  { label: "Rua ao anoitecer", value: "a city street at golden hour, blurred background" },
  { label: "Vitrine de loja", value: "a modern upscale clothing store interior, softly lit" },
  { label: "Passarela", value: "a fashion runway with soft spotlights and a dark backdrop" },
];

const BG_COLOR_PRESETS = [
  { label: "Azul-marinho (marca)", value: "#164092" },
  { label: "Laranja (marca)", value: "#ff6123" },
  { label: "Cinza claro", value: "#d9d9d9" },
  { label: "Branco", value: "#ffffff" },
];

function waitForVideoReady(video: HTMLVideoElement): Promise<void> {
  if (video.readyState >= 2 && video.videoWidth > 0) return Promise.resolve();
  return new Promise((resolve) => {
    const onReady = () => {
      video.removeEventListener("loadeddata", onReady);
      resolve();
    };
    video.addEventListener("loadeddata", onReady);
  });
}

export default function TesteFundoPage() {
  const { stream, error: cameraError, startCamera, stopCamera } = useCamera();
  const { status, error: decartError, connect, disconnect, clientRef } =
    useDecartTestConnect();
  const bg = useBackgroundReplace();

  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);

  const [path, setPath] = useState<"A" | "B">("B");
  const [productId, setProductId] = useState(PRODUCTS[0]?.id ?? "");
  const [backgroundText, setBackgroundText] = useState(BACKGROUND_PRESETS[0].value);
  const [backgroundColor, setBackgroundColor] = useState(BG_COLOR_PRESETS[0].value);
  const [running, setRunning] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [totalSecondsUsed, setTotalSecondsUsed] = useState(0);
  const [log, setLog] = useState<string[]>([]);

  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const bgInitedRef = useRef(false);

  const addLog = useCallback((msg: string) => {
    setLog((prev) => [...prev, `${new Date().toLocaleTimeString()} — ${msg}`]);
  }, []);

  useEffect(() => {
    if (localVideoRef.current && stream) {
      localVideoRef.current.srcObject = stream;
    }
  }, [stream]);

  useEffect(() => {
    return () => {
      disconnect();
      bg.stop();
      stopCamera();
      if (tickRef.current) clearInterval(tickRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const product = PRODUCTS.find((p) => p.id === productId) ?? PRODUCTS[0];

  const handleConnect = useCallback(async () => {
    if (!product) return;

    let activeStream = stream;
    if (!activeStream) {
      activeStream = await startCamera();
      if (!activeStream) return;
    }
    if (!localVideoRef.current) return;
    localVideoRef.current.srcObject = activeStream;
    await waitForVideoReady(localVideoRef.current);

    const res = await fetch("/api/tokens", { method: "POST" });
    const { apiKey } = await res.json();

    addLog(`Conectando — Caminho ${path}, peça "${product.nome}"`);

    if (path === "A") {
      const combinedPrompt = `${product.prompt}. Also, change the background to ${backgroundText}.`;
      addLog(`Prompt combinado: ${combinedPrompt}`);
      const rtClient = await connect({
        apiKey,
        stream: activeStream,
        model: "lucy-2.5",
        prompt: combinedPrompt,
        onRemoteStream: (remoteStream) => {
          if (remoteVideoRef.current) remoteVideoRef.current.srcObject = remoteStream;
        },
      });
      if (!rtClient) {
        addLog("Falha ao conectar (ver erro abaixo).");
        return;
      }
    } else {
      if (!bgInitedRef.current) {
        addLog("Carregando modelo de segmentação (primeira vez)...");
        await bg.init();
        bgInitedRef.current = true;
      }
      const composedStream = bg.start(localVideoRef.current, { color: backgroundColor });
      const rtClient = await connect({
        apiKey,
        stream: composedStream,
        model: "lucy-vton-3.5",
        onRemoteStream: (remoteStream) => {
          if (remoteVideoRef.current) remoteVideoRef.current.srcObject = remoteStream;
        },
      });
      if (!rtClient) {
        addLog("Falha ao conectar (ver erro abaixo).");
        bg.stop();
        return;
      }
      const blob = await urlToImageBlob(product.imagem);
      const resized = await resizeImageBlob(blob);
      rtClient.setImage(resized, { prompt: product.prompt, enhance: false });
    }

    setRunning(true);
    setElapsedSeconds(0);
    tickRef.current = setInterval(() => {
      setElapsedSeconds((s) => s + 1);
      setTotalSecondsUsed((s) => s + 1);
    }, 1000);
  }, [product, stream, startCamera, path, backgroundText, backgroundColor, connect, bg, addLog]);

  const handleDisconnect = useCallback(() => {
    disconnect();
    bg.stop();
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
    setRunning(false);
    addLog(`Desconectado — ${elapsedSeconds}s nesta sessão (~$${(elapsedSeconds * COST_PER_SECOND).toFixed(2)})`);
  }, [disconnect, bg, elapsedSeconds, addLog]);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        <header>
          <h1 className="text-2xl font-bold">Teste de fundo — CLAUDE.md seção 4.7</h1>
          <p className="text-gray-400 mt-1">
            Isolado do quiosque. Nada aqui entra em produção sem aprovação explícita. Custo confirmado na
            doc: $0.02/s nos dois modelos (modo padrão, sem &quot;fast&quot;).
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr_320px] gap-4">
          {/* Câmera local (fonte) */}
          <div className="space-y-2">
            <p className="text-sm text-gray-400">Câmera (fonte)</p>
            <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
              <video
                ref={localVideoRef}
                autoPlay
                playsInline
                muted
                className="absolute inset-0 w-full h-full object-cover"
                style={{ transform: "scaleX(-1)" }}
              />
            </div>
            {!stream && (
              <button
                onClick={() => startCamera()}
                className="w-full rounded-lg bg-gray-800 hover:bg-gray-700 px-4 py-2 text-sm"
              >
                Ligar câmera
              </button>
            )}
            {cameraError && <p className="text-red-400 text-sm">{cameraError}</p>}
          </div>

          {/* Resultado da Decart */}
          <div className="space-y-2">
            <p className="text-sm text-gray-400">Resultado (Decart) — status: {status}</p>
            <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
              <video
                ref={remoteVideoRef}
                autoPlay
                playsInline
                muted
                className="absolute inset-0 w-full h-full object-cover"
                style={{ transform: "scaleX(-1)" }}
              />
            </div>
            {decartError && <p className="text-red-400 text-sm">{decartError}</p>}
            {running && (
              <p className="text-sm text-gray-300">
                {elapsedSeconds}s nesta sessão (~${(elapsedSeconds * COST_PER_SECOND).toFixed(2)}) · total
                acumulado hoje: {totalSecondsUsed}s (~${(totalSecondsUsed * COST_PER_SECOND).toFixed(2)})
              </p>
            )}
          </div>

          {/* Controles */}
          <div className="space-y-4 bg-gray-900 rounded-lg p-4">
            <div>
              <p className="text-sm text-gray-400 mb-1">Caminho</p>
              <div className="flex gap-2">
                <button
                  disabled={running}
                  onClick={() => setPath("B")}
                  className={`flex-1 rounded-lg px-3 py-2 text-sm ${
                    path === "B" ? "bg-brand-orange text-black" : "bg-gray-800"
                  }`}
                >
                  B: VTON + fundo local
                </button>
                <button
                  disabled={running}
                  onClick={() => setPath("A")}
                  className={`flex-1 rounded-lg px-3 py-2 text-sm ${
                    path === "A" ? "bg-brand-orange text-black" : "bg-gray-800"
                  }`}
                >
                  A: lucy-2.5
                </button>
              </div>
            </div>

            <div>
              <p className="text-sm text-gray-400 mb-1">Peça</p>
              <select
                disabled={running}
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
                className="w-full rounded-lg bg-gray-800 px-3 py-2 text-sm"
              >
                {PRODUCTS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nome}
                  </option>
                ))}
              </select>
            </div>

            {path === "A" ? (
              <div>
                <p className="text-sm text-gray-400 mb-1">Fundo (texto do prompt)</p>
                <select
                  disabled={running}
                  value={backgroundText}
                  onChange={(e) => setBackgroundText(e.target.value)}
                  className="w-full rounded-lg bg-gray-800 px-3 py-2 text-sm mb-2"
                >
                  {BACKGROUND_PRESETS.map((b) => (
                    <option key={b.label} value={b.value}>
                      {b.label}
                    </option>
                  ))}
                </select>
                <textarea
                  disabled={running}
                  value={backgroundText}
                  onChange={(e) => setBackgroundText(e.target.value)}
                  rows={2}
                  className="w-full rounded-lg bg-gray-800 px-3 py-2 text-sm"
                />
              </div>
            ) : (
              <div>
                <p className="text-sm text-gray-400 mb-1">Fundo (cor sólida local)</p>
                <div className="grid grid-cols-2 gap-2 mb-2">
                  {BG_COLOR_PRESETS.map((c) => (
                    <button
                      key={c.value}
                      disabled={running}
                      onClick={() => setBackgroundColor(c.value)}
                      className={`rounded-lg px-3 py-2 text-xs flex items-center gap-2 ${
                        backgroundColor === c.value ? "ring-2 ring-brand-orange" : ""
                      }`}
                      style={{ backgroundColor: c.value, color: "#fff", textShadow: "0 1px 2px rgba(0,0,0,.6)" }}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
                <input
                  disabled={running}
                  type="color"
                  value={backgroundColor}
                  onChange={(e) => setBackgroundColor(e.target.value)}
                  className="w-full h-8 rounded"
                />
              </div>
            )}

            {!running ? (
              <button
                onClick={handleConnect}
                className="w-full rounded-lg bg-green-600 hover:bg-green-500 px-4 py-3 font-medium"
              >
                Conectar
              </button>
            ) : (
              <button
                onClick={handleDisconnect}
                className="w-full rounded-lg bg-red-600 hover:bg-red-500 px-4 py-3 font-medium"
              >
                Desconectar
              </button>
            )}
          </div>
        </div>

        <div className="bg-gray-900 rounded-lg p-4">
          <p className="text-sm text-gray-400 mb-2">Log (anote aqui o que observar: borda, latência, qualidade da roupa)</p>
          <div className="text-xs font-mono text-gray-300 space-y-1 max-h-40 overflow-y-auto">
            {log.length === 0 && <p className="text-gray-500">Nada ainda.</p>}
            {log.map((l, i) => (
              <p key={i}>{l}</p>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
