"""Adversarial stress-tests and empirical verification for Data-to-Dirt directory scanning.

Tests:
1. Path Sanitization & Boundary Conditions (quotes, spaces, tilde, empty, traversal, non-existent, file)
2. State Consistency & Session Isolation across requests and revokes
3. In-memory scanner lifecycle & potential memory retention on revoke
4. Concurrency & Rapid Fire Requests (interleaved scan and revoke across multiple threads)
5. Deep Traversal Permission Error capture
"""

import os
import sys
import shutil
import tempfile
import unittest
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.app.server import create_flask_app, global_scanner, load_state, save_state
from src.services.scanner import FileScanner, ScanState, PermissionRequiredError
from src.security.sanitizer import (
    sanitize_path,
    sanitize_directory,
    ValidationError,
    validate_scan_request
)


class TestEmpiricalChallengerPathSanitization(unittest.TestCase):
    """Adversarial stress testing for path sanitization."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="challenger_path_test_")
        self.sub_dir = os.path.join(self.tmp_dir, "valid folder with spaces")
        os.makedirs(self.sub_dir, exist_ok=True)
        with open(os.path.join(self.sub_dir, "doc.txt"), "w") as f:
            f.write("content")
        self.scanner = FileScanner()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_path_surrounded_by_double_quotes(self):
        quoted = f'"{self.sub_dir}"'
        self.assertTrue(self.scanner.request_access(quoted))
        self.assertEqual(self.scanner._active_path, self.sub_dir)
        items = self.scanner.scan()
        self.assertEqual(len(items), 1)

    def test_path_surrounded_by_single_quotes(self):
        quoted = f"'{self.sub_dir}'"
        self.assertTrue(self.scanner.request_access(quoted))
        self.assertEqual(self.scanner._active_path, self.sub_dir)
        items = self.scanner.scan()
        self.assertEqual(len(items), 1)

    def test_path_with_outer_whitespace_and_quotes(self):
        messy = f"   '{self.sub_dir}'   "
        self.assertTrue(self.scanner.request_access(messy))
        self.assertEqual(self.scanner._active_path, self.sub_dir)

    def test_path_with_whitespace_inside_clean_folder(self):
        self.assertTrue(self.scanner.request_access(self.sub_dir))
        self.assertEqual(self.scanner._active_path, self.sub_dir)

    def test_tilde_expansion_home(self):
        home_dir = os.path.expanduser("~")
        if os.path.isdir(home_dir):
            self.assertTrue(self.scanner.request_access("~"))
            self.assertEqual(self.scanner._active_path, home_dir)

    def test_quoted_tilde_expansion(self):
        home_dir = os.path.expanduser("~")
        if os.path.isdir(home_dir):
            self.assertTrue(self.scanner.request_access('"~"'))
            self.assertEqual(self.scanner._active_path, home_dir)

    def test_empty_and_whitespace_inputs_raise_value_error(self):
        for bad_input in ["", "   ", "''", '""']:
            with self.subTest(bad_input=bad_input):
                with self.assertRaises(ValueError):
                    self.scanner.request_access(bad_input)

        # Quotes with spaces inside (e.g. " ' ' ") have spaces preserved within quotes
        for spaced_quote in [" ' ' ", ' " " ']:
            with self.subTest(spaced_quote=spaced_quote):
                # When stripped once, ' ' has inner space, so it's treated as nonexistent relative path
                with self.assertRaises((ValueError, FileNotFoundError)):
                    self.scanner.request_access(spaced_quote)

    def test_nonexistent_directory_raises_file_not_found(self):
        fake = os.path.join(self.tmp_dir, "ghost_folder_404")
        with self.assertRaises(FileNotFoundError):
            self.scanner.request_access(fake)

    def test_regular_file_raises_not_a_directory(self):
        regular_file = os.path.join(self.sub_dir, "doc.txt")
        with self.assertRaises(NotADirectoryError):
            self.scanner.request_access(regular_file)

    def test_security_sanitizer_traversal_attack_blocked(self):
        traversal = "../../../../etc/passwd"
        with self.assertRaises(ValidationError) as ctx:
            sanitize_path(traversal)
        self.assertIn("traversal", str(ctx.exception).lower())

    def test_security_sanitizer_shell_injection_blocked(self):
        injections = [
            f"{self.sub_dir}; rm -rf /",
            f"{self.sub_dir} && ls",
            f"{self.sub_dir} | cat",
            f"{self.sub_dir}`whoami`",
            f"{self.sub_dir}$(id)",
        ]
        for inj in injections:
            with self.subTest(inj=inj):
                with self.assertRaises(ValidationError) as ctx:
                    sanitize_path(inj)
                self.assertIn("shell metacharacters", str(ctx.exception).lower())

    def test_security_sanitizer_null_byte_blocked(self):
        null_path = f"{self.sub_dir}\x00/evil"
        with self.assertRaises(ValidationError) as ctx:
            sanitize_path(null_path)
        self.assertIn("null bytes", str(ctx.exception).lower())


class TestEmpiricalChallengerApiStateConsistency(unittest.TestCase):
    """Empirical verification of API error surfacing and session state reset."""

    def setUp(self):
        self.app = create_flask_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.tmp_dir = tempfile.mkdtemp(prefix="challenger_api_state_")

        # Create valid test directory
        self.valid_dir = os.path.join(self.tmp_dir, "valid_scan")
        os.makedirs(self.valid_dir, exist_ok=True)
        with open(os.path.join(self.valid_dir, "item.txt"), "w") as f:
            f.write("test file content")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_error_surfacing_and_state_transition(self):
        """Verify failed scan sets scanner.state = ERROR and records error message."""
        fake_dir = os.path.join(self.tmp_dir, "does_not_exist_dir")
        res = self.client.post("/api/scan/request", json={"folder_path": fake_dir})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("error", data)
        self.assertIn("does not exist", data["error"].lower())
        self.assertEqual(data["files_found"], 0)
        self.assertEqual(data["files"], [])

        # Check server persistent state
        state = load_state()
        self.assertEqual(state["scanner"]["state"], "ERROR")
        self.assertIsNotNone(state["scanner"]["error"])
        self.assertIn("does not exist", state["scanner"]["error"].lower())
        self.assertEqual(state["scanner"]["files"], [])

    def test_revoke_resets_error_state_and_cleans_session(self):
        """Verify /api/scan/revoke cleans error state and does not leak errors."""
        # Step 1: Cause error
        fake_dir = os.path.join(self.tmp_dir, "does_not_exist_dir")
        self.client.post("/api/scan/request", json={"folder_path": fake_dir})
        state_err = load_state()
        self.assertEqual(state_err["scanner"]["state"], "ERROR")
        self.assertIsNotNone(state_err["scanner"]["error"])

        # Step 2: Revoke
        res_revoke = self.client.post("/api/scan/revoke")
        self.assertEqual(res_revoke.status_code, 200)
        state_revoked = load_state()
        self.assertEqual(state_revoked["scanner"]["state"], "BLIND")
        self.assertIsNone(state_revoked["scanner"]["error"], "Revoke must reset error to None")
        self.assertIsNone(state_revoked["scanner"]["current_folder"])
        self.assertEqual(state_revoked["scanner"]["files"], [])

        # Step 3: Subsequent scan of valid folder succeeds with clean state
        res_scan = self.client.post("/api/scan/request", json={"folder_path": self.valid_dir})
        self.assertEqual(res_scan.status_code, 200)
        data_scan = res_scan.get_json()
        self.assertEqual(data_scan["status"], "completed")
        self.assertEqual(data_scan["files_found"], 1)

        state_completed = load_state()
        self.assertEqual(state_completed["scanner"]["state"], "COMPLETED")
        self.assertIsNone(state_completed["scanner"]["error"])
        self.assertEqual(len(state_completed["scanner"]["files"]), 1)

    def test_global_scanner_in_memory_state_on_revoke(self):
        """Empirically inspect global_scanner instance lifecycle on revoke."""
        # Perform valid scan
        res_scan = self.client.post("/api/scan/request", json={"folder_path": self.valid_dir})
        self.assertEqual(res_scan.status_code, 200)
        self.assertEqual(global_scanner.get_state(), ScanState.COMPLETED)
        self.assertGreater(len(global_scanner.get_scanned_files()), 0)

        # Call revoke API
        res_revoke = self.client.post("/api/scan/revoke")
        self.assertEqual(res_revoke.status_code, 200)

        # Note empirical observation:
        # Does api_scan_revoke call global_scanner.revoke_access()?
        # We test whether global_scanner._scanned_files was wiped or retained:
        has_global_scanner_purged = (len(global_scanner.get_scanned_files()) == 0)
        has_global_scanner_blind = (global_scanner.get_state() == ScanState.BLIND)

        print(f"\n[Empirical Finding Check] global_scanner purged: {has_global_scanner_purged}, state: {global_scanner.get_state()}")


class TestEmpiricalChallengerDeepTraversalPermissions(unittest.TestCase):
    """Stress test for directory traversal with unreadable subdirectories."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="challenger_traversal_")
        self.scanner = FileScanner()

    def tearDown(self):
        # Restore permissions so cleanup succeeds
        for root, dirs, files in os.walk(self.tmp_dir):
            try:
                os.chmod(root, 0o755)
            except OSError:
                pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_unreadable_child_subdirectory_raises_permission_error(self):
        """If a child subdirectory within the scoped tree is unreadable, FileScanner catches it."""
        if hasattr(os, "getuid") and os.getuid() == 0:
            self.skipTest("Running as root; permission bit 000 is bypassed by superuser.")

        # Structure:
        # root/
        #   file1.txt
        #   unreadable_sub/ (chmod 000)
        #     secret.txt
        with open(os.path.join(self.tmp_dir, "file1.txt"), "w") as f:
            f.write("visible")

        child_sub = os.path.join(self.tmp_dir, "unreadable_sub")
        os.makedirs(child_sub, exist_ok=True)
        with open(os.path.join(child_sub, "secret.txt"), "w") as f:
            f.write("secret")

        # Grant access (root is readable)
        self.scanner.request_access(self.tmp_dir)
        self.assertEqual(self.scanner.get_state(), ScanState.ACCESS_ACTIVE_SCOPED)

        # Make child unreadable
        os.chmod(child_sub, 0o000)

        # Scan should encounter PermissionError on the child directory
        with self.assertRaises(PermissionError) as ctx:
            self.scanner.scan()

        self.assertEqual(self.scanner.get_state(), ScanState.ERROR)
        self.assertEqual(len(self.scanner.get_scanned_files()), 0)
        self.assertIn("permission denied", str(ctx.exception).lower())

    def test_macos_tcc_eperm_guidance_error(self):
        """Simulate macOS TCC Errno 1 Operation not permitted during request_access."""
        from unittest.mock import patch
        with patch("os.scandir", side_effect=PermissionError(1, "Operation not permitted")):
            with self.assertRaises(PermissionError) as ctx:
                self.scanner.request_access(self.tmp_dir)
            err_str = str(ctx.exception)
            self.assertIn("macOS System Settings", err_str)
            self.assertIn("Privacy & Security", err_str)
            self.assertIn("Operation not permitted", err_str)

    def test_analysis_engine_propagates_validation_error(self):
        """AnalysisEngine.scan propagates validation error instead of empty result."""
        from src.analyzer.engine import AnalysisEngine
        from src.fileclean_core.config import Config
        engine = AnalysisEngine(Config())

        # Nonexistent path
        with self.assertRaises(ValidationError):
            engine.scan(Path(self.tmp_dir) / "nonexistent_subfolder")


