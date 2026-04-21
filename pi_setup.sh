#!/bin/bash
# Raspberry Pi 5 Setup Script for Smart Attendance System

echo "=== Smart Attendance System - Raspberry Pi 5 Setup ==="

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies for Pi 5
echo "Installing system dependencies..."
sudo apt install -y python3 python3-pip python3-venv python3-opencv python3-numpy python3-rpi.gpio python3-spidev
sudo apt install -y libatlas-base-dev libjasper-dev libqtgui4 libqt4-test libhdf5-dev
sudo apt install -y libilmbase-dev libopenexr-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev

# Setup camera permissions for USB webcam
echo "Setting up camera permissions..."
sudo usermod -a -G video $USER
sudo usermod -a -G dialout $USER  # For GPIO access

# Enable camera interface (for Pi Camera if used)
echo "Enabling camera interface..."
sudo raspi-config nonint do_camera 1

# Create project directory
echo "Setting up project directory..."
mkdir -p ~/smart-attendance-system
cd ~/smart-attendance-system

# Setup virtual environment
echo "Creating virtual environment..."
python3 -m venv attendance_env
source attendance_env/bin/activate

# Install Python dependencies
echo "Installing Python packages..."
pip install --upgrade pip
pip install flask flask-cors opencv-python numpy mfrc522 spidev pyserial
pip install pillow

# Test hardware
echo "Testing camera..."
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera failed'); cap.release()"

echo "Testing GPIO..."
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('GPIO OK')"

# Create systemd service for auto-start
echo "Creating systemd service..."
sudo tee /etc/systemd/system/attendance.service > /dev/null <<EOF
[Unit]
Description=Smart Attendance System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/smart-attendance-system
ExecStart=/home/pi/smart-attendance-system/attendance_env/bin/python3 app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "Enabling auto-start service..."
sudo systemctl daemon-reload
sudo systemctl enable attendance
sudo systemctl start attendance

echo "=== Setup Complete ==="
echo "Service status: sudo systemctl status attendance"
echo "Service logs: sudo journalctl -u attendance -f"
echo "Web access: http://<pi-ip>:5000"
echo ""
echo "To restart service: sudo systemctl restart attendance"
echo "To stop service: sudo systemctl stop attendance"