import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import DB_PATH, DATA_DIR


class AttendanceDatabase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                tag_id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                class_name TEXT DEFAULT '',
                section TEXT DEFAULT '',
                roll_no TEXT DEFAULT '',
                stored_image TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT
            )
            """
        )
        self._ensure_column(cursor, "students", "class_name", "TEXT DEFAULT ''")
        self._ensure_column(cursor, "students", "section", "TEXT DEFAULT ''")
        self._ensure_column(cursor, "students", "roll_no", "TEXT DEFAULT ''")
        self.connection.commit()

    def _ensure_column(self, cursor, table_name: str, column_name: str, definition: str):
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cursor.fetchall()}
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def get_student_by_tag(self, tag_id: str) -> Optional[sqlite3.Row]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM students WHERE tag_id = ?", (tag_id,))
        return cursor.fetchone()

    def get_student_by_student_id(self, student_id: str) -> Optional[sqlite3.Row]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
        return cursor.fetchone()

    def list_students(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM students ORDER BY name ASC, student_id ASC")
        return cursor.fetchall()

    def add_student(
        self,
        tag_id: str,
        student_id: str,
        name: str,
        stored_image: str,
        class_name: str = "",
        section: str = "",
        roll_no: str = "",
    ):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO students
            (tag_id, student_id, name, class_name, section, roll_no, stored_image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (tag_id, student_id, name, class_name, section, roll_no, stored_image),
        )
        self.connection.commit()

    def list_attendance(self, limit: int = 100):
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM attendance_log ORDER BY timestamp DESC LIMIT ?",
            (int(limit),),
        )
        return cursor.fetchall()

    def has_attendance_for_date(self, student_id: str, date_prefix: Optional[str] = None) -> bool:
        date_prefix = date_prefix or datetime.now().date().isoformat()
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT 1 FROM attendance_log WHERE student_id = ? AND timestamp LIKE ? LIMIT 1",
            (student_id, f"{date_prefix}%"),
        )
        return cursor.fetchone() is not None

    def mark_attendance(self, tag_id: str, student_id: str, name: str, status: str, notes: str = ""):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO attendance_log (tag_id, student_id, name, timestamp, status, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (tag_id, student_id, name, datetime.now().isoformat(), status, notes),
        )
        self.connection.commit()

    def close(self):
        self.connection.close()
