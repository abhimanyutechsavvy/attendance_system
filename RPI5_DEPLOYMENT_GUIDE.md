# Raspberry Pi 5 Deployment Guide - Smart Attendance System

## Quick Start

```bash
# 1. Transfer project to the Pi
scp -r smart-attendance-system pi@192.168.1.100:~

# 2. SSH into the Pi and run setup
ssh pi@192.168.1.100
cd ~/smart-attendance-system
chmod +x pi_setup.sh pi5_optimize.sh pi5_quickref.sh
./pi_setup.sh

# 3. Log out and back in once so group changes apply
# 4. Start the service
sudo systemctl start attendance

# 5. Open the web interface
# http://<pi-ip>:5000
```

## Hardware Requirements

### Raspberry Pi 5

- Raspberry Pi 5
- MicroSD card, 32 GB or larger
- Reliable power supply
- Cooling recommended for long use

### Camera

- USB webcam, or
- Raspberry Pi camera module

### NFC Reader

- MFRC522 RFID/NFC module
- SPI connection enabled on the Pi

### Buttons

- Green confirm button on GPIO 17
- Red retry button on GPIO 27

## Hardware Wiring

### RC522 to Raspberry Pi 5

```text
MFRC522     | Raspberry Pi 5
----------- | ----------------
VCC         | 3.3V (Pin 1)
GND         | GND (Pin 6)
RST         | GPIO 22 (Pin 15)
IRQ         | Not connected
MISO        | GPIO 9 (Pin 21)
MOSI        | GPIO 10 (Pin 19)
SCK         | GPIO 11 (Pin 23)
SDA / SS    | GPIO 8 (Pin 24)
```

### Buttons

```text
Confirm button | GPIO 17 (Pin 11)
Retry button   | GPIO 27 (Pin 13)
Ground         | GND (Pin 9)
```

## Software Setup

### 1. Enable Interfaces

```bash
sudo raspi-config
```

Enable:

- `Interface Options > SPI`
- camera support if you use a Pi camera module

### 2. Run Setup Script

```bash
cd ~/smart-attendance-system
./pi_setup.sh
```

This script:

- installs required system packages
- creates the Python virtual environment
- installs `requirements.txt`
- enables SPI
- initializes the database
- creates the `attendance` systemd service

### 3. Start and Check the Service

```bash
sudo systemctl start attendance
sudo systemctl status attendance
```

### 4. Open the Dashboard

Find the Pi IP:

```bash
hostname -I
```

Open:

```text
http://<pi-ip>:5000
```

## Helpful Commands

Use the helper script:

```bash
./pi5_quickref.sh status
./pi5_quickref.sh logs
./pi5_quickref.sh restart
./pi5_quickref.sh camera-test
./pi5_quickref.sh gpio-test
./pi5_quickref.sh init-db
```

## Troubleshooting

### Camera not detected

```bash
ls /dev/video*
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL'); cap.release()"
```

### RC522 not working

```bash
lsmod | grep spi
groups $USER
```

Make sure SPI is enabled and the user has access to the needed groups.

### Service logs

```bash
sudo journalctl -u attendance -f
```

### Reinitialize sample data

```bash
python3 main.py --init-db
```

## Notes

- Attendance is marked only once per student per day.
- The project works best as a local Pi-hosted system on the same network.
- For a school project, SQLite is enough and keeps deployment simple.

---

**Last Updated:** April 21, 2026  
**Compatible with:** Raspberry Pi 5 and Raspberry Pi OS 64-bit
