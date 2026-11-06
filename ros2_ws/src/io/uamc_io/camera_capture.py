"""Single-slot bounded-consumer camera acquisition; the worker owns the device."""
import math
import threading
import time
import cv2

class CameraCapture:
    def __init__(self, device, width, height, fps, fourcc, stamp, capture_factory=None):
        self.device, self.width, self.height = device, width, height
        self.fps, self.fourcc, self.stamp = fps, fourcc, stamp
        self.factory = capture_factory or cv2.VideoCapture
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.started = time.monotonic()
        self.last_read = None
        self.slot = None
        self.error = None
        self.negotiated = None
        self.thread = threading.Thread(target=self._run, daemon=True, name="camera-acquisition")
        self.thread.start()
    def _run(self):
        cap = None
        try:
            cap = self.factory(self.device, cv2.CAP_V4L2)
            if not cap.isOpened():
                raise RuntimeError("camera open failed")
            for prop, value in ((cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.fourcc)),
                                (cv2.CAP_PROP_BUFFERSIZE, 1),
                                (cv2.CAP_PROP_FRAME_WIDTH, self.width),
                                (cv2.CAP_PROP_FRAME_HEIGHT, self.height),
                                (cv2.CAP_PROP_FPS, self.fps)):
                cap.set(prop, value)
            negotiated = tuple(cap.get(p) for p in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT,
                                                     cv2.CAP_PROP_FPS, cv2.CAP_PROP_FOURCC))
            if not all(math.isfinite(x) for x in negotiated):
                raise RuntimeError("camera returned non-finite negotiated properties")
            if negotiated[0] != self.width or negotiated[1] != self.height or int(negotiated[3]) != cv2.VideoWriter_fourcc(*self.fourcc):
                raise RuntimeError(f"camera negotiation mismatch: {negotiated}")
            with self.lock:
                self.negotiated = negotiated
            while not self.stop_event.is_set():
                ok, frame = cap.read()
                received = time.monotonic()
                stamp = self.stamp()
                if self.stop_event.is_set():
                    break
                if not ok or frame is None:
                    raise RuntimeError("camera read failed")
                if (frame.dtype.name != "uint8" or frame.ndim != 3 or
                        frame.shape != (self.height, self.width, 3)):
                    raise RuntimeError("camera frame format or dimensions mismatch")
                with self.lock:
                    self.last_read = received
                    self.slot = (frame, received, stamp)
        except Exception as exc:
            with self.lock:
                self.error = str(exc)
                self.slot = None
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception as exc:
                    with self.lock:
                        self.error = (f"{self.error}; camera release failed: {exc}"
                                      if self.error else f"camera release failed: {exc}")
                        self.slot = None
    def poll(self, startup_timeout, frame_timeout, max_age):
        now = time.monotonic()
        with self.lock:
            if self.error:
                raise RuntimeError(self.error)
            if self.last_read is None:
                if now - self.started > startup_timeout:
                    raise RuntimeError("camera startup timeout")
                return None
            if now - self.last_read > frame_timeout:
                raise RuntimeError("camera frame timeout")
            result, self.slot = self.slot, None
        if result is not None and now - result[1] <= max_age:
            return result
        return None
    def close(self, timeout=0.2):
        self.stop_event.set()
        self.thread.join(timeout)
        return not self.thread.is_alive()
