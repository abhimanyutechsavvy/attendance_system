import cv2
import platform

from config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS


class CameraManager:
    def __init__(self, camera_index: int = CAMERA_INDEX):
        self.camera_index = camera_index
        self.camera = None

        # Try different backends based on platform
        if platform.system() == "Windows":
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF]
        else:  # Linux (Raspberry Pi)
            backends = [cv2.CAP_V4L2, cv2.CAP_GSTREAMER]

        for backend in backends:
            try:
                self.camera = cv2.VideoCapture(self.camera_index, backend)
                if self.camera.isOpened():
                    # Set Pi 5 optimized camera properties
                    if platform.system() == "Linux":
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                        self.camera.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
                        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
                    print(f"Camera opened successfully with backend {backend}")
                    break
            except:
                continue

        # Fallback to default if no backend worked
        if not self.camera or not self.camera.isOpened():
            self.camera = cv2.VideoCapture(self.camera_index)

        if not self.camera.isOpened():
            raise RuntimeError(f"Unable to open camera index {self.camera_index}. Check /dev/video* on Linux or camera permissions.")

    def capture(self):
        print("Capturing live image from camera...")
        
        # Allow camera to stabilize and adjust settings
        import time
        time.sleep(0.5)  # 500ms delay for camera stabilization
        
        for attempt in range(3):
            ret, frame = self.camera.read()
            if ret:
                return frame
            print("Camera capture failed, retrying...")
            time.sleep(0.2)  # Brief delay between retries
        raise RuntimeError("Camera failed to capture an image.")

    def release(self):
        self.camera.release()