class TestEmpiricalChallengerConcurrency(unittest.TestCase):
    """Concurrency and rapid stress testing on the scan endpoints."""

    def setUp(self):
        self.app = create_flask_app()
        self.app.config["TESTING"] = True
        self.tmp_dir = tempfile.mkdtemp(prefix="challenger_concurrency_")
        self.valid_dirs = []
        for i in range(3):
            d = os.path.join(self.tmp_dir, f"folder_{i}")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f"file_{i}.txt"), "w") as f:
                f.write(f"content {i}")
            self.valid_dirs.append(d)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_rapid_sequential_scan_and_revoke_cycles(self):
        """Execute 30 rapid interleaved cycles of scan, error scan, and revoke."""
        client = self.app.test_client()
        for i in range(10):
            # 1. Valid scan
            target = self.valid_dirs[i % len(self.valid_dirs)]
            res = client.post("/api/scan/request", json={"folder_path": target})
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.get_json()["status"], "completed")

            # 2. Revoke
            res_rev = client.post("/api/scan/revoke")
            self.assertEqual(res_rev.status_code, 200)

            # 3. Invalid scan
            res_err = client.post("/api/scan/request", json={"folder_path": "/nonexistent/xyz_999"})
            self.assertEqual(res_err.status_code, 400)
            self.assertEqual(res_err.get_json()["status"], "error")

            # 4. Revoke
            res_rev2 = client.post("/api/scan/revoke")
            self.assertEqual(res_rev2.status_code, 200)

        final_state = load_state()
        self.assertEqual(final_state["scanner"]["state"], "BLIND")
        self.assertIsNone(final_state["scanner"]["error"])

    def test_concurrent_multithreaded_scans(self):
        """10 threads concurrently dispatching scan requests."""
        def make_request(idx):
            client = self.app.test_client()
            if idx % 2 == 0:
                folder = self.valid_dirs[idx % len(self.valid_dirs)]
                res = client.post("/api/scan/request", json={"folder_path": folder})
                return ("valid", res.status_code, res.get_json())
            else:
                fake_folder = os.path.join(self.tmp_dir, f"fake_{idx}")
                res = client.post("/api/scan/request", json={"folder_path": fake_folder})
                return ("invalid", res.status_code, res.get_json())

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(results), 10)
        for req_type, code, data in results:
            if req_type == "valid":
                self.assertIn(code, [200, 400])  # Concurrent race may see state transition
            else:
                self.assertEqual(code, 400)
                self.assertEqual(data["status"], "error")

        # Final state sanity check - state file must remain valid JSON
        state = load_state()
        self.assertIn("scanner", state)
        self.assertIn(state["scanner"]["state"], ["COMPLETED", "ERROR", "SCANNING", "BLIND"])


if __name__ == "__main__":
    unittest.main()
