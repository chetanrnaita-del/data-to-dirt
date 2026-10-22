# Survey Report: Test Suite Architecture, Coverage, and Gap Analysis

**Agent**: `explorer_survey_3` (teamwork_preview_explorer)  
**Date**: 2026-09-08T11:58:00Z  
**Project Workspace**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt`  
**Authoritative Reference**: `.agents/ORIGINAL_REQUEST.md`  
**Status**: COMPLETE  

---

## 1. Executive Summary

An exhaustive investigation was conducted into the test architecture, configuration, execution environment, and existing test suites for **Data-to-Dirt**. The investigation specifically evaluated test coverage against the three Acceptance Criteria mandated in `ORIGINAL_REQUEST.md`:
1. **Valid Directory Indexing**: Scanning a valid local directory with files populates the frontend UI successfully.
2. **Regression Invariant**: The existing test suite (`make test`) continues to pass without regressions.
3. **Restricted/Invalid Path Error Surfacing**: Scanning a directory with restricted permissions or a non-existent/fake path displays a visible error string in the UI rather than "0 files indexed".

### Core Findings
1. **Test Runner Mechanics (`make test`)**:
   - `Makefile` line 40 defines `test:` as `@$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v`.
   - The test runner uses Python standard library `unittest` (pure offline, airgapped, zero external dependencies).
   - Because `tests/e2e` contains `__init__.py`, `unittest discover` recursively discovers tests both directly in `tests/` and in `tests/e2e/`.
2. **Why Existing Tests Missed the "0 Files Indexed" Bug**:
   - `tests/test_scanner.py` only tests happy-path scanning in isolated temporary directories with small synthetic files (`test_metadata_extraction_integrity`).
   - `tests/test_ui_and_build.py` line 195 only tests scanning the project's own `"tests"` directory (`test_api_scan_and_revoke_workflow`).
   - **Silent Suppression in FileScanner**: `FileScanner.scan()` in `src/services/scanner.py` (line 292) calls `os.walk(self._active_path, followlinks=False)` with default `onerror=None`. When `self._active_path` is unreadable due to OS permissions or macOS TCC constraints (`[Errno 1] Operation not permitted`), `os.walk` silently swallows the error and yields 0 directories and 0 files.
   - **Silent Suppression in Server Endpoint**: In `src/app/server.py` line 315, `api_scan_request()` wraps `request_access()` and `scan()` in `try ... except Exception as e:`. On exception, it sets `state["scanner"]["state"] = "ERROR"` and prints to stdout, but **returns HTTP 200 with `status: "completed"` and `files_found: 0`**.
   - **Silent Suppression in Frontend UI**: In `src/ui/js/views/student.js` line 378, `executeScan()` does not inspect `res.status` or `res.error`, and always formats the banner as: `✅ Access Active: Scoped to ${res.folder} (${res.files_found} files indexed)`.
   - **Zero Test Coverage for Error Cases**: There is **not a single test** in the entire repository that asserts that an unreadable directory, restricted directory, or non-existent path returns an error status code or error payload from `/api/scan/request`, nor that `FileScanner` raises a detectable permission exception when the root folder cannot be opened.

---

## 2. Test Architecture & Toolchain Analysis

### 2.1 Toolchain & Execution Commands
| Target / Runner | Command | Framework | Scope | Output Artifact |
|---|---|---|---|---|
| `make test` | `python3 -m unittest discover -s tests -p "test_*.py" -v` | Python `unittest` | All unit, integration, and E2E suites | Console verbose output |
| E2E Master Runner | `python3 tests/e2e/run_all_e2e.py` | Python `unittest` + custom reporter | 4-tier E2E specification tests | `tests/e2e/test_results.json` |
| Direct Tier Runs | `python3 -m unittest tests/e2e/test_tier[1-4]_*.py` | Python `unittest` | Specific E2E tiers | Console output |
| Direct Unit Runs | `python3 -m unittest tests/test_*.py` | Python `unittest` | Specific service unit tests | Console output |

### 2.2 Test Suite Inventory & Breakdown
The repository contains two primary test layers:

#### Layer 1: Unit, Stress & REST Integration Tests (`tests/`)
Contains 9 test modules with **119 total test methods**:
1. `tests/test_scanner.py` (17 tests):
   - State transitions (`BLIND`, `ACCESS_ACTIVE_SCOPED`, `COMPLETED`, `REVOKED`).
   - `request_access` error checks for `""` (ValueError), non-existent path (FileNotFoundError), regular file (NotADirectoryError).
   - Metadata extraction (`size_bytes`, `extension`, `mime_category`, `file_id`).
   - Dark data heuristics (stale relic >180d, heavy media >500MB, duplicate sizes, cache artifacts).
   - Confidentiality filters (`.env`, `id_rsa`, passwords) and deletion candidate exclusion.
   - PII text preview scrubbing regex and preview blurring.
   - Instant revocation and in-memory wipe.
2. `tests/test_ui_and_build.py` (20 tests):
   - Filesystem layout verification (`PROJECT.md`, `Makefile`, `run.sh`, `index.html`, CSS, JS).
   - Carbon calculation math formulas.
   - REST API endpoints via Flask test client (`/`, `/api/health`, `/api/student/stats`, `/api/student/leaderboard`, `/api/tree/growth`, `/api/scan/request`, `/api/scan/revoke`, `/api/deletion/submit`, `/api/auth/login`, `/api/teacher/queue`, `/api/admin/ecofund`).
3. `tests/test_carbon.py` (15 tests):
   - Mathematical model verification for kWh and Singapore grid factor ($405.7\,\text{g/kWh}$).
   - Equivalency conversions (tree-years, smartphone charges, car kilometers).
4. `tests/test_cloud.py` (15 tests):
   - `ICloudStorageProvider` interface compliance, mock Google Drive hierarchy, quota calculations, soft trash restoration.
5. `tests/test_eco_fund.py` (16 tests):
   - `EcoFundManager` budget controller, Tree-Nation micro-donations, double-entry ledger balance.
6. `tests/test_neural_net.py` (17 tests):
   - Subword tokenizer (1024 tokens), MMCRTransformer forward pass, latency <5ms, anti-gaming 3-strike escalation loop.
7. `tests/test_teacher_admin.py` (18 tests):
   - RBAC PIN verification, teacher confirmation queue, tri-state actions (approve, reject, flag), analytics aggregation.
8. `tests/test_tree_nation.py` (10 tests):
   - TreeNationClient API contract, synthetic certificate verification.
9. `tests/test_adversarial_challenger2.py` (9 tests):
   - Multi-block SHA-256 tamper-evident blockchain verification, double-entry reconciliation, multi-threaded concurrency stress testing.

#### Layer 2: Four-Tier E2E Specification Tests (`tests/e2e/`)
Contains 4 tier modules with **345 total test cases**:
- **Tier 1: Feature Coverage** (`test_tier1_features.py`, 150 tests): 5 unit tests for each of features F-01 through F-30.
- **Tier 2: Boundary & Corner Cases** (`test_tier2_boundaries.py`, 150 tests): 5 edge/boundary tests per feature.
- **Tier 3: Pairwise & Cross-Feature** (`test_tier3_pairwise.py`, 30 tests): Multi-component integration tests.
- **Tier 4: End-to-End User Scenarios** (`test_tier4_scenarios.py`, 15 tests): Multi-step user story lifecycles.

---

## 3. Analysis of Existing Coverage vs. Acceptance Criteria

| Acceptance Criterion | Existing Coverage | Status | Key Flaw / Gap |
|---|---|---|---|
| **AC 1: Valid Directory Indexing** | `test_metadata_extraction_integrity` in `test_scanner.py`<br>`test_api_scan_and_revoke_workflow` in `test_ui_and_build.py` | **PARTIAL** | Only tests trivial folders; does not test integration between `FileScanner` and `AnalysisEngine`; does not verify frontend rendering of indexed items. |
| **AC 2: Regression Invariant (`make test`)** | 119 unit tests in `tests/`<br>345 E2E tests in `tests/e2e/` | **PASSING (BASELINE)** | Existing tests assert old behavior where `/api/scan/request` returned `status: "completed"`. Any changes to endpoint response shape must maintain backward compatibility or update `test_api_scan_and_revoke_workflow`. |
| **AC 3: Restricted / Fake Path Error Surfacing** | None. `test_request_access_invalid_paths` only checks Python exceptions on `FileScanner`, never on the API endpoint or UI. | **FAILING / MISSING** | **ZERO** tests exist for permission-restricted folders (`chmod 000` or macOS TCC). **ZERO** tests assert that `/api/scan/request` returns an error status or error message. **ZERO** tests verify UI error string display. |

---

## 4. Root Cause Analysis from Test Perspective

Why did the test suite not catch the bug where scanning `/Users/narayan/Desktop/NEWSLETTER` returns 0 files?

### 4.1 Root Cause in `src/services/scanner.py`
In `src/services/scanner.py`:
```python
# Lines 225-230
resolved = os.path.abspath(os.path.expanduser(folder_path))
if not os.path.exists(resolved):
    raise FileNotFoundError(f"Selected folder does not exist: {folder_path}")
