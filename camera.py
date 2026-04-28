import cv2
import platform
import numpy as np

from config import (
    CAMERA_BRIGHTNESS,
    CAMERA_CONTRAST,
    CAMERA_EXPOSURE,
    CAMERA_FPS,
    CAMERA_GAIN,
    CAMERA_HEIGHT,
    CAMERA_INDEX,
    CAMERA_LOCK_SETTINGS,
    CAMERA_SATURATION,
    CAMERA_WB_TEMPERATURE,
    CAMERA_WIDTH,
)


def _try_set(camera, prop, value, label):
    """Best-effort property write. Driver may silently ignore it."""
    try:
        ok = camera.set(prop, value)
        actual = camera.get(prop)
        print(f"  [cam] {label}: requested={value} actual={actual} {'OK' if ok else 'IGNORED'}")
        return ok
    except Exception as exc:
        print(f"  [cam] {label}: failed ({exc})")
        return False


def _stream_alive(camera, attempts: int = 5) -> bool:
    """Return True if the camera can still produce a frame."""
    import time
    for _ in range(attempts):
        if camera.grab():
            return True
        time.sleep(0.05)
    return False


def lock_camera_settings(camera):
    """Disable auto-exposure / auto-WB / autofocus and pin manual values
    so the webcam stops re-calibrating between captures.

    Some backends (notably Windows MSMF) interpret EXPOSURE in different
    units than DSHOW, and writing the wrong value can stop the stream.
    We test the stream after each risky write and roll the property back
    to auto if the camera dies.
    """
    print("[cam] Locking exposure / white balance / gain ...")

    manual_ae = 0.25 if platform.system() == "Windows" else 1
    auto_ae = 0.75 if platform.system() == "Windows" else 3

    _try_set(camera, cv2.CAP_PROP_AUTO_EXPOSURE, manual_ae, "AUTO_EXPOSURE=manual")
    _try_set(camera, cv2.CAP_PROP_EXPOSURE, CAMERA_EXPOSURE, "EXPOSURE")
    if not _stream_alive(camera):
        print("  [cam] Manual exposure broke the stream - reverting to AUTO_EXPOSURE.")
        _try_set(camera, cv2.CAP_PROP_AUTO_EXPOSURE, auto_ae, "AUTO_EXPOSURE=auto (rollback)")
        # Drain the recovery
        _stream_alive(camera, attempts=10)

    _try_set(camera, cv2.CAP_PROP_GAIN, CAMERA_GAIN, "GAIN")
    _try_set(camera, cv2.CAP_PROP_AUTO_WB, 0, "AUTO_WB=off")
    _try_set(camera, cv2.CAP_PROP_WB_TEMPERATURE, CAMERA_WB_TEMPERATURE, "WB_TEMPERATURE")
    _try_set(camera, cv2.CAP_PROP_BRIGHTNESS, CAMERA_BRIGHTNESS, "BRIGHTNESS")
    _try_set(camera, cv2.CAP_PROP_CONTRAST, CAMERA_CONTRAST, "CONTRAST")
    _try_set(camera, cv2.CAP_PROP_SATURATION, CAMERA_SATURATION, "SATURATION")

    try:
        camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
    except Exception:
        pass


def enable_camera_auto_settings(camera):
    """Return the webcam to its own auto pipeline."""
    print("[cam] Enabling camera auto exposure / auto white balance.")
    auto_ae = 0.75 if platform.system() == "Windows" else 3
    _try_set(camera, cv2.CAP_PROP_AUTO_EXPOSURE, auto_ae, "AUTO_EXPOSURE=auto")
    try:
        _try_set(camera, cv2.CAP_PROP_AUTO_WB, 1, "AUTO_WB=on")
    except Exception:
        pass
    try:
        camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
    except Exception:
        pass


def _frame_looks_corrupted(frame) -> bool:
    """Heuristic: catch heavily clipped and strongly color-skewed frames."""
    if frame is None or frame.size == 0:
        return True

    channel_means = frame.reshape(-1, 3).mean(axis=0)
    overall_mean = float(channel_means.mean())
    if overall_mean < 1:
        return True

    brightness = frame.mean(axis=2)
    clipped_ratio = float((brightness > 245).mean())
    darkest_ratio = float((brightness < 10).mean())
    color_spread = float(channel_means.max() / max(channel_means.min(), 1.0))

    return clipped_ratio > 0.18 or darkest_ratio > 0.40 or color_spread > 1.8


class CameraManager:
    def __init__(self, camera_index: int = CAMERA_INDEX):
        self.camera_index = camera_index
        self.camera = None
        self.using_manual_settings = False

        # Try different backends based on platform
        if platform.system() == "Windows":
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF]
        else:  # Linux (Raspberry Pi)
            backends = [cv2.CAP_V4L2, cv2.CAP_GSTREAMER]

        for backend in backends:
            try:
                self.camera = cv2.VideoCapture(self.camera_index, backend)
                if self.camera.isOpened():
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                    self.camera.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
                    self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                    if CAMERA_LOCK_SETTINGS:
                        lock_camera_settings(self.camera)
                        self.using_manual_settings = True

                    print(f"Camera opened successfully with backend {backend}")
                    break
            except Exception:
                continue

        # Fallback to default if no backend worked
        if not self.camera or not self.camera.isOpened():
            self.camera = cv2.VideoCapture(self.camera_index)
            if self.camera and self.camera.isOpened() and CAMERA_LOCK_SETTINGS:
                lock_camera_settings(self.camera)
                self.using_manual_settings = True

        if not self.camera.isOpened():
            raise RuntimeError(
                f"Unable to open camera index {self.camera_index}. "
                "Check /dev/video* on Linux or camera permissions."
            )

        # Warm-up: many UVC cams need several frames to honor manual
        # exposure / WB registers. Pull and discard so the next capture()
        # returns a frame taken with the locked settings.
        import time
        for _ in range(10):
            self.camera.grab()
            time.sleep(0.03)

    def read_live_frame(self):
        """Read one frame without flushing buffers; suitable for continuous preview."""
        ret, frame = self.camera.read()
        if not ret:
            return None

        if self.using_manual_settings and _frame_looks_corrupted(frame):
            print("[cam] Captured frame looks overexposed or color-skewed; falling back to auto settings.")
            enable_camera_auto_settings(self.camera)
            self.using_manual_settings = False
            return None

        return frame

    def capture(self):
        print("Capturing live image from camera...")
        import time

        # Flush stale buffered frames for manual one-shot captures. The web
        # app uses read_live_frame() through a background feed instead.
        for _ in range(5):
            self.camera.grab()
            time.sleep(0.03)

        for attempt in range(3):
            frame = self.read_live_frame()
            if frame is not None:
                return frame
            print("Camera capture failed, retrying...")
            time.sleep(0.2)
        raise RuntimeError("Camera failed to capture an image.")

    def release(self):
        if self.camera is not None:
            self.camera.release()
