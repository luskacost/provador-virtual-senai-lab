"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Product } from "@/lib/catalog";
import { useCamera } from "@/hooks/useCamera";
import { useDecartRealtime } from "@/hooks/useDecartRealtime";
import { usePersonDetection } from "@/hooks/usePersonDetection";
import { ForceEndReason, useSessionTimer } from "@/hooks/useSessionTimer";
import { SessionEndReason } from "@/lib/metrics";
import { urlToImageBlob, resizeImageBlob } from "@/lib/image-utils";
import { ProductSidebar } from "@/components/ProductSidebar";
import { PersonDetectionView } from "@/components/PersonDetectionView";

// CLAUDE.md 4.3 - configurável. O padrão do documento é 90s, mas o usuário decidiu em 07/10/2026 manter
// estes valores de forma permanente (suficiente para o visitante e economiza créditos da Decart).
const SESSION_LIMIT_SECONDS = 30;
const INACTIVITY_LIMIT_SECONDS = 15;
const COOLDOWN_SECONDS = 10;

export default function PersonDetectionPage() {
  const [activeProduct, setActiveProduct] = useState<Product | null>(null);
  const { stream, startCamera, stopCamera } = useCamera();
  const { status, error, connect, disconnect, clientRef } =
    useDecartRealtime();

  const remoteVideoRef = useRef<React.RefObject<HTMLVideoElement | null>>(null);
  const [localVideoElement, setLocalVideoElement] =
    useState<HTMLVideoElement | null>(null);
  const garmentBlobRef = useRef<Blob | null>(null);
  const lastProductRef = useRef<Product | null>(null);
  const connectingRef = useRef(false);

  // Métricas locais (CLAUDE.md 4.5): só timestamps, duração e ids de peça — nunca vídeo/imagem do
  // visitante. sessionStartedAtRef não-nulo é como o resto do código sabe "há uma sessão para registrar".
  const sessionStartedAtRef = useRef<string | null>(null);
  const sessionProductsRef = useRef<string[]>([]);

  const logSession = useCallback((endReason: SessionEndReason) => {
    const startedAt = sessionStartedAtRef.current;
    if (!startedAt) return; // nada a registrar (ex.: atalho do operador sem sessão ativa)
    const endedAt = new Date().toISOString();
    const durationSeconds = (new Date(endedAt).getTime() - new Date(startedAt).getTime()) / 1000;
    const payload = { startedAt, endedAt, durationSeconds, endReason, products: sessionProductsRef.current };
    sessionStartedAtRef.current = null;
    sessionProductsRef.current = [];
    fetch("/api/metrics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).catch(() => {
      // best-effort: metricas nunca devem quebrar a experiencia do visitante (CLAUDE.md 4.4)
    });
  }, []);

  const { personPresent, isReady: detectionReady } =
    usePersonDetection(localVideoElement);

  // Encerramento forçado (limite de tempo, inatividade, aba escondida, atalho do operador): larga a
  // conexão da Decart e limpa a peça selecionada. O cooldown do hook impede a mesma pessoa ser
  // reconectada na hora pela detecção de presença (senão o limite não teria efeito nenhum).
  const handleForceEnd = useCallback(
    (reason: ForceEndReason) => {
      logSession(reason);
      disconnect();
      setActiveProduct(null);
      lastProductRef.current = null;
      garmentBlobRef.current = null;
    },
    [disconnect, logSession]
  );

  const timer = useSessionTimer({
    limitSeconds: SESSION_LIMIT_SECONDS,
    inactivityLimitSeconds: INACTIVITY_LIMIT_SECONDS,
    cooldownSeconds: COOLDOWN_SECONDS,
    onForceEnd: handleForceEnd,
  });

  const handleRemoteStreamRef = useCallback(
    (ref: React.RefObject<HTMLVideoElement | null>) => {
      remoteVideoRef.current = ref;
    },
    []
  );

  const handleLocalVideoRef = useCallback(
    (ref: React.RefObject<HTMLVideoElement | null>) => {
      setLocalVideoElement(ref.current);
    },
    []
  );

  // Start camera on mount (detection runs on the camera feed, Decart connects later)
  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, [startCamera, stopCamera]);

  // Connect/disconnect based on person detection
  useEffect(() => {
    if (!detectionReady || !stream) return;

    if (
      personPresent &&
      !clientRef.current &&
      !connectingRef.current &&
      !timer.cooling
    ) {
      // Person detected → connect to Decart
      connectingRef.current = true;

      (async () => {
        const res = await fetch("/api/tokens", { method: "POST" });
        const { apiKey } = await res.json();

        const rtClient = await connect({
          apiKey,
          stream,
          onRemoteStream: (remoteStream) => {
            if (remoteVideoRef.current?.current) {
              remoteVideoRef.current.current.srcObject = remoteStream;
            }
          },
        });

        connectingRef.current = false;

        if (rtClient) {
          timer.start(); // CLAUDE.md 4.3: sessão começa a contar aqui, não no clique da primeira peça
          sessionStartedAtRef.current = new Date().toISOString(); // CLAUDE.md 4.5
          sessionProductsRef.current = [];

          // Re-apply last garment if reconnecting
          if (lastProductRef.current && garmentBlobRef.current) {
            rtClient.setImage(garmentBlobRef.current, {
              prompt: lastProductRef.current.prompt,
              enhance: false,
            });
          }
        }
      })();
    } else if (!personPresent && clientRef.current && !connectingRef.current) {
      // Pessoa saiu por conta própria (não foi um encerramento forçado): sem cooldown, a próxima pessoa
      // (ou a mesma, voltando) já pode conectar na hora.
      logSession("pessoa_saiu");
      disconnect();
      timer.stop();
    }
  }, [personPresent, detectionReady, stream, connect, disconnect, clientRef, timer, logSession]);

  // Atalhos do operador (CLAUDE.md 4.3): Ctrl+Shift+E encerra a sessão atual agora; Ctrl+Shift+R
  // reseta o app inteiro (mesmo caminho do botão "Tentar de novo" de erro: recarregar é o reset mais
  // confiável). Combinação improvável de alguém apertar por acidente.
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (!e.ctrlKey || !e.shiftKey) return;
      const key = e.key.toLowerCase();
      if (key === "e") {
        e.preventDefault();
        timer.forceEnd("operador");
      } else if (key === "r") {
        e.preventDefault();
        window.location.reload();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [timer]);

  // Encerra se a aba/janela perder o foco (CLAUDE.md 4.3: "ao trocar de aba") — evita gastar sessão com
  // ninguém olhando.
  useEffect(() => {
    function onVisibilityChange() {
      if (document.hidden) timer.forceEnd("visibilidade");
    }
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => document.removeEventListener("visibilitychange", onVisibilityChange);
  }, [timer]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  const handleSelectProduct = useCallback(
    async (product: Product) => {
      setActiveProduct(product);
      lastProductRef.current = product;
      timer.markInteraction(); // reinicia o relógio de inatividade (não o limite total da sessão)
      if (sessionStartedAtRef.current) sessionProductsRef.current.push(product.id);

      if (!clientRef.current) return;

      const blob = await urlToImageBlob(product.imagem);
      const resized = await resizeImageBlob(blob);
      garmentBlobRef.current = resized;

      clientRef.current.setImage(resized, {
        prompt: product.prompt,
        enhance: false,
      });
    },
    [clientRef, timer]
  );

  return (
    <div className="h-screen flex">
      <ProductSidebar
        activeProduct={activeProduct}
        onSelectProduct={handleSelectProduct}
      />
      <PersonDetectionView
        localStream={stream}
        status={status}
        error={error}
        personPresent={personPresent}
        detectionReady={detectionReady}
        onRemoteStream={handleRemoteStreamRef}
        onLocalVideo={handleLocalVideoRef}
        sessionSecondsLeft={timer.secondsLeft}
        cooling={timer.cooling}
      />
    </div>
  );
}