if not os.path.isdir(resolved):
    raise NotADirectoryError(f"Selected path is not a directory: {folder_path}")
```
- `request_access` never checks `os.access(resolved, os.R_OK)` or attempts to verify directory read permission.
- Then, in `scan()` (lines 292-305):
```python
for root, dirs, files in os.walk(self._active_path, followlinks=False):
```
- By Python specification, `os.walk` takes `onerror=None` by default. If `os.scandir(self._active_path)` encounters `PermissionError` (e.g. macOS TCC `[Errno 1] Operation not permitted` or Unix `000` permissions), `os.walk` **catches and suppresses the exception silently**.
- As a result, the loop terminates immediately without yielding anything. `scanned_items` remains `[]`.
- The scanner transitions to `ScanState.COMPLETED` and returns `[]`.

### 4.2 Root Cause in `src/analyzer/engine.py`
In `src/analyzer/engine.py` lines 40-45:
```python
try:
    directory = validate_scan_request(str(directory))
except ValidationError as e:
    return ScanResult(directory=directory, scan_duration=0.0)
```
- When `AnalysisEngine.scan(Path(self._active_path))` runs, `validate_scan_request()` calls `sanitize_directory()` in `src/security/sanitizer.py` line 134: `if not os.access(path, os.R_OK): raise ValidationError(...)`.
- `AnalysisEngine` catches `ValidationError` and **silently returns an empty `ScanResult`** with 0 issues, masking the failure.

### 4.3 Root Cause in `src/app/server.py`
In `src/app/server.py` lines 302-327:
```python
try:
    global_scanner.request_access(target_path, session_only)
    scanned_items = global_scanner.scan()
    ...
    state["scanner"]["files"] = files
    state["scanner"]["state"] = "COMPLETED"
