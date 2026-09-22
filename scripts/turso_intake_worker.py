#!/usr/bin/env python3
"""
ktunDepo — Turso Intake Queue Worker
Bridges ktunBot Telegram uploads with ktunDepo's AI material intake pipeline.

Workflow:
1. Polls `intake_queue` table in Turso SQLite (status = 'QUEUED')
2. Runs heuristic quality checks & duplicate detection (Qdrant)
3. Approves or rejects the material
4. Moves approved materials to STEM storage (`storage/materials/{dept}/{course}/`)
5. Updates student magnum credits (+2 credits per accepted contribution)
"""

import os
import sys
import time
import shutil
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.quality_checker import QualityChecker, QualityDecision
from scripts.course_resolver import CourseResolver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("turso_intake_worker")


def find_db_path() -> Path:
    """Locate the Turso SQLite database file."""
    env_url = os.getenv("TURSO_DATABASE_URL", "")
    if env_url.startswith("file:"):
        path_str = env_url.replace("file:", "")
        candidate = Path(path_str).resolve()
        if candidate.exists() or candidate.parent.exists():
            return candidate

    candidates = [
        Path(__file__).parent.parent.parent / "ktunBot" / "data" / "ktunbot.db",
        Path(__file__).parent.parent / "data" / "ktunbot.db",
        Path(__file__).parent.parent.parent / "data" / "ktunbot.db",
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()

    # Default fallback
    return (Path(__file__).parent.parent.parent / "ktunBot" / "data" / "ktunbot.db").resolve()


class TursoIntakeWorker:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or find_db_path()
        logger.info(f"Connected to Turso SQLite database at: {self.db_path}")
        self.root_dir = Path(__file__).parent.parent.parent.resolve()
        self.materials_dir = self.root_dir / "storage" / "materials"
        self.materials_dir.mkdir(parents=True, exist_ok=True)
        self.checker = QualityChecker()
        self.resolver = CourseResolver()
        self.ensure_tables()

    def get_db_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_tables(self):
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS intake_queue (
                    id TEXT PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    storage_path TEXT NOT NULL,
                    department TEXT,
                    course_hint TEXT,
                    status TEXT NOT NULL DEFAULT 'QUEUED',
                    quality_score INTEGER,
                    rejection_reason TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    processed_at TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS student_profiles (
                    chat_id INTEGER PRIMARY KEY,
                    department TEXT NOT NULL DEFAULT 'EEM',
                    grade INTEGER NOT NULL DEFAULT 1,
                    term TEXT NOT NULL DEFAULT 'Guz',
                    magnum_credits INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def fetch_queued_items(self, limit: int = 10) -> List[sqlite3.Row]:
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM intake_queue WHERE status = 'QUEUED' ORDER BY created_at ASC LIMIT ?",
                (limit,)
            )
            return cursor.fetchall()
        finally:
            conn.close()

    def update_item_status(
        self,
        item_id: str,
        status: str,
        quality_score: Optional[int] = None,
        rejection_reason: Optional[str] = None
    ):
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE intake_queue 
                   SET status = ?, quality_score = ?, rejection_reason = ?, processed_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (status, quality_score, rejection_reason, item_id)
            )
            conn.commit()
        finally:
            conn.close()

    def reward_student(self, chat_id: int, credits: int = 2):
        conn = self.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE student_profiles SET magnum_credits = magnum_credits + ?, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ?",
                (credits, chat_id)
            )
            conn.commit()
            logger.info(f"Awarded +{credits} Magnum credits to student chat_id: {chat_id}")
        finally:
            conn.close()

    def process_item(self, row: sqlite3.Row) -> bool:
        item_id = row["id"]
        chat_id = row["chat_id"]
        file_name = row["file_name"]
        storage_path = Path(row["storage_path"])
        department = row["department"] or "GENEL"
        course_hint = row["course_hint"] or ""

        logger.info(f"Processing item [{item_id}] '{file_name}' for chat_id: {chat_id} (dept: {department})")

        if not storage_path.exists():
            logger.error(f"File not found on disk: {storage_path}")
            self.update_item_status(item_id, "REJECTED", rejection_reason="Dosya diskte bulunamadı")
            return False

        # Mark as processing
        self.update_item_status(item_id, "PROCESSING")

        # 1. Quality & heuristic check
        result = self.checker.check_file(file_path=str(storage_path))
        decision, score, reason = result.decision, result.score, result.reason

        logger.info(f"Quality check result for '{file_name}': decision={decision}, score={score}, reason={reason}")

        if decision == QualityDecision.REJECTED or decision == QualityDecision.DUPLICATE:
            logger.warning(f"Rejecting '{file_name}': {reason}")
            self.update_item_status(item_id, "REJECTED", quality_score=score, rejection_reason=reason)
            try:
                storage_path.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Could not delete rejected file: {e}")
            return False

        # 2. Determine target course directory
        try:
            match = self.resolver.resolve(course_hint or file_name)
            course_id = match.course_name
        except Exception:
            # Fallback to sanitized course hint or file name
            course_id = (course_hint or "GENEL").replace("/", "_").replace(" ", "_")

        target_dir = self.materials_dir / department.upper() / course_id.upper()
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / storage_path.name
        shutil.move(str(storage_path), str(target_path))
        logger.info(f"Successfully moved accepted material to: {target_path}")

        # 3. Update status & reward student
        self.update_item_status(item_id, "ACCEPTED", quality_score=score)
        self.reward_student(chat_id, credits=2)
        return True

    def process_all_queued(self) -> int:
        items = self.fetch_queued_items(limit=20)
        if not items:
            logger.info("No pending items in intake queue.")
            return 0

        logger.info(f"Found {len(items)} pending intake items to process.")
        processed = 0
        for item in items:
            try:
                if self.process_item(item):
                    processed += 1
            except Exception as e:
                logger.exception(f"Error processing item {item['id']}: {e}")
                self.update_item_status(item["id"], "REJECTED", rejection_reason=f"İşlem hatası: {str(e)}")

        logger.info(f"Finished processing batch: {processed}/{len(items)} accepted.")
        return processed


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ktunDepo Turso Intake Worker")
    parser.add_argument("mode", choices=["run", "watch", "status"], default="run", nargs="?", help="Execution mode")
    parser.add_argument("--interval", type=int, default=15, help="Polling interval in seconds for watch mode")

    args = parser.parse_args()
    worker = TursoIntakeWorker()

    if args.mode == "status":
        with worker.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, count(*) FROM intake_queue GROUP BY status")
            rows = cursor.fetchall()
            print("=== Intake Queue Status ===")
            for r in rows:
                print(f"• {r[0]}: {r[1]}")
    elif args.mode == "run":
        worker.process_all_queued()
    elif args.mode == "watch":
        logger.info(f"Starting intake worker daemon (polling every {args.interval}s)...")
        while True:
            worker.process_all_queued()
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
