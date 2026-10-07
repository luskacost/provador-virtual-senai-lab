"use client";

import { useState, useCallback, useRef } from "react";

// Câmera do estande (Canon EOS 2000D, vista pelo navegador como "EOS Webcam Utility") tem prioridade sobre a
// webcam do notebook. Sem ela conectada, o app segue com a câmera padrão.
const PREFERRED_CAMERA = /canon|eos/i;

async function findPreferredCameraId(): Promise<string | null> {
  const devices = await navigator.mediaDevices.enumerateDevices();
  const camera = devices.find(
    (d) => d.kind === "videoinput" && PREFERRED_CAMERA.test(d.label)
  );
  return camera?.deviceId ?? null;
}

export function useCamera() {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startCamera = useCallback(async () => {
    try {
      let mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "user" },
      });

      // O navegador só revela o nome das câmeras depois da permissão — por isso abre a padrão primeiro e
      // troca para a preferida se ela não for a que veio.
      const preferredId = await findPreferredCameraId();
      const currentId = mediaStream.getVideoTracks()[0]?.getSettings().deviceId;
      if (preferredId && preferredId !== currentId) {
        try {
          const preferred = await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: { deviceId: { exact: preferredId } },
          });
          mediaStream.getTracks().forEach((t) => t.stop());
          mediaStream = preferred;
        } catch {
          // a preferida falhou (ocupada por outro programa?): segue com a padrão em vez de ficar sem câmera
        }
      }
      console.info("[camera] usando:", mediaStream.getVideoTracks()[0]?.label);

      streamRef.current = mediaStream;
      setStream(mediaStream);
      setError(null);
      return mediaStream;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Camera access denied";
      setError(msg);
      return null;
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      setStream(null);
    }
  }, []);

  return { stream, error, startCamera, stopCamera };
}
