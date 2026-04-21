#!/bin/bash
set -e

echo "=== Smart Attendance System - Raspberry Pi 5 Setup ==="

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_FILE="/etc/systemd/system/attendance.service"
CURRENT_USER="$(whoami)"

echo "Project directory: $PROJECT_DIR"

echo "Updating system packages..."
sudo apt update
sudo apt install -y \
  python3 \
  python3-pip \
  python3-venv \
  python3-opencv \
  python3-numpy \
  python3-rpi.gpio \
  python3-spidev \
  libatlas-base-dev \
  libhdf5-dev \
  libgstreamer1.0-dev \
  libgstreamer-plugins-base1.0-dev

echo "Adding current user to required groups..."
sudo usermod -a -G video "$CURRENT_USER"
sudo usermod -a -G dialout "$CURRENT_USER"
sudo usermod -a -G spi "$CURRENT_USER" || true
sudo usermod -a -G gpio "$CURRENT_USER" || true

echo "Enabling SPI for RC522..."
sudo raspi-config nonint do_spi 0

echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "Installing Python dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

echo "Ensuring database and data folders exist..."
python3 "$PROJECT_DIR/main.py" --init-db

echo "Running quick hardware checks..."
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera not detected'); cap.release()"
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('GPIO OK'); GPIO.cleanup()"

echo "Creating systemd service..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Smart Attendance System
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "Enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable attendance.service

echo "=== Setup Complete ==="
echo "Start service: sudo systemctl start attendance"
echo "Service status: sudo systemctl status attendance"
echo "Service logs: sudo journalctl -u attendance -f"
echo "Web access: http://<pi-ip>:5000"
echo ""
echo "Log out and back in once so new group memberships take effect."
