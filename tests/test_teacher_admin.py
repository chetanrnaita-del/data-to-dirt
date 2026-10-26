"""
Data-to-Dirt — Teacher & Admin View & Approval Workflow Unit Test Suite (M4)

Comprehensive unit and integration tests covering:
1. Teacher and Admin login with correct/incorrect PINs (RBAC).
2. Session token generation, HMAC validation, expiration, and revocation.
3. Role verification decorator / middleware and hierarchy enforcement.
4. Thread-safe confirmation queue insertion, retrieval, and DeletionRequest model properties.
5. Sorting by AI confidence (lowest first to prioritize suspicious items), filtering, search, pagination.
6. Approve, Reject, and Flag state transitions and workflows (real file recycling, student credits, eco-fund).
7. Aggregate classroom analytics and environmental audit reports.
8. Thread safety under high concurrency.
"""

import os
import sys
import time
import shutil
import tempfile
import unittest
import threading
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.auth import (
    AuthService,
    AuthSession,
    AuthenticationError,
    AuthorizationError,
    ROLE_STUDENT,
    ROLE_TEACHER,
    ROLE_ADMIN,
    DEFAULT_TEACHER_PIN,
    DEFAULT_ADMIN_PIN,
)
from src.services.teacher_queue import (
    TeacherQueue,
    DeletionRequest,
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_FLAGGED,
)
from src.services.analytics import AnalyticsService, ClassroomStats
from src.services.carbon_calculator import CarbonCalculator, calculate_carbon_grams


class MockGamificationTracker:
    """Mock student gamification tracker to test credits and penalties."""
    def __init__(self):
        self.students = {
            "stu_alex": {
                "student_id": "stu_alex",
                "name": "Alex River",
                "points": 200,
                "streak": 5,
                "deleted_bytes": 104857600,
                "strikes": 0,
            },
            "stu_sarah": {
                "student_id": "stu_sarah",
                "name": "Sarah Chen",
                "points": 350,
                "streak": 8,
                "deleted_bytes": 524288000,
                "strikes": 0,
            }
        }

    def record_deletion(self, student_id: str, bytes_deleted: int):
        if student_id not in self.students:
            self.students[student_id] = {
                "student_id": student_id,
                "name": f"Student {student_id}",
                "points": 0,
                "streak": 0,
                "deleted_bytes": 0,
                "strikes": 0,
            }
        stu = self.students[student_id]
        stu["deleted_bytes"] += bytes_deleted
        pts = max(5, int(bytes_deleted / (10 * 1024 * 1024))) + 20
        stu["points"] += pts
        stu["streak"] += 1
        return {"points_earned": pts, "new_total_points": stu["points"], "new_streak": stu["streak"]}

    def register_strike(self, student_id: str):
        if student_id not in self.students:
            self.students[student_id] = {"student_id": student_id, "points": 0, "streak": 0, "strikes": 0}
        stu = self.students[student_id]
        stu["strikes"] = stu.get("strikes", 0) + 1
        stu["streak"] = 0
        stu["points"] = max(0, stu.get("points", 0) - 50)
        return {"strikes": stu["strikes"], "action": "STRIKE_PENALTY"}


class MockEcoFundLedger:
    """Mock Eco-Fund accumulator to test threshold crossing."""
    def __init__(self, initial_budget_usd: float = 100.0, threshold_bytes: int = 1073741824):
        self.budget_usd = initial_budget_usd
        self.threshold_bytes = threshold_bytes
        self.cumulative_waste_bytes = 0
        self.trees_planted = 0
        self.cost_per_tree = 1.50

    def accumulate_waste(self, approved_bytes: int):
        self.cumulative_waste_bytes += approved_bytes
        trees_to_trigger = self.cumulative_waste_bytes // self.threshold_bytes
        trees_new = trees_to_trigger - self.trees_planted
        if trees_new > 0:
            self.trees_planted += trees_new
            self.budget_usd = max(0.0, round(self.budget_usd - (trees_new * self.cost_per_tree), 2))
            return {
                "cumulative_waste": self.cumulative_waste_bytes,
                "trees_triggered": trees_new,
                "status": "DONATION_EXECUTED",
                "remaining_budget": self.budget_usd,
            }
        return {
            "cumulative_waste": self.cumulative_waste_bytes,
            "trees_triggered": 0,
            "status": "ACCUMULATING",
        }


