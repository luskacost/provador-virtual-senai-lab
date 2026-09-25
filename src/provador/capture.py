"""Captura da webcam em thread própria: o consumidor sempre recebe o frame mais recente."""

import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Self

import numpy as np

from .metrics import RateCounter


@dataclass(frozen=True)
class Frame:
    """Frame BGR (H, W, 3, uint8) e o instante (perf_counter) em que o driver o entregou."""

    id: int
    image: np.ndarray
    t_capture: float


class CameraThread:
    """Lê a webcam num loop dedicado. O consumidor pega o frame mais recente (sem fila, sem atraso
    acumulado); os últimos HISTORY frames ficam disponíveis por id para sincronizar vídeo e pose."""

    HISTORY = 8

    def __init__(self, index: int = 0, width: int = 1280, height: int = 720, fps: int = 30,
                 settings_dialog: bool = False):
        self.index = index
        self.settings_dialog = settings_dialog
        self.width, self.height, self.fps = width, height, fps
        self.capture_rate = RateCounter()
        self._cap = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._frame: Frame | None = None
        self._history: deque[Frame] = deque(maxlen=self.HISTORY)
        self._next_id = 0
        self.error: str | None = None

    def start(self) -> Self:
        """Abre a câmera (falha cedo, com mensagem clara) e inicia a thread de leitura."""
        import cv2

        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        cap = cv2.VideoCapture(self.index, backend)
        if not cap.isOpened():
            raise RuntimeError(f"Webcam {self.index} não abriu (em uso por outro app ou índice errado?)")
        # A ORDEM IMPORTA no DirectShow: com o FOURCC antes da resolução a câmera cai num formato
        # não comprimido e entrega ~10 FPS em 720p. Resolução → FPS → MJPG dá ~30 FPS.
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # O driver DirectShow guarda o modo de exposição entre execuções (outro app ou teste pode ter deixado em
        # manual, e a imagem sai escura): pedir automática garante um estado conhecido.
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
        if self.settings_dialog:
            cap.set(cv2.CAP_PROP_SETTINGS, 1)      # diálogo do driver (DirectShow): compensação de pouca luz etc.
        self._cap = cap
        self._thread = threading.Thread(target=self._run, name="camera", daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        while not self._stop.is_set():
            ok, image = self._cap.read()
            if not ok:
                self.error = "a webcam parou de entregar frames"
                time.sleep(0.05)
                continue
            self.error = None
            t = time.perf_counter()
            with self._lock:
                self._frame = Frame(self._next_id, image, t)
                self._history.append(self._frame)
                self._next_id += 1
            self.capture_rate.tick()

    def latest(self, after_id: int = -1) -> Frame | None:
        """Frame mais recente, ou None se ainda não há um com id > after_id."""
        with self._lock:
            frame = self._frame
        if frame is None or frame.id <= after_id:
            return None
        return frame

    def get(self, frame_id: int) -> Frame | None:
        """Frame com esse id, se ainda estiver no histórico."""
        with self._lock:
            for frame in reversed(self._history):
                if frame.id == frame_id:
                    return frame
        return None

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()
