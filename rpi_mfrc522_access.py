import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time

# Raspberry Pi 5 pin mapping
# Use BCM numbering
LASER_PIN = 17  # physical pin 11
TARGET_ID = "922422290"

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(LASER_PIN, GPIO.OUT)
GPIO.output(LASER_PIN, GPIO.LOW)

# Initialize RFID reader using SPI0 CE0 by default
rfid = MFRC522()

print("Scan RFID...")

try:
    while True:
        # Look for new cards
        (status, TagType) = rfid.MFRC522_Request(rfid.PICC_REQIDL)
        if status != rfid.MI_OK:
            time.sleep(0.1)
            continue

        # Get the UID of the card
        (status, uid) = rfid.MFRC522_Anticoll()
        if status != rfid.MI_OK:
            continue

        uid_str = "".join(str(x) for x in uid)
        print(f"UID: {uid_str}")

        if uid_str == TARGET_ID:
            print("✅ Access Granted")
            GPIO.output(LASER_PIN, GPIO.HIGH)
            time.sleep(2)
            GPIO.output(LASER_PIN, GPIO.LOW)
        else:
            print("❌ Access Denied")

        # Stop reading this card until it is removed
        rfid.MFRC522_Halt()
        time.sleep(1)

except KeyboardInterrupt:
    print("\nExiting...")

finally:
    GPIO.cleanup()