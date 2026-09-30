"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Captura uma foto ou um vídeo curto do vídeo COM a roupa aplicada (o elemento de vídeo remoto da Decart),
// espelhado como o visitante vê na tela, com o logo do SENAI Lab Fashion marcado no canto. Envia para
// /api/capture (guardado só na memória, nunca em disco) e devolve a URL/QR code para o celular do
// visitante. Ver lib/capture-store.ts para o porquê de ser efêmero.
const MAX_RECORD_SECONDS = 8;
const LOGO_SRC = "/brand/senai-lab-fashion.png";

export type CaptureResult = {
  kind: "foto" | "video";
  url: string;
  qrDataUrl: string;
  expiresInSeconds: number;
};

type CaptureState = "idle" | "recording" | "enviando" | "pronto" | "erro";

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
  const [result, setResult] = useState<CaptureResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recordingSeconds, setRecordingSeconds] = useState(0);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const logoRef = useRef<HTMLImageElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const autoStopRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadLogo()
      .then((img) => {
        logoRef.current = img;
      })
      .catch(() => {
        // sem logo, a captura continua funcionando, só sem a marca no canto
      });
  }, []);

  const getCanvas = useCallback((w: number, h: number) => {
    if (!canvasRef.current) canvasRef.current = document.createElement("canvas");
    const canvas = canvasRef.current;
    canvas.width = w;
    canvas.height = h;
    return canvas;
  }, []);

  // Espelha (como na tela) e marca o logo no canto inferior direito, com uma faixa escura atrás para
  // o logo (que tem texto preto) continuar legível em fotos de fundo claro.
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

  const upload = useCallback(async (blob: Blob, kind: "foto" | "video") => {
    setState("enviando");
    setError(null);
    try {
      const form = new FormData();
      form.append("kind", kind);
      form.append("file", blob, kind === "foto" ? "foto.jpg" : "video.webm");
      const res = await fetch("/api/capture", { method: "POST", body: form });
      if (!res.ok) throw new Error("falha no envio");
      const data = await res.json();
      setResult({ kind, url: data.url, qrDataUrl: data.qrDataUrl, expiresInSeconds: data.expiresInSeconds });
      setState("pronto");
    } catch {
      setError("Não conseguimos preparar sua " + (kind === "foto" ? "foto" : "vídeo") + ". Tente de novo.");
      setState("erro");
    }
  }, []);

  const takePhoto = useCallback(() => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return;
    const canvas = getCanvas(video.videoWidth, video.videoHeight);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    drawFrame(video, ctx, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (blob) upload(blob, "foto");
      },
      "image/jpeg",
      0.92
    );
  }, [videoRef, getCanvas, drawFrame, upload]);

  const stopRecording = useCallback(() => {
    if (autoStopRef.current) clearTimeout(autoStopRef.current);
    if (tickRef.current) clearInterval(tickRef.current);
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    recorderRef.current?.stop();
  }, []);

  const startRecording = useCallback(() => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0 || state === "recording") return;
    const canvas = getCanvas(video.videoWidth, video.videoHeight);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const draw = () => {
      drawFrame(video, ctx, canvas.width, canvas.height);
      rafRef.current = requestAnimationFrame(draw);
    };
    draw();

    const stream = canvas.captureStream(25);
    const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
      ? "video/webm;codecs=vp9"
      : "video/webm";
    const recorder = new MediaRecorder(stream, { mimeType });
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };
    recorder.onstop = () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      upload(new Blob(chunks, { type: "video/webm" }), "video");
    };
    recorderRef.current = recorder;
    recorder.start();
    setState("recording");
    setRecordingSeconds(0);
    tickRef.current = setInterval(() => setRecordingSeconds((s) => s + 1), 1000);
    autoStopRef.current = setTimeout(stopRecording, MAX_RECORD_SECONDS * 1000);
  }, [videoRef, getCanvas, drawFrame, upload, state, stopRecording]);

  const dismiss = useCallback(() => {
    setResult(null);
    setError(null);
    setState("idle");
  }, []);

  useEffect(
    () => () => {
      if (autoStopRef.current) clearTimeout(autoStopRef.current);
      if (tickRef.current) clearInterval(tickRef.current);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    },
    []
  );

  return {
    state,
    result,
    error,
    recordingSeconds,
    maxRecordSeconds: MAX_RECORD_SECONDS,
    takePhoto,
    startRecording,
    stopRecording,
    dismiss,
  };
}
