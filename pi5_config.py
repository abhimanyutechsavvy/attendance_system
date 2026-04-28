# Raspberry Pi 5 Specific Configuration
# This file contains Pi 5 optimized settings

# Camera settings optimized for Pi 5
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 15

# GPIO pins for Pi 5 (BCM numbering)
BUTTON_CONFIRM_PIN = 17
BUTTON_RETRY_PIN = 27
NFC_RST_PIN = 22
NFC_SPI_BUS = 0
NFC_SPI_DEVICE = 0

# Performance settings for Pi 5
MAX_WORKERS = 4
IMAGE_CACHE_SIZE = 50

# Network settings
HOST = '0.0.0.0'
PORT = 5000
DEBUG = False

# Database settings
DB_CONNECTION_POOL = 5

# Face recognition settings optimized for Pi 5
FACE_RECOGNITION_THRESHOLD = 0.6
IMAGE_QUALITY_THRESHOLD = 80
