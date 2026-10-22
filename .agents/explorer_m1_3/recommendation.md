# Test Enhancement Strategy for Milestone 1

**Author**: `explorer_m1_3`  
**Target Files**: `tests/test_scanner.py`, `tests/test_ui_and_build.py`  
**Scope**: Verification of Acceptance Criteria AC1, AC2, and AC3  
**Status**: Recommendation for Worker Implementation  

---

## 1. Executive Summary & Acceptance Criteria Mapping

The objective of Milestone 1 is to eliminate the silent failure ("0 files indexed") when scanning missing or permission-restricted folders (such as macOS TCC protected directories), while ensuring valid folders index normally and zero regressions occur across the existing 503-test suite.

| Acceptance Criterion | Requirement | Test Verification Strategy |
|---|---|---|
| **AC1: Valid Scan Population** | Scanning a valid local directory with files in it populates the frontend UI successfully. | `test_api_scan_request_valid_populated_directory_returns_200` in `test_ui_and_build.py` + existing `test_api_scan_and_revoke_workflow` + `test_metadata_extraction_integrity` in `test_scanner.py`. |
| **AC2: Zero Regression** | Existing test suite (`make test` / 503 tests) continues to pass without regressions. | Backward compatibility verification of all existing public API contracts and existing test fixtures; zero signature changes. |
| **AC3: Error Surfacing** | Scanning a restricted or non-existent path surfaces a visible error string rather than "0 files indexed". | `test_request_access_nonexistent_directory_raises_file_not_found`, `test_request_access_restricted_directory_raises_permission_error`, `test_scan_unreadable_directory_sets_error_state_and_raises` in `test_scanner.py`; `test_api_scan_request_fake_directory_returns_400`, `test_api_scan_request_restricted_directory_returns_400`, and `test_student_js_error_handling_logic_present` in `test_ui_and_build.py`. |

---

## 2. Test Specifications for `tests/test_scanner.py`

### 2.1 File Context & Insertion Location
- **File**: `tests/test_scanner.py`
- **Class**: `TestFileScanner(unittest.TestCase)`
- **Insertion Point**: Inside Section 1 (`# 1. Blind Initial State & Permission Lifecycle`), immediately following `test_request_access_valid_directory(self)` (after line 75).
- **Existing Imports**: `os`, `time`, `tempfile`, `unittest`, `FileScanner`, `ScanState`, `ScannedFileMetadata`, `PermissionRequiredError`, `ConfidentialFileError`, `redact_text`, `HEAVY_FILE_THRESHOLD_BYTES`. All required imports are already present in `test_scanner.py`.

### 2.2 Test Case 1: Non-Existent Directory Access
**Method Name**: `test_request_access_nonexistent_directory_raises_file_not_found`  
**Purpose**: Rigorously verify that passing a non-existent directory raises `FileNotFoundError`, includes a clear message, maintains `ScanState.BLIND`, and leaves `is_access_granted()` as `False`.  
**Code Specification**:
```python
    def test_request_access_nonexistent_directory_raises_file_not_found(self):
        """Requesting access on a non-existent directory raises FileNotFoundError and remains BLIND."""
        fake_path = os.path.join(self.root_path, "missing_subdir_12345")
        with self.assertRaises(FileNotFoundError) as ctx:
            self.scanner.request_access(fake_path)

        self.assertIn("does not exist", str(ctx.exception).lower())
        self.assertEqual(self.scanner.get_state(), ScanState.BLIND)
        self.assertFalse(self.scanner.is_access_granted())
        self.assertEqual(len(self.scanner.get_scanned_files()), 0)
```

