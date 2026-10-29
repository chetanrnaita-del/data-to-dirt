import os
import time
import unittest
import json
import copy
from src.app.server import app, load_state, save_state, reset_all_auth_lockouts, create_flask_app
from src.services.auth import default_auth_service

class TestLiveAuthentication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._class_saved_state = copy.deepcopy(load_state())

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_class_saved_state") and cls._class_saved_state:
            save_state(copy.deepcopy(cls._class_saved_state))
        reset_all_auth_lockouts()

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.orig_state = copy.deepcopy(self._class_saved_state)
        reset_all_auth_lockouts()
        state = load_state()
        if not any(s.get("student_id") == "STU-001" for s in state.get("students", [])):
            state.setdefault("students", []).append({
                "student_id": "STU-001",
                "name": "Alex River",
                "class_code": "bio101",
                "role": "student"
            })
            save_state(state)

    def tearDown(self):
        save_state(copy.deepcopy(self.orig_state))
        reset_all_auth_lockouts()

    def test_student_unknown_username_rejected(self):
        """Any random student username is rejected with 401."""
        res = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": "nonexistent_student_99999",
            "pin": "bio101"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("not found", data["message"].lower())

    def test_student_wrong_class_code_rejected(self):
        """Valid student ID with incorrect class code/password is rejected with 401."""
        res = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": "STU-001",
            "pin": "wrong_class_code"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("incorrect class code", data["message"].lower())

    def test_student_valid_credentials_succeeds(self):
        """Valid student ID and matching class code succeeds."""
        res = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": "STU-001",
            "pin": "bio101"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "authenticated")
        self.assertEqual(data["role"], "student")
        self.assertEqual(data["user_id"], "STU-001")
        self.assertEqual(data["class_code"], "bio101")
        self.assertIn("token", data)

    def test_student_valid_name_succeeds(self):
        """Valid student full name and matching class code succeeds."""
        res = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": "Alex River",
            "pin": "bio101"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "authenticated")
        self.assertEqual(data["user_id"], "STU-001")
        self.assertEqual(data["student_name"], "Alex River")

    def test_student_valid_name_wrong_class_code_rejected(self):
        """Valid student full name with wrong class code is rejected with 401."""
        res = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": "Alex River",
            "pin": "cs301"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("incorrect class code", data["message"].lower())

    def test_teacher_fake_account_rejected(self):
        """Non-existent teacher account is rejected with 401."""
        res = self.client.post("/api/auth/login", json={
            "role": "teacher",
            "user_id": "fake_teacher_random",
            "pin": "teacher123"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("not found", data["message"].lower())

    def test_teacher_wrong_password_rejected(self):
        """Valid teacher account with wrong password is rejected with 401."""
        res = self.client.post("/api/auth/login", json={
            "role": "teacher",
            "user_id": "teacher_cs301",
            "pin": "wrongpass123"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("invalid teacher password", data["message"].lower())

    def test_teacher_shorthand_pin_rejected(self):
        """Teacher login rejects lazy shortcuts like '1234'."""
        res = self.client.post("/api/auth/login", json={
            "role": "teacher",
            "user_id": "teacher_cs301",
            "pin": "1234"
        })
        self.assertEqual(res.status_code, 401)

    def test_teacher_valid_credentials_succeeds(self):
        """Valid teacher account with 'teacher123' succeeds."""
        res = self.client.post("/api/auth/login", json={
            "role": "teacher",
            "user_id": "teacher_cs301",
            "pin": "teacher123"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "authenticated")
        self.assertEqual(data["role"], "teacher")
        self.assertEqual(data["class_code"], "cs301")

    def test_admin_fake_username_rejected(self):
        """Admin login with unrecognized username is rejected with 401."""
        res = self.client.post("/api/auth/login", json={
            "role": "admin",
            "user_id": "not_an_admin",
            "pin": "admin2026"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("not recognized", data["message"].lower())

    def test_admin_wrong_passcode_rejected(self):
        """Admin login with wrong passcode is rejected with 401."""
        res = self.client.post("/api/auth/login", json={
            "role": "admin",
            "user_id": "admin",
            "pin": "wrongpass"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("invalid administrator passcode", data["message"].lower())

    def test_admin_backdoors_rejected(self):
        """Admin login rejects backdoors like '1234', 'code', 'password', 'root'."""
        for bad_pin in ["1234", "code", "password", "root"]:
            res = self.client.post("/api/auth/login", json={
                "role": "admin",
                "user_id": "admin",
                "pin": bad_pin
            })
            self.assertEqual(res.status_code, 401, f"Failed for bad_pin: {bad_pin}")

    def test_admin_valid_passcode_succeeds(self):
        """Admin login with 'admin2026' succeeds."""
        res = self.client.post("/api/auth/login", json={
            "role": "admin",
            "user_id": "admin",
            "pin": "admin2026"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "authenticated")
        self.assertEqual(data["role"], "admin")

    def test_safety_lock_activates_after_three_wrong_passwords(self):
        """Entering 3 wrong passwords activates a 10-second safety lockout."""
        # Attempt 1: wrong password
        r1 = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": "STU-001",
            "pin": "wrong1"
        })
        self.assertEqual(r1.status_code, 401)
        self.assertEqual(r1.get_json().get("failed_attempts"), 1)

        # Attempt 2: wrong password
        r2 = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": "STU-001",
            "pin": "wrong2"
        })
        self.assertEqual(r2.status_code, 401)
        self.assertEqual(r2.get_json().get("failed_attempts"), 2)

        # Attempt 3: 3rd wrong password triggers safety lock of 10s
        r3 = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": "STU-001",
            "pin": "wrong3"
        })
        self.assertEqual(r3.status_code, 401)
        d3 = r3.get_json()
        self.assertEqual(d3.get("error_code"), "safety_lock")
        self.assertEqual(d3.get("failed_attempts"), 3)
        self.assertEqual(d3.get("lockout_seconds"), 10)
        self.assertIn("safety lock active", d3.get("message", "").lower())

        # Attempt while locked out is blocked even with correct password
        r_blocked = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": "STU-001",
            "pin": "bio101"
        })
        self.assertEqual(r_blocked.status_code, 401)
        self.assertEqual(r_blocked.get_json().get("error_code"), "safety_lock")

    def test_safety_lock_time_increases_with_further_wrong_passwords(self):
        """Each additional wrong password after the 3rd increases lockout duration (+10s per extra attempt)."""
        # Fail 3 times -> 10s
        for i in range(1, 4):
            self.client.post("/api/auth/login", json={
                "role": "teacher",
                "user_id": "teacher_bio101",
                "pin": f"bad_{i}"
            })

        # 4th wrong password -> increases lockout to 20s
        import time
        from src.app.server import _auth_failed_attempts, get_lockout_key, _auth_lockout_lock
        # Fast-forward lockout expiry so 4th attempt can be made
        key = get_lockout_key("teacher", "teacher_bio101", "127.0.0.1")
        with _auth_lockout_lock:
            if key in _auth_failed_attempts:
                _auth_failed_attempts[key]["lockout_until"] = time.time() - 1

        r4 = self.client.post("/api/auth/login", json={
            "role": "teacher",
            "user_id": "teacher_bio101",
            "pin": "bad_4"
        })
        self.assertEqual(r4.status_code, 401)
        d4 = r4.get_json()
        self.assertEqual(d4.get("error_code"), "safety_lock")
        self.assertEqual(d4.get("failed_attempts"), 4)
        self.assertEqual(d4.get("lockout_seconds"), 20)

        # Fast-forward lockout expiry again
        with _auth_lockout_lock:
            if key in _auth_failed_attempts:
                _auth_failed_attempts[key]["lockout_until"] = time.time() - 1

        # 5th wrong password -> increases lockout to 30s
        r5 = self.client.post("/api/auth/login", json={
            "role": "teacher",
            "user_id": "teacher_bio101",
            "pin": "bad_5"
        })
        self.assertEqual(r5.status_code, 401)
        d5 = r5.get_json()
        self.assertEqual(d5.get("error_code"), "safety_lock")
        self.assertEqual(d5.get("failed_attempts"), 5)
        self.assertEqual(d5.get("lockout_seconds"), 30)

        # Successful login clears the lockout
        with _auth_lockout_lock:
            if key in _auth_failed_attempts:
                _auth_failed_attempts[key]["lockout_until"] = time.time() - 1

        r_ok = self.client.post("/api/auth/login", json={
            "role": "teacher",
            "user_id": "teacher_bio101",
            "pin": "teacher123"
        })
        self.assertEqual(r_ok.status_code, 200)
        self.assertEqual(r_ok.get_json().get("status"), "authenticated")
        with _auth_lockout_lock:
            self.assertNotIn(key, _auth_failed_attempts)


class IndividualDailyDeletionIsolationTest(unittest.TestCase):
    """Verifies that daily deletions are strictly isolated per individual student and never pooled class-wide."""

    @classmethod
    def setUpClass(cls):
        cls._class_saved_state = copy.deepcopy(load_state())

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_class_saved_state") and cls._class_saved_state:
            save_state(copy.deepcopy(cls._class_saved_state))

    def setUp(self):
        os.environ["TEST_MODE"] = "0"  # Enforce strict daily limit enforcement
        self.app = create_flask_app()
        self.client = self.app.test_client()

    def tearDown(self):
        os.environ["TEST_MODE"] = "1"

    def test_individual_student_daily_deletions_isolation(self):
        """Student A reaching the daily deletion limit must NOT block Student B."""
        student_a = f"STU_INDIV_A_{int(time.time())}"
        student_b = f"STU_INDIV_B_{int(time.time())}"

        # 1. Student A submits 5 deletion requests
        for i in range(5):
            res = self.client.post("/api/deletion/submit", json={
                "student_id": student_a,
                "file_id": f"file_a_{i}_{time.time()}",
                "file_name": f"test_doc_a_{i}.pdf",
                "file_size": 2 * 1024 * 1024,
                "reason": "Old duplicate study notes from past biology exam",
                "is_drive": False
            })
            self.assertEqual(res.status_code, 200, f"Deletion {i+1} for Student A should succeed")

        # 2. Student A stats should show 5/5 deletions and can_delete == False
        stats_a = self.client.get(f"/api/student/stats?student_id={student_a}").get_json()
        self.assertEqual(stats_a.get("daily_deletions_today"), 5)
        self.assertEqual(stats_a.get("daily_deletion_limit"), 5)
        self.assertFalse(stats_a.get("can_delete"))

        # 3. Student A's 6th deletion must be blocked with HTTP 429
        res_a_6 = self.client.post("/api/deletion/submit", json={
            "student_id": student_a,
            "file_id": f"file_a_extra_{time.time()}",
            "file_name": "extra_doc.pdf",
            "file_size": 1024 * 1024,
            "reason": "Old duplicate study notes from past biology exam",
            "is_drive": False
        })
        self.assertEqual(res_a_6.status_code, 429)
        self.assertEqual(res_a_6.get_json().get("status"), "limit_exceeded")

        # 4. Student B stats must be completely isolated at 0/5
        stats_b = self.client.get(f"/api/student/stats?student_id={student_b}").get_json()
        self.assertEqual(stats_b.get("daily_deletions_today"), 0, "Student B must start with 0 deletions")
        self.assertEqual(stats_b.get("daily_deletion_limit"), 5)
        self.assertTrue(stats_b.get("can_delete"), "Student B must be permitted to delete")

        # 5. Student B submits their first deletion and succeeds
        res_b_1 = self.client.post("/api/deletion/submit", json={
            "student_id": student_b,
            "file_id": f"file_b_1_{time.time()}",
            "file_name": "chem_lab_duplicate.pdf",
            "file_size": 3 * 1024 * 1024,
            "reason": "Obsolete chemistry lab draft from previous semester",
            "is_drive": False
        })
        self.assertEqual(res_b_1.status_code, 200, "Student B's deletion must succeed independently")
        stats_b_after = self.client.get(f"/api/student/stats?student_id={student_b}").get_json()
        self.assertEqual(stats_b_after.get("daily_deletions_today"), 1)
        self.assertTrue(stats_b_after.get("can_delete"))

    def test_daily_deletion_resets_on_new_calendar_day(self):
        """When calendar day advances, student daily deletions must automatically reset to 0."""
        student_c = f"STU_INDIV_C_{int(time.time())}"
        
        # Populate student C with yesterday's date and 5 deletions
        from src.app.server import load_state, save_state, resolve_student_in_state
        state = load_state()
        stu = resolve_student_in_state(state, student_c)
        stu["daily_deletions_today"] = 5
        stu["last_deletion_date"] = "2020-01-01"  # Old date
        save_state(state)

        # Checking stats should reset daily_deletions_today to 0
        stats = self.client.get(f"/api/student/stats?student_id={student_c}").get_json()
        self.assertEqual(stats.get("daily_deletions_today"), 0)
        self.assertTrue(stats.get("can_delete"))

    def test_cache_control_headers_prevent_stale_cache(self):
        """Index, JS, and Service Worker responses must have no-cache headers."""
        r_index = self.client.get("/")
        self.assertIn("no-cache", r_index.headers.get("Cache-Control", ""))
        self.assertIn("no-store", r_index.headers.get("Cache-Control", ""))

        r_sw = self.client.get("/sw.js")
        self.assertIn("no-cache", r_sw.headers.get("Cache-Control", ""))

    def test_no_autofill_banner_in_login_view(self):
        """Verifies that login.js contains zero autofill banner or recent account buttons."""
        login_js_path = os.path.join(os.path.dirname(__file__), "..", "src", "ui", "js", "views", "login.js")
        with open(login_js_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("Auto-Fill", content)
        self.assertNotIn("recent-account-banner", content)
        self.assertNotIn("btn-use-recent", content)
        self.assertIn('autocomplete="off"', content)


    def test_student_leaderboard_class_isolation_and_trees_defined(self):
        """Verifies students in respective classes only appear in their class leaderboard and trees is always an integer."""
        from src.app.server import load_state, save_state
        state = load_state()
        ts = int(time.time())
        stu_bio = {
            "student_id": f"STU_BIO_{ts}",
            "name": f"Bio Student {ts}",
            "class_code": "bio101",
            "eco_points": 50,
            "bytes_cleared": 1024 * 1024 * 100,
            "trees": 1
        }
        stu_cs = {
            "student_id": f"STU_CS_{ts}",
            "name": f"CS Student {ts}",
            "class_code": "cs301",
            "eco_points": 80,
            "bytes_cleared": 1024 * 1024 * 200,
            "trees": 2
        }
        state["students"].extend([stu_bio, stu_cs])
        save_state(state)

        # Query BIO101 leaderboard
        res_bio = self.client.get(f"/api/student/leaderboard?class_code=bio101&student_id={stu_bio['student_id']}")
        self.assertEqual(res_bio.status_code, 200)
        data_bio = res_bio.get_json()
        lb_bio = data_bio.get("leaderboard", [])
        bio_ids = [entry.get("student_id") for entry in lb_bio]
        self.assertIn(stu_bio["student_id"], bio_ids)
        self.assertNotIn(stu_cs["student_id"], bio_ids, "CS student must not appear in BIO101 leaderboard")

        # Every entry must have trees as integer >= 0, never None or undefined
        for entry in lb_bio:
            self.assertIsNotNone(entry.get("trees"))
            self.assertIsInstance(entry.get("trees"), int)
            self.assertGreaterEqual(entry.get("trees"), 0)

        # Query CS301 leaderboard
        res_cs = self.client.get(f"/api/student/leaderboard?class_code=cs301&student_id={stu_cs['student_id']}")
        self.assertEqual(res_cs.status_code, 200)
        data_cs = res_cs.get_json()
        lb_cs = data_cs.get("leaderboard", [])
        cs_ids = [entry.get("student_id") for entry in lb_cs]
        self.assertIn(stu_cs["student_id"], cs_ids)
        self.assertNotIn(stu_bio["student_id"], cs_ids, "Bio student must not appear in CS301 leaderboard")

    def test_teacher_students_strictly_scoped_to_assigned_class(self):
        """Teacher session token for bio101 strictly scopes student directory to bio101."""
        from src.services.auth import default_auth_service
        teacher_session = default_auth_service.create_session(
            role="teacher",
            user_id="teacher_bio101",
            class_code="bio101",
            name="Dr. Reed"
        )
        token = teacher_session["token"]

        res = self.client.get("/api/teacher/students", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        students = data.get("students", [])
        for s in students:
            self.assertEqual(s.get("class_code", "").lower(), "bio101", f"Student {s} has wrong class for Dr. Reed")

    def test_google_oauth_profile_resolution_unifies_with_fuzzy_matching_student(self):
        """Google OAuth userinfo with slight spelling variation resolves to authentic student record without duplicating."""
        from unittest.mock import patch, MagicMock
        from src.app.server import _resolve_google_user_profile, resolve_student_in_state

        state = load_state()
        state["students"] = [
            {
                "student_id": "STU-8SB8FZ",
                "user_id": "STU-8SB8FZ",
                "name": "Aaryan Agarawal",
                "class_code": "grade5",
                "bytes_cleared": 77004,
                "eco_points": 20,
                "streak_days": 2,
                "daily_deletions_today": 1,
                "daily_deletion_limit": 5,
                "strikes": 0
            }
        ]
        save_state(state)

        # Mock urllib.request.urlopen returning Google profile with lowercase / alternate spelling
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "name": "aaryan agarwal",
            "email": "aaryan.agarwal@lighthouse.edu",
            "sub": "1234567890"
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            profile = _resolve_google_user_profile("fake_token", provider="school", target_grade="grade5")

        self.assertEqual(profile["student_id"], "STU-8SB8FZ")
        self.assertEqual(profile["name"], "Aaryan Agarawal")
        self.assertEqual(profile["class_code"], "grade5")
        self.assertTrue(profile["existing"])

        # Check persisted state: points preserved and email linked
        curr_state = load_state()
        stu = next((s for s in curr_state.get("students", []) if s.get("student_id") == "STU-8SB8FZ"), None)
        self.assertIsNotNone(stu)
        self.assertEqual(stu["eco_points"], 20)
        self.assertEqual(stu["bytes_cleared"], 77004)
        self.assertEqual(stu["email"], "aaryan.agarwal@lighthouse.edu")
        # Ensure no duplicate student exists
        self.assertEqual(len(curr_state.get("students", [])), 1)

    def test_leaderboard_deduplication_and_you_tag(self):
        """Leaderboard deduplicates fuzzy matching students and correctly tags (You)."""
        state = load_state()
        state["students"] = [
            {
                "student_id": "STU-8SB8FZ",
                "user_id": "STU-8SB8FZ",
                "name": "Aaryan Agarawal",
                "class_code": "grade5",
                "bytes_cleared": 77004,
                "eco_points": 20,
                "streak_days": 2,
                "trees": 0
            },
            {
                "student_id": "GOOGLE-SCHOOL-TEST",
                "user_id": "GOOGLE-SCHOOL-TEST",
                "name": "aaryan agarwal",
                "class_code": "grade5",
                "bytes_cleared": 0,
                "eco_points": 0,
                "streak_days": 1,
                "trees": 0
            }
        ]
        save_state(state)

        # Query leaderboard passing Google user ID or name
        res = self.client.get("/api/student/leaderboard?class_code=grade5&student_id=STU-8SB8FZ")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        lb = data.get("leaderboard", [])

        # Deduplication must merge both into a single entry
        aaryan_entries = [e for e in lb if "aaryan" in e.get("name", "").lower()]
        self.assertEqual(len(aaryan_entries), 1, "Duplicate Aaryan entries must be merged into one")
        self.assertEqual(aaryan_entries[0]["eco_points"], 20)
        self.assertIn("(You)", aaryan_entries[0]["name"])

        # Query with Google OAuth lowercase name as student_id
        res2 = self.client.get("/api/student/leaderboard?class_code=grade5&student_id=aaryan%20agarwal")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        lb2 = data2.get("leaderboard", [])
        aaryan_entries2 = [e for e in lb2 if "aaryan" in e.get("name", "").lower()]
        self.assertEqual(len(aaryan_entries2), 1)
        self.assertIn("(You)", aaryan_entries2[0]["name"])

    def test_student_password_change_flow(self):
        """Validates that a student can change their password from their account and log in with it."""
        from src.services.auth import default_auth_service

        state = load_state()
        test_student_id = "STU-PW-TEST"
        state["students"] = [s for s in state.get("students", []) if s.get("student_id") != test_student_id]
        state["students"].append({
            "student_id": test_student_id,
            "user_id": test_student_id,
            "name": "Password Test Student",
            "class_code": "grade6",
            "pin": "initial123",
            "password": "initial123",
            "eco_points": 10,
            "bytes_cleared": 1024
        })
        save_state(state)

        # 1. Unauthenticated request without student_id should fail
        res_unauth = self.client.post("/api/student/password", json={"new_password": "newsecret123"})
        self.assertEqual(res_unauth.status_code, 401)

        # 2. Too short password should fail
        session = default_auth_service.create_session(role="student", user_id=test_student_id, class_code="grade6")
        token = session["token"]
        res_short = self.client.post(
            "/api/student/password",
            headers={"Authorization": f"Bearer {token}"},
            json={"student_id": test_student_id, "new_password": "ab"}
        )
        self.assertEqual(res_short.status_code, 400)

        # 3. Successful password change
        new_pw = "supersecret2026"
        res_success = self.client.post(
            "/api/student/password",
            headers={"Authorization": f"Bearer {token}"},
            json={"student_id": test_student_id, "new_password": new_pw}
        )
        self.assertEqual(res_success.status_code, 200)
        data = res_success.get_json()
        self.assertEqual(data["status"], "ok")

        # 4. Login with the new password must succeed
        res_login = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": test_student_id,
            "pin": new_pw
        })
        self.assertEqual(res_login.status_code, 200)
        login_data = res_login.get_json()
        self.assertEqual(login_data["status"], "authenticated")
        self.assertEqual(login_data["user_id"], test_student_id)

        # 5. Login with an incorrect password must fail
        res_fail = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": test_student_id,
            "pin": "wrongpasswordxyz"
        })
        self.assertEqual(res_fail.status_code, 401)


if __name__ == "__main__":
    unittest.main()