except Exception as e:
    state["scanner"]["state"] = "ERROR"
    print(f"Error scanning: {e}")
    
save_state(state)

return jsonify({
    "status": "completed",
    "folder": state["scanner"]["current_folder"],
    "files_found": len(state["scanner"]["files"]),
    "files": state["scanner"]["files"],
    "session_only": session_only
})
```
- When `request_access` raises `FileNotFoundError` or `PermissionError`, the exception is caught, printed to stdout, and the server **returns HTTP 200 with `status: "completed"` and `files_found: 0`**.
- The API response contains **no `error` field**, preventing any caller from discovering that an error occurred.

### 4.4 Root Cause in `src/ui/js/views/student.js`
In `src/ui/js/views/student.js` lines 370-386:
```javascript
const res = await fetch("/api/scan/request", { ... }).then((r) => r.json());

this.scannedFiles = res.files || [];
if (banner) {
  banner.innerHTML = `<span>✅ <strong>Access Active</strong>: Scoped to <em>${res.folder}</em> (${res.files_found} files indexed)</span>`;
}
```
- The frontend blindly renders a green checkmark indicating successful indexing of 0 files, even if the folder does not exist or access was denied.

---

## 5. Test Gap Breakdown

### 5.1 Gap 1: Valid Directory Traversal & AnalysisEngine Integration
- **Missing Test**: A unit test in `test_scanner.py` that verifies that `FileScanner.scan()` successfully runs end-to-end with `AnalysisEngine` enabled, verifying that files are indexed AND dark data candidates are correctly flagged.
- **Missing Test**: An API integration test in `test_ui_and_build.py` asserting that scanning a populated directory returns HTTP 200 with `status: "completed"`, `files_found > 0`, and that each item contains the frontend-required fields (`size_formatted`, `category`, `dark_data_tag`).

### 5.2 Gap 2: Non-Existent and Fake Path Error Handling
- **Missing Test**: In `tests/test_ui_and_build.py`, test calling `POST /api/scan/request` with `{"folder_path": "/nonexistent_folder_path_xyz_123"}`:
  - Must assert that response is an error (e.g. `status: "error"`, HTTP 400 or 404).
  - Must assert that `error` message string is present and describes the missing folder.
  - Must assert that `state["scanner"]["files"]` is reset to empty, not retaining stale state.

### 5.3 Gap 3: Restricted Permissions & macOS TCC Constraints
- **Missing Test**: In `tests/test_scanner.py`:
  - Test scanning an unreadable directory (`chmod 000` on Unix or mocked `os.scandir` raising `PermissionError`).
  - Must assert that `FileScanner.request_access()` or `FileScanner.scan()` raises `PermissionError` (or a specific `ScanPermissionError`), rather than silently returning `[]`.
- **Missing Test**: In `tests/test_ui_and_build.py`:
  - Call `POST /api/scan/request` with a restricted directory path.
  - Must assert that the endpoint returns `status: "error"`, HTTP 403 (or 400), and an error payload containing a clear diagnostic string (e.g. "Permission denied: unable to read folder. Check OS permissions or macOS Privacy settings").

### 5.4 Gap 4: Frontend UI Error Banner Assertion
- **Missing Test**: In `src/ui/js/views/student.js`, `executeScan` should inspect `res.status === "error"` or `res.error` or HTTP non-200.
- When an error occurs, `#scanner-status-banner` must render:
  `<span>❌ <strong>Scan Error</strong>: ${res.error || 'Failed to scan folder'}</span>`
  and `#scanned-files-container` must show a clear error alert rather than `"No active files in memory. System is completely blind."`.

