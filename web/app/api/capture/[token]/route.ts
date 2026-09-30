import { get } from "@/lib/capture-store";

const EXPIRED_HTML = `<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Link expirado</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{font-family:system-ui,sans-serif;background:#0a0a0a;color:#fff;display:flex;
height:100vh;align-items:center;justify-content:center;text-align:center;padding:2rem}</style>
</head><body><div><h1>Este link expirou</h1>
<p>Volte ao quiosque e toque em "Tirar foto" ou "Gravar vídeo" de novo.</p></div></body></html>`;

// Entrega a foto/vídeo capturado ao celular do visitante (escaneou o QR code de /api/capture).
// Não some no primeiro acesso (ver capture-store.ts) - só expira por tempo.
export async function GET(_request: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const entry = get(token);
  if (!entry) {
    return new Response(EXPIRED_HTML, {
      status: 404,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }
  const filename = entry.contentType === "image/jpeg" ? "senai-lab-fashion.jpg" : "senai-lab-fashion.webm";
  return new Response(new Uint8Array(entry.data), {
    headers: {
      "Content-Type": entry.contentType,
      "Content-Disposition": `attachment; filename="${filename}"`,
      "Cache-Control": "no-store",
    },
  });
}
