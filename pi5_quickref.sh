#!/bin/bash
# Raspberry Pi 5 Quick Reference Commands

echo "=== Raspberry Pi 5 - Smart Attendance System ==="
echo "Quick Reference Commands"
echo ""

case "$1" in
    "status")
        echo "=== Service Status ==="
        sudo systemctl status attendance
        ;;
    "logs")
        echo "=== Service Logs ==="
        sudo journalctl -u attendance -f
        ;;
    "restart")
        echo "=== Restarting Service ==="
        sudo systemctl restart attendance
        echo "Service restarted"
        ;;
    "stop")
        echo "=== Stopping Service ==="
        sudo systemctl stop attendance
        echo "Service stopped"
        ;;
    "start")
        echo "=== Starting Service ==="
        sudo systemctl start attendance
        echo "Service started"
        ;;
    "camera-test")
        echo "=== Camera Test ==="
        python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera FAILED'); cap.release()"
        ;;
    "gpio-test")
        echo "=== GPIO Test ==="
        python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('GPIO OK')"
        ;;
    "system-info")
        echo "=== System Information ==="
        echo "CPU Temperature: $(vcgencmd measure_temp)"
        echo "CPU Frequency: $(vcgencmd measure_clock arm)"
        echo "Memory: $(free -h | grep Mem)"
        echo "Disk: $(df -h / | tail -1)"
        ;;
    "network")
        echo "=== Network Information ==="
        echo "Local IP: $(hostname -I)"
        echo "External IP: $(curl -s ifconfig.me)"
        ;;
    "backup")
        echo "=== Creating Backup ==="
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        tar -czf "backup_${TIMESTAMP}.tar.gz" data/
        echo "Backup created: backup_${TIMESTAMP}.tar.gz"
        ;;
    "update")
        echo "=== Updating System ==="
        sudo apt update && sudo apt upgrade -y
        echo "System updated"
        ;;
    *)
        echo "Usage: $0 {status|logs|restart|stop|start|camera-test|gpio-test|system-info|network|backup|update}"
        echo ""
        echo "Examples:"
        echo "  $0 status     - Check service status"
        echo "  $0 logs       - View service logs"
        echo "  $0 restart    - Restart the service"
        echo "  $0 camera-test - Test camera functionality"
        echo "  $0 backup     - Create data backup"
        echo ""
        echo "Web Interface: http://$(hostname -I | awk '{print $1}'):5000"
        ;;
esac