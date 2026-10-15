// Gestos do visitante para escolher/tirar peça sem tocar na TV (usa só os pontos do corpo que o MediaPipe
// Pose já entrega; nenhum custo na Decart). Lógica pura, sem React, para poder ser testada com dados falsos.
//
// Regras (pensadas para NÃO trocar a roupa por engano):
// - Sem peça ("browsing"): mão DIREITA levantada acima do ombro = próxima peça; mão ESQUERDA = anterior
//   (repete enquanto segurar). As DUAS mãos acima da cabeça por 1,5 s = escolher a peça em foco.
// - Com peça ("wearing"): só um gesto vale — as DUAS mãos acima da cabeça por 1,5 s = tirar a peça. Mexer
//   os braços para experimentar a roupa não faz nada.
// - Depois de uma ação, é preciso baixar as mãos e esperar um instante antes do próximo gesto.

export interface Point {
  x: number;
  y: number;
  visibility?: number;
}

export interface PoseSample {
  nose: Point;
  leftShoulder: Point;
  rightShoulder: Point;
  leftWrist: Point;
  rightWrist: Point;
}

export type GestureMode = "browsing" | "wearing";
export type GestureEvent = "next" | "prev" | "select" | "remove";
export type HoldKind = "next" | "prev" | "confirm";

export interface GestureOutput {
  event: GestureEvent | null;
  /** Gesto em andamento, para a tela mostrar o progresso (0 a 1). null = nenhum. */
  hold: { kind: HoldKind; progress: number } | null;
}

export const GESTURE_TIMING = {
  confirmMs: 1500,
  stepStartMs: 500,
  stepRepeatMs: 900,
  lockoutMs: 1200,
};

const MIN_VISIBILITY = 0.5;
const SHOULDER_MARGIN = 0.04; // fração da altura da imagem
const HEAD_MARGIN = 0.02;

function visible(p: Point): boolean {
  return (p.visibility ?? 1) >= MIN_VISIBILITY;
}

export function createGestureEngine() {
  let holdKind: HoldKind | null = null;
  let holdStart = 0;
  let lastStepAt = 0;
  let lockedUntil = 0;
  let needRelease = false;

  function reset() {
    holdKind = null;
  }

  function update(pose: PoseSample | null, now: number, mode: GestureMode): GestureOutput {
    const none: GestureOutput = { event: null, hold: null };
    if (!pose) {
      reset();
      return none;
    }

    const rightUp =
      visible(pose.rightWrist) &&
      visible(pose.rightShoulder) &&
      pose.rightWrist.y < pose.rightShoulder.y - SHOULDER_MARGIN;
    const leftUp =
      visible(pose.leftWrist) &&
      visible(pose.leftShoulder) &&
      pose.leftWrist.y < pose.leftShoulder.y - SHOULDER_MARGIN;
    const bothOverHead =
      visible(pose.rightWrist) &&
      visible(pose.leftWrist) &&
      visible(pose.nose) &&
      pose.rightWrist.y < pose.nose.y - HEAD_MARGIN &&
      pose.leftWrist.y < pose.nose.y - HEAD_MARGIN;

    if (needRelease) {
      if (!rightUp && !leftUp && !bothOverHead) needRelease = false;
      reset();
      return none;
    }
    if (now < lockedUntil) {
      reset();
      return none;
    }

    if (bothOverHead) {
      if (holdKind !== "confirm") {
        holdKind = "confirm";
        holdStart = now;
      }
      const progress = Math.min(1, (now - holdStart) / GESTURE_TIMING.confirmMs);
      if (progress >= 1) {
        reset();
        lockedUntil = now + GESTURE_TIMING.lockoutMs;
        needRelease = true;
        return { event: mode === "browsing" ? "select" : "remove", hold: null };
      }
      return { event: null, hold: { kind: "confirm", progress } };
    }

    if (mode === "browsing" && rightUp !== leftUp) {
      const kind: HoldKind = rightUp ? "next" : "prev";
      if (holdKind !== kind) {
        holdKind = kind;
        holdStart = now;
        lastStepAt = 0;
      }
      const heldMs = now - holdStart;
      const due = lastStepAt === 0 ? heldMs >= GESTURE_TIMING.stepStartMs : now - lastStepAt >= GESTURE_TIMING.stepRepeatMs;
      if (due) {
        lastStepAt = now;
        return { event: kind, hold: { kind, progress: 0 } };
      }
      const sinceRef = lastStepAt === 0 ? heldMs : now - lastStepAt;
      const span = lastStepAt === 0 ? GESTURE_TIMING.stepStartMs : GESTURE_TIMING.stepRepeatMs;
      return { event: null, hold: { kind, progress: Math.min(1, sinceRef / span) } };
    }

    reset();
    return none;
  }

  return { update };
}