class TestAuthService(unittest.TestCase):
    """Test Role-Based Authentication & Session Management."""

    def setUp(self):
        self.auth = AuthService(
            teacher_pin="teacher123",
            admin_pin="admin2026",
            session_ttl=3600,
        )

    def test_student_login_no_pin_required(self):
        """Student role is guest/default and requires no PIN."""
        res = self.auth.login(role=ROLE_STUDENT)
        self.assertEqual(res["role"], ROLE_STUDENT)
        self.assertTrue(res["is_active"])
        self.assertTrue(len(res["token"]) > 16)

    def test_teacher_login_valid_pin(self):
        """Teacher login succeeds with default PIN 'teacher123'."""
        res = self.auth.login(role=ROLE_TEACHER, pin="teacher123")
        self.assertEqual(res["role"], ROLE_TEACHER)
        self.assertFalse(res["is_expired"])
        self.assertTrue(self.auth.verify_pin(ROLE_TEACHER, "teacher123"))

    def test_teacher_login_invalid_pin_fails(self):
        """Teacher login fails with wrong PIN."""
        with self.assertRaises(AuthenticationError):
            self.auth.login(role=ROLE_TEACHER, pin="wrong_pin")
        self.assertFalse(self.auth.verify_pin(ROLE_TEACHER, "wrong_pin"))

    def test_teacher_pin_case_sensitivity(self):
        """Teacher PIN verification must be strictly case-sensitive."""
        self.assertFalse(self.auth.verify_pin(ROLE_TEACHER, "Teacher123"))
        self.assertFalse(self.auth.verify_pin(ROLE_TEACHER, "TEACHER123"))
        with self.assertRaises(AuthenticationError):
            self.auth.login(role=ROLE_TEACHER, pin="Teacher123")

    def test_admin_login_valid_pin(self):
        """Admin login succeeds with PIN 'admin2026'."""
        res = self.auth.login(role=ROLE_ADMIN, pin="admin2026")
        self.assertEqual(res["role"], ROLE_ADMIN)
        self.assertTrue(self.auth.verify_pin(ROLE_ADMIN, "admin2026"))

    def test_admin_login_invalid_pin_fails(self):
        """Admin login fails with wrong PIN."""
        with self.assertRaises(AuthenticationError):
            self.auth.login(role=ROLE_ADMIN, pin="incorrect_admin")
        self.assertFalse(self.auth.verify_pin(ROLE_ADMIN, "incorrect_admin"))

    def test_empty_pin_rejected_for_privileged_roles(self):
        """Empty or None PIN is rejected for teacher and admin."""
        self.assertFalse(self.auth.verify_pin(ROLE_TEACHER, ""))
        self.assertFalse(self.auth.verify_pin(ROLE_TEACHER, None))
        self.assertFalse(self.auth.verify_pin(ROLE_ADMIN, ""))
        self.assertFalse(self.auth.verify_pin(ROLE_ADMIN, None))

    def test_unknown_role_fails(self):
        """Attempting to authenticate an undefined role raises AuthenticationError."""
        with self.assertRaises(AuthenticationError):
            self.auth.login(role="super_user", pin="1234")

    def test_session_token_validation_and_expiration(self):
        """Tokens validate when active, and fail when expired."""
        # Short TTL session: 1 second
        session = self.auth.login(role=ROLE_TEACHER, pin="teacher123", ttl_seconds=1)
        token = session["token"]

        # Immediately valid
        val = self.auth.validate_token(token)
        self.assertIsNotNone(val)
        self.assertEqual(val["role"], ROLE_TEACHER)

        # Wait for expiration
        time.sleep(1.1)
        val_expired = self.auth.validate_token(token)
        self.assertIsNone(val_expired, "Expired token must return None")

    def test_token_revocation(self):
        """Revoking a session token immediately renders it invalid."""
        session = self.auth.login(role=ROLE_TEACHER, pin="teacher123")
        token = session["token"]

        self.assertIsNotNone(self.auth.validate_token(token))
        revoked = self.auth.revoke_token(token)
        self.assertTrue(revoked)
        self.assertIsNone(self.auth.validate_token(token))

    def test_purge_expired_sessions(self):
        """Purge removes expired and revoked sessions from memory."""
        s1 = self.auth.login(role=ROLE_STUDENT, ttl_seconds=1)
        s2 = self.auth.login(role=ROLE_TEACHER, pin="teacher123", ttl_seconds=3600)
        self.auth.revoke_token(s2["token"])

        time.sleep(1.1)
        purged_count = self.auth.purge_expired_sessions()
        self.assertGreaterEqual(purged_count, 2)

    def test_role_hierarchy_permissions(self):
        """Role hierarchy: Admin (3) >= Teacher (2) >= Student (1)."""
        admin_sess = self.auth.login(role=ROLE_ADMIN, pin="admin2026")
        teacher_sess = self.auth.login(role=ROLE_TEACHER, pin="teacher123")
        student_sess = self.auth.login(role=ROLE_STUDENT)

        # Admin satisfies all
        self.assertTrue(self.auth.has_role(admin_sess["token"], ROLE_ADMIN))
        self.assertTrue(self.auth.has_role(admin_sess["token"], ROLE_TEACHER))
        self.assertTrue(self.auth.has_role(admin_sess["token"], ROLE_STUDENT))

        # Teacher satisfies teacher and student, not admin
        self.assertFalse(self.auth.has_role(teacher_sess["token"], ROLE_ADMIN))
        self.assertTrue(self.auth.has_role(teacher_sess["token"], ROLE_TEACHER))
        self.assertTrue(self.auth.has_role(teacher_sess["token"], ROLE_STUDENT))

        # Student satisfies only student
        self.assertFalse(self.auth.has_role(student_sess["token"], ROLE_ADMIN))
        self.assertFalse(self.auth.has_role(student_sess["token"], ROLE_TEACHER))
        self.assertTrue(self.auth.has_role(student_sess["token"], ROLE_STUDENT))

    def test_require_role_decorator(self):
        """Test function decorated with @require_role."""
        @self.auth.require_role(ROLE_TEACHER)
        def teacher_only_action(data_param: str, token: str = None):
            return f"Action done: {data_param}"

        teacher_sess = self.auth.login(role=ROLE_TEACHER, pin="teacher123")
        student_sess = self.auth.login(role=ROLE_STUDENT)

        # Valid teacher executes cleanly
        res = teacher_only_action("grade_test", token=teacher_sess["token"])
        self.assertEqual(res, "Action done: grade_test")

        # Student is blocked with AuthorizationError
        with self.assertRaises(AuthorizationError):
            teacher_only_action("grade_test", token=student_sess["token"])

        # Missing token is blocked with AuthenticationError
        with self.assertRaises(AuthenticationError):
            teacher_only_action("grade_test", token=None)


