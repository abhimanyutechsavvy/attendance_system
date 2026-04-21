# Smart Attendance System

This is a dual-verification smart attendance system for Raspberry Pi 5.
It uses NFC tag scanning and ID card image recognition to verify attendance.

## Features
- NFC-based student identification using RC522
- ID card image capture with camera
- Stored image comparison for verification
- Manual confirmation with two buttons: green = confirm, red = retry
- Attendance logging in SQLite database

## Hardware
- Raspberry Pi 5 (16GB)
- RC522 NFC reader
- NFC / RFID ID cards
- Camera module or USB webcam
- Display screen
- Two physical buttons (green confirm, red retry)
- Jumper wires
- 1K ohm resistor for RC522 wiring

## Project Structure
- `main.py` — application entry point
- `config.py` — hardware and path settings
- `database.py` — SQLite student and attendance store
- `hardware.py` — NFC reader and button interface
- `camera.py` — camera capture interface
- `image_processing.py` — image comparison utilities
- `requirements.txt` — Python dependencies

## Setup
1. Create the database and add the sample student by running:
   ```bash
   python main.py --init-db
   ```
2. The sample stored image is created automatically as `data/stored_ids/student1.jpg`.

## Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python main.py
```

## Notes
- The camera captures and compares live ID card images.
- If the live image matches the stored image, press the green button to record attendance.
- Press the red button to retry if the match is wrong.
