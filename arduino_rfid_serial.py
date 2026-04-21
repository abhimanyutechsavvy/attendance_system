import time

import serial

SERIAL_PORT = "/dev/ttyACM0"  # Update if your Arduino appears on a different device
BAUD_RATE = 9600


def main():
    print("Opening serial port", SERIAL_PORT)
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        time.sleep(2)
        print("Arduino bridge connected")

        while True:
            raw = ser.readline().decode("utf-8", errors="ignore").strip()
            if not raw:
                continue

            if raw.startswith("RFID:"):
                uid = raw.split(":", 1)[1].strip()
                print(f"RFID UID read: {uid}")
            elif raw.startswith("JOY:"):
                payload = raw.split(":", 1)[1].strip()
                print(f"Joystick state: {payload}")
            elif raw.startswith("SYSTEM:"):
                print(f"Bridge status: {raw.split(':', 1)[1].strip()}")
            else:
                print(f"Arduino: {raw}")


if __name__ == "__main__":
    main()
