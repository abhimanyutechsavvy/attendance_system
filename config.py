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

# Manual camera exposure / ISO lock.
# On Raspberry Pi / Linux, many webcams behave better with their own auto
# exposure and white-balance pipeline. Forced manual values can produce the
# green/washed-out frames seen on some UVC devices, so keep locking OFF there
# unless you intentionally tune the values for that exact camera.
#   CAMERA_EXPOSURE: log2 seconds on most UVC webcams via DirectShow.
#                    Typical range -8 (very dark/fast) .. -1 (bright/slow).
#                    -6 is a sane indoor default (~1/64s).
#   CAMERA_GAIN:     0..255 on most UVC cams. Lower = less noise / darker.
#   CAMERA_BRIGHTNESS / CONTRAST / SATURATION: device-specific 0..255.
#   CAMERA_WB_TEMPERATURE: Kelvin, e.g. 4500 indoor, 6500 daylight.
CAMERA_LOCK_SETTINGS = platform.system() == "Windows"
CAMERA_EXPOSURE = -6
CAMERA_GAIN = 50
CAMERA_BRIGHTNESS = 128
CAMERA_CONTRAST = 128
CAMERA_SATURATION = 128
CAMERA_WB_TEMPERATURE = 4500

# Display and matching
DISPLAY_WINDOW_NAME = "Attendance Verification"
MATCH_THRESHOLD = 0.01

# Arduino bridge (set to a serial port string to read RFID + joystick from
# the Arduino sketch in attendance_system_arduino_all_in_one.ino instead of
# the Pi's GPIO/SPI).
# Examples: "COM10" on Windows, "/dev/ttyACM0" on Linux. Leave as None to use
# the Pi-native MFRC522 + GPIO buttons.
ARDUINO_SERIAL_PORT = None
ARDUINO_BAUD_RATE = 9600
