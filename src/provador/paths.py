"""Caminhos do projeto (raiz, modelos, assets, docs)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
ASSETS = ROOT / "assets"
GARMENTS = ASSETS / "garments"
TEMPLATES = ASSETS / "templates"
DOCS = ROOT / "docs"

POSE_MODEL = MODELS / "pose_landmarker_full.task"
SEG_MODEL = MODELS / "selfie_multiclass_256x256.tflite"

MODEL_URLS = {
    POSE_MODEL: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task",
    SEG_MODEL: "https://storage.googleapis.com/mediapipe-models/image_segmenter/"
    "selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite",
}
