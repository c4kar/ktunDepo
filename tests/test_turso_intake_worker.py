import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

# Add repo to sys.path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.turso_intake_worker import TursoIntakeWorker


class TestTursoIntakeWorker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir.name)
        self.db_path = self.temp_dir_path / "test_ktunbot.db"

        # Initialize worker with custom temp db
        self.worker = TursoIntakeWorker(db_path=self.db_path)
        self.worker.materials_dir = self.temp_dir_path / "materials"
        self.worker.materials_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy student
        with self.worker.get_db_connection() as conn:
            conn.execute(
                "INSERT INTO student_profiles (chat_id, department, grade, term, magnum_credits) VALUES (?, ?, ?, ?, ?)",
                (999888, "EEM", 2, "Guz", 1)
            )
            conn.commit()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_queue_processing_and_reward(self):
        # 1. Create a valid lecture note file exceeding 50KB and having >= 2 pages
        dummy_file = self.temp_dir_path / "intake_test_eem201_vize.pdf"
        real_pdf_source = Path(__file__).parent.parent.parent / "storage" / "magnum" / "FIZIK_1_MAGNUM.pdf"
        if real_pdf_source.exists():
            dummy_file.write_bytes(real_pdf_source.read_bytes())
        else:
            # Fallback if magnum pdf not present
            dummy_content = b"%PDF-1.4\n" + b" " * (60 * 1024) + b"\n%%EOF\n"
            dummy_file.write_bytes(dummy_content)

        # 2. Insert into intake queue
        with self.worker.get_db_connection() as conn:
            conn.execute(
                """INSERT INTO intake_queue (id, chat_id, file_name, file_size, storage_path, department, course_hint, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                ("intake_item_001", 999888, "eem201_vize.pdf", len(dummy_file.read_bytes()), str(dummy_file), "EEM", "Devre Teorisi 1", "QUEUED")
            )
            conn.commit()

        # 3. Verify queued item exists
        items = self.worker.fetch_queued_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "intake_item_001")

        # 4. Process the queue
        processed = self.worker.process_all_queued()
        self.assertEqual(processed, 1)

        # 5. Check queue status updated to ACCEPTED
        with self.worker.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, quality_score FROM intake_queue WHERE id = ?", ("intake_item_001",))
            row = cursor.fetchone()
            self.assertEqual(row["status"], "ACCEPTED")

            # Check student credits increased (1 initial + 2 reward = 3)
            cursor.execute("SELECT magnum_credits FROM student_profiles WHERE chat_id = ?", (999888,))
            credits = cursor.fetchone()["magnum_credits"]
            self.assertEqual(credits, 3)


if __name__ == "__main__":
    unittest.main()