---

## 6. Test Specification Proposal

To satisfy Acceptance Criteria 1, 2, and 3, the following concrete tests should be added to the test suite:

### 6.1 New Tests for `tests/test_scanner.py`
```python
def test_request_access_permission_denied(self):
    """Unreadable directory raises PermissionError on request_access."""
    restricted_dir = os.path.join(self.root_path, "restricted_dir")
    os.makedirs(restricted_dir, exist_ok=True)
    try:
        os.chmod(restricted_dir, 0o000)
        with self.assertRaises((PermissionError, OSError)):
            self.scanner.request_access(restricted_dir)
    finally:
        os.chmod(restricted_dir, 0o755)

def test_scan_unreadable_root_raises_permission_error(self):
    """If root directory cannot be read, scan() must raise PermissionError, not return 0 files."""
    restricted_dir = os.path.join(self.root_path, "unreadable_dir")
    os.makedirs(restricted_dir, exist_ok=True)
    with open(os.path.join(restricted_dir, "secret.txt"), "w") as f:
        f.write("data")
    try:
        os.chmod(restricted_dir, 0o000)
        # Assuming request_access passed or mocked
        self.scanner._active_path = restricted_dir
        self.scanner._state = ScanState.ACCESS_ACTIVE_SCOPED
        with self.assertRaises((PermissionError, OSError)):
            self.scanner.scan()
    finally:
        os.chmod(restricted_dir, 0o755)

def test_scan_tcc_mac_error_diagnostic(self):
    """Simulated macOS TCC EPERM raises PermissionError with diagnostic message."""
    with unittest.mock.patch("os.walk", side_effect=PermissionError(1, "Operation not permitted")):
        self.scanner.request_access(self.root_path)
        with self.assertRaises(PermissionError) as ctx:
            self.scanner.scan()
        self.assertIn("Operation not permitted", str(ctx.exception))
```

