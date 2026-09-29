"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Product } from "@/lib/catalog";
import { useCamera } from "@/hooks/useCamera";
import { useDecartRealtime } from "@/hooks/useDecartRealtime";
import { usePersonDetection } from "@/hooks/usePersonDetection";
import { useSessionTimer } from "@/hooks/useSessionTimer";
import { urlToImageBlob, resizeImageBlob } from "@/lib/image-utils";
import { ProductSidebar } from "@/components/ProductSidebar";
import { PersonDetectionView } from "@/components/PersonDetectionView";

// CLAUDE.md 4.3 - configurável. 90s é o padrão pedido; os outros dois números não têm um padrão fixado
// no documento, escolhidos para o ritmo de uma exposição (ajustar aqui se ficar curto/longo demais).
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

  const { personPresent, isReady: detectionReady } =
    usePersonDetection(localVideoElement);

  // Encerramento forçado (limite de tempo, inatividade, aba escondida, atalho do operador): larga a
  // conexão da Decart e limpa a peça selecionada. O cooldown do hook impede a mesma pessoa ser
  // reconectada na hora pela detecção de presença (senão o limite não teria efeito nenhum).
  const handleForceEnd = useCallback(() => {
    disconnect();
    setActiveProduct(null);
    lastProductRef.current = null;
    garmentBlobRef.current = null;
  }, [disconnect]);

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
      disconnect();
      timer.stop();
    }
  }, [personPresent, detectionReady, stream, connect, disconnect, clientRef, timer]);

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
