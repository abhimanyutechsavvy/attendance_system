import argparse
from pathlib import Path

from config import DB_PATH, STORED_IMAGES_DIR
from database import AttendanceDatabase


def remove_student(student_id: str, expected_name: str = ""):
    db = AttendanceDatabase(DB_PATH)
    cursor = db.connection.cursor()

    student = db.get_student_by_student_id(student_id)
    if student is None:
        print(f"No student found with student_id={student_id}")
        return 1

    student_name = student["name"]
    if expected_name and student_name.strip().lower() != expected_name.strip().lower():
        print(
            "Student ID was found, but the name does not match: "
            f"found '{student_name}', expected '{expected_name}'. Nothing deleted."
        )
        return 2

    image_names = {student["stored_image"]}
    for extension in (".jpg", ".jpeg", ".png"):
        image_names.update(path.name for path in Path(STORED_IMAGES_DIR).glob(f"{student_id}_*{extension}"))

    cursor.execute("DELETE FROM attendance_log WHERE student_id = ?", (student_id,))
    attendance_deleted = cursor.rowcount
    cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    students_deleted = cursor.rowcount
    db.connection.commit()

    removed_images = []
    for image_name in image_names:
        image_path = Path(STORED_IMAGES_DIR) / image_name
        if image_path.exists():
            image_path.unlink()
            removed_images.append(image_path.name)

    print(f"Deleted student: {student_name} ({student_id})")
    print(f"Student rows deleted: {students_deleted}")
    print(f"Attendance rows deleted: {attendance_deleted}")
    print(f"Stored images deleted: {', '.join(removed_images) if removed_images else 'none'}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Delete one student from the attendance database.")
    parser.add_argument("student_id", help="Student ID to delete, for example 15436")
    parser.add_argument("--name", default="", help="Optional safety check for the student's exact name")
    args = parser.parse_args()
    raise SystemExit(remove_student(args.student_id, args.name))


if __name__ == "__main__":
    main()
