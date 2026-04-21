import argparse
import cv2
import numpy as np
from pathlib import Path

from camera import CameraManager
from config import DB_PATH, DISPLAY_WINDOW_NAME, MATCH_THRESHOLD, STORED_IMAGES_DIR
from database import AttendanceDatabase
from hardware import ButtonController, NFCReader
from image_processing import compare_images, draw_side_by_side


def create_sample_image(image_path: Path):
    image_path.parent.mkdir(parents=True, exist_ok=True)
    if image_path.exists():
        return
    image = 255 * np.ones((360, 640, 3), dtype=np.uint8)
    cv2.putText(image, "Student1", (40, 210), cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 0), 8, cv2.LINE_AA)
    cv2.putText(image, "Attendance", (30, 320), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.imwrite(str(image_path), image)


def initialize_database(db: AttendanceDatabase):
    sample_image_dir = Path(STORED_IMAGES_DIR)
    sample_image_dir.mkdir(parents=True, exist_ok=True)
    sample_student = {
        "tag_id": "123456789012",
        "student_id": "S001",
        "name": "Student One",
        "stored_image": "student1.jpg",
    }
    sample_image_path = sample_image_dir / sample_student["stored_image"]
    create_sample_image(sample_image_path)
    db.add_student(
        sample_student["tag_id"],
        sample_student["student_id"],
        sample_student["name"],
        sample_student["stored_image"],
    )
    print(f"Database initialized at {db.db_path}")
    print("A sample student has been created for testing.")


def load_stored_image(student, base_dir: Path):
    image_path = base_dir / student["stored_image"]
    if not image_path.exists():
        raise FileNotFoundError(f"Stored image not found: {image_path}")
    image = cv2.imread(str(image_path))
    if image is None:
        raise RuntimeError(f"Failed to load stored image from {image_path}")
    return image


def main():
    parser = argparse.ArgumentParser(description="Smart Attendance System")
    parser.add_argument("--init-db", action="store_true", help="Initialize database and sample folders")
    args = parser.parse_args()

    db = AttendanceDatabase(DB_PATH)
    if args.init_db:
        initialize_database(db)
        db.close()
        return

    nfc_reader = None
    camera = None
    button_controller = None
    try:
        nfc_reader = NFCReader()
        camera = CameraManager()
        button_controller = ButtonController()

        while True:
            print("\n1) Tap the NFC card")
            print("2) Show your ID card to the camera")
            print("3) Press green to confirm or red to retry")
            tag_id = nfc_reader.wait_for_tag()
            if not tag_id:
                continue

            student = db.get_student_by_tag(tag_id)
            if student is None:
                print("No student record found for that tag. Try again.")
                continue

            try:
                stored_image = load_stored_image(student, Path(STORED_IMAGES_DIR))
            except Exception as exc:
                print(exc)
                continue

            live_image = camera.capture()
            if live_image is None:
                print("Could not capture live image.")
                continue

            match, score = compare_images(live_image, stored_image, threshold=MATCH_THRESHOLD)
            status_text = "MATCH" if match else "NO MATCH"
            draw_side_by_side(live_image, stored_image, DISPLAY_WINDOW_NAME, status_text=status_text, score=score)
            print(f"Match score: {score:.3f} (threshold {MATCH_THRESHOLD})")

            if match:
                print("Good match. Press green to confirm attendance.")
            else:
                print("No match. Press red to retry.")

            decision = button_controller.wait_for_decision()
            if decision == "confirm" and match:
                db.mark_attendance(tag_id, student["student_id"], student["name"], status="present", notes=f"Match score {score:.3f}")
                print(f"Attendance marked for {student['name']}.")
            elif decision == "retry" or not match:
                print("Retrying verification process.")
            elif decision is None:
                print("No button pressed. Restarting process.")

            if cv2.getWindowProperty(DISPLAY_WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                print("Display window closed, exiting.")
                break

    except KeyboardInterrupt:
        print("Interrupted by user. Exiting.")
    except Exception as exc:
        print(f"Unhandled exception: {exc}")
    finally:
        if button_controller:
            button_controller.cleanup()
        if camera:
            camera.release()
        cv2.destroyAllWindows()
        db.close()


if __name__ == "__main__":
    main()
