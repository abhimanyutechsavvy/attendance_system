#!/bin/bash
# Raspberry Pi 5 Performance Optimizations for Smart Attendance System

echo "=== Raspberry Pi 5 Performance Optimizations ==="

# Enable performance governor
echo "Setting CPU governor to performance..."
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Increase GPU memory for camera processing
echo "Increasing GPU memory..."
sudo raspi-config nonint do_memory_split 256

# Disable unnecessary services
echo "Disabling unnecessary services..."
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
sudo systemctl disable triggerhappy

# Optimize network settings
echo "Optimizing network settings..."
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF
net.core.rmem_max=262144
net.core.wmem_max=262144
net.ipv4.tcp_rmem=4096 131072 262144
net.ipv4.tcp_wmem=4096 131072 262144
EOF

# Create swap file for better memory management
echo "Setting up swap file..."
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=1024/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Optimize boot options
echo "Optimizing boot options..."
sudo sed -i 's/$/ quiet splash loglevel=3/' /boot/firmware/cmdline.txt

# Install performance monitoring tools
echo "Installing monitoring tools..."
sudo apt install -y htop iotop

echo "=== Optimizations Complete ==="
echo "Reboot required: sudo reboot"
echo ""
echo "Monitor performance:"
echo "  htop - system monitor"
echo "  iotop - I/O monitor"
echo "  sudo journalctl -u attendance -f - service logs"