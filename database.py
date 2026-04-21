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
                student_id TEXT NOT NULL,
                name TEXT NOT NULL,
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
        self.connection.commit()

    def get_student_by_tag(self, tag_id: str) -> Optional[sqlite3.Row]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM students WHERE tag_id = ?", (tag_id,))
        return cursor.fetchone()

    def add_student(self, tag_id: str, student_id: str, name: str, stored_image: str):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO students (tag_id, student_id, name, stored_image) VALUES (?, ?, ?, ?)",
            (tag_id, student_id, name, stored_image),
        )
        self.connection.commit()

    def mark_attendance(self, tag_id: str, student_id: str, name: str, status: str, notes: str = ""):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO attendance_log (tag_id, student_id, name, timestamp, status, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (tag_id, student_id, name, datetime.now().isoformat(), status, notes),
        )
        self.connection.commit()

    def close(self):
        self.connection.close()