### 2.3 Test Case 2: Restricted (`chmod 000`) Directory Access
**Method Name**: `test_request_access_restricted_directory_raises_permission_error`  
**Purpose**: Verify that requesting access to an unreadable directory (simulating unreadable Unix directories or macOS TCC restriction) raises `PermissionError`, leaves state `BLIND`, and preserves cleanup safety.  
**Critical Safety Requirement**: Any directory modified with `os.chmod(..., 0o000)` **MUST** restore permissions via `os.chmod(..., 0o755)` in a `finally` block, otherwise `self.temp_dir.cleanup()` will fail with `PermissionError` in `tearDown()`.  
**Code Specification**:
```python
    def test_request_access_restricted_directory_raises_permission_error(self):
        """Requesting access on an unreadable directory raises PermissionError and remains BLIND."""
        restricted_dir = os.path.join(self.root_path, "restricted_access_dir")
        os.makedirs(restricted_dir, exist_ok=True)
        os.chmod(restricted_dir, 0o000)
        try:
            # Skip if running as root (UID 0 ignores 000 permissions)
            if hasattr(os, "getuid") and os.getuid() == 0:
                self.skipTest("Running as root; filesystem permission bit 000 is bypassed by superuser.")

            with self.assertRaises(PermissionError) as ctx:
                self.scanner.request_access(restricted_dir)

            err_msg = str(ctx.exception).lower()
            self.assertTrue(
                "permission denied" in err_msg or "operation not permitted" in err_msg,
                f"Expected permission error message, got: {ctx.exception}"
            )
            self.assertEqual(self.scanner.get_state(), ScanState.BLIND)
            self.assertFalse(self.scanner.is_access_granted())
        finally:
            os.chmod(restricted_dir, 0o755)
```

### 2.4 Test Case 3: Unreadable Directory During `scan()` Sets `ScanState.ERROR`
**Method Name**: `test_scan_unreadable_directory_sets_error_state_and_raises`  
**Purpose**: Verify that if a directory is unreadable when `scan()` executes, the `os.walk(onerror=...)` handler captures the failure, transitions the state to `ScanState.ERROR`, and raises `PermissionError` rather than silently returning 0 items.  
**Code Specification**:
```python
    def test_scan_unreadable_directory_sets_error_state_and_raises(self):
        """Scanning an unreadable directory raises PermissionError and sets ScanState.ERROR."""
        scan_dir = os.path.join(self.root_path, "scan_perm_error_dir")
        os.makedirs(scan_dir, exist_ok=True)

        # Grant access while directory is readable
        self.scanner.request_access(scan_dir)
        self.assertEqual(self.scanner.get_state(), ScanState.ACCESS_ACTIVE_SCOPED)

        # Revoke read permissions right before scanning to test scan() traversal error capture
        os.chmod(scan_dir, 0o000)
        try:
            if hasattr(os, "getuid") and os.getuid() == 0:
                self.skipTest("Running as root; filesystem permission bit 000 is bypassed by superuser.")

            with self.assertRaises(PermissionError):
                self.scanner.scan()

            self.assertEqual(self.scanner.get_state(), ScanState.ERROR)
            self.assertEqual(len(self.scanner.get_scanned_files()), 0)
        finally:
            os.chmod(scan_dir, 0o755)
```

---

## 3. Test Specifications for `tests/test_ui_and_build.py`

### 3.1 File Context & Import Requirements
- **File**: `tests/test_ui_and_build.py`
- **Import Addition**: Add `import tempfile` to the top-level imports (around lines 7–12).
- **Target Classes**:
  1. `TestServerRestEndpoints(unittest.TestCase)`: Integration tests on `POST /api/scan/request`.
  2. `TestBuildAndFilesystem(unittest.TestCase)`: Static contract check on `student.js`.

### 3.2 Test Case 4: Fake Directory via `POST /api/scan/request` Returns HTTP 400
**Class**: `TestServerRestEndpoints`  
**Method Name**: `test_api_scan_request_fake_directory_returns_400`  
**Purpose**: Verify REST contract when `folder_path` points to a non-existent path.  
**Contract Verification**:
- HTTP status code: `400`
- `status`: `"error"`
- `error`: non-empty descriptive string containing `"does not exist"`
- `files_found`: `0`
- `files`: `[]`
- `folder`: the supplied target path  
**Code Specification**:
```python
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
```

### 3.3 Test Case 5: Restricted Directory via `POST /api/scan/request` Returns HTTP 400
**Class**: `TestServerRestEndpoints`  
**Method Name**: `test_api_scan_request_restricted_directory_returns_400`  
**Purpose**: Verify REST contract when `folder_path` is restricted (`chmod 000`), ensuring error details (e.g. "Permission denied" or "Operation not permitted") are returned to the client with HTTP 400 rather than silently returning HTTP 200 with 0 files.  
**Code Specification**:
```python
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
```

