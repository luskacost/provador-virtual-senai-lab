"""Worker de pose: MediaPipe PoseLandmarker (VIDEO, full, CPU) em thread própria + filtro One Euro."""

import threading
import time
from dataclasses import dataclass
from typing import Self

import numpy as np

from . import paths
from .capture import CameraThread
from .metrics import LatencyStats, RateCounter
from .oneeuro import OneEuroFilter

# Índices dos landmarks do MediaPipe Pose (33 pontos)
NOSE, L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST = 0, 11, 12, 13, 14, 15, 16
L_HIP, R_HIP = 23, 24

# Parâmetros do One Euro. Pixels: parado ~1 Hz de corte; beta alto o bastante para não arrastar braços.
PX_FILTER = {"min_cutoff": 1.0, "beta": 0.05}
# Mundo em milímetros (metros × 1000), para os mesmos parâmetros terem efeito parecido.
WORLD_FILTER = {"min_cutoff": 1.0, "beta": 0.02}
LOST_RESET_S = 0.5       # sem pessoa por este tempo → zera os filtros (evita "arrastar" da posição antiga)


@dataclass(frozen=True)
class PoseResult:
    """Landmarks de um frame. Coordenadas de imagem NÃO espelhadas (o espelho é só na exibição)."""

    frame_id: int
    t_capture: float
    t_done: float
    image_size: tuple[int, int]     # (largura, altura) do frame
    px: np.ndarray                  # (33, 3) filtrado: x, y em pixels; z na escala de x (menor = mais perto)
    px_raw: np.ndarray              # (33, 3) sem filtro (para medir o jitter)
    world: np.ndarray               # (33, 3) filtrado, metros, origem no centro do quadril
    visibility: np.ndarray          # (33,) 0..1
    inference_ms: float


class PoseWorker:
    """Consome sempre o frame mais recente da câmera; publica o último PoseResult (None = sem pessoa)."""

    def __init__(self, cam: CameraThread, model_path=paths.POSE_MODEL):
        self.cam = cam
        self.model_path = model_path
        self.rate = RateCounter()
        self.inference = LatencyStats()
        self.error: str | None = None
        self._lock = threading.Lock()
        self._result: PoseResult | None = None
        self._result_frame_id = -1
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    def start(self, wait_ready_s: float = 15.0) -> Self:
        self._thread = threading.Thread(target=self._run, name="pose", daemon=True)
        self._thread.start()
        self._ready.wait(wait_ready_s)     # carregar o modelo leva ~1 s; falha cedo se o modelo não abrir
        if self.error:
            raise RuntimeError(self.error)
        return self

    def latest(self) -> tuple[int, PoseResult | None]:
        """(id do último frame processado, resultado ou None se não havia pessoa)."""
        with self._lock:
            return self._result_frame_id, self._result

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)

    def _run(self) -> None:
        try:
            import cv2
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions, vision

            options = vision.PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=vision.RunningMode.VIDEO,
                num_poses=1,
            )
            landmarker = vision.PoseLandmarker.create_from_options(options)
        except Exception as exc:  # noqa: BLE001
            self.error = f"não foi possível iniciar a pose ({exc.__class__.__name__}: {exc})"
            self._ready.set()
            return
        self._ready.set()

        px_filter = OneEuroFilter(**PX_FILTER)
        world_filter = OneEuroFilter(**WORLD_FILTER)
        last_id, last_ts_ms, last_seen = -1, -1, 0.0
        try:
            while not self._stop.is_set():
                frame = self.cam.latest(last_id)
                if frame is None:
                    time.sleep(0.001)
                    continue
                last_id = frame.id
                h, w = frame.image.shape[:2]
                rgb = cv2.cvtColor(frame.image, cv2.COLOR_BGR2RGB)
                ts_ms = max(int(frame.t_capture * 1000), last_ts_ms + 1)   # MediaPipe exige ts crescente
                last_ts_ms = ts_ms

                t0 = time.perf_counter()
                res = landmarker.detect_for_video(mp.Image(mp.ImageFormat.SRGB, rgb), ts_ms)
                infer_s = time.perf_counter() - t0
                self.inference.add(infer_s)

                if not res.pose_landmarks:
                    if frame.t_capture - last_seen > LOST_RESET_S:
                        px_filter.reset()
                        world_filter.reset()
                    self._publish(frame.id, None)
                    continue

                last_seen = frame.t_capture
                lm = res.pose_landmarks[0]
                raw = np.array([[p.x * w, p.y * h, p.z * w] for p in lm], np.float64)
                vis = np.array([p.visibility for p in lm], np.float32)
                world_raw = np.array([[p.x, p.y, p.z] for p in res.pose_world_landmarks[0]], np.float64)
                t = frame.t_capture
                result = PoseResult(
                    frame_id=frame.id,
                    t_capture=frame.t_capture,
                    t_done=time.perf_counter(),
                    image_size=(w, h),
                    px=px_filter(raw, t).astype(np.float32),
                    px_raw=raw.astype(np.float32),
                    world=(world_filter(world_raw * 1000.0, t) / 1000.0).astype(np.float32),
                    visibility=vis,
                    inference_ms=infer_s * 1000.0,
                )
                self._publish(frame.id, result)
        except Exception as exc:  # noqa: BLE001
            self.error = f"a pose parou ({exc.__class__.__name__}: {exc})"
        finally:
            landmarker.close()

    def _publish(self, frame_id: int, result: PoseResult | None) -> None:
        with self._lock:
            self._result_frame_id = frame_id
            self._result = result
        self.rate.tick()

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()
