#!/usr/bin/env node
// Auto-hospeda os arquivos do MediaPipe (usado só para detectar presença, hooks/usePersonDetection.ts) em
// public/mediapipe/, para o quiosque não depender de CDNs externas em tempo de execução (CLAUDE.md, seção 4.4
// — "nada de dependência de recursos externos além da Decart"). Mesmo padrão do plano Python anterior
// (tools/download_models.py): baixa uma vez, na configuração; os binários não entram no git (.gitignore).
//
// - O runtime WASM já vem dentro do pacote @mediapipe/tasks-vision (node_modules) — é só copiar.
// - O modelo de pose (.task) não vem no pacote; baixa do Google Cloud Storage uma vez.
//
// Roda automaticamente no "npm install" (hook postinstall). Não falha o install se a rede estiver fora —
// avisa e segue, porque node_modules já foi baixado com sucesso até aqui (rede geralmente disponível), mas
// isso não deve travar quem estiver sem internet num passo posterior.

import { existsSync, mkdirSync, copyFileSync } from "node:fs";
import { createWriteStream } from "node:fs";
import { pipeline } from "node:stream/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const WASM_SRC = path.join(ROOT, "node_modules", "@mediapipe", "tasks-vision", "wasm");
const OUT_DIR = path.join(ROOT, "public", "mediapipe");
const WASM_OUT = path.join(OUT_DIR, "wasm");
const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";
const MODEL_OUT = path.join(OUT_DIR, "pose_landmarker_lite.task");

function copyWasm() {
  if (!existsSync(WASM_SRC)) {
    console.warn(`[setup-mediapipe] ${WASM_SRC} não existe — rode "npm install" antes.`);
    return false;
  }
  mkdirSync(WASM_OUT, { recursive: true });
  const files = ["vision_wasm_internal.js", "vision_wasm_internal.wasm",
    "vision_wasm_nosimd_internal.js", "vision_wasm_nosimd_internal.wasm"];
  for (const f of files) copyFileSync(path.join(WASM_SRC, f), path.join(WASM_OUT, f));
  console.log(`[setup-mediapipe] wasm copiado de node_modules para public/mediapipe/wasm/ (${files.length} arquivos)`);
  return true;
}

async function downloadModel() {
  if (existsSync(MODEL_OUT)) {
    console.log("[setup-mediapipe] pose_landmarker_lite.task já existe, não baixei de novo.");
    return true;
  }
  console.log(`[setup-mediapipe] baixando ${MODEL_URL} ...`);
  try {
    const res = await fetch(MODEL_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    mkdirSync(OUT_DIR, { recursive: true });
    await pipeline(res.body, createWriteStream(MODEL_OUT));
    console.log("[setup-mediapipe] modelo salvo em public/mediapipe/pose_landmarker_lite.task");
    return true;
  } catch (err) {
    console.warn(`[setup-mediapipe] AVISO: não consegui baixar o modelo (${err.message}). A detecção de\n` +
      "  presença vai falhar até isso ser corrigido. Rode de novo com internet: node scripts/setup-mediapipe.mjs");
    return false;
  }
}

const wasmOk = copyWasm();
const modelOk = await downloadModel();
if (!wasmOk || !modelOk) process.exitCode = 0; // aviso, não erro — não quero travar o "npm install" por isso