### 6.2 New Tests for `tests/test_ui_and_build.py`
```python
def test_api_scan_request_fake_path_returns_error(self):
    """Scanning non-existent path returns error status and visible error message."""
    res = self.client.post("/api/scan/request", json={"folder_path": "/nonexistent_folder_xyz_987"})
    self.assertIn(res.status_code, [400, 404])
    data = res.get_json()
    self.assertEqual(data["status"], "error")
    self.assertIn("error", data)
    self.assertTrue(len(data["error"]) > 0)

def test_api_scan_request_restricted_folder_returns_error(self):
    """Scanning restricted directory returns error status and visible error message."""
    temp_dir = tempfile.mkdtemp()
    try:
        os.chmod(temp_dir, 0o000)
        res = self.client.post("/api/scan/request", json={"folder_path": temp_dir})
        self.assertIn(res.status_code, [400, 403])
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("error", data)
        self.assertIn("Permission denied", data["error"])
    finally:
        os.chmod(temp_dir, 0o755)
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_api_scan_request_valid_directory_populates_files(self):
    """Scanning valid directory returns completed status and non-zero files."""
    res = self.client.post("/api/scan/request", json={"folder_path": "tests", "session_only": True})
    self.assertEqual(res.status_code, 200)
    data = res.get_json()
    self.assertEqual(data["status"], "completed")
    self.assertGreater(data["files_found"], 0)
    self.assertIsInstance(data["files"], list)
    first = data["files"][0]
    self.assertIn("file_name", first)
    self.assertIn("size_formatted", first)
    self.assertIn("dark_data_tag", first)
```

---

## 7. Regression Strategy

To ensure `make test` continues to pass without regressions:
1. **Endpoint Contract Compatibility**:
   For valid directory scans, `/api/scan/request` must continue to return:
   `{"status": "completed", "folder": ..., "files_found": ..., "files": [...], "session_only": ...}` with HTTP 200.
   This guarantees that existing `test_api_scan_and_revoke_workflow` in `tests/test_ui_and_build.py` succeeds without modification.
2. **Error Contract Addition**:
   For failed scans (non-existent, unreadable, TCC-restricted), `/api/scan/request` should return:
   `{"status": "error", "error": "<diagnostic error message>", "folder": ...}` with HTTP 400/403/404.
3. **Execution Verification**:
   Run `make test` which executes `python3 -m unittest discover -s tests -p "test_*.py" -v`.
   All 119 existing unit tests + 345 E2E tests + newly added tests must complete with 0 failures and 0 errors.

---

## 8. Summary Table of Gaps & Fixes

| Component | Current Defect | Recommended Fix | Test Verification |
|---|---|---|---|
| `src/services/scanner.py` | `os.walk` with `onerror=None` swallows permissions; `request_access` does not check `os.R_OK` | Add readability verification in `request_access`; pass `onerror` callback in `os.walk` that raises `PermissionError` when root cannot be read | `test_request_access_permission_denied`, `test_scan_unreadable_root_raises_permission_error` |
| `src/analyzer/engine.py` | Catches `ValidationError` and returns empty `ScanResult(0)` | Propagate or log permission validation failure so caller knows scan failed | Verify integration between `FileScanner` and `AnalysisEngine` |
| `src/app/server.py` | Catches all exceptions and returns HTTP 200 `status: "completed"`, `files_found: 0` | Return HTTP 400/403 with `status: "error"`, `error: str(e)` | `test_api_scan_request_fake_path_returns_error`, `test_api_scan_request_restricted_folder_returns_error` |
| `src/ui/js/views/student.js` | Blindly renders `Access Active (0 files indexed)` even on error | Check `res.status === "error"` or `res.error` or `!r.ok`, display visible error banner `❌ Scan failed: ${res.error}` | Manual UI check & API contract test in `test_ui_and_build.py` |
