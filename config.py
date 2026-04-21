from pathlib import Path
import platform

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
STORED_IMAGES_DIR = DATA_DIR / "stored_ids"
DB_PATH = DATA_DIR / "attendance.db"

# Load Pi 5 specific config if running on Linux (Raspberry Pi)
if platform.system() == 'Linux':
    try:
        from pi5_config import *
        print("Loaded Raspberry Pi 5 optimized configuration")
    except ImportError:
        print("Pi 5 config not found, using default settings")
else:
    # Default settings for development (Windows/Mac)
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    CAMERA_FPS = 15
    MAX_WORKERS = 2
    IMAGE_CACHE_SIZE = 20
    FACE_RECOGNITION_THRESHOLD = 0.7
    IMAGE_QUALITY_THRESHOLD = 60

# Hardware pins (BCM numbering) - Default values
BUTTON_CONFIRM_PIN = getattr(__import__('__main__', fromlist=['BUTTON_CONFIRM_PIN']), 'BUTTON_CONFIRM_PIN', 17)
BUTTON_RETRY_PIN = getattr(__import__('__main__', fromlist=['BUTTON_RETRY_PIN']), 'BUTTON_RETRY_PIN', 27)

# NFC reader settings
NFC_RST_PIN = getattr(__import__('__main__', fromlist=['NFC_RST_PIN']), 'NFC_RST_PIN', 22)
NFC_SPI_BUS = getattr(__import__('__main__', fromlist=['NFC_SPI_BUS']), 'NFC_SPI_BUS', 0)
NFC_SPI_DEVICE = getattr(__import__('__main__', fromlist=['NFC_SPI_DEVICE']), 'NFC_SPI_DEVICE', 0)

# Camera
CAMERA_INDEX = 0

# Display and matching
DISPLAY_WINDOW_NAME = "Attendance Verification"
MATCH_THRESHOLD = 0.01
