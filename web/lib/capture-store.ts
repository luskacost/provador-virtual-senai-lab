// Guarda a foto/vídeo capturado SÓ NA MEMÓRIA do processo, por um tempo curto — nunca em disco, nunca em
// data/. É o que torna a funcionalidade de foto/vídeo compatível com "não armazenado pelo estande": o
// arquivo existe só enquanto alguém não escaneou o QR code (ou até expirar), depois some.
//
// Também por isso, isto só funciona com o servidor rodando como UM processo único e persistente
// (`next start` numa máquina, como é o caso do quiosque) — não funcionaria num deploy serverless/multi-
// instância, onde cada requisição pode cair num processo diferente sem essa memória.
import { randomUUID } from "node:crypto";

const TTL_MS = 10 * 60 * 1000; // 10 minutos: dá tempo de sobra para escanear o QR code e baixar

interface Entry {
  data: Buffer;
  contentType: string;
  expiresAt: number;
}

const store = new Map<string, Entry>();

function sweepExpired(): void {
  const now = Date.now();
  for (const [token, entry] of store) {
    if (entry.expiresAt < now) store.delete(token);
  }
}

// Limpeza periódica para o Map não crescer sem limite se ninguém escanear o QR code de uma captura.
setInterval(sweepExpired, 60_000);

export function put(data: Buffer, contentType: string): string {
  sweepExpired();
  const token = randomUUID();
  store.set(token, { data, contentType, expiresAt: Date.now() + TTL_MS });
  return token;
}

/** Não apaga no primeiro acesso de propósito: um prefetch do navegador/antivírus no celular do visitante
 * poderia "gastar" o link antes da pessoa ver a imagem. A expiração por tempo (sweepExpired) já garante
 * que não fica guardado por muito tempo. */
export function get(token: string): Entry | null {
  const entry = store.get(token);
  if (!entry || entry.expiresAt < Date.now()) return null;
  return entry;
}

export const TTL_SECONDS = TTL_MS / 1000;
