"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Controle de sessão por visitante (CLAUDE.md 4.3): limite de tempo total (padrão 90 s, configurável),
// encerramento por inatividade (visitante parado sem trocar de peça) e um pequeno "resfriamento" depois de
// um encerramento forçado, para a mesma pessoa não ser reconectada na hora pela detecção de presença — o
// próximo visitante (ou a mesma pessoa, de verdade saindo e voltando) só entra depois do resfriamento.
export type ForceEndReason = "limite" | "inatividade" | "visibilidade" | "operador";

export interface UseSessionTimerOptions {
  limitSeconds?: number;
  inactivityLimitSeconds?: number;
  cooldownSeconds?: number;
  onForceEnd: (reason: ForceEndReason) => void;
}

export function useSessionTimer({
  limitSeconds = 90,
  inactivityLimitSeconds = 45,
  cooldownSeconds = 5,
  onForceEnd,
}: UseSessionTimerOptions) {
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const [cooling, setCooling] = useState(false);

  const startedAtRef = useRef<number | null>(null);
  const lastInteractionRef = useRef<number | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cooldownRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTick = useCallback(() => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  const stop = useCallback(() => {
    clearTick();
    startedAtRef.current = null;
    setSecondsLeft(null);
  }, [clearTick]);

  const startCooldown = useCallback(() => {
    setCooling(true);
    if (cooldownRef.current) clearTimeout(cooldownRef.current);
    cooldownRef.current = setTimeout(() => setCooling(false), cooldownSeconds * 1000);
  }, [cooldownSeconds]);

  const start = useCallback(() => {
    const now = Date.now();
    startedAtRef.current = now;
    lastInteractionRef.current = now;
    setSecondsLeft(limitSeconds);
    clearTick();
    tickRef.current = setInterval(() => {
      if (startedAtRef.current == null) return;
      const t = Date.now();
      const remaining = Math.max(0, Math.ceil(limitSeconds - (t - startedAtRef.current) / 1000));
      setSecondsLeft(remaining);
      const idleFor = (t - (lastInteractionRef.current ?? t)) / 1000;
      if (remaining <= 0) {
        stop();
        startCooldown();
        onForceEnd("limite");
      } else if (idleFor >= inactivityLimitSeconds) {
        stop();
        startCooldown();
        onForceEnd("inatividade");
      }
    }, 1000);
  }, [limitSeconds, inactivityLimitSeconds, clearTick, stop, startCooldown, onForceEnd]);

  const markInteraction = useCallback(() => {
    lastInteractionRef.current = Date.now();
  }, []);

  /** Encerramento por um gatilho externo (aba escondida, atalho do operador). Não faz nada se não há
   * sessão em andamento (startedAtRef nulo) — evita, por exemplo, o atalho do operador disparar de novo
   * sem uma sessão ativa. */
  const forceEnd = useCallback(
    (reason: ForceEndReason) => {
      if (startedAtRef.current == null) return;
      stop();
      startCooldown();
      onForceEnd(reason);
    },
    [stop, startCooldown, onForceEnd]
  );

  useEffect(
    () => () => {
      clearTick();
      if (cooldownRef.current) clearTimeout(cooldownRef.current);
    },
    [clearTick]
  );

  return { secondsLeft, cooling, start, stop, markInteraction, forceEnd };
}