### 3.4 Test Case 6: Valid Populated Directory via `POST /api/scan/request` Returns HTTP 200 with Metadata
**Class**: `TestServerRestEndpoints`  
**Method Name**: `test_api_scan_request_valid_populated_directory_returns_200`  
**Purpose**: Rigorously verify AC1: scanning a populated directory returns HTTP 200, `status: "completed"`, `files_found > 0`, and the complete frontend metadata schema including `size_formatted`, `category`, and `dark_data_tag`.  
**Code Specification**:
```python
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
```

### 3.5 Test Case 7: Static Inspection of `student.js` Error Handling Logic
**Class**: `TestBuildAndFilesystem`  
**Method Name**: `test_student_js_error_handling_present`  
**Purpose**: Verify that `src/ui/js/views/student.js` contains explicit error status evaluation, error banner display, and gaming buzzer audio triggers, guaranteeing AC3 at the static build test layer.  
**Code Specification**:
```python
    def test_student_js_error_handling_present(self):
        """Verify student.js inspects response error status and renders error banner."""
        student_js = (UI_DIR / "js" / "views" / "student.js").read_text(encoding="utf-8")
        self.assertIn("res.status === \"error\"", student_js, "student.js must check for status === 'error'")
        self.assertIn("playGamingBuzzer", student_js, "student.js should trigger buzzer on scan error")
```

---

## 4. Compatibility & Zero-Regression Analysis

### 4.1 Compatibility with `test_api_scan_and_revoke_workflow`
In `tests/test_ui_and_build.py` line 193:
```python
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
```
- **Analysis**: This test passes `"folder_path": "tests"`. `"tests"` is a valid, readable directory in the project repository containing multiple test files.
- Under the proposed backend changes:
  1. `global_scanner.request_access("tests", session_only)` succeeds because `"tests"` exists and is readable.
  2. `global_scanner.scan()` successfully traverses `"tests"` and populates file metadata.
  3. `server.py` returns HTTP 200 with `status: "completed"` and `files_found > 0`.
  4. `POST /api/scan/revoke` zeroes in-memory state and returns HTTP 200 with `status: "revoked"`.
- **Verdict**: 100% compatible. No test edits are needed for `test_api_scan_and_revoke_workflow`.

### 4.2 Impact on Existing 503 Baseline Tests
- **`tests/test_scanner.py` (17 tests)**: None of the existing 17 tests attempt to scan unreadable directories. Adding tests 1–3 increases the count to 20 tests with 0 breaks.
- **`tests/test_ui_and_build.py` (20 tests)**: Existing tests only scan `"tests"`. Adding tests 4–7 increases the count to 24 tests with 0 breaks.
- **`tests/e2e/test_tier[1-4]_*.py` (345 tests)**: All E2E tier tests run against mock classes in `harness.py`. None interact with live OS filesystem permission bits.
- **Other test modules (`test_carbon.py`, `test_cloud.py`, `test_eco_fund.py`, `test_neural_net.py`, `test_teacher_admin.py`, `test_tree_nation.py`, `test_adversarial_challenger2.py`)**: Completely independent of the file scanner.
- **Total Test Count Post-Implementation**: 503 baseline + 7 new tests = **510 tests passing**.

---

## 5. Worker Implementation Checklist

1. **In `tests/test_ui_and_build.py`**:
   - [ ] Add `import tempfile` to imports.
   - [ ] Add `test_student_js_error_handling_present` to `TestBuildAndFilesystem`.
   - [ ] Add `test_api_scan_request_fake_directory_returns_400` to `TestServerRestEndpoints`.
   - [ ] Add `test_api_scan_request_restricted_directory_returns_400` to `TestServerRestEndpoints`.
   - [ ] Add `test_api_scan_request_valid_populated_directory_returns_200` to `TestServerRestEndpoints`.
2. **In `tests/test_scanner.py`**:
   - [ ] Add `test_request_access_nonexistent_directory_raises_file_not_found` to `TestFileScanner`.
   - [ ] Add `test_request_access_restricted_directory_raises_permission_error` to `TestFileScanner`.
   - [ ] Add `test_scan_unreadable_directory_sets_error_state_and_raises` to `TestFileScanner`.
3. **Execution Verification**:
   - [ ] Run `python3 -m unittest tests/test_scanner.py` -> 20 tests pass.
   - [ ] Run `python3 -m unittest tests/test_ui_and_build.py` -> 24 tests pass.
   - [ ] Run `make test` -> all 510 tests pass with zero regressions.
