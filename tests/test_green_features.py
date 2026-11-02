"""Unit and integration tests for Green-Light Feature Suite:
1. Keep-or-Sweep Overhaul & Instant Direct Student Sweep (Item 15 & Page 3)
2. Batch Sweep API for duplicates, expired, and burst candidates (Item 15)
3. Digital Biodegradability (TTL, decay metrics, and composting) (Item 4)
4. Whiteboard & Notes Neural OCR Converter (Item 5)
5. Public School Shared-Drive Deduplication & Curriculum Commons (Item 2)
6. Perceptual Global Asset Pooling (Meme/Stock pHash) (Item 10)
7. Polyglot Rehydration & Dynamic On-Demand Translation (Item 11)
8. Screenshot Burst Deduplication & Stack Pruning (Item 13)
9. Category-Scoped Teacher Bulk Approvals (Item 15)
"""

import os
import unittest
import json
import time
from pathlib import Path

# Ensure test environment
os.environ["TEST_MODE"] = "1"

from src.app.server import (
    app,
    load_state,
    save_state,
    enrich_file_iq1000,
    group_screenshot_bursts,
    reset_all_auth_lockouts,
)
from src.services.auth import default_auth_service


class TestGreenLightFeatures(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        reset_all_auth_lockouts()
        self.state = load_state()
        self.original_state = json.loads(json.dumps(self.state))

        # Setup test student session
        self.student_id = "STU-GREEN-001"
        self.student_session = default_auth_service.create_session(role="student", user_id=self.student_id)
        self.student_headers = {"Authorization": f"Bearer {self.student_session['token']}"}

        # Setup test teacher session
        self.teacher_id = "TEACHER-GREEN-001"
        self.teacher_session = default_auth_service.create_session(role="teacher", user_id=self.teacher_id)
        self.teacher_headers = {"Authorization": f"Bearer {self.teacher_session['token']}"}

    def tearDown(self):
        reset_all_auth_lockouts()
        save_state(self.original_state)

    def test_instant_direct_student_sweep_bypasses_teacher_queue(self):
        """Item 15 & Page 3: High-confidence junk with is_direct_sweep: True is deleted directly without teacher queue bottleneck."""
        # Setup student file in scanner state
        file_id = "test_junk_file_001"
        state = load_state()
        state["scanner"]["files"] = [{
            "file_id": file_id,
            "file_name": "temp_cache.tmp",
            "size_bytes": 1024 * 1024 * 5,
            "size_formatted": "5.0 MB",
            "tier": "TIER_1_JUNK",
            "can_instant_sweep": True
        }]
        save_state(state)

        # Submit direct sweep
        res = self.client.post("/api/deletion/submit", json={
            "file_id": file_id,
            "file_name": "temp_cache.tmp",
            "file_size": 1024 * 1024 * 5,
            "is_direct_sweep": True,
            "reason": "Temporary application cache file that is no longer needed",
            "student_id": self.student_id
        }, headers=self.student_headers)

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "swept_directly")
        self.assertTrue(data.get("is_direct_sweep"))
        self.assertGreater(data.get("eco_points", 0), 0)

        # Verify teacher queue did NOT receive a PENDING item
        updated_state = load_state()
        pending_in_teacher_queue = [
            item for item in updated_state.get("teacher_queue", [])
            if item.get("file_id") == file_id and item.get("status") == "PENDING"
        ]
        self.assertEqual(len(pending_in_teacher_queue), 0, "Direct sweep must not be held in teacher queue")

    def test_batch_sweep_api(self):
        """Item 15: /api/deletion/batch_sweep clears multiple files at once."""
        state = load_state()
        state["scanner"]["files"] = [
            {"file_id": "f1", "file_name": "old_backup.bak", "size_bytes": 2 * 1024 * 1024, "can_instant_sweep": True},
            {"file_id": "f2", "file_name": "clone_report.pdf", "size_bytes": 3 * 1024 * 1024, "sha_match": True, "can_instant_sweep": True},
            {"file_id": "f3", "file_name": "final_thesis.pdf", "size_bytes": 4 * 1024 * 1024, "tier": "TIER_3_ACADEMIC", "can_instant_sweep": False}
        ]
        save_state(state)

        # Batch sweep junk
        res = self.client.post("/api/deletion/batch_sweep", json={
            "category": "all_junk",
            "student_id": self.student_id
        }, headers=self.student_headers)

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["files_swept"], 2)
        self.assertEqual(data["bytes_cleaned"], 5 * 1024 * 1024)

        # Academic file should remain in scanner
        updated_state = load_state()
        remaining = updated_state.get("scanner", {}).get("files", [])
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["file_id"], "f3")

    def test_digital_biodegradability_ttl_and_decay_calculation(self):
        """Item 4: Verifies TTL assignment, decay percentage, and expiration calculation."""
        now = time.time()

        # Temp file: 7 days TTL, aged 10 days -> expired
        f_temp = {
            "file_name": "session_dump.tmp",
            "size_bytes": 500000,
            "last_modified_epoch_s": now - (10 * 86400),
            "age_days": 10
        }
        res_temp = enrich_file_iq1000(f_temp, now)
        self.assertEqual(res_temp["ttl_days"], 7)
        self.assertEqual(res_temp["decay_pct"], 100)
        self.assertTrue(res_temp["is_expired"])
        self.assertEqual(res_temp["tier"], "TIER_1_JUNK")

        # Active coursework: 180 days TTL, aged 30 days -> ~16% decay, not expired
        f_doc = {
            "file_name": "Chemistry_Homework.pdf",
            "size_bytes": 1000000,
            "last_modified_epoch_s": now - (30 * 86400),
            "age_days": 30
        }
        res_doc = enrich_file_iq1000(f_doc, now)
        self.assertEqual(res_doc["ttl_days"], 180)
        self.assertEqual(res_doc["decay_pct"], 16)
        self.assertFalse(res_doc["is_expired"])

    def test_biodegradability_status_api(self):
        """Item 4: /api/biodegradability/status endpoint returns expired counts and reclamation stats."""
        state = load_state()
        state["scanner"]["files"] = [
            {"file_id": "exp1", "file_name": "old_draft.tmp", "size_bytes": 1000000, "is_expired": True},
            {"file_id": "act1", "file_name": "notes.pdf", "size_bytes": 2000000, "is_expired": False, "decay_pct": 50}
        ]
        save_state(state)

        res = self.client.get("/api/biodegradability/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["expired_count"], 1)
        self.assertEqual(data["expired_bytes"], 1000000)
        self.assertEqual(data["recommended_action"], "compost_all")

    def test_notes_ocr_endpoint(self):
        """Item 5: /api/scan/ocr_notes transcribes whiteboard photos into structured markdown notes."""
        res = self.client.post("/api/scan/ocr_notes", json={
            "file_name": "Whiteboard_Physics_Lecture.jpg",
            "file_size_bytes": 8500000,
            "title": "Kinematics & Dynamics"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        note = data["note"]
        self.assertIn("Kinematics & Dynamics", note["title"])
        self.assertGreater(note["bytes_saved"], 8000000)
        self.assertIn("99.", note["savings_pct"])

        # Check /api/notes/list
        list_res = self.client.get("/api/notes/list")
        self.assertEqual(list_res.status_code, 200)
        notes = list_res.get_json()["notes"]
        self.assertTrue(any(n["note_id"] == note["note_id"] for n in notes))

    def test_school_curriculum_pool_endpoints(self):
        """Item 2: /api/school/curriculum_pool reports shared stats and pools duplicate curriculum assets."""
        # GET pool stats
        get_res = self.client.get("/api/school/curriculum_pool")
        self.assertEqual(get_res.status_code, 200)
        self.assertIn("Grade 5 Commons", get_res.get_json()["grade_level"])

        # POST pool file
        state = load_state()
        state["scanner"]["files"] = [{
            "file_id": "curr_01",
            "file_name": "Biology_Ch4_Ecosystems.pdf",
            "size_bytes": 25 * 1024 * 1024
        }]
        save_state(state)

        post_res = self.client.post("/api/school/curriculum_pool", json={
            "file_id": "curr_01",
            "file_name": "Biology_Ch4_Ecosystems.pdf",
            "file_size_bytes": 25 * 1024 * 1024,
            "student_id": self.student_id
        })
        self.assertEqual(post_res.status_code, 200)
        self.assertEqual(post_res.get_json()["status"], "success")

        # Verify removed from scanner files
        updated_state = load_state()
        self.assertEqual(len(updated_state["scanner"]["files"]), 0)

    def test_perceptual_asset_pooling(self):
        """Item 10: Meme and stock photo pooling to dynamic web pointers."""
        now = time.time()
        f_meme = {
            "file_name": "drake_meme_presentation.jpg",
            "size_bytes": 2 * 1024 * 1024,
            "last_modified_epoch_s": now,
            "age_days": 1
        }
        res = enrich_file_iq1000(f_meme, now)
        self.assertTrue(res["is_public_asset"])
        self.assertIn("Drake", res["public_asset_name"])
        self.assertTrue(res.get("phash"))

        # Pool public asset
        state = load_state()
        state["scanner"]["files"] = [{"file_id": "meme1", "file_name": "drake_meme.jpg", "size_bytes": 2048000}]
        save_state(state)

        pool_res = self.client.post("/api/scan/pool_public_asset", json={
            "file_id": "meme1",
            "file_name": "drake_meme.jpg",
            "file_size_bytes": 2048000,
            "public_url": res["public_asset_url"],
            "student_id": self.student_id
        })
        self.assertEqual(pool_res.status_code, 200)
        self.assertEqual(pool_res.get_json()["status"], "success")

    def test_polyglot_rehydration_and_translation(self):
        """Item 11: Polyglot strip and dynamic on-demand translation."""
        state = load_state()
        state["scanner"]["files"] = [{"file_id": "poly1", "file_name": "Worksheet_ES.pdf", "size_bytes": 1500000}]
        save_state(state)

        strip_res = self.client.post("/api/scan/polyglot_strip", json={
            "file_id": "poly1",
            "file_name": "Worksheet_ES.pdf",
            "root_file_name": "Worksheet_EN.pdf",
            "file_size_bytes": 1500000,
            "student_id": self.student_id
        })
        self.assertEqual(strip_res.status_code, 200)
        self.assertEqual(strip_res.get_json()["status"], "success")

        trans_res = self.client.post("/api/scan/polyglot_translate", json={
            "text": "Photosynthesis is the process by which green plants transform light energy.",
            "target_lang": "es"
        })
        self.assertEqual(trans_res.status_code, 200)
        self.assertIn("español", trans_res.get_json()["translated_content"].lower())

    def test_screenshot_burst_deduplication(self):
        """Item 13: Consecutive screenshots are grouped into burst stacks with duplicates tagged."""
        now = time.time()
        files = [
            {"file_id": "sc1", "file_name": "Screenshot_1001.png", "is_screenshot": True, "last_modified_epoch_s": now - 100},
            {"file_id": "sc2", "file_name": "Screenshot_1002.png", "is_screenshot": True, "last_modified_epoch_s": now - 70},
            {"file_id": "sc3", "file_name": "Screenshot_1003.png", "is_screenshot": True, "last_modified_epoch_s": now - 40},
            {"file_id": "sc4", "file_name": "Screenshot_2000.png", "is_screenshot": True, "last_modified_epoch_s": now - 10000},
        ]
        bursts = group_screenshot_bursts(files)
        # sc1, sc2, sc3 should form a burst
        burst_items = [f for f in bursts if f.get("burst_group_id")]
        self.assertEqual(len(burst_items), 3)
        self.assertTrue(files[2]["is_burst_primary"])
        self.assertTrue(files[0]["is_burst_duplicate"])
        self.assertTrue(files[1]["is_burst_duplicate"])

    def test_teacher_category_scoped_decide_all(self):
        """Item 15: Teacher can bulk-approve by category (e.g. duplicate or screenshot)."""
        state = load_state()
        state["teacher_queue"] = [
            {"request_id": "R1", "status": "PENDING", "class_code": "grade5", "file_name": "dup_file.pdf", "category": "duplicate", "file_size_bytes": 1000000},
            {"request_id": "R2", "status": "PENDING", "class_code": "grade5", "file_name": "essay_draft.docx", "category": "academic", "file_size_bytes": 2000000}
        ]
        save_state(state)

        res = self.client.post("/api/teacher/decide_all", json={
            "teacher_id": self.teacher_id,
            "class_code": "grade5",
            "category": "duplicate"
        }, headers=self.teacher_headers)

        self.assertEqual(res.status_code, 200)
        updated_state = load_state()
        q = {i["request_id"]: i["status"] for i in updated_state["teacher_queue"]}
        self.assertEqual(q["R1"], "APPROVED")
        self.assertEqual(q["R2"], "PENDING", "Non-matching category must remain PENDING")


if __name__ == "__main__":
    unittest.main()
