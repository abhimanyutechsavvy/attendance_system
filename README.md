# Smart Attendance System

Dual-verification attendance system for Raspberry Pi 5. It combines NFC/RFID tag scanning with camera-based image verification to make attendance faster, harder to fake, and easier to manage.

## Project Goal

Each student carries an ID card with an embedded NFC tag. The system:

1. reads the student's NFC/RFID tag,
2. captures an image using the camera,
3. compares the captured image with the stored record,
4. lets the user confirm or retry,
5. stores attendance in SQLite.

This dual-verification flow reduces proxy attendance and improves reliability.

## Main Features

- NFC/RFID identification with RC522
- Camera capture and stored image comparison
- Web dashboard for verification, student management, and attendance history
- Hardware CLI mode for direct Pi usage with buttons
- Duplicate-attendance protection for the same student on the same day
- SQLite-based local storage
- Raspberry Pi 5 setup and deployment scripts

## Hardware

- Raspberry Pi 5
- RC522 NFC/RFID reader
- NFC/RFID student ID cards
- Camera module or USB webcam
- Display screen
- Two physical buttons:
  - green = confirm
  - red = retry
- Jumper wires
- 1 kOhm resistor for RC522 wiring
- Optional Arduino or ESP32 for supporting hardware integrations

## Project Structure

- `app.py` - Flask web application and API
- `main.py` - hardware-first attendance loop for the Pi
- `config.py` - shared configuration and Pi-specific settings
- `database.py` - SQLite database helper
- `hardware.py` - RC522 and GPIO button handling
- `camera.py` - camera capture helpers
- `image_processing.py` - ORB image comparison logic
- `joystick.py` - optional Arduino joystick keyboard bridge
- `arduino_rfid_serial.py` - serial monitor for the combined Arduino RC522 and joystick bridge
- `attendance_system_arduino_all_in_one.ino` - single Arduino sketch for RC522 plus joystick over one USB serial link
- `joystick_arduino.ino` - older joystick-only sketch
- `arduino_rfid_bridge.ino` - older combined bridge sketch
- `web/` - dashboard templates and static assets
- `pi_setup.sh` - Raspberry Pi setup script
- `RPI5_DEPLOYMENT_GUIDE.md` - Raspberry Pi deployment notes

## Raspberry Pi Setup

```bash
cd ~/smart-attendance-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Enable SPI for the RC522:

```bash
sudo raspi-config
```

Then enable `Interface Options > SPI`.

## Initialize the Database

```bash
python3 main.py --init-db
```

This creates `data/attendance.db` and a sample stored image at `data/stored_ids/student1.jpg`.

## Run the Web App

```bash
python3 app.py
```

Open:

- `http://127.0.0.1:5000` on the Pi
- `http://<pi-ip>:5000` from another device on the same network

## Run the Hardware Flow

```bash
python3 main.py
```

This mode uses:

- RC522 scan input
- live camera capture
- physical confirm/retry buttons

If the Pi hardware modules are unavailable, the code falls back to safe simulated input where possible.

## Optional Joystick Bridge

Upload `joystick_arduino.ino` to the Arduino, then run:

```bash
python3 joystick.py --port /dev/ttyACM0
```

Use the actual device name shown by:

```bash
ls /dev/ttyACM* /dev/ttyUSB*
```

## Single Arduino Upload

If you are using one Arduino for the attendance system, upload `attendance_system_arduino_all_in_one.ino`. This single sketch already includes both RFID and joystick support and sends:

- `RFID:<uid>` when a card is scanned
- `JOY:x,y,button` for joystick state

Use these pin mappings in the sketch:

- RC522 `SS/SDA` -> `D10`
- RC522 `RST` -> `D9`
- Joystick `VRx` -> `A0`
- Joystick `VRy` -> `A1`
- Joystick `SW` -> `D2`

You can monitor the combined serial output with:

```bash
python3 arduino_rfid_serial.py
```

## Notes

- Attendance is only marked once per student per day.
- Student images are stored in `data/stored_ids/`.
- The web dashboard supports adding students, viewing logs, and verification from the browser.
