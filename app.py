import os
import sys
import cv2
import numpy as np
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import base64

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import AttendanceDatabase
from config import ARDUINO_BAUD_RATE, ARDUINO_SERIAL_PORT, DB_PATH, STORED_IMAGES_DIR, MATCH_THRESHOLD
from image_processing import compare_images

# Flask app with correct paths to web folder
web_dir = os.path.join(os.path.dirname(__file__), 'web')
app = Flask(__name__, 
            template_folder=os.path.join(web_dir, 'templates'),
            static_folder=os.path.join(web_dir, 'static'))
CORS(app)

db = AttendanceDatabase(DB_PATH)
Path(STORED_IMAGES_DIR).mkdir(parents=True, exist_ok=True)
arduino_bridge = None

if ARDUINO_SERIAL_PORT:
    try:
        from arduino_bridge import ArduinoBridge
        arduino_bridge = ArduinoBridge(ARDUINO_SERIAL_PORT, ARDUINO_BAUD_RATE)
        arduino_bridge.start()
        print(f"Web app connected to Arduino bridge on {ARDUINO_SERIAL_PORT}")
    except Exception as exc:
        print(f"[WARN] Arduino bridge unavailable in web app: {exc}")
        arduino_bridge = None


def error_response(message: str, status_code: int = 400):
    return jsonify({"error": message}), status_code


def decode_base64_image(image_data: str):
    if not image_data or "," not in image_data:
        raise ValueError("Image data must be a base64 data URL")

    image_bytes = base64.b64decode(image_data.split(",", 1)[1])
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unable to decode image data")
    return image


def normalized_image_filename(student_id: str):
    safe_id = secure_filename(student_id).strip()
    if not safe_id:
        raise ValueError("Invalid student_id for image filename")
    return f"{safe_id}.jpg"


def student_to_dict(student):
    if student is None:
        return None
    return {
        "tag_id": student["tag_id"],
        "student_id": student["student_id"],
        "name": student["name"],
        "class_name": student["class_name"] if "class_name" in student.keys() else "",
        "section": student["section"] if "section" in student.keys() else "",
        "roll_no": student["roll_no"] if "roll_no" in student.keys() else "",
        "stored_image": student["stored_image"],
    }


def get_request_json():
    return request.get_json(silent=True) or {}

@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})


@app.route('/api/hardware/poll', methods=['GET'])
def poll_hardware():
    if arduino_bridge is None:
        return jsonify({
            "arduino_connected": False,
            "tag_id": None,
            "decision": None,
            "joystick": None,
        })

    return jsonify({
        "arduino_connected": True,
        "tag_id": arduino_bridge.pop_uid(),
        "decision": arduino_bridge.pop_decision(),
        "joystick": arduino_bridge.joystick_state(),
    })

@app.route('/api/students', methods=['GET'])
def get_students():
    try:
        students = [student_to_dict(row) for row in db.list_students()]
        return jsonify(students)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/students', methods=['POST'])
def add_student():
    try:
        data = get_request_json()
        tag_id = (data.get('tag_id') or '').strip()
        student_id = (data.get('student_id') or '').strip()
        name = (data.get('name') or '').strip()
        class_name = (data.get('class_name') or '').strip()
        section = (data.get('section') or '').strip()
        roll_no = (data.get('roll_no') or '').strip()

        if not tag_id or not student_id or not name:
            return error_response("tag_id, student_id, and name are required")

        image_data = data.get('image')
        if image_data:
            image = decode_base64_image(image_data)
            image_filename = normalized_image_filename(student_id)
            image_path = Path(STORED_IMAGES_DIR) / image_filename
            if not cv2.imwrite(str(image_path), image):
                return error_response("Failed to save student image", 500)
        else:
            return error_response("Student image is required")

        db.add_student(tag_id, student_id, name, image_filename, class_name=class_name, section=section, roll_no=roll_no)
        return jsonify({
            "message": "Student added successfully",
            "data": {
                "tag_id": tag_id,
                "student_id": student_id,
                "name": name,
                "class_name": class_name,
                "section": section,
                "roll_no": roll_no,
                "stored_image": image_filename,
            }
        }), 201
    except Exception as e:
        message = str(e)
        if "UNIQUE constraint failed: students.student_id" in message:
            return error_response("student_id already exists", 409)
        return jsonify({"error": message}), 500

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    try:
        logs = [dict(row) for row in db.list_attendance(limit=100)]
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/verify', methods=['POST'])
def verify_attendance():
    try:
        data = get_request_json()
        tag_id = (data.get('tag_id') or '').strip()
        image_data = data.get('image')

        if not tag_id:
            return error_response("tag_id is required")
        if not image_data:
            return error_response("image is required")

        student = db.get_student_by_tag(tag_id)
        if student is None:
            return jsonify({"error": "Student not found", "match": False}), 404

        live_image = decode_base64_image(image_data)
        stored_image_path = Path(STORED_IMAGES_DIR) / student['stored_image']
        if not stored_image_path.exists():
            return error_response(f"Stored image missing for student {student['student_id']}", 404)

        stored_image = cv2.imread(str(stored_image_path))
        if stored_image is None:
            return error_response(f"Stored image could not be read for student {student['student_id']}", 500)

        match, score = compare_images(live_image, stored_image, threshold=MATCH_THRESHOLD)
        
        return jsonify({
            "match": match,
            "score": float(score),
            "student": {
                "name": student['name'],
                "student_id": student['student_id'],
                "tag_id": student['tag_id'],
                "class_name": student['class_name'] if 'class_name' in student.keys() else "",
                "section": student['section'] if 'section' in student.keys() else "",
                "roll_no": student['roll_no'] if 'roll_no' in student.keys() else "",
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/confirm-attendance', methods=['POST'])
def confirm_attendance():
    try:
        data = get_request_json()
        tag_id = (data.get('tag_id') or '').strip()
        score = float(data.get('score', 0) or 0)

        if not tag_id:
            return error_response("tag_id is required")

        student = db.get_student_by_tag(tag_id)
        if student is None:
            return jsonify({"error": "Student not found"}), 404

        if db.has_attendance_for_date(student['student_id']):
            return jsonify({
                "error": "Attendance already marked for this student today",
                "student_id": student['student_id']
            }), 409

        db.mark_attendance(tag_id, student['student_id'], student['name'], status='present', notes=f"Score: {score:.3f}")
        return jsonify({"message": "Attendance marked successfully", "score": score})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/student/<student_id>/image', methods=['GET'])
def get_student_image(student_id):
    try:
        student = db.get_student_by_student_id(student_id)

        if student is None:
            return error_response("Student not found", 404)

        image_path = Path(STORED_IMAGES_DIR) / student["stored_image"]
        if not image_path.exists():
            return error_response("Student image not found", 404)

        return send_file(image_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/capture', methods=['POST'])
def capture_image():
    camera = None
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
    finally:
        if camera is not None:
            try:
                camera.release()
            except Exception:
                pass

if __name__ == '__main__':
    # For Raspberry Pi deployment, bind to all interfaces
    # For development on laptop, use 127.0.0.1
    import platform
    host = '0.0.0.0' if platform.system() == 'Linux' else '127.0.0.1'
    app.run(debug=False, host=host, port=5000)
