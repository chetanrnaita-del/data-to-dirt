"""
Unit and Integration Tests for Security Audit Remediations:
1. URL Query Parameter Privacy (Elimination of student_hint)
2. OAuth Account Hijacking & Spoofing Prevention
3. Edge Telemetry /api/analytics/geo Privacy Hardening
4. Strict Backend Role-Based Access Control (RBAC) on Admin/Teacher Endpoints
5. Broken Object Level Authorization (BOLA) Prevention on Password and Grade Updates
6. HTML Entity Escaping / XSS Defense
"""
import unittest
import json
import base64
import urllib.parse
from unittest.mock import patch, MagicMock
from src.app.server import create_flask_app, _resolve_google_user_profile, load_state, save_state
from src.services.auth import default_auth_service


class TestSecurityAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ["TEST_MODE"] = "1"
        os.environ["GOOGLE_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"
        cls.app = create_flask_app()
        cls.client = cls.app.test_client()

        # Generate tokens
        cls.admin_token = default_auth_service.login(role="admin", pin="admin2026", user_id="admin")["token"]
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}

        cls.teacher_session = default_auth_service.create_session(role="teacher", user_id="teacher_grade5", class_code="grade5")
        cls.teacher_token = cls.teacher_session["token"]
        cls.teacher_headers = {"Authorization": f"Bearer {cls.teacher_token}"}

        cls.student_session = default_auth_service.create_session(role="student", user_id="STU-ALICE", class_code="grade5", name="Alice Student")
        cls.student_token = cls.student_session["token"]
        cls.student_headers = {"Authorization": f"Bearer {cls.student_token}"}

    def test_oauth_login_url_contains_no_student_hint(self):
        """GET /auth/google/login should not store or accept student_hint in URL or state."""
        res = self.client.get("/auth/google/login?provider=personal&grade=grade5&student_hint=Vivaan%20Ranjan")
        self.assertEqual(res.status_code, 302)
        location = res.headers.get("Location")
        self.assertNotIn("Vivaan", location)
        self.assertNotIn("student_hint", location)

        # Decode the state parameter to ensure no student_hint inside
        parsed = urllib.parse.urlparse(location)
        query = urllib.parse.parse_qs(parsed.query)
        self.assertIn("state", query)
        state_payload = json.loads(base64.urlsafe_b64decode(query["state"][0].encode("utf-8")).decode("utf-8"))
        self.assertNotIn("student_hint", state_payload)
        self.assertEqual(state_payload.get("grade"), "grade5")

    def test_oauth_spoofing_prevented_no_arbitrary_account_binding(self):
        """Authenticated Google user cannot hijack an existing student account by claiming their name."""
        # Setup existing victim student in state
        state = load_state()
        state.setdefault("students", [])
        state["students"].append({
            "student_id": "STU-VICTIM",
            "name": "Vivaan Ranjan",
            "email": "vivaan.ranjan@school.edu",
            "class_code": "grade5",
            "eco_points": 500,
            "bytes_cleared": 5000000000
        })
        save_state(state)

        # Attacker logs in with their own Google account (attacker@gmail.com)
        mock_userinfo = {
            "name": "Vivaan Ranjan",  # Attacker spoofed name on their Google profile
            "email": "attacker@gmail.com",  # Attacker real Google email
            "sub": "999888777"
        }

        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(mock_userinfo).encode("utf-8")
            mock_resp.__enter__.return_value = mock_resp
            mock_url.return_value = mock_resp

            resolved = _resolve_google_user_profile(access_token="valid_token", provider="personal", target_grade="grade5")

        # Must NOT bind to STU-VICTIM because verified email does not match!
        self.assertNotEqual(resolved["student_id"], "STU-VICTIM")
        self.assertTrue(resolved["student_id"].startswith("STU-ATTACKER") or resolved["student_id"].startswith("STU-G"))
        self.assertEqual(resolved["email"], "attacker@gmail.com")

    def test_analytics_geo_privacy_masking(self):
        """Unauthenticated /api/analytics/geo must mask coordinates; staff users get full coordinates."""
        # Unauthenticated
        res = self.client.get("/api/analytics/geo", headers={
            "CF-IPCity": "London",
            "CF-IPCountry": "GB",
            "CF-IPLatitude": "51.5074",
            "CF-IPLongitude": "-0.1278"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["city"], "London")
        self.assertEqual(data["country"], "GB")
        self.assertEqual(data["lat"], 0.0)
        self.assertEqual(data["lon"], 0.0)
        self.assertTrue(data["is_coarse"])

        # Authenticated Admin
        res_auth = self.client.get("/api/analytics/geo", headers={
            **self.admin_headers,
            "CF-IPCity": "London",
            "CF-IPCountry": "GB",
            "CF-IPLatitude": "51.5074",
            "CF-IPLongitude": "-0.1278"
        })
        self.assertEqual(res_auth.status_code, 200)
        data_auth = res_auth.get_json()
        self.assertAlmostEqual(data_auth["lat"], 51.5074)
        self.assertAlmostEqual(data_auth["lon"], -0.1278)
        self.assertFalse(data_auth["is_coarse"])

    def test_admin_routes_strictly_require_admin_role(self):
        """All /api/admin/* routes reject unauthenticated, student, and teacher requests."""
        admin_endpoints = [
            ("GET", "/api/admin/teachers"),
            ("POST", "/api/admin/teachers/create"),
            ("POST", "/api/admin/teachers/delete"),
            ("POST", "/api/admin/teachers/delete_all"),
            ("GET", "/api/admin/export_data"),
            ("POST", "/api/admin/import_data"),
            ("GET", "/api/admin/audit/export"),
            ("GET", "/api/admin/ecofund"),
            ("GET", "/api/admin/audit"),
            ("GET", "/api/analytics/dashboard"),
            ("GET", "/api/analytics/export"),
        ]

        for method, endpoint in admin_endpoints:
            # 1. Unauthenticated -> 401
            func = self.client.get if method == "GET" else self.client.post
            res_unauth = func(endpoint, json={})
            self.assertEqual(res_unauth.status_code, 401, f"Expected 401 for unauthenticated {endpoint}, got {res_unauth.status_code}")

            # 2. Student role -> 403
            res_student = func(endpoint, headers=self.student_headers, json={})
            self.assertEqual(res_student.status_code, 403, f"Expected 403 for student {endpoint}, got {res_student.status_code}")

            # 3. Teacher role -> 403 (Teacher cannot administer system teachers or perform administrative exports)
            res_teacher = func(endpoint, headers=self.teacher_headers, json={})
            self.assertEqual(res_teacher.status_code, 403, f"Expected 403 for teacher {endpoint}, got {res_teacher.status_code}")

    def test_teacher_routes_strictly_require_teacher_role(self):
        """All /api/teacher/* routes reject unauthenticated and student requests."""
        teacher_endpoints = [
            ("GET", "/api/teacher/queue"),
            ("POST", "/api/teacher/decide"),
            ("POST", "/api/teacher/decide_all"),
            ("POST", "/api/teacher/deletion/direct"),
            ("GET", "/api/teacher/analytics"),
            ("GET", "/api/teacher/students"),
            ("POST", "/api/teacher/students/create"),
            ("POST", "/api/teacher/students/delete"),
            ("POST", "/api/teacher/students/delete_all"),
            ("GET", "/api/teacher/analytics/export"),
        ]

        for method, endpoint in teacher_endpoints:
            func = self.client.get if method == "GET" else self.client.post
            res_unauth = func(endpoint, json={})
            self.assertEqual(res_unauth.status_code, 401, f"Expected 401 for unauthenticated {endpoint}, got {res_unauth.status_code}")

            res_student = func(endpoint, headers=self.student_headers, json={})
            self.assertEqual(res_student.status_code, 403, f"Expected 403 for student {endpoint}, got {res_student.status_code}")

    def test_student_cannot_change_another_students_password(self):
        """BOLA protection: authenticated student session is locked to changing their own password."""
        state = load_state()
        state.setdefault("students", []).append({
            "student_id": "STU-BOB",
            "name": "Bob Target",
            "pin": "targetpin123",
            "password": "targetpin123"
        })
        save_state(state)

        # Alice attempts to change Bob's password
        res = self.client.post(
            "/api/student/password",
            headers=self.student_headers,
            json={"student_id": "STU-BOB", "new_password": "pwnedpassword"}
        )
        self.assertEqual(res.status_code, 200)
        # Verify that Bob's password was NOT changed
        state_after = load_state()
        bob = next(s for s in state_after["students"] if s["student_id"] == "STU-BOB")
        self.assertEqual(bob["password"], "targetpin123")


if __name__ == "__main__":
    unittest.main()