class TestTeacherConfirmationQueue(unittest.TestCase):
    """Test Teacher Confirmation Queue, Decision Workflows, and Lifecycle."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="d2d_test_queue_")
        self.gamification = MockGamificationTracker()
        self.ledger = MockEcoFundLedger()
        self.auth = AuthService()
        self.queue = TeacherQueue(
            ledger=self.ledger,
            gamification=self.gamification,
            auth_service=self.auth,
            teacher_pin="teacher123",
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_submit_request_model_and_id(self):
        """Submitting request generates REQ-xxxx ID with valid DeletionRequest model."""
        rid = self.queue.submit_request(
            student_id="stu_alex",
            file_name="Video_Take1_Uncut.mov",
            size_bytes=524288000,
            reason="Redundant raw camera take",
            ai_score=0.88,
            ai_summary="Verified: Redundant video asset",
            file_path="/tmp/Video_Take1_Uncut.mov",
            student_name="Alex River",
        )
        self.assertTrue(rid.startswith("REQ-"))
        self.assertEqual(len(self.queue), 1)

        req = self.queue.get_by_id(rid)
        self.assertIsNotNone(req)
        self.assertEqual(req.student_id, "stu_alex")
        self.assertEqual(req.file_name, "Video_Take1_Uncut.mov")
        self.assertEqual(req.file_size_bytes, 524288000)
        self.assertGreater(req.carbon_offset_grams, 0)
        self.assertEqual(req.status, STATUS_PENDING)
        self.assertEqual(req.ai_confidence_score, 0.88)
        self.assertIn("Verified", req.ai_summary)

        # Verify dictionary compatibility
        self.assertEqual(req["request_id"], rid)
        self.assertEqual(req["size_bytes"], 524288000)
        self.assertEqual(req["status"], "PENDING")

    def test_sorting_by_ai_confidence_lowest_first(self):
        """Sorting by confidence lowest-first highlights suspicious items first."""
        self.queue.submit_request("stu_1", "file_high.mp4", 1000, "legit", 0.92, "Verified high")
        self.queue.submit_request("stu_2", "file_suspicious.docx", 2000, "asdf", 0.18, "Gaming alert")
        self.queue.submit_request("stu_3", "file_mid.tmp", 1500, "cache", 0.65, "Moderate")

        # Ascending: lowest first (0.18, 0.65, 0.92)
        res_asc = self.queue.get_queue(sort_by="confidence", sort_asc=True)
        scores_asc = [item["ai_confidence_score"] for item in res_asc["items"]]
        self.assertEqual(scores_asc, [0.18, 0.65, 0.92])

        # Descending: highest first (0.92, 0.65, 0.18)
        res_desc = self.queue.get_queue(sort_by="confidence", sort_asc=False)
        scores_desc = [item["ai_confidence_score"] for item in res_desc["items"]]
        self.assertEqual(scores_desc, [0.92, 0.65, 0.18])

    def test_filtering_and_searching(self):
        """Filter by status, student_id, and free-text search."""
        rid1 = self.queue.submit_request("stu_alex", "Final_Presentation.mp4", 10000, "old take", 0.85, "Verified")
        rid2 = self.queue.submit_request("stu_sarah", "Physics_Notes_Stale.pdf", 5000, "archive", 0.75, "Verified")
        rid3 = self.queue.submit_request("stu_alex", "Temp_Cache.tmp", 2000, "temp", 0.90, "Verified")

        self.queue.approve(rid1)
        self.queue.reject(rid2, "Keep your physics notes")

        # Filter by status
        pending_list = self.queue.get_queue(status="pending")["items"]
        self.assertEqual(len(pending_list), 1)
        self.assertEqual(pending_list[0]["id"], rid3)

        approved_list = self.queue.get_queue(status="approved")["items"]
        self.assertEqual(len(approved_list), 1)
        self.assertEqual(approved_list[0]["id"], rid1)

        # Search query by keyword
        search_res = self.queue.get_queue(search_query="physics")["items"]
        self.assertEqual(len(search_res), 1)
        self.assertEqual(search_res[0]["id"], rid2)

        # Search query by student
        sarah_res = self.queue.get_queue(student_id="stu_sarah")["items"]
        self.assertEqual(len(sarah_res), 1)

    def test_pagination(self):
        """Pagination breaks large queues into discrete pages."""
        for i in range(15):
            self.queue.submit_request(f"stu_{i}", f"file_{i}.tmp", 1000, "clean", 0.8, "Summary")

        page1 = self.queue.get_queue(page=1, page_size=5)
        self.assertEqual(len(page1["items"]), 5)
        self.assertEqual(page1["total_count"], 15)
        self.assertEqual(page1["total_pages"], 3)
        self.assertEqual(page1["page"], 1)

        page3 = self.queue.get_queue(page=3, page_size=5)
        self.assertEqual(len(page3["items"]), 5)
        self.assertEqual(page3["page"], 3)

    def test_approve_action_workflow_and_file_recycling(self):
        """Approve removes file via Send2Trash, credits student, and accumulates Eco-Fund."""
        # Create a real file on disk in sandbox
        real_file = os.path.join(self.test_dir, "real_delete_candidate.mov")
        with open(real_file, "wb") as f:
            f.write(b"0" * 1024 * 1024)  # 1 MB real file
        self.assertTrue(os.path.exists(real_file))

        initial_points = self.gamification.students["stu_alex"]["points"]
        initial_streak = self.gamification.students["stu_alex"]["streak"]

        rid = self.queue.submit_request(
            student_id="stu_alex",
            file_name="real_delete_candidate.mov",
            size_bytes=1024 * 1024,
            reason="Uncut video footage",
            ai_score=0.85,
            ai_summary="Verified video redundancy",
            file_path=real_file,
        )

        res = self.queue.approve(rid, teacher_id="TEACHER-MR-SMITH")
        self.assertEqual(res["status"], "APPROVED")
        self.assertEqual(res["decided_by"], "TEACHER-MR-SMITH")
        self.assertTrue(res["recycled"])

        # File is recycled / removed from its original path
        self.assertFalse(os.path.exists(real_file), "File must be removed/recycled upon teacher approval")

        # Student gamification updated
        new_stu = self.gamification.students["stu_alex"]
        self.assertGreater(new_stu["points"], initial_points)
        self.assertEqual(new_stu["streak"], initial_streak + 1)

        # Eco-fund accumulated bytes
        self.assertEqual(self.ledger.cumulative_waste_bytes, 1024 * 1024)

    def test_approve_threshold_crossing_triggers_tree_donation(self):
        """Accumulating 1.0 GB or more triggers Tree-Nation micro-donation."""
        # Submit and approve 1.2 GB waste
        rid = self.queue.submit_request(
            student_id="stu_sarah",
            file_name="heavy_dataset.tar",
            size_bytes=int(1.2 * 1073741824),
            reason="Obsolete large dataset",
            ai_score=0.95,
            ai_summary="Verified",
        )
        res = self.queue.approve(rid)
        self.assertTrue(res["donation_triggered"])
        self.assertEqual(self.ledger.trees_planted, 1)
        self.assertAlmostEqual(self.ledger.budget_usd, 100.0 - 1.50, places=2)

    def test_reject_action_preserves_file_and_protects_student(self):
        """Reject preserves file on disk, logs feedback, and protects student points."""
        real_file = os.path.join(self.test_dir, "keep_this_file.docx")
        with open(real_file, "w") as f:
            f.write("Important course notes.")
        self.assertTrue(os.path.exists(real_file))

        pts_before = self.gamification.students["stu_alex"]["points"]
        streak_before = self.gamification.students["stu_alex"]["streak"]

        rid = self.queue.submit_request(
            student_id="stu_alex",
            file_name="keep_this_file.docx",
            size_bytes=1000,
            reason="not sure",
            ai_score=0.45,
            ai_summary="Vague reason",
            file_path=real_file,
        )

        res = self.queue.reject(rid, teacher_id_or_reason="TEACHER-001", reason="Please keep this file for semester 2.")
        self.assertEqual(res["status"], "REJECTED")
        self.assertIn("Please keep this file", res["feedback"])

        # File is preserved
        self.assertTrue(os.path.exists(real_file), "Rejected file must remain intact on disk")

        # Student profile is untouched
        self.assertEqual(self.gamification.students["stu_alex"]["points"], pts_before)
        self.assertEqual(self.gamification.students["stu_alex"]["streak"], streak_before)

    def test_flag_action_enforces_disciplinary_strike(self):
        """Flag preserves file, resets streak to 0, deducts points, and logs strike."""
        rid = self.queue.submit_request(
            student_id="stu_alex",
            file_name="system_library.dll",
            size_bytes=5000,
            reason="free points farm",
            ai_score=0.12,
            ai_summary="Malicious / gaming attempt",
        )

        res = self.queue.flag(rid, "TEACHER-001", "Intentional score gaming strike")
        self.assertEqual(res["status"], "FLAGGED")

        stu = self.gamification.students["stu_alex"]
        self.assertEqual(stu["streak"], 0, "Streak must reset to 0 upon flag")
        self.assertEqual(stu["strikes"], 1)

    def test_double_decision_prevented(self):
        """Attempting to decide an already approved/rejected request raises ValueError."""
        rid = self.queue.submit_request("stu_alex", "doc.txt", 100, "clean", 0.8, "Verified")
        self.queue.approve(rid)

        with self.assertRaises(ValueError):
            self.queue.approve(rid)
        with self.assertRaises(ValueError):
            self.queue.reject(rid, "too late")
        with self.assertRaises(ValueError):
            self.queue.flag(rid, "too late")

    def test_nonexistent_request_decision_fails(self):
        """Calling approve/reject/flag with an unknown ID raises KeyError."""
        with self.assertRaises(KeyError):
            self.queue.approve("REQ-NONEXISTENT")
        with self.assertRaises(KeyError):
            self.queue.reject("REQ-NONEXISTENT", "note")
        with self.assertRaises(KeyError):
            self.queue.flag("REQ-NONEXISTENT", "note")


class TestClassroomAnalytics(unittest.TestCase):
    """Test Classroom Analytics Calculation & CSV Reporting."""

    def test_aggregate_analytics_calculation(self):
        queue = TeacherQueue()
        # 2 Approved requests
        r1 = queue.submit_request("stu_1", "f1.mp4", 1073741824, "take1", 0.9, "Verified") # 1 GB
        r2 = queue.submit_request("stu_2", "f2.mov", 2147483648, "take2", 0.85, "Verified") # 2 GB
        # 1 Rejected
        r3 = queue.submit_request("stu_1", "f3.docx", 50000, "draft", 0.4, "Vague")
        # 1 Flagged
        r4 = queue.submit_request("stu_3", "f4.exe", 10000, "farm", 0.1, "Gaming")

        queue.approve(r1)
        queue.approve(r2)
        queue.reject(r3, "Keep file")
        queue.flag(r4, "Strike logged")

        stats = queue.get_analytics()

        self.assertEqual(stats["total_requests"], 4)
        self.assertEqual(stats["approved_count"], 2)
        self.assertEqual(stats["rejected_count"], 1)
        self.assertEqual(stats["flagged_count"], 1)
        self.assertAlmostEqual(stats["total_data_cleaned_gb"], 3.0, places=2)
        self.assertGreater(stats["total_carbon_offset_kg"], 0.2)
        self.assertEqual(stats["active_students_count"], 3)
        self.assertEqual(stats["total_trees_funded"], 3)
        self.assertEqual(len(stats["incident_log"]), 1)
        self.assertEqual(stats["incident_log"][0]["student_id"], "stu_3")
        self.assertGreater(stats["car_km_avoided"], 0.0)
        self.assertGreater(stats["smartphone_charges_avoided"], 0.0)

    def test_csv_report_generation(self):
        queue = TeacherQueue()
        rid = queue.submit_request("stu_alex", "clip.mp4", 1073741824, "old clip", 0.9, "Verified")
        queue.approve(rid)

        stats_obj = AnalyticsService.calculate_analytics(queue.queue)
        csv_str = AnalyticsService.export_csv_report(stats_obj)

        self.assertIn("Total Deletion Requests,1,count", csv_str)
        self.assertIn("Approved Deletions,1,count", csv_str)
        self.assertIn("Total Data Cleared,1.0000,GB", csv_str)


class TestConcurrencyAndThreadSafety(unittest.TestCase):
    """Test thread safety under high concurrency."""

    def test_concurrent_request_submissions(self):
        queue = TeacherQueue()
        num_threads = 20
        requests_per_thread = 10
        errors = []

        def worker(thread_idx: int):
            try:
                for i in range(requests_per_thread):
                    queue.submit_request(
                        student_id=f"stu_thread_{thread_idx}",
                        file_name=f"file_{thread_idx}_{i}.mp4",
                        size_bytes=1000 * (i + 1),
                        reason="batch clean",
                        ai_score=0.8,
                        ai_summary="Verified",
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(queue), num_threads * requests_per_thread)

        # Check unique IDs
        all_ids = [item.id for item in queue.queue]
        self.assertEqual(len(all_ids), len(set(all_ids)), "All generated request IDs must be strictly unique")


class TestTeacherDeduplicationAndManagement(unittest.TestCase):
    def setUp(self):
        from src.app.server import app
        self.app = app
        self.client = self.app.test_client()
        # Log in as admin to get admin token
        res = self.client.post("/api/auth/login", json={
            "role": "admin",
            "user_id": "admin",
            "pin": "admin2026"
        })
        self.admin_token = res.get_json().get("token")

    def test_auth_teachers_deduplication_and_filtering(self):
        """Verify /api/auth/teachers filters test accounts and returns strictly unique teachers."""
        res = self.client.get("/api/auth/teachers")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "ok")
        teachers = data["teachers"]

        # Check no test accounts present
        for t in teachers:
            self.assertFalse(t["teacher_id"].startswith("test_"), f"Test teacher found: {t['teacher_id']}")
            self.assertFalse(t["teacher_id"].startswith("live_teacher_"), f"Live test teacher found: {t['teacher_id']}")
            self.assertNotEqual(t["teacher_id"].lower(), "teacher-001")

        # Check all names are unique
        names = [t["name"] for t in teachers]
        self.assertEqual(len(names), len(set(names)), f"Duplicate teacher names found: {names}")

    def test_admin_teacher_duplicate_rejection(self):
        """Admin attempting to create a teacher with an existing name is rejected with 409."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        # First creation attempt
        res1 = self.client.post("/api/admin/teachers/create", headers=headers, json={
            "name": "Prof. Charles Babbage",
            "teacher_id": "teacher_babbage",
            "class_code": "cs301",
            "pin": "babbage123"
        })
        self.assertIn(res1.status_code, [201, 409])

        # Second creation attempt with same name
        res2 = self.client.post("/api/admin/teachers/create", headers=headers, json={
            "name": "Prof. Charles Babbage",
            "teacher_id": "teacher_babbage_2",
            "class_code": "cs301",
            "pin": "babbage123"
        })
        self.assertEqual(res2.status_code, 409)
        self.assertIn("already exists", res2.get_json()["message"].lower())

        # Cleanup: delete created teacher
        del_res = self.client.post("/api/admin/teachers/delete", headers=headers, json={
            "teacher_id": "teacher_babbage"
        })
        self.assertEqual(del_res.status_code, 200)

    def test_admin_delete_protected_system_teachers(self):
        """Admin attempting to delete a built-in system teacher is rejected."""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.post("/api/admin/teachers/delete", headers=headers, json={
            "teacher_id": "teacher_bio101"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("cannot delete built-in", res.get_json()["message"].lower())


if __name__ == "__main__":
    unittest.main()
