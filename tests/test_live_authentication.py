import unittest
import json
from src.app.server import app, load_state, save_state
from src.services.auth import default_auth_service

class TestLiveAuthentication(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.orig_state = load_state()
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

if __name__ == "__main__":
    unittest.main()
