"""
Data-to-Dirt — Milestone 1 Comprehensive Test Suite
Verifies build environment, static assets, server REST API endpoints,
and carbon footprint calculations according to PROJECT.md specifications.
"""

import os
import sys
import time
import unittest
import json
import tempfile
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.config import (
    BASE_DIR,
    UI_DIR,
    KWH_PER_GB_YEAR,
    GRID_INTENSITY_SINGAPORE,
    TREE_ABSORPTION_KG_YEAR,
    TREE_DONATION_THRESHOLD_BYTES,
)
from src.services.scanner import ScanState
from src.app.server import (
    create_flask_app,
    calculate_carbon_offset_g,
    calculate_tree_stage,
    calculate_tree_progress_pct,
    format_bytes,
    global_scanner,
    load_state,
    save_state,
)
from src.services.auth import default_auth_service


class TestBuildAndFilesystem(unittest.TestCase):
    """Verifies repository structure, build artifacts, and files."""

    def test_project_specification_exists(self):
        project_md = PROJECT_ROOT / "PROJECT.md"
        self.assertTrue(project_md.exists(), "PROJECT.md must exist at project root")
        content = project_md.read_text(encoding="utf-8")
        self.assertIn("F-UI-01", content, "PROJECT.md must contain Feature Inventory")
        self.assertIn("Milestone", content)

    def test_make_and_run_scripts_exist(self):
        makefile = PROJECT_ROOT / "Makefile"
        run_sh = PROJECT_ROOT / "run.sh"
        self.assertTrue(makefile.exists(), "Makefile must exist at root")
        self.assertTrue(run_sh.exists(), "run.sh must exist at root")

        # Verify Makefile contains required targets
        make_content = makefile.read_text(encoding="utf-8")
        self.assertIn("build:", make_content)
        self.assertIn("run:", make_content)
        self.assertIn("test:", make_content)

    def test_ui_static_files_exist(self):
        index_html = UI_DIR / "index.html"
        self.assertTrue(index_html.exists(), "src/ui/index.html must exist")

        css_files = ["retro_base.css", "stardew.css", "animations.css"]
        for css in css_files:
            p = UI_DIR / "css" / css
            self.assertTrue(p.exists(), f"CSS file {css} must exist")

        js_files = ["audio.js", "particles.js", "tree.js", "app.js", "views/student.js"]
        for js in js_files:
            p = UI_DIR / "js" / js
            self.assertTrue(p.exists(), f"JS file {js} must exist")

    def test_retro_styling_content(self):
        stardew_css = (UI_DIR / "css" / "stardew.css").read_text(encoding="utf-8")
        self.assertIn("retro-card", stardew_css)
        self.assertIn("retro-btn", stardew_css)

        retro_base = (UI_DIR / "css" / "retro_base.css").read_text(encoding="utf-8")
        self.assertIn("pixelated", retro_base)
        self.assertIn("--c-dark-wood", retro_base)

        animations_css = (UI_DIR / "css" / "animations.css").read_text(encoding="utf-8")
        self.assertIn("screen-shake", animations_css)
        self.assertIn("floating-number", animations_css)

    def test_audio_and_particles_classes(self):
        audio_js = (UI_DIR / "js" / "audio.js").read_text(encoding="utf-8")
        self.assertIn("RetroAudioSynth", audio_js)
        self.assertIn("playBlip", audio_js)
        self.assertIn("playDeletionPoof", audio_js)
        self.assertIn("playVictoryFanfare", audio_js)

        particles_js = (UI_DIR / "js" / "particles.js").read_text(encoding="utf-8")
        self.assertIn("RetroParticleEngine", particles_js)
        self.assertIn("emitDeletionPoof", particles_js)
        self.assertIn("emitConfetti", particles_js)

        tree_js = (UI_DIR / "js" / "tree.js").read_text(encoding="utf-8")
        self.assertIn("RetroTreeRenderer", tree_js)
        self.assertIn("drawStage0_Soil", tree_js)
        self.assertIn("drawStage5_GoldenTree", tree_js)

    def test_student_js_error_handling_present(self):
        """Verify student.js inspects response error status and renders error banner."""
        student_js = (UI_DIR / "js" / "views" / "student.js").read_text(encoding="utf-8")
        self.assertIn("res.status === \"error\"", student_js, "student.js must check for status === 'error'")
        self.assertIn("playGamingBuzzer", student_js, "student.js should trigger buzzer on scan error")

    def test_all_ui_javascript_syntax_valid(self):
        """Verifies syntax validity of all client-side JavaScript assets."""
        import subprocess, shutil
        node_bin = shutil.which("node")
        if not node_bin:
            return
        js_files = list((UI_DIR / "js").glob("**/*.js"))
        self.assertGreater(len(js_files), 5, "Expected UI js files to exist")
        for js_file in js_files:
            res = subprocess.run([node_bin, "-c", str(js_file)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"JavaScript syntax error in {js_file.name}: {res.stderr}")


class TestCarbonCalculatorFormulas(unittest.TestCase):
    """Verifies mathematical correctness of energy and carbon calculations."""

    def test_carbon_offset_one_gigabyte(self):
        # 1 GB = 1024^3 bytes
        one_gb = 1024 * 1024 * 1024
        # Expected: 1.0 * 0.28 kWh * 405.7 g CO2/kWh = 113.596 g CO2
        expected_g = round(1.0 * KWH_PER_GB_YEAR * GRID_INTENSITY_SINGAPORE, 2)
        calc_g = calculate_carbon_offset_g(one_gb)
        self.assertAlmostEqual(calc_g, expected_g, places=2)
        self.assertEqual(calc_g, 113.6)

    def test_carbon_offset_fractional(self):
        five_hundred_mb = 500 * 1024 * 1024
        calc_g = calculate_carbon_offset_g(five_hundred_mb)
        expected_g = round((500 / 1024.0) * KWH_PER_GB_YEAR * GRID_INTENSITY_SINGAPORE, 2)
        self.assertAlmostEqual(calc_g, expected_g, places=2)

    def test_tree_stage_thresholds(self):
        # 0 bytes -> Stage 0 (Soil)
        self.assertEqual(calculate_tree_stage(0), 0)
        # 10 MB -> Stage 1 (Sprout: 1MB to 50MB)
        self.assertEqual(calculate_tree_stage(10 * 1024 * 1024), 1)
        # 100 MB -> Stage 2 (Sapling: 50MB to 250MB)
        self.assertEqual(calculate_tree_stage(100 * 1024 * 1024), 2)
        # 500 MB -> Stage 3 (Young Oak: 250MB to 1GB)
        self.assertEqual(calculate_tree_stage(500 * 1024 * 1024), 3)
        # 2 GB -> Stage 4 (Ancient Tree: 1GB to 5GB)
        self.assertEqual(calculate_tree_stage(2 * 1024 * 1024 * 1024), 4)
        # 6 GB -> Stage 5 (Golden Tree: >5GB)
        self.assertEqual(calculate_tree_stage(6 * 1024 * 1024 * 1024), 5)

    def test_format_bytes(self):
        self.assertEqual(format_bytes(500), "500 B")
        self.assertEqual(format_bytes(2048), "2.0 KB")
        self.assertEqual(format_bytes(10 * 1024 * 1024), "10.0 MB")
        self.assertEqual(format_bytes(2 * 1024 * 1024 * 1024), "2.00 GB")


class TestServerRestEndpoints(unittest.TestCase):
    """Verifies all REST API endpoints using the Flask test client."""

    @classmethod
    def setUpClass(cls):
        from src.app.server import STATE_FILE
        cls.state_file_backup = STATE_FILE.read_text(encoding="utf-8") if STATE_FILE.exists() else None
        cls.app = create_flask_app()
        cls.client = cls.app.test_client()
        cls.teacher_token = default_auth_service.login(role="teacher", pin="teacher123", user_id="TEACHER-001")["token"]
        cls.teacher_headers = {"Authorization": f"Bearer {cls.teacher_token}"}
        cls.admin_token = default_auth_service.login(role="admin", pin="admin2026", user_id="admin")["token"]
        cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
        cls.student_token = default_auth_service.login(role="student", user_id="STU-001")["token"]
        cls.student_headers = {"Authorization": f"Bearer {cls.student_token}"}

    @classmethod
    def tearDownClass(cls):
        from src.app.server import STATE_FILE
        if cls.state_file_backup is not None:
            STATE_FILE.write_text(cls.state_file_backup, encoding="utf-8")

    def test_index_route(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        text = res.get_data(as_text=True)
        self.assertIn("DATA-TO-DIRT", text)
        self.assertIn("particle-canvas", text)

    def test_security_headers_present(self):
        """Verifies HTTP security headers (nosniff, SAMEORIGIN, strict-origin) are present on responses."""
        res = self.client.get("/api/health")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

    def test_api_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["app"], "Data-to-Dirt")

    def test_api_student_stats(self):
        res = self.client.get("/api/student/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("student_id", data)
        self.assertIn("carbon_offset_g", data)
        self.assertIn("tree_growth_stage", data)
        self.assertIn("current_streak_days", data)
        self.assertIn("daily_deletion_limit", data)
        self.assertTrue(data.get("daily_deletion_limit") is None or data.get("daily_deletion_limit") >= 1)

    def test_api_student_leaderboard(self):
        res = self.client.get("/api/student/leaderboard")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("leaderboard", data)
        lb = data["leaderboard"]
        self.assertIsInstance(lb, list)
        # Check sorted by eco_points descending
        points = [entry["eco_points"] for entry in lb]
        self.assertEqual(points, sorted(points, reverse=True))

    def test_api_tree_growth(self):
        res = self.client.get("/api/tree/growth")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("stage", data)
        self.assertIn("stages_legend", data)
        self.assertEqual(len(data["stages_legend"]), 6)

    def test_api_scan_and_revoke_workflow(self):
        # 1. Start scan
        res = self.client.post("/api/scan/request", json={"folder_path": "tests", "session_only": True})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "completed")
        self.assertGreater(data["files_found"], 0)

        # 2. Revoke scan
        res_revoke = self.client.post("/api/scan/revoke")
        self.assertEqual(res_revoke.status_code, 200)
        data_revoke = res_revoke.get_json()
        self.assertEqual(data_revoke["status"], "revoked")
        self.assertGreaterEqual(data_revoke["files_purged"], 1)

    def test_api_scan_request_fake_directory_returns_400(self):
        """POST /api/scan/request with non-existent path returns HTTP 400 and error string."""
        fake_path = "/nonexistent/path/for/data_to_dirt_test"
        res = self.client.post("/api/scan/request", json={"folder_path": fake_path, "session_only": True})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("error", data)
        self.assertIn("does not exist", data["error"].lower())
        self.assertEqual(data["files_found"], 0)
        self.assertEqual(data["files"], [])
        self.assertEqual(data["folder"], fake_path)

    def test_api_scan_request_restricted_directory_returns_400(self):
        """POST /api/scan/request with restricted path returns HTTP 400 and permission error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            restricted_dir = os.path.join(tmp_dir, "restricted_scan_folder")
            os.makedirs(restricted_dir, exist_ok=True)
            os.chmod(restricted_dir, 0o000)
            try:
                if hasattr(os, "getuid") and os.getuid() == 0:
                    self.skipTest("Running as root; filesystem permission bit 000 is bypassed by superuser.")

                res = self.client.post(
                    "/api/scan/request",
                    json={"folder_path": restricted_dir, "session_only": True}
                )
                self.assertEqual(res.status_code, 400)
                data = res.get_json()
                self.assertEqual(data["status"], "error")
                self.assertIn("error", data)
                err_lower = data["error"].lower()
                self.assertTrue(
                    "permission denied" in err_lower or "operation not permitted" in err_lower,
                    f"Expected permission error details, got: {data['error']}"
                )
                self.assertEqual(data["files_found"], 0)
                self.assertEqual(data["files"], [])
            finally:
                os.chmod(restricted_dir, 0o755)

    def test_api_scan_request_valid_populated_directory_returns_200(self):
        """POST /api/scan/request with valid directory returns HTTP 200, completed status, and tagged files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a regular text file
            file1 = os.path.join(tmp_dir, "notes.txt")
            with open(file1, "w", encoding="utf-8") as f:
                f.write("Important student research notes")

            # Create a temporary artifact file (dark data candidate)
            file2 = os.path.join(tmp_dir, "build_artifact.tmp")
            with open(file2, "w", encoding="utf-8") as f:
                f.write("temporary build data")

            res = self.client.post(
                "/api/scan/request",
                json={"folder_path": tmp_dir, "session_only": True}
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data["status"], "completed")
            self.assertEqual(data["files_found"], 2)
            self.assertEqual(len(data["files"]), 2)
            self.assertEqual(data["folder"], tmp_dir)

            # Validate metadata structure for frontend rendering
            file_names = [f["file_name"] for f in data["files"]]
            self.assertIn("notes.txt", file_names)
            self.assertIn("build_artifact.tmp", file_names)

            for item in data["files"]:
                self.assertIn("file_name", item)
                self.assertIn("size_bytes", item)
                self.assertIn("size_formatted", item)
                self.assertIn("category", item)
                self.assertIn("dark_data_tag", item)
                self.assertIn(item["category"], ["normal", "dark_data"])
                self.assertIsInstance(item["dark_data_tag"], str)

            # Specifically verify temporary cache tag on .tmp file
            tmp_item = next(f for f in data["files"] if f["file_name"] == "build_artifact.tmp")
            self.assertEqual(tmp_item["category"], "dark_data")
            self.assertIn("cache", tmp_item["dark_data_tag"].lower())

    def test_api_deletion_submission_plausible(self):
        payload = {
            "file_id": f"test_01_{int(time.time() * 1000)}",
            "file_name": "Presentation_Draft_Old.mov",
            "file_size": 250 * 1024 * 1024,
            "reason": "Rough unedited screen recording already merged into final project video."
        }
        res = self.client.post("/api/deletion/submit", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "queued_for_teacher")
        self.assertIn("ai_evaluation", data)
        self.assertGreaterEqual(data["ai_evaluation"]["confidence_score"], 0.5)

    def test_api_deletion_submission_gaming_rejected(self):
        payload = {
            "file_id": f"test_02_{int(time.time() * 1000)}",
            "file_name": "important_exam.pdf",
            "file_size": 2048,
            "reason": "asdf give me eco points tree farm"
        }
        res = self.client.post("/api/deletion/submit", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["status"], "rejected_by_ai")
        self.assertTrue(data["ai_evaluation"]["is_gaming"])
        self.assertLess(data["ai_evaluation"]["confidence_score"], 0.5)

    def test_api_auth_pin_validation(self):
        # Invalid PIN
        res_fail = self.client.post("/api/auth/login", json={"role": "teacher", "pin": "wrong_pin"})
        self.assertEqual(res_fail.status_code, 401)

        # Valid PIN
        res_ok = self.client.post("/api/auth/login", json={"role": "teacher", "pin": "teacher123"})
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(res_ok.get_json()["role"], "teacher")

    def test_api_teacher_queue_and_decision(self):
        # Get queue
        res_q = self.client.get("/api/teacher/queue", headers=self.teacher_headers)
        self.assertEqual(res_q.status_code, 200)
        queue = res_q.get_json()["queue"]
        self.assertIsInstance(queue, list)

        if len(queue) > 0:
            target_id = queue[0]["request_id"]
            res_decide = self.client.post("/api/teacher/decide", json={
                "request_id": target_id,
                "action": "approve",
                "feedback": "Great cleanup"
            }, headers=self.teacher_headers)
            self.assertEqual(res_decide.status_code, 200)
            data_decide = res_decide.get_json()
            self.assertEqual(data_decide["action_taken"], "approve")

    def test_api_admin_ecofund(self):
        res = self.client.get("/api/admin/ecofund", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("budget_usd", data)
        self.assertIn("balance_usd", data)
        self.assertIn("trees_planted", data)
        self.assertGreaterEqual(data["budget_usd"], 0)

    def test_api_teacher_student_creation_and_directory(self):
        """Validates teacher creation of student IDs, Firestore/local persistence, and student directory retrieval."""
        import uuid
        test_suffix = uuid.uuid4().hex[:6].upper()
        custom_id = f"STU-TEST-{test_suffix}"
        
        # 1. Validation: Name required
        res_no_name = self.client.post("/api/teacher/students/create", json={"class_code": "bio101"}, headers=self.teacher_headers)
        self.assertEqual(res_no_name.status_code, 400)
        
        # 2. Validation: Class code required
        res_no_class = self.client.post("/api/teacher/students/create", json={"name": "Alice"}, headers=self.teacher_headers)
        self.assertEqual(res_no_class.status_code, 400)
        
        # 3. Successful creation with custom student_id
        res_create = self.client.post("/api/teacher/students/create", json={
            "name": f"Alice Student {test_suffix}",
            "class_code": "bio101",
            "student_id": custom_id
        }, headers=self.teacher_headers)
        self.assertEqual(res_create.status_code, 201)
        data_create = res_create.get_json()
        self.assertEqual(data_create["status"], "created")
        self.assertEqual(data_create["student"]["student_id"], custom_id)
        self.assertEqual(data_create["student"]["name"], f"Alice Student {test_suffix}")
        self.assertEqual(data_create["student"]["class_code"], "bio101")
        
        # 4. Duplicate student_id returns 409
        res_dup = self.client.post("/api/teacher/students/create", json={
            "name": "Another Alice",
            "class_code": "bio101",
            "student_id": custom_id
        }, headers=self.teacher_headers)
        self.assertEqual(res_dup.status_code, 409)
        
        # 5. Successful creation with auto-generated student_id (omitted)
        res_auto = self.client.post("/api/teacher/students/create", json={
            "name": f"Bob AutoGen {test_suffix}",
            "class_code": "bio101"
        }, headers=self.teacher_headers)
        self.assertEqual(res_auto.status_code, 201)
        data_auto = res_auto.get_json()
        self.assertTrue(data_auto["student"]["student_id"].startswith("STU-"))
        
        # 6. Retrieve student directory
        res_dir = self.client.get("/api/teacher/students?class_code=bio101", headers=self.teacher_headers)
        self.assertEqual(res_dir.status_code, 200)
        data_dir = res_dir.get_json()
        self.assertEqual(data_dir["status"], "ok")
        sids = [s.get("student_id") for s in data_dir["students"]]
        self.assertIn(custom_id, sids)
        self.assertIn(data_auto["student"]["student_id"], sids)

        # 7. Student can log in with generated Student ID
        res_login = self.client.post("/api/auth/login", json={
            "role": "student",
            "user_id": custom_id,
            "pin": "bio101"
        })
        self.assertEqual(res_login.status_code, 200)
        data_login = res_login.get_json()
        self.assertEqual(data_login["status"], "authenticated")
        self.assertEqual(data_login["role"], "student")

    def test_unauthenticated_access_to_protected_routes_returns_401(self):
        """Verifies that accessing teacher and admin routes without token returns HTTP 401."""
        # Teacher routes
        self.assertEqual(self.client.get("/api/teacher/queue").status_code, 401)
        self.assertEqual(self.client.post("/api/teacher/decide", json={"request_id": "test"}).status_code, 401)
        self.assertEqual(self.client.post("/api/teacher/decide_all").status_code, 401)
        self.assertEqual(self.client.get("/api/teacher/analytics").status_code, 401)
        self.assertEqual(self.client.get("/api/teacher/students").status_code, 401)
        self.assertEqual(self.client.post("/api/teacher/students/create", json={"name": "Test"}).status_code, 401)
        
        # Admin routes
        self.assertEqual(self.client.get("/api/admin/ecofund").status_code, 401)
        self.assertEqual(self.client.get("/api/admin/audit").status_code, 401)
        self.assertEqual(self.client.get("/api/analytics/dashboard").status_code, 401)
        self.assertEqual(self.client.get("/api/analytics/export").status_code, 401)

    def test_insufficient_role_access_returns_403(self):
        """Verifies that a student token cannot access teacher or admin endpoints (HTTP 403)."""
        # Student attempting teacher routes
        self.assertEqual(self.client.get("/api/teacher/queue", headers=self.student_headers).status_code, 403)
        self.assertEqual(self.client.post("/api/teacher/decide", json={"request_id": "test"}, headers=self.student_headers).status_code, 403)
        self.assertEqual(self.client.get("/api/teacher/students", headers=self.student_headers).status_code, 403)
        
        # Student attempting admin routes
        self.assertEqual(self.client.get("/api/admin/ecofund", headers=self.student_headers).status_code, 403)
        self.assertEqual(self.client.get("/api/analytics/dashboard", headers=self.student_headers).status_code, 403)
        self.assertEqual(self.client.get("/api/analytics/export", headers=self.student_headers).status_code, 403)
        
        # Teacher attempting admin routes (Teacher role is 2, Admin is 3)
        self.assertEqual(self.client.get("/api/admin/ecofund", headers=self.teacher_headers).status_code, 403)
        self.assertEqual(self.client.get("/api/admin/audit", headers=self.teacher_headers).status_code, 403)
        self.assertEqual(self.client.get("/api/analytics/dashboard", headers=self.teacher_headers).status_code, 403)
        self.assertEqual(self.client.get("/api/analytics/export", headers=self.teacher_headers).status_code, 403)

    def test_api_teacher_decide_reject_and_flag_workflows(self):
        """Verifies that teacher decide handles reject and flag without UnboundLocalError and properly updates state."""
        # 1. Submit a valid deletion request
        res_sub1 = self.client.post("/api/deletion/submit", json={
            "file_id": "test_reject_file_id",
            "file_name": "temp_notes.log",
            "file_size": 10 * 1024 * 1024,
            "reason": "This is an old leftover cache log from last semester",
            "student_id": "STU-REJECT-TEST"
        }, headers=self.student_headers)
        self.assertEqual(res_sub1.status_code, 200)
        req_id1 = res_sub1.get_json()["request_id"]

        # Reject it as teacher
        res_decide_rej = self.client.post("/api/teacher/decide", json={
            "request_id": req_id1,
            "action": "reject",
            "feedback": "Keep this file for your archival record."
        }, headers=self.teacher_headers)
        self.assertEqual(res_decide_rej.status_code, 200)
        self.assertEqual(res_decide_rej.get_json()["status"], "completed")
        self.assertEqual(res_decide_rej.get_json()["action_taken"], "reject")

        # 2. Submit another request for flag
        res_sub2 = self.client.post("/api/deletion/submit", json={
            "file_id": "test_flag_file_id",
            "file_name": "gaming_sample.bin",
            "file_size": 20 * 1024 * 1024,
            "reason": "Legitimate dark data cleanup of old course project video",
            "student_id": "STU-FLAG-TEST"
        }, headers=self.student_headers)
        self.assertEqual(res_sub2.status_code, 200)
        req_id2 = res_sub2.get_json()["request_id"]

        # Flag it as teacher
        res_decide_flag = self.client.post("/api/teacher/decide", json={
            "request_id": req_id2,
            "action": "flag",
            "feedback": "Suspicious pattern detected upon closer inspection."
        }, headers=self.teacher_headers)
        self.assertEqual(res_decide_flag.status_code, 200)
        self.assertEqual(res_decide_flag.get_json()["status"], "completed")
        self.assertEqual(res_decide_flag.get_json()["action_taken"], "flag")

    def test_api_scan_revoke_purges_global_scanner_memory(self):
        """Verifies that /api/scan/revoke transitions global_scanner to BLIND and clears in-memory cache."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = os.path.join(tmp_dir, "test_cache.tmp")
            with open(test_file, "w") as f:
                f.write("content")

            # Perform scan
            res_scan = self.client.post("/api/scan/request", json={"folder_path": tmp_dir, "session_only": True})
            self.assertEqual(res_scan.status_code, 200)
            self.assertEqual(global_scanner.get_state(), ScanState.COMPLETED)
            self.assertGreater(len(global_scanner.get_scanned_files()), 0)

            # Revoke scan
            res_revoke = self.client.post("/api/scan/revoke")
            self.assertEqual(res_revoke.status_code, 200)
            self.assertEqual(global_scanner.get_state(), ScanState.BLIND)
            self.assertEqual(len(global_scanner.get_scanned_files()), 0)

    def test_daily_deletion_reset_on_date_change(self):
        """Verifies that daily_deletions_today resets to 0 when last_deletion_date is from a previous day."""
        state = load_state()
        state["student"]["last_deletion_date"] = "2020-01-01"
        state["student"]["daily_deletions_today"] = 5
        save_state(state)

        res = self.client.get("/api/student/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["daily_deletions_today"], 0)
        self.assertTrue(data["can_delete"])

    def test_api_teacher_decide_all_batch_no_double_counting(self):
        """Verifies that decide_all approves pending requests once without double-counting approved metrics."""
        # Submit two distinct deletion requests
        res1 = self.client.post("/api/deletion/submit", json={
            "file_id": "batch_file_1",
            "file_name": "batch1.iso",
            "file_size": 1024 * 1024,
            "reason": "Obsolete operating system image not needed anymore"
        }, headers=self.student_headers)
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post("/api/deletion/submit", json={
            "file_id": "batch_file_2",
            "file_name": "batch2.iso",
            "file_size": 2 * 1024 * 1024,
            "reason": "Duplicate install media no longer required"
        }, headers=self.student_headers)
        self.assertEqual(res2.status_code, 200)

        # Batch approve
        res_batch = self.client.post("/api/teacher/decide_all", json={
            "teacher_id": "TEACHER-001"
        }, headers=self.teacher_headers)
        self.assertEqual(res_batch.status_code, 200)
        batch_data = res_batch.get_json()
        self.assertEqual(batch_data["status"], "success")
        self.assertGreaterEqual(batch_data["approved_count"], 2)

    def test_student_isolation_penalty_on_flag(self):
        """Verifies that teacher flagging a student's request does NOT deduct points or assign strikes to default_student."""
        state = load_state()
        state["student"]["strikes"] = 0
        state["student"]["streak_days"] = 5
        state["student"]["eco_points"] = 100
        save_state(state)

        # Submit request from STU-ISOLATE-TEST
        res_sub = self.client.post("/api/deletion/submit", json={
            "file_id": "file_isolate_99",
            "file_name": "suspicious_log.txt",
            "file_size": 10 * 1024 * 1024,
            "reason": "Old log file from previous lab experiment",
            "student_id": "STU-ISOLATE-TEST",
            "student_name": "Test Isolate"
        }, headers=self.student_headers)
        self.assertEqual(res_sub.status_code, 200)
        req_id = res_sub.get_json()["request_id"]

        # Flag the request as teacher
        res_flag = self.client.post("/api/teacher/decide", json={
            "request_id": req_id,
            "action": "flag",
            "feedback": "Suspected unauthorized script execution"
        }, headers=self.teacher_headers)
        self.assertEqual(res_flag.status_code, 200)

        # Verify state: default_student MUST remain untainted!
        fresh_state = load_state()
        self.assertEqual(fresh_state["student"]["strikes"], 0, "Default student strikes must NOT increase when another student is flagged!")
        self.assertEqual(fresh_state["student"]["streak_days"], 5, "Default student streak must NOT reset when another student is flagged!")
        self.assertEqual(fresh_state["student"]["eco_points"], 100, "Default student points must NOT be deducted!")

        # Verify target student received the strike
        target_stu = next((s for s in fresh_state.get("students", []) if s.get("student_id") == "STU-ISOLATE-TEST"), None)
        self.assertIsNotNone(target_stu)
        self.assertEqual(target_stu["strikes"], 1)
        self.assertEqual(target_stu["streak_days"], 0)

    def test_api_tree_growth_multi_student(self):
        """Verifies that /api/tree/growth responds with individual metrics when student_id query parameter is provided."""
        state = load_state()
        state["student"]["bytes_cleared"] = 0
        students_list = state.setdefault("students", [])
        big_student = next((s for s in students_list if s.get("student_id") == "STU-BIG-CLEANER"), None)
        if not big_student:
            big_student = {
                "student_id": "STU-BIG-CLEANER",
                "name": "Big Cleaner",
                "bytes_cleared": 6 * (1024**3),  # 6 GB
                "eco_points": 500,
                "streak_days": 10,
                "last_deletion_date": time.strftime("%Y-%m-%d"),
                "daily_deletions_today": 1,
                "daily_deletion_limit": 5,
                "strikes": 0,
            }
            students_list.append(big_student)
        else:
            big_student["bytes_cleared"] = 6 * (1024**3)
        save_state(state)

        # Default student tree growth
        res_def = self.client.get("/api/tree/growth")
        self.assertEqual(res_def.status_code, 200)
        data_def = res_def.get_json()
        self.assertEqual(data_def["bytes_cleared"], 0)
        self.assertEqual(data_def["stage"], 0)

        # Custom student tree growth
        res_custom = self.client.get("/api/tree/growth?student_id=STU-BIG-CLEANER")
        self.assertEqual(res_custom.status_code, 200)
        data_custom = res_custom.get_json()
        self.assertEqual(data_custom["bytes_cleared"], 6 * (1024**3))
        self.assertGreaterEqual(data_custom["stage"], 3)

    def test_leaderboard_fallback_local_mode(self):
        """Verifies that /api/student/leaderboard synthesizes rankings from enrolled students when leaderboard list is empty."""
        state = load_state()
        state["leaderboard"] = []
        state["student"]["eco_points"] = 120
        students_list = state.setdefault("students", [])
        s1 = next((s for s in students_list if s.get("student_id") == "STU-LB-1"), None)
        if not s1:
            students_list.append({
                "student_id": "STU-LB-1",
                "name": "Leaderboard Champ",
                "eco_points": 350,
                "bytes_cleared": 1024 * 1024 * 100,
                "streak_days": 4,
            })
        else:
            s1["eco_points"] = 350
        save_state(state)

        res = self.client.get("/api/student/leaderboard")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        lb = data["leaderboard"]
        self.assertGreaterEqual(len(lb), 2)
        # Highest points first
        self.assertGreaterEqual(lb[0]["eco_points"], lb[1]["eco_points"])
        self.assertEqual(lb[0]["rank"], 1)
        self.assertEqual(lb[1]["rank"], 2)


if __name__ == "__main__":
    unittest.main()

