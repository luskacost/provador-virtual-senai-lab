"use client";

import { useState, useEffect, useRef } from "react";
import { PoseLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";
import type { PoseSample } from "@/lib/gesture-engine";

// Em espera, 1 leitura por segundo basta para saber se tem alguém. Com sessão ativa, os gestos precisam de
// mais leituras (~8 por segundo). O tempo para considerar "pessoa saiu" é o mesmo nos dois casos (3 s).
const IDLE_INTERVAL_MS = 1000;
const FAST_INTERVAL_MS = 125;
const ABSENCE_MS = 3000;

interface Options {
  /** true durante a sessão: lê a pose mais vezes por segundo, para os gestos. */
  fast?: boolean;
  /** Chamado a cada leitura com os pontos do corpo (ou null se não há ninguém). */
  onPose?: (pose: PoseSample | null, now: number) => void;
}

export function usePersonDetection(
  videoElement: HTMLVideoElement | null,
  { fast = false, onPose }: Options = {}
) {
  const [personPresent, setPersonPresent] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const landmarkerRef = useRef<PoseLandmarker | null>(null);
  const missCountRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onPoseRef = useRef(onPose);

  useEffect(() => {
    onPoseRef.current = onPose;
  }, [onPose]);

  // Initialize PoseLandmarker
  useEffect(() => {
    let cancelled = false;

    async function init() {
      // Auto-hospedado (CLAUDE.md 4.4: nada externo além da Decart em tempo de execução). Os arquivos vêm
      // de public/mediapipe/, gerados por "npm install" (scripts/setup-mediapipe.mjs) e fora do git.
      const vision = await FilesetResolver.forVisionTasks("/mediapipe/wasm");
      if (cancelled) return;

      const landmarker = await PoseLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: "/mediapipe/pose_landmarker_lite.task",
          delegate: "GPU",
        },
        runningMode: "VIDEO",
        numPoses: 1,
      });
      if (cancelled) return;

      landmarkerRef.current = landmarker;
      setIsReady(true);
    }

    init();

    return () => {
      cancelled = true;
      landmarkerRef.current?.close();
      landmarkerRef.current = null;
    };
  }, []);

  // Poll video for person detection
  useEffect(() => {
    if (!isReady || !videoElement) return;

    const intervalMs = fast ? FAST_INTERVAL_MS : IDLE_INTERVAL_MS;
    const missThreshold = Math.ceil(ABSENCE_MS / intervalMs);

    function detect() {
      if (
        !landmarkerRef.current ||
        !videoElement ||
        videoElement.readyState < 2
      )
        return;

      const now = performance.now();
      const result = landmarkerRef.current.detectForVideo(videoElement, now);

      if (result.landmarks.length > 0) {
        missCountRef.current = 0;
        setPersonPresent(true);
        const lm = result.landmarks[0];
        // índices do MediaPipe Pose: 0 nariz, 11/12 ombros esq./dir., 15/16 pulsos esq./dir. ("esquerda"
        // e "direita" são da própria pessoa, não da imagem)
        onPoseRef.current?.(
          {
            nose: lm[0],
            leftShoulder: lm[11],
            rightShoulder: lm[12],
            leftWrist: lm[15],
            rightWrist: lm[16],
          },
          now
        );
      } else {
        missCountRef.current++;
        onPoseRef.current?.(null, now);
        if (missCountRef.current >= missThreshold) {
          setPersonPresent(false);
        }
      }
    }

    intervalRef.current = setInterval(detect, intervalMs);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isReady, videoElement, fast]);

  return { personPresent, isReady };
}
