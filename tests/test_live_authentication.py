import unittest
import json
from src.app.server import app, load_state, save_state, reset_all_auth_lockouts
from src.services.auth import default_auth_service

class TestLiveAuthentication(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.orig_state = load_state()
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
        save_state(self.orig_state)
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

if __name__ == "__main__":
    unittest.main()
