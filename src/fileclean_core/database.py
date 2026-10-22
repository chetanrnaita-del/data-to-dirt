"""SQLite database for storing user feedback and scan history."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Generator


class FeedbackDatabase:
    """Manages user feedback data for adaptive model learning.

    Stores user decisions (keep/delete) for files, which can later be used
    to retrain the classifier with personalized preferences.
    """

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            from src.fileclean_core.config import Config
            data_dir = Config.default_data_dir()
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "feedback.db"

        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        with self._connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    extension TEXT,
                    size INTEGER,
                    days_since_modified REAL,
                    days_since_accessed REAL,
                    category TEXT NOT NULL,
                    predicted_action TEXT NOT NULL,
                    user_action TEXT NOT NULL,
                    confidence TEXT,
                    source TEXT,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    directory TEXT NOT NULL,
                    total_files INTEGER,
                    total_issues INTEGER,
                    reclaimable_bytes INTEGER,
                    scan_duration REAL,
                    ai_enabled INTEGER,
                    timestamp TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_feedback_extension
                    ON feedback(extension);
                CREATE INDEX IF NOT EXISTS idx_feedback_category
                    ON feedback(category);
                CREATE INDEX IF NOT EXISTS idx_feedback_user_action
                    ON feedback(user_action);
            """)

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_feedback(
        self,
        file_path: str,
        extension: str,
        size: int,
        days_since_modified: float,
        days_since_accessed: float,
        category: str,
        predicted_action: str,
        user_action: str,
        confidence: str = "high",
        source: str = "rule",
    ) -> None:
        """Record a user's decision about a file.

        Args:
            file_path: Path to the file.
            extension: File extension.
            size: File size in bytes.
            days_since_modified: Days since last modification.
            days_since_accessed: Days since last access.
            category: Issue category (duplicate, junk, old, large).
            predicted_action: What the model suggested (delete/keep).
            user_action: What the user actually did (delete/keep/skip).
            confidence: Model's confidence level.
            source: Detection source (rule/classifier/ai).
        """
        with self._connection() as conn:
            conn.execute(
                """INSERT INTO feedback
                   (file_path, extension, size, days_since_modified,
                    days_since_accessed, category, predicted_action,
                    user_action, confidence, source, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    file_path, extension, size, days_since_modified,
                    days_since_accessed, category, predicted_action,
                    user_action, confidence, source,
                    datetime.now().isoformat(),
                ),
            )

    def record_scan(
        self,
        directory: str,
        total_files: int,
        total_issues: int,
        reclaimable_bytes: int,
        scan_duration: float,
        ai_enabled: bool,
    ) -> None:
        """Record a scan operation in history."""
        with self._connection() as conn:
            conn.execute(
                """INSERT INTO scan_history
                   (directory, total_files, total_issues, reclaimable_bytes,
                    scan_duration, ai_enabled, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    directory, total_files, total_issues, reclaimable_bytes,
                    scan_duration, int(ai_enabled),
                    datetime.now().isoformat(),
                ),
            )

    def get_feedback_count(self) -> int:
        """Return total number of feedback records."""
        with self._connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()
            return row[0] if row else 0

    def get_all_feedback(self) -> list[dict]:
        """Retrieve all feedback records as dicts (for retraining)."""
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM feedback ORDER BY timestamp").fetchall()
            return [dict(row) for row in rows]

    def get_accuracy_stats(self) -> dict:
        """Compute accuracy stats: how often the model agreed with the user."""
        with self._connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            if total == 0:
                return {"total": 0, "correct": 0, "accuracy": 0.0}
            correct = conn.execute(
                "SELECT COUNT(*) FROM feedback WHERE predicted_action = user_action"
            ).fetchone()[0]
            return {
                "total": total,
                "correct": correct,
                "accuracy": round(correct / total * 100, 1),
            }
