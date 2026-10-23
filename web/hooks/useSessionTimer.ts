"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Controle de sessão por visitante (CLAUDE.md 4.3): limite de tempo total e encerramento por inatividade
// (visitante parado sem trocar de peça) — ambos opcionais (null = sem limite) — e um pequeno "resfriamento" depois de
// um encerramento forçado, para a mesma pessoa não ser reconectada na hora pela detecção de presença — o
// próximo visitante (ou a mesma pessoa, de verdade saindo e voltando) só entra depois do resfriamento.
export type ForceEndReason = "limite" | "inatividade" | "visibilidade" | "operador";

export interface UseSessionTimerOptions {
  /** Limite total da sessão em segundos. null/ausente = sem limite. */
  limitSeconds?: number | null;
  /** Encerra se ninguém interagir por esse tempo. null/ausente = sem limite. */
  inactivityLimitSeconds?: number | null;
  cooldownSeconds?: number;
  onForceEnd: (reason: ForceEndReason) => void;
}

export function useSessionTimer({
  limitSeconds = null,
  inactivityLimitSeconds = null,
  cooldownSeconds = 5,
  onForceEnd,
}: UseSessionTimerOptions) {
  // secondsLeft só existe quando há limite de tempo; "active" diz se há sessão, com ou sem limite.
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const [active, setActive] = useState(false);
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
    setActive(false);
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
    setActive(true);
    clearTick();
    if (limitSeconds == null && inactivityLimitSeconds == null) return; // sem limites: nada a vigiar
    tickRef.current = setInterval(() => {
      if (startedAtRef.current == null) return;
      const t = Date.now();
      const remaining =
        limitSeconds != null
          ? Math.max(0, Math.ceil(limitSeconds - (t - startedAtRef.current) / 1000))
          : null;
      if (remaining != null) setSecondsLeft(remaining);
      const idleFor = (t - (lastInteractionRef.current ?? t)) / 1000;
      if (remaining != null && remaining <= 0) {
        stop();
        startCooldown();
        onForceEnd("limite");
      } else if (inactivityLimitSeconds != null && idleFor >= inactivityLimitSeconds) {
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

  return { secondsLeft, active, cooling, start, stop, markInteraction, forceEnd };
}
