import { NextResponse } from "next/server";
import QRCode from "qrcode";
import { put, TTL_SECONDS } from "@/lib/capture-store";

// Recebe a foto/vídeo capturado no navegador do visitante, guarda só na memória (lib/capture-store.ts) e
// devolve um QR code para o celular DELE baixar — nunca fica salvo pelo estande (CLAUDE.md 4.5/4.6).
//
// IMPORTANTE para o dia do evento: a URL do QR code usa o mesmo host que o navegador do quiosque usou
// para abrir a página. Se o quiosque abrir por "localhost:3000", o QR vira um link que só a própria
// máquina do quiosque alcança — inútil para o celular do visitante. O quiosque precisa abrir pelo IP da
// máquina na rede do evento (ex.: http://192.168.1.50:3000), com o celular do visitante na mesma rede.
export async function POST(request: Request) {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return NextResponse.json({ error: "corpo inválido" }, { status: 400 });
  }
  const file = form.get("file");
  const kind = form.get("kind");
  if (!(file instanceof Blob) || (kind !== "foto" && kind !== "video")) {
    return NextResponse.json({ error: "corpo inválido" }, { status: 400 });
  }
  if (file.size === 0 || file.size > 60 * 1024 * 1024) {
    return NextResponse.json({ error: "tamanho de arquivo inválido" }, { status: 400 });
  }

  const buffer = Buffer.from(await file.arrayBuffer());
  const contentType = kind === "foto" ? "image/jpeg" : "video/webm";
  const token = put(buffer, contentType);
  const url = new URL(`/api/capture/${token}`, request.url).toString();

  try {
    const qrDataUrl = await QRCode.toDataURL(url, { margin: 1, width: 320 });
    return NextResponse.json({ url, qrDataUrl, expiresInSeconds: TTL_SECONDS });
  } catch (err) {
    console.error("Falha ao gerar QR code:", err);
    return NextResponse.json({ error: "falha ao gerar QR code" }, { status: 500 });
  }
}
