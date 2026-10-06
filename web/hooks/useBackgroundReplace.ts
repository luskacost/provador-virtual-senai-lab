"use client";

import { useCallback, useRef, useState } from "react";
import { FilesetResolver, ImageSegmenter } from "@mediapipe/tasks-vision";

// Teste isolado da seção 4.7 do CLAUDE.md (Caminho B) — NUNCA usado pelo quiosque principal (app/page.tsx).
// Troca o fundo da webcam localmente (segmentação de pessoa via MediaPipe), ANTES de mandar o vídeo pra
// Decart, pra testar a hipótese não verificada: será que o VTON preserva um fundo já trocado?
export interface BackgroundReplaceOptions {
  /** Cor CSS sólida usada como fundo (ex.: "#164092"). Simples de propósito — só pra testar se a borda
   * aguenta; cenário fotográfico de verdade (passarela, rua, vitrine) só entra se isto for aprovado. */
  color: string;
}

export function useBackgroundReplace() {
  const segmenterRef = useRef<ImageSegmenter | null>(null);
  const rafRef = useRef<number | null>(null);
  const [ready, setReady] = useState(false);

  const init = useCallback(async () => {
    const vision = await FilesetResolver.forVisionTasks("/mediapipe/wasm");
    const segmenter = await ImageSegmenter.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: "/mediapipe/selfie_segmenter.tflite",
        delegate: "GPU",
      },
      runningMode: "VIDEO",
      outputConfidenceMasks: true,
      outputCategoryMask: false,
    });
    segmenterRef.current = segmenter;
    setReady(true);
  }, []);

  /** Recebe o <video> já tocando a webcam e devolve um MediaStream (canvas.captureStream) com o fundo já
   * trocado — é esse stream que vai pro client.realtime.connect() no lugar do stream bruto da câmera. */
  const start = useCallback(
    (video: HTMLVideoElement, options: BackgroundReplaceOptions): MediaStream => {
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      const ctx2d = canvas.getContext("2d");
      if (!ctx2d) throw new Error("Canvas 2D não disponível");
      const ctx: CanvasRenderingContext2D = ctx2d;

      const maskCanvas = document.createElement("canvas");
      const maskCtx2d = maskCanvas.getContext("2d");
      if (!maskCtx2d) throw new Error("Canvas 2D não disponível (máscara)");
      const maskCtx: CanvasRenderingContext2D = maskCtx2d;

      function renderFrame() {
        const segmenter = segmenterRef.current;
        if (!segmenter || video.readyState < 2) {
          rafRef.current = requestAnimationFrame(renderFrame);
          return;
        }

        const result = segmenter.segmentForVideo(video, performance.now());
        const mask = result.confidenceMasks?.[0];

        if (mask) {
          // 1) pinta a confiança de "pessoa" num canvas no tamanho nativo da máscara (geralmente menor que
          //    o vídeo) — mais simples que remapear índice a índice entre resoluções diferentes.
          maskCanvas.width = mask.width;
          maskCanvas.height = mask.height;
          const values = mask.getAsFloat32Array();
          const maskImage = maskCtx.createImageData(mask.width, mask.height);
          for (let i = 0; i < values.length; i++) {
            const alpha = Math.max(0, Math.min(255, Math.round(values[i] * 255)));
            maskImage.data[i * 4] = 255;
            maskImage.data[i * 4 + 1] = 255;
            maskImage.data[i * 4 + 2] = 255;
            maskImage.data[i * 4 + 3] = alpha;
          }
          maskCtx.putImageData(maskImage, 0, 0);
          result.close();

          // 2) desenha a pessoa, recorta pela máscara (ampliada pro tamanho do canvas final) e põe o fundo
          //    atrás — truque padrão de composição 2D (destination-in / destination-over).
          ctx.globalCompositeOperation = "source-over";
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          ctx.globalCompositeOperation = "destination-in";
          ctx.drawImage(maskCanvas, 0, 0, canvas.width, canvas.height);
          ctx.globalCompositeOperation = "destination-over";
          ctx.fillStyle = options.color;
          ctx.fillRect(0, 0, canvas.width, canvas.height);
        } else {
          result.close();
          ctx.globalCompositeOperation = "source-over";
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        }

        rafRef.current = requestAnimationFrame(renderFrame);
      }

      renderFrame();
      return canvas.captureStream(24);
    },
    []
  );

  const stop = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  const dispose = useCallback(() => {
    stop();
    segmenterRef.current?.close();
    segmenterRef.current = null;
    setReady(false);
  }, [stop]);

  return { init, start, stop, dispose, ready };
}
