// Métricas locais (CLAUDE.md 4.5): início/fim de cada sessão, duração, peças experimentadas — nunca vídeo
// ou imagem do visitante. Só server-side (usa "fs"); importar apenas de Route Handlers ou Server Components.
import { promises as fs } from "fs";
import path from "path";
import { ForceEndReason } from "@/hooks/useSessionTimer";

const METRICS_DIR = path.join(process.cwd(), "data");
const METRICS_FILE = path.join(METRICS_DIR, "metricas.json");

/** "pessoa_saiu": o visitante foi embora por conta própria (não é um encerramento forçado do timer). */
export type SessionEndReason = ForceEndReason | "pessoa_saiu";

export interface SessionMetric {
  startedAt: string; // ISO 8601
  endedAt: string; // ISO 8601
  durationSeconds: number;
  endReason: SessionEndReason;
  /** ids do catalogo, na ordem em que foram experimentados (repetições contam: reforça engajamento). */
  products: string[];
}

function isSessionMetric(body: unknown): body is SessionMetric {
  if (!body || typeof body !== "object") return false;
  const b = body as Record<string, unknown>;
  return (
    typeof b.startedAt === "string" &&
    typeof b.endedAt === "string" &&
    typeof b.durationSeconds === "number" &&
    Number.isFinite(b.durationSeconds) &&
    typeof b.endReason === "string" &&
    Array.isArray(b.products) &&
    b.products.every((p) => typeof p === "string")
  );
}

async function readAll(): Promise<SessionMetric[]> {
  try {
    const raw = await fs.readFile(METRICS_FILE, "utf-8");
    const data = JSON.parse(raw);
    return Array.isArray(data) ? (data as SessionMetric[]) : [];
  } catch (err) {
    if ((err as NodeJS.ErrnoException)?.code === "ENOENT") return [];
    throw err;
  }
}

// Fila simples em memória: evita que duas escritas simultâneas leiam o arquivo ao mesmo tempo e uma
// sobrescreva a outra. O quiosque só tem uma sessão ativa por vez, então isso é mais uma rede de segurança
// do que uma necessidade real.
let writeQueue: Promise<unknown> = Promise.resolve();

/** Valida e acrescenta um registro de sessão a data/metricas.json (cria a pasta/arquivo se faltar). */
export async function appendSession(body: unknown): Promise<void> {
  if (!isSessionMetric(body)) {
    throw new Error("registro de sessão inválido");
  }
  const session = body;
  const task = writeQueue.then(async () => {
    const all = await readAll();
    all.push(session);
    await fs.mkdir(METRICS_DIR, { recursive: true });
    await fs.writeFile(METRICS_FILE, JSON.stringify(all, null, 2), "utf-8");
  });
  writeQueue = task.catch(() => {}); // uma escrita que falhou não deve travar as próximas
  await task;
}

export async function loadSessions(): Promise<SessionMetric[]> {
  return readAll();
}

export interface MetricsSummary {
  totalSessions: number;
  averageDurationSeconds: number;
  endReasonCounts: Record<string, number>;
  /** Contagem de vezes que cada peça foi experimentada, da mais para a menos popular. */
  productRanking: { id: string; count: number }[];
}

export function summarize(sessions: SessionMetric[]): MetricsSummary {
  const totalSessions = sessions.length;
  const averageDurationSeconds = totalSessions
    ? sessions.reduce((sum, s) => sum + s.durationSeconds, 0) / totalSessions
    : 0;
  const endReasonCounts: Record<string, number> = {};
  const productCounts = new Map<string, number>();
  for (const s of sessions) {
    endReasonCounts[s.endReason] = (endReasonCounts[s.endReason] ?? 0) + 1;
    for (const id of s.products) productCounts.set(id, (productCounts.get(id) ?? 0) + 1);
  }
  const productRanking = [...productCounts.entries()]
    .map(([id, count]) => ({ id, count }))
    .sort((a, b) => b.count - a.count);
  return { totalSessions, averageDurationSeconds, endReasonCounts, productRanking };
}
