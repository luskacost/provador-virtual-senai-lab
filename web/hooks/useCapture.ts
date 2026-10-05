"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Captura uma foto do vídeo COM a roupa aplicada (o elemento de vídeo remoto da Decart), espelhada como o
// visitante vê na tela, com o logo do SENAI Lab Fashion marcado no canto. A foto vai direto para a
// impressora do quiosque (window.print()) - nunca sai da máquina, nunca passa por rede ou servidor. Troca
// o plano anterior (QR code para o celular do visitante), abandonado por depender da rede do evento não
// ter isolamento entre dispositivos (ver docs/aprendizados.md).
const LOGO_SRC = "/brand/senai-lab-fashion.png";

type CaptureState = "idle" | "pronto" | "erro";

function loadLogo(): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("falha ao carregar o logo"));
    img.src = LOGO_SRC;
  });
}

export function useCapture(videoRef: React.RefObject<HTMLVideoElement | null>) {
  const [state, setState] = useState<CaptureState>("idle");
  const [photoDataUrl, setPhotoDataUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const logoRef = useRef<HTMLImageElement | null>(null);

  useEffect(() => {
    loadLogo()
      .then((img) => {
        logoRef.current = img;
      })
      .catch(() => {
        // sem logo, a captura continua funcionando, só sem a marca no canto
      });
  }, []);

  // Espelha (como na tela) e marca o logo no canto inferior direito, com uma faixa clara atrás para o
  // logo (que tem texto preto) continuar legível em fotos de fundo escuro.
  const drawFrame = useCallback((video: HTMLVideoElement, ctx: CanvasRenderingContext2D, w: number, h: number) => {
    ctx.save();
    ctx.translate(w, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, w, h);
    ctx.restore();

    const logo = logoRef.current;
    if (logo) {
      const logoW = Math.round(w * 0.22);
      const logoH = Math.round(logoW * (logo.height / logo.width));
      const pad = Math.round(w * 0.02);
      ctx.fillStyle = "rgba(255,255,255,0.92)";
      ctx.fillRect(w - logoW - pad * 2, h - logoH - pad * 2, logoW + pad, logoH + pad);
      ctx.drawImage(logo, w - logoW - pad, h - logoH - pad, logoW, logoH);
    }
  }, []);

  const takePhoto = useCallback(() => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) {
      setError("A câmera ainda não está pronta. Tente de novo em um instante.");
      setState("erro");
      return;
    }
    if (!canvasRef.current) canvasRef.current = document.createElement("canvas");
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    drawFrame(video, ctx, canvas.width, canvas.height);
    setPhotoDataUrl(canvas.toDataURL("image/jpeg", 0.92));
    setError(null);
    setState("pronto");
  }, [videoRef, drawFrame]);

  const dismiss = useCallback(() => {
    setPhotoDataUrl(null);
    setError(null);
    setState("idle");
  }, []);

  return { state, photoDataUrl, error, takePhoto, dismiss };
}
