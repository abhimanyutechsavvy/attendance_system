import os
import sys
import json
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import base64
from io import BytesIO

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import AttendanceDatabase
from config import DB_PATH, STORED_IMAGES_DIR
from image_processing import compare_images

# Flask app with correct paths to web folder
web_dir = os.path.join(os.path.dirname(__file__), 'web')
app = Flask(__name__, 
            template_folder=os.path.join(web_dir, 'templates'),
            static_folder=os.path.join(web_dir, 'static'))
CORS(app)

db = AttendanceDatabase(DB_PATH)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/students', methods=['GET'])
def get_students():
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        students = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(students)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/students', methods=['POST'])
def add_student():
    try:
        data = request.json
        tag_id = data.get('tag_id')
        student_id = data.get('student_id')
        name = data.get('name')
        
        image_data = data.get('image')
        if image_data:
            image_bytes = base64.b64decode(image_data.split(',')[1])
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            image_filename = f"{student_id}.jpg"
            image_path = Path(STORED_IMAGES_DIR) / image_filename
            cv2.imwrite(str(image_path), image)
        else:
            image_filename = f"{student_id}.jpg"
        
        db.add_student(tag_id, student_id, name, image_filename)
        return jsonify({"message": "Student added successfully", "data": {"tag_id": tag_id, "student_id": student_id, "name": name}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM attendance_log ORDER BY timestamp DESC LIMIT 100")
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/verify', methods=['POST'])
def verify_attendance():
    try:
        data = request.json
        tag_id = data.get('tag_id')
        image_data = data.get('image')
        
        student = db.get_student_by_tag(tag_id)
        if student is None:
            return jsonify({"error": "Student not found", "match": False}), 404
        
        image_bytes = base64.b64decode(image_data.split(',')[1])
        nparr = np.frombuffer(image_bytes, np.uint8)
        live_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        stored_image_path = Path(STORED_IMAGES_DIR) / student['stored_image']
        stored_image = cv2.imread(str(stored_image_path))
        
        match, score = compare_images(live_image, stored_image, threshold=0.01)
        
        return jsonify({
            "match": match,
            "score": float(score),
            "student": {
                "name": student['name'],
                "student_id": student['student_id'],
                "tag_id": student['tag_id']
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/confirm-attendance', methods=['POST'])
def confirm_attendance():
    try:
        data = request.json
        tag_id = data.get('tag_id')
        score = data.get('score', 0)
        
        student = db.get_student_by_tag(tag_id)
        if student is None:
            return jsonify({"error": "Student not found"}), 404
        
        db.mark_attendance(tag_id, student['student_id'], student['name'], status='present', notes=f"Score: {score:.3f}")
        return jsonify({"message": "Attendance marked successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/capture', methods=['POST'])
def capture_image():
    try:
        print("Initializing camera for capture...")
        from camera import CameraManager
        from config import CAMERA_INDEX
        
        camera = CameraManager(CAMERA_INDEX)
        print("Camera initialized, capturing image...")
        frame = camera.capture()
        camera.release()
        
        if frame is None:
            return jsonify({"error": "Failed to capture image"}), 500
        
        # Convert to base64
        import cv2
        _, buffer = cv2.imencode('.jpg', frame)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        print("Image captured and processed successfully")
        return jsonify({"image": f"data:image/jpeg;base64,{img_base64}"})
    except Exception as e:
        print(f"Camera capture error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # For Raspberry Pi deployment, bind to all interfaces
    # For development on laptop, use 127.0.0.1
    import platform
    host = '0.0.0.0' if platform.system() == 'Linux' else '127.0.0.1'
    app.run(debug=False, host=host, port=5000)
