"""Worker de segmentação: selfie multiclasse (ONNX Runtime; DirectML na GPU, CPU como reserva) em thread própria.

Publica uma máscara RGBA uint8 de 256x256 que cobre o frame inteiro (esticado, igual à entrada do modelo):
R = pele do corpo (braços, mãos) · G = cabelo · B = pele do rosto · A = pessoa (1 - fundo).
A máscara é suavizada no tempo (EMA) para não cintilar.
"""

import threading
import time
from typing import Self

import numpy as np

from . import paths
from .capture import CameraThread
from .metrics import LatencyStats, RateCounter

SIZE = 256
# Classes do modelo: 0 fundo, 1 cabelo, 2 pele do corpo, 3 pele do rosto, 4 roupa, 5 outros
EMA = 0.55                 # peso da máscara nova (maior = responde mais rápido, cintila mais)


def probabilities_to_rgba(probs: np.ndarray) -> np.ndarray:
    """(H, W, 6) probabilidades → (H, W, 4) float: pele do corpo, cabelo, rosto, pessoa."""
    return np.stack([probs[..., 2], probs[..., 1], probs[..., 3], 1.0 - probs[..., 0]], axis=-1)


def softmax(z: np.ndarray) -> np.ndarray:
    e = np.exp(z - z.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def _create_session(model_path):
    """DirectML no adaptador mais rápido (em notebook híbrido o índice da NVIDIA varia); senão, CPU."""
    import onnxruntime as ort

    ort.set_default_logger_severity(3)
    x = np.zeros((1, SIZE, SIZE, 3), np.float32)
    best = None
    if "DmlExecutionProvider" in ort.get_available_providers():
        for device in (0, 1):
            try:
                s = ort.InferenceSession(str(model_path), providers=[("DmlExecutionProvider", {"device_id": device})])
                name = s.get_inputs()[0].name
                s.run(None, {name: x})
                t = time.perf_counter()
                for _ in range(3):
                    s.run(None, {name: x})
                ms = (time.perf_counter() - t) / 3 * 1000
                if best is None or ms < best[1]:
                    best = (s, ms, f"DirectML gpu{device}")
            except Exception:  # noqa: BLE001, S112 — adaptador inexistente: tenta o próximo
                continue
    if best is None:
        best = (ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"]), 0.0, "CPU")
    return best[0], best[2]


class SegWorker:
    def __init__(self, cam: CameraThread, model_path=paths.SEG_ONNX):
        self.cam = cam
        self.model_path = model_path
        self.rate = RateCounter()
        self.inference = LatencyStats()
        self.provider = "?"
        self.error: str | None = None
        self._lock = threading.Lock()
        self._mask: np.ndarray | None = None
        self._mask_id = -1
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, wait_ready_s: float = 20.0) -> Self:
        self._thread = threading.Thread(target=self._run, name="segmentacao", daemon=True)
        self._thread.start()
        self._ready.wait(wait_ready_s)
        if self.error:
            raise RuntimeError(self.error)
        return self

    def latest(self) -> tuple[int, np.ndarray | None]:
        """(contador de máscaras publicadas, máscara RGBA uint8 (256, 256, 4) ou None)."""
        with self._lock:
            return self._mask_id, self._mask

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)

    def _run(self) -> None:
        try:
            import cv2

            if not self.model_path.exists():
                raise FileNotFoundError(f"{self.model_path.name} ausente -> python tools/convert_seg_model.py")
            session, self.provider = _create_session(self.model_path)
            input_name = session.get_inputs()[0].name
        except Exception as exc:  # noqa: BLE001
            self.error = f"não foi possível iniciar a segmentação ({exc.__class__.__name__}: {exc})"
            self._ready.set()
            return
        self._ready.set()

        smooth: np.ndarray | None = None
        last_id, count = -1, 0
        try:
            while not self._stop.is_set():
                frame = self.cam.latest(last_id)
                if frame is None:
                    time.sleep(0.001)
                    continue
                last_id = frame.id
                small = cv2.resize(frame.image, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
                x = cv2.cvtColor(small, cv2.COLOR_BGR2RGB).astype(np.float32)[None] / 255.0
                t0 = time.perf_counter()
                logits = session.run(None, {input_name: x})[0][0]
                self.inference.add(time.perf_counter() - t0)
                rgba = probabilities_to_rgba(softmax(logits))
                smooth = rgba if smooth is None else EMA * rgba + (1.0 - EMA) * smooth
                mask = np.clip(smooth * 255.0 + 0.5, 0, 255).astype(np.uint8)
                count += 1
                with self._lock:
                    self._mask, self._mask_id = mask, count
                self.rate.tick()
        except Exception as exc:  # noqa: BLE001
            self.error = f"a segmentação parou ({exc.__class__.__name__}: {exc})"
