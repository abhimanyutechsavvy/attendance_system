# Smart Attendance System - Web Interface

A full-featured web application for the Smart Attendance System running on localhost.

## Features

- 📷 **Real-time Camera Feed** — Live webcam capture from browser
- 🆔 **NFC Tag Input** — Manual tag ID entry or NFC scanning
- ✅ **Face/ID Card Verification** — ORB-based image matching
- 👥 **Student Management** — Add, view, and manage students
- 📊 **Attendance Dashboard** — Real-time log and statistics
- 📱 **Responsive Design** — Works on desktop and mobile devices

## Installation

### 1. Install Dependencies

On your Raspberry Pi or laptop:

```bash
cd ~/smart-attendance-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python3 main.py --init-db
```

## Running the Web Application

### From the same directory:

```bash
cd web
python3 app.py
```

### Then open your browser:

```
http://localhost:5000
```

---

## How to Use

### 1. **Verification Tab** (Main Interface)
   - Enter NFC tag ID (or use test: `123456789012`)
   - Click "Capture" to take a photo from the camera
   - System will compare the live image with the stored image
   - If match: Click "Confirm Attendance"
   - If no match: Click "Retry" and try again

### 2. **Students Tab** (Add New Students)
   - Fill in the form with student details
   - Upload a photo (will be saved as `<student_id>.jpg`)
   - Click "Add Student"
   - New students appear in the list below

### 3. **Attendance Log Tab**
   - View all marked attendance records
   - Shows name, timestamp, status, and match score
   - Automatically refreshes every 10 seconds

---

## API Endpoints

- `GET /api/students` — Get all students
- `POST /api/students` — Add new student
- `GET /api/attendance` — Get attendance log
- `POST /api/verify` — Verify image against stored image
- `POST /api/confirm-attendance` — Mark attendance as present
- `GET /api/student/<student_id>/image` — Get student photo

---

## Default Test Data

**Student 1 (Sample)**
- NFC Tag: `123456789012`
- Student ID: `S001`
- Name: `Student One`
- Photo: `data/stored_ids/student1.jpg`

---

## Troubleshooting

### Camera not accessible
```bash
# Check if camera is detected
ls /dev/video*

# Test OpenCV camera access
python3 -c "import cv2; cap=cv2.VideoCapture(0); print('OK' if cap.isOpened() else 'FAIL'); cap.release()"
```

### Flask not found
```bash
pip install flask flask-cors
```

### Permission denied on Pi
```bash
# Run with user privileges
python3 app.py
```

---

## Accessing from Another Device

To access the web app from another computer on the same network:

1. Find your Pi's IP address:
   ```bash
   hostname -I
   ```

2. From another computer, open:
   ```
   http://<pi-ip>:5000
   ```

Example: `http://192.168.1.100:5000`

---

## File Structure

```
web/
├── app.py                    # Flask backend
├── templates/
│   └── dashboard.html        # Web interface
└── static/
    ├── script.js             # Frontend logic
    └── style.css             # Styling
```

---

## Running on Background (Raspberry Pi)

To keep the web app running even after closing the terminal:

```bash
nohup python3 app.py > attendance.log 2>&1 &
```

To stop it:

```bash
pkill -f "python3 app.py"
```

---

## Next Steps

- Add database statistics and reports
- Implement email notifications
- Add QR code alternative to NFC
- Deploy to a web server (Gunicorn + Nginx)
