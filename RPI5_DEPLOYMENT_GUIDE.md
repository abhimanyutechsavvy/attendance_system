# Raspberry Pi 5 Deployment Guide - Smart Attendance System

## 🚀 Quick Start
```bash
# 1. Transfer project to Pi
scp -r smart-attendance-system pi@192.168.1.100:~

# 2. SSH to Pi and run setup
ssh pi@192.168.1.100
cd smart-attendance-system
chmod +x pi_setup.sh pi5_optimize.sh
./pi_setup.sh

# 3. Optional: Performance optimizations
./pi5_optimize.sh
sudo reboot

# 4. Access web interface
# http://<pi-ip>:5000
```

## 📋 Hardware Requirements

### Raspberry Pi 5
- Raspberry Pi 5 (4GB or 8GB RAM recommended)
- MicroSD card (32GB+ Class 10)
- Power supply (27W USB-C recommended)
- Cooling (active cooling recommended for sustained use)

### Camera
- USB webcam (Logitech C920, C270, or similar)
- Alternative: Raspberry Pi Camera Module 3 (with adapter)

### NFC Reader (Optional)
- MFRC522 RFID/NFC module
- Connection: SPI interface

### Buttons (Optional)
- 2x Push buttons for manual confirmation/retry
- GPIO pins: 17 (confirm), 27 (retry)

## 🔧 Detailed Setup Steps

### Step 1: Initial Pi Setup
```bash
# Update Raspberry Pi OS
sudo apt update && sudo apt full-upgrade -y

# Enable interfaces
sudo raspi-config
# - Interfacing Options > Camera > Enable
# - Interfacing Options > SPI > Enable
# - Interfacing Options > I2C > Enable (optional)
```

### Step 2: Hardware Connections

#### USB Camera
- Simply plug into any USB port
- No additional configuration needed

#### NFC Reader (MFRC522)
```
MFRC522     | Raspberry Pi 5
-----------|----------------
VCC         | 3.3V (Pin 1)
GND         | GND (Pin 6)
RST         | GPIO 22 (Pin 15)
IRQ         | Not connected
MISO        | GPIO 9 (Pin 21)
MOSI        | GPIO 10 (Pin 19)
SCK         | GPIO 11 (Pin 23)
SDA/SS      | GPIO 8 (Pin 24)
```

#### Buttons (Optional)
```
Button 1 (Confirm) | GPIO 17 (Pin 11)
Button 2 (Retry)   | GPIO 27 (Pin 13)
GND                | GND (Pin 9)
```

### Step 3: Software Installation
Run the automated setup script:
```bash
./pi_setup.sh
```

This will:
- ✅ Update system packages
- ✅ Install dependencies
- ✅ Setup virtual environment
- ✅ Configure permissions
- ✅ Create systemd service
- ✅ Test hardware

### Step 4: Performance Optimization (Optional)
```bash
./pi5_optimize.sh
sudo reboot
```

## 🌐 Network Configuration

### Find Pi IP Address
```bash
hostname -I
# or
ip addr show wlan0 | grep inet
```

### Static IP (Recommended)
```bash
sudo nano /etc/dhcpcd.conf
# Add at end:
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
```

### Port Forwarding (External Access)
Configure your router to forward port 5000 to the Pi's IP.

## 🔒 Security Setup

### Change Default Password
```bash
passwd
```

### SSH Key Authentication
```bash
# On your computer
ssh-keygen -t rsa -b 4096
ssh-copy-id pi@192.168.1.100

# Disable password authentication
sudo nano /etc/ssh/sshd_config
# Change: PasswordAuthentication no
sudo systemctl restart ssh
```

### Firewall
```bash
sudo apt install ufw
sudo ufw allow ssh
sudo ufw allow 5000
sudo ufw enable
```

## 📊 Monitoring & Maintenance

### Service Management
```bash
# Check status
sudo systemctl status attendance

# View logs
sudo journalctl -u attendance -f

# Restart service
sudo systemctl restart attendance

# Stop service
sudo systemctl stop attendance
```

### Performance Monitoring
```bash
# System resources
htop

# I/O monitoring
sudo iotop

# Camera test
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL'); cap.release()"
```

### Log Rotation
```bash
sudo nano /etc/logrotate.d/attendance
# Add:
/home/pi/smart-attendance-system/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

## 🛠 Troubleshooting

### Camera Issues
```bash
# Check camera detection
ls /dev/video*

# Test camera access
sudo usermod -a -G video pi
# Logout and login again

# Test OpenCV
python3 -c "import cv2; print(cv2.__version__)"
```

### GPIO Issues
```bash
# Check GPIO permissions
groups pi

# Add to dialout group
sudo usermod -a -G dialout pi
```

### Memory Issues
```bash
# Check memory usage
free -h

# Clear cache
sudo sync; sudo echo 3 > /proc/sys/vm/drop_caches
```

### Network Issues
```bash
# Check network
ping 8.8.8.8

# Restart networking
sudo systemctl restart dhcpcd
```

## 📱 Mobile Access

### From Phone/Tablet
- Connect to same WiFi network
- Access: `http://<pi-ip>:5000`

### Remote Access (VPN)
```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Get Tailscale IP and access remotely
```

## 🔄 Backup & Recovery

### Backup Data
```bash
# Backup database and images
tar -czf backup_$(date +%Y%m%d).tar.gz data/

# Backup entire project
tar -czf full_backup_$(date +%Y%m%d).tar.gz smart-attendance-system/
```

### Restore from Backup
```bash
tar -xzf backup_20241201.tar.gz
```

## 📈 Performance Tuning

### For High Traffic
```bash
# Increase workers in config
MAX_WORKERS = 8

# Use Gunicorn instead of Flask dev server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Camera Optimization
- Use higher resolution only when needed
- Implement image caching
- Adjust face recognition threshold based on lighting

## 🎯 Production Deployment

### SSL Certificate (HTTPS)
```bash
sudo apt install certbot
certbot certonly --standalone -d yourdomain.com
# Update Flask app to use SSL
```

### Load Balancing
Use nginx as reverse proxy:
```bash
sudo apt install nginx
# Configure nginx.conf for the app
```

### Database Optimization
- Use PostgreSQL for production
- Implement connection pooling
- Add database migrations

## 📞 Support

For issues:
1. Check logs: `sudo journalctl -u attendance -f`
2. Test components individually
3. Verify hardware connections
4. Check network connectivity
5. Monitor system resources

---
**Last Updated:** April 20, 2026
**Compatible with:** Raspberry Pi 5, Raspberry Pi OS (64-bit)