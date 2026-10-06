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

// Segmentação de pessoa (selfie) - só usada no teste isolado de fundo da seção 4.7 (app/teste-fundo/),
// nunca no quiosque principal. Mesmo motivo de auto-hospedar: nada de CDN externa em tempo de execução.
const SEGMENTER_URL =
  "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite";
const SEGMENTER_OUT = path.join(OUT_DIR, "selfie_segmenter.tflite");

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

async function downloadFile(url, out, label) {
  if (existsSync(out)) {
    console.log(`[setup-mediapipe] ${label} já existe, não baixei de novo.`);
    return true;
  }
  console.log(`[setup-mediapipe] baixando ${url} ...`);
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    mkdirSync(OUT_DIR, { recursive: true });
    await pipeline(res.body, createWriteStream(out));
    console.log(`[setup-mediapipe] salvo em public/mediapipe/${path.basename(out)}`);
    return true;
  } catch (err) {
    console.warn(`[setup-mediapipe] AVISO: não consegui baixar ${label} (${err.message}). Rode de novo com\n` +
      "  internet: node scripts/setup-mediapipe.mjs");
    return false;
  }
}

const wasmOk = copyWasm();
const poseOk = await downloadFile(MODEL_URL, MODEL_OUT, "pose_landmarker_lite.task (detecção de presença)");
const segmenterOk = await downloadFile(SEGMENTER_URL, SEGMENTER_OUT, "selfie_segmenter.tflite (teste de fundo)");
if (!wasmOk || !poseOk || !segmenterOk) process.exitCode = 0; // aviso, não erro — não travar o "npm install" por isso
