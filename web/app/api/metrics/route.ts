import { NextResponse } from "next/server";
import { appendSession } from "@/lib/metrics";

// CLAUDE.md 4.5: registra localmente início/fim de cada sessão, duração e peças experimentadas.
// Nunca recebe nem grava vídeo ou imagem — só o corpo pequeno definido em SessionMetric.
export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "JSON inválido" }, { status: 400 });
  }
  try {
    await appendSession(body);
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("Falha ao gravar métricas:", err);
    return NextResponse.json({ error: "falha ao gravar" }, { status: 400 });
  }
}
