import threading
import time
import cv2
import numpy as np
import pytest
from uamc_io.camera_capture import CameraCapture

class Fake:
    def __init__(self, mismatch=False):
        self.props = {}
        self.block = threading.Event()
        self.released = False
        self.mismatch = mismatch
        self.reads = 0
    def isOpened(self):
        return True
    def set(self, prop, value):
        self.props[prop] = value
        return True
    def get(self, prop):
        return self.props[prop] + (1 if self.mismatch and prop == cv2.CAP_PROP_FRAME_WIDTH else 0)
    def read(self):
        self.reads += 1
        if self.reads > 1:
            self.block.wait(2)
            return False, None
        return True, np.zeros((3, 4, 3), dtype=np.uint8)
    def release(self):
        self.released = True

def wait_for(predicate):
    deadline = time.monotonic() + 1
    while not predicate() and time.monotonic() < deadline:
        time.sleep(.005)
    assert predicate()

def test_settings_single_slot_and_blocked_cleanup():
    fake = Fake()
    calls = []
    def factory(*args):
        calls.append(args)
        return fake
    cap = CameraCapture("/dev/v4l/by-id/test", 4, 3, 30.0, "MJPG", lambda: 123, factory)
    try:
        wait_for(lambda: cap.last_read is not None)
        assert calls == [("/dev/v4l/by-id/test", cv2.CAP_V4L2)]
        assert fake.props[cv2.CAP_PROP_BUFFERSIZE] == 1
        assert fake.props[cv2.CAP_PROP_FPS] == 30
        assert cap.poll(1, 1, 1)[2] == 123
        assert cap.poll(1, 1, 1) is None
        assert cap.close(.01) is False
        fake.block.set()
        assert cap.close(1)
        assert fake.released
    finally:
        fake.block.set()
        cap.close(1)

def test_expired_and_timeout():
    fake = Fake()
    cap = CameraCapture("device", 4, 3, 30.0, "MJPG", lambda: 1, lambda *_: fake)
    try:
        wait_for(lambda: cap.last_read is not None)
        time.sleep(.03)
        assert cap.poll(1, 1, .01) is None
        with pytest.raises(RuntimeError, match="frame timeout"):
            cap.poll(1, .01, 1)
    finally:
        fake.block.set()
        cap.close(1)

def test_negotiation_mismatch():
    fake = Fake(mismatch=True)
    cap = CameraCapture("device", 4, 3, 30.0, "MJPG", lambda: 1, lambda *_: fake)
    try:
        wait_for(lambda: cap.error is not None)
        with pytest.raises(RuntimeError, match="negotiation mismatch"):
            cap.poll(1, 1, 1)
        assert fake.released
    finally:
        cap.close(1)

def test_startup_timeout():
    block = threading.Event()
    def factory(*_):
        block.wait(1)
        return Fake()
    cap = CameraCapture("device", 4, 3, 30.0, "MJPG", lambda: 1, factory)
    try:
        time.sleep(.02)
        with pytest.raises(RuntimeError, match="startup timeout"):
            cap.poll(.01, 1, 1)
    finally:
        block.set()
        cap.close(.1)


def test_release_error_preserves_capture_error():
    class BrokenRelease(Fake):
        def release(self):
            raise RuntimeError("release broke")
    fake = BrokenRelease(mismatch=True)
    cap = CameraCapture("device", 4, 3, 30.0, "MJPG", lambda: 1, lambda *_: fake)
    assert cap.close(1)
    with pytest.raises(RuntimeError, match="negotiation mismatch.*release failed"):
        cap.poll(1, 1, 1)
