"use client";

import { useState, useEffect, useRef } from "react";
import { PoseLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";

const DETECTION_INTERVAL_MS = 1000;
const MISS_THRESHOLD = 3;

export function usePersonDetection(
  videoElement: HTMLVideoElement | null
) {
  const [personPresent, setPersonPresent] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const landmarkerRef = useRef<PoseLandmarker | null>(null);
  const missCountRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
    if (!videoElement) {
      // Pausado (standby do operador): ninguém "presente" até voltar a olhar o vídeo, senão uma detecção
      // velha conectaria na Decart ao acordar.
      missCountRef.current = 0;
      setPersonPresent(false);
      return;
    }
    if (!isReady) return;

    function detect() {
      if (
        !landmarkerRef.current ||
        !videoElement ||
        videoElement.readyState < 2
      )
        return;

      const result = landmarkerRef.current.detectForVideo(
        videoElement,
        performance.now()
      );

      if (result.landmarks.length > 0) {
        missCountRef.current = 0;
        setPersonPresent(true);
      } else {
        missCountRef.current++;
        if (missCountRef.current >= MISS_THRESHOLD) {
          setPersonPresent(false);
        }
      }
    }

    intervalRef.current = setInterval(detect, DETECTION_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isReady, videoElement]);

  return { personPresent, isReady };
}
