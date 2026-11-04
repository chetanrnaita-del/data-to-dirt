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

    def setUp(self):
        import copy
        self.orig_state = copy.deepcopy(load_state())

    def tearDown(self):
        save_state(self.orig_state)
        from src.app.server import reset_all_auth_lockouts
        reset_all_auth_lockouts()

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
            ("POST", "/api/sync/rehydrate"),
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
            json={"student_id": "STU-BOB", "current_password": "grade5", "new_password": "pwnedpassword"}
        )
        self.assertEqual(res.status_code, 200)
        # Verify that Bob's password was NOT changed
        state_after = load_state()
        bob = next(s for s in state_after["students"] if s["student_id"] == "STU-BOB")
        self.assertEqual(bob["password"], "targetpin123")

    def test_teacher_delete_student_grade_scoping(self):
        """Teachers assigned to a grade cannot delete students from another grade."""
        state = load_state()
        state.setdefault("students", [])
        state["students"].extend([
            {"student_id": "STU-SCOPE-G5", "name": "Grade 5 Kid", "class_code": "grade5"},
            {"student_id": "STU-SCOPE-G7", "name": "Grade 7 Kid", "class_code": "grade7"}
        ])
        save_state(state)

        # teacher_grade5 tries to delete Grade 7 student -> 403 Forbidden
        res_cross = self.client.post(
            "/api/teacher/students/delete",
            headers=self.teacher_headers,
            json={"student_id": "STU-SCOPE-G7"}
        )
        self.assertEqual(res_cross.status_code, 403)
        self.assertIn("Forbidden", res_cross.get_json()["message"])

        # teacher_grade5 deletes Grade 5 student -> 200 OK
        res_own = self.client.post(
            "/api/teacher/students/delete",
            headers=self.teacher_headers,
            json={"student_id": "STU-SCOPE-G5"}
        )
        self.assertEqual(res_own.status_code, 200)
        self.assertEqual(res_own.get_json()["status"], "deleted")

        # Admin can delete student from any grade -> 200 OK
        res_admin = self.client.post(
            "/api/teacher/students/delete",
            headers=self.admin_headers,
            json={"student_id": "STU-SCOPE-G7"}
        )
        self.assertEqual(res_admin.status_code, 200)
        self.assertEqual(res_admin.get_json()["status"], "deleted")

    def test_delete_all_requires_explicit_confirmation(self):
        """Mass deletion endpoints require explicit confirmation flag to prevent CSRF and accidental mass wipe."""
        # 1. Teacher bulk delete without confirmation -> 400
        res_tch_unconfirmed = self.client.post(
            "/api/teacher/students/delete_all",
            headers=self.teacher_headers,
            json={"class_code": "grade5"}
        )
        self.assertEqual(res_tch_unconfirmed.status_code, 400)
        self.assertIn("confirmation required", res_tch_unconfirmed.get_json()["message"].lower())

        # 2. Teacher bulk delete with confirmation -> 200
        res_tch_confirmed = self.client.post(
            "/api/teacher/students/delete_all",
            headers=self.teacher_headers,
            json={"class_code": "grade5", "confirm": True}
        )
        self.assertEqual(res_tch_confirmed.status_code, 200)
        self.assertEqual(res_tch_confirmed.get_json()["status"], "deleted_all")

        # 3. Admin bulk delete teachers without confirmation -> 400
        res_adm_unconfirmed = self.client.post(
            "/api/admin/teachers/delete_all",
            headers=self.admin_headers,
            json={}
        )
        self.assertEqual(res_adm_unconfirmed.status_code, 400)
        self.assertIn("confirmation required", res_adm_unconfirmed.get_json()["message"].lower())

        # 4. Admin bulk delete teachers with confirmation -> 200
        res_adm_confirmed = self.client.post(
            "/api/admin/teachers/delete_all",
            headers=self.admin_headers,
            json={"confirmation": "DELETE_ALL"}
        )
        self.assertEqual(res_adm_confirmed.status_code, 200)
        self.assertEqual(res_adm_confirmed.get_json()["status"], "deleted_all")

    def test_sync_rehydrate_prevents_privilege_escalation_and_payload_limits(self):
        """Rehydrate strips admin injection attempts and enforces payload size limits."""
        state = load_state()
        state["deleted_student_ids"] = []
        save_state(state)

        # Attempt to inject an admin account through client teachers payload
        res = self.client.post(
            "/api/sync/rehydrate",
            headers=self.admin_headers,
            json={
                "teachers": [
                    {"teacher_id": "admin", "name": "Fake Admin", "role": "admin", "pin": "hacked"},
                    {"teacher_id": "teacher_legit", "name": "Legit Teacher", "role": "teacher", "pin": "teach123"}
                ],
                "students": [
                    {"student_id": "STU-ESCAL-TEST", "name": "Rehydrated Kid", "class_code": "grade5", "role": "admin"}
                ]
            }
        )
        self.assertEqual(res.status_code, 200)
        state_after = load_state()
        # Verify fake admin was NOT added to teachers
        self.assertFalse(any(t.get("teacher_id") == "admin" for t in state_after.get("teachers", [])))
        # Verify student role was forced to "student"
        rehyd_stu = next(s for s in state_after.get("students", []) if s.get("student_id") == "STU-ESCAL-TEST")
        self.assertEqual(rehyd_stu.get("role"), "student")

    def test_student_password_requires_current_password(self):
        """Student password update requires correct current password."""
        state = load_state()
        state.setdefault("students", []).append({
            "student_id": "STU-CHARLIE",
            "name": "Charlie",
            "pin": "secret123",
            "password": "secret123",
            "class_code": "grade5"
        })
        save_state(state)

        charlie_session = default_auth_service.create_session(role="student", user_id="STU-CHARLIE", class_code="grade5")
        charlie_headers = {"Authorization": f"Bearer {charlie_session['token']}"}

        # 1. Wrong current password -> 401
        res_wrong = self.client.post(
            "/api/student/password",
            headers=charlie_headers,
            json={"current_password": "wrongpassword", "new_password": "newsecret456"}
        )
        self.assertEqual(res_wrong.status_code, 401)
        self.assertIn("Incorrect current password", res_wrong.get_json()["message"])

        # 2. Correct current password -> 200
        res_correct = self.client.post(
            "/api/student/password",
            headers=charlie_headers,
            json={"current_password": "secret123", "new_password": "newsecret456"}
        )
        self.assertEqual(res_correct.status_code, 200)
        self.assertEqual(res_correct.get_json()["status"], "ok")

    def test_student_cannot_submit_deletion_for_other_student(self):
        """Student cannot submit a file deletion on behalf of another student's account."""
        res = self.client.post(
            "/api/deletion/submit",
            headers=self.student_headers,
            json={
                "student_id": "STU-VICTIM-99",
                "file_id": "file_victim_01",
                "file_name": "victim_doc.pdf",
                "file_size": 1024 * 1024,
                "reason": "Test"
            }
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Forbidden", res.get_json()["message"])

    def test_analytics_track_rate_limiting_and_validation(self):
        """Flooding /api/analytics/track triggers rate limit and invalid payloads are rejected."""
        # 1. Invalid payload -> 400
        res_invalid = self.client.post("/api/analytics/track", data="not json", content_type="application/json")
        self.assertIn(res_invalid.status_code, (400, 429))

        # 2. Excessive requests from same IP triggers 429
        last_status = 200
        for _ in range(35):
            res = self.client.post("/api/analytics/track", json={
                "action": "Rapid Ping",
                "city": "Singapore",
                "country": "SG"
            })
            last_status = res.status_code
            if last_status == 429:
                break
        self.assertEqual(last_status, 429)

    def test_service_worker_bypasses_api_and_clears_on_logout(self):
        """Service Worker configuration strictly bypasses /api/* and /auth/* and clears caches on logout."""
        import pathlib
        sw_path = pathlib.Path(__file__).resolve().parent.parent / "src" / "ui" / "sw.js"
        with open(sw_path, "r", encoding="utf-8") as f:
            sw_content = f.read()

        self.assertIn("url.pathname.startsWith('/auth/')", sw_content)
        self.assertIn("url.pathname.startsWith('/api/')", sw_content)
        self.assertIn("CLEAR_CACHES", sw_content)
        self.assertTrue(any(v in sw_content for v in ["data-to-dirt-v102", "data-to-dirt-v105", "data-to-dirt-v106", "data-to-dirt-v107", "data-to-dirt-v108", "data-to-dirt-v109", "data-to-dirt-v110", "data-to-dirt-v111", "data-to-dirt-v112", "data-to-dirt-v113"]))

        app_js_path = pathlib.Path(__file__).resolve().parent.parent / "src" / "ui" / "js" / "app.js"
        with open(app_js_path, "r", encoding="utf-8") as f:
            app_js = f.read()

        self.assertIn("sessionStorage.clear()", app_js)
        self.assertIn("caches.delete", app_js)
        self.assertIn("CLEAR_CACHES", app_js)
        self.assertIn("/api/auth/logout", app_js)


if __name__ == "__main__":
    unittest.main()
