# Handoff Report: Test Enhancement Strategy for Milestone 1

**From**: `explorer_m1_3` (teamwork_preview_explorer)  
**To**: `orchestrator` (parent id: `e21f5569-9a5c-4ba2-987c-97f42180e634`)  
**Task**: Formulate the exact test enhancement strategy for `tests/test_scanner.py` and `tests/test_ui_and_build.py` covering AC1, AC2, and AC3.  
**Working Directory**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_m1_3`  
**Recommendation File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_m1_3/recommendation.md`  
**Handoff Type**: Hard Handoff (Investigation and formulation complete)  

---

## 1. Observation

### Obs 1: Existing Test Suite Scope and Gaps in `tests/test_scanner.py`
- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/tests/test_scanner.py` (398 lines, 17 tests).
- Lines 54–68:
  ```python
  def test_request_access_invalid_paths(self):
      """Requesting access on non-existent or file paths raises appropriate errors."""
      with self.assertRaises(ValueError):
          self.scanner.request_access("")

      with self.assertRaises(FileNotFoundError):
          self.scanner.request_access(os.path.join(self.root_path, "does_not_exist"))

      # Create a file and verify NotADirectoryError
      test_file = os.path.join(self.root_path, "regular_file.txt")
      with open(test_file, "w") as f:
          f.write("sample")
      with self.assertRaises(NotADirectoryError):
          self.scanner.request_access(test_file)
  ```
  - While line 59 checks `FileNotFoundError`, it does not assert that state remains `ScanState.BLIND` or that `is_access_granted()` is `False`.
  - Zero tests in `tests/test_scanner.py` check permission-restricted directories (`chmod 000`) or unreadable root paths.
  - Line 292 of `src/services/scanner.py` executes `os.walk(self._active_path, followlinks=False)` without an `onerror` handler, so when a root directory is unreadable, `os.walk` silently catches the `OSError` and yields 0 files. Zero tests currently exercise `scan()` with an unreadable root directory to verify that `ScanState.ERROR` is set and `PermissionError` is raised.

### Obs 2: Existing REST Endpoint Scanning Test in `tests/test_ui_and_build.py`
- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/tests/test_ui_and_build.py` (276 lines, 20 tests).
- Lines 193–200:
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
  - This is the only test in the entire repository exercising `POST /api/scan/request`.
  - It only tests a valid existing directory (`"tests"`).
  - There are zero tests asserting HTTP 400 or `status: "error"` when a fake path or permission-restricted folder is requested.
  - In `tests/test_ui_and_build.py`, `tempfile` is not imported.

### Obs 3: Silent Suppression in `src/app/server.py`
- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/app/server.py` lines 315–327:
  ```python
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
  - Exceptions during scanning log to console and set state to `"ERROR"`, but `server.py` still returns HTTP 200 with `"status": "completed"`, `files_found: 0`, and no `error` field in JSON.

### Obs 4: UI Blindness in `src/ui/js/views/student.js`
- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/ui/js/views/student.js` lines 370–384:
  ```javascript
  const res = await fetch("/api/scan/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_path: folderPath, session_only: sessionOnly }),
  }).then((r) => r.json());

  this.scannedFiles = res.files || [];
  if (banner) {
    banner.innerHTML = `<span>✅ <strong>Access Active</strong>: Scoped to <em>${res.folder}</em> (${res.files_found} files indexed)</span>`;
  }
  ```
  - The UI ignores HTTP status and JSON status, unconditionally rendering green success banner `(0 files indexed)` and playing the success chime.

### Obs 5: Test Suite Baseline Metrics
- Current test suite execution (`make test`) runs `python3 -m unittest discover -s tests -p "test_*.py" -v`.
- Baseline count: 503 tests passing (158 in `tests/`, 345 in `tests/e2e/`), 0 failures, 0 errors.

---

## 2. Logic Chain

1. **Premise 1 (Obs 1 & Obs 2)**: The current test suite passes 100% because no test checks error states or permission constraints on `/api/scan/request` or `FileScanner.scan()`.
2. **Premise 2 (Obs 3 & Obs 4)**: The silent failure bug reported in `ORIGINAL_REQUEST.md` ("0 files indexed" on inaccessible directories) is enabled by this test gap: `server.py` swallows exceptions and returns HTTP 200 `"status": "completed"`, and `student.js` treats all responses as successful scans.
3. **Premise 3 (Obs 5 & Obs 2)**: The existing test `test_api_scan_and_revoke_workflow` scans `"tests"`, a valid readable directory. When the bug is fixed, valid directories must continue returning HTTP 200 and `status: "completed"`. Thus, `test_api_scan_and_revoke_workflow` will not regress.
4. **Deduction 1 (AC3 Error Surfacing)**:
   - In `tests/test_scanner.py`: We must add tests asserting that:
     1. Non-existent path raises `FileNotFoundError` and preserves `ScanState.BLIND`.
     2. Restricted path (`chmod 000`) raises `PermissionError` in `request_access()` and preserves `ScanState.BLIND`.
     3. Unreadable root directory during `scan()` triggers `os.walk(onerror=...)`, transitions to `ScanState.ERROR`, and raises `PermissionError`.
   - In `tests/test_ui_and_build.py`: We must add tests asserting that:
     1. Non-existent path via `POST /api/scan/request` returns HTTP 400, `status: "error"`, `error` containing `"does not exist"`, `files_found: 0`, and `files: []`.
     2. Restricted path (`chmod 000`) via `POST /api/scan/request` returns HTTP 400, `status: "error"`, `error` containing permission details, `files_found: 0`, and `files: []`.
     3. Static check on `student.js` verifies `res.status === "error"` check and `playGamingBuzzer` are present.
5. **Deduction 2 (AC1 Valid Directory Population)**:
   - In `tests/test_ui_and_build.py`: We must add a dedicated test scanning a populated temporary folder containing both normal and temporary files. It verifies HTTP 200, `status: "completed"`, `files_found == 2`, and validates file metadata schemas (`size_formatted`, `category`, `dark_data_tag`).
6. **Deduction 3 (AC2 Zero Regressions)**:
   - All 7 new test methods strictly adhere to standard Python `unittest` conventions.
   - All directory manipulations using `chmod 000` are protected by `try...finally: os.chmod(..., 0o755)` to prevent teardown permission failures.
   - When Worker implements these tests and the fixes, `make test` will expand from 503 to 510 tests passing with 0 failures.

---

## 3. Caveats

1. **Root Superuser Execution (UID 0)**: In container environments where tests run as `root`, the OS kernel ignores POSIX `000` permission bits on directory reads. The test cases include an `os.getuid() == 0` check using `self.skipTest` to prevent false failures in root containers. On macOS host (where UID != 0), the tests run natively and rigorously verify permission blocking.
2. **Teardown Cleanup Safety**: If `os.chmod(..., 0o755)` is omitted after setting `0o000`, `tempfile.TemporaryDirectory().cleanup()` crashes during `tearDown()`. The recommended test cases mandate `try...finally` blocks.
3. **Frontend Automated Testing Limitation**: The repository does not include a headless browser runner (Playwright/Puppeteer/Selenium). UI error handling is therefore verified through static AST/content inspection in `test_ui_and_build.py` (`test_student_js_error_handling_present`) combined with manual browser verification.

---

## 4. Conclusion

The test enhancement strategy has been fully specified in `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_m1_3/recommendation.md`.

Seven new automated tests are specified:
- **`tests/test_scanner.py` (+3 tests)**:
  1. `test_request_access_nonexistent_directory_raises_file_not_found`
  2. `test_request_access_restricted_directory_raises_permission_error`
  3. `test_scan_unreadable_directory_sets_error_state_and_raises`
- **`tests/test_ui_and_build.py` (+4 tests)**:
  4. `test_api_scan_request_fake_directory_returns_400`
  5. `test_api_scan_request_restricted_directory_returns_400`
  6. `test_api_scan_request_valid_populated_directory_returns_200`
  7. `test_student_js_error_handling_present`

These tests provide end-to-end verification of AC1, AC2, and AC3 without introducing regressions into the existing test suite.

---

## 5. Verification Method

### 5.1 Project Test Command
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
# or
make test
```
- **Current Baseline**: 503 tests passing.
- **Post-Worker Baseline**: 510 tests passing (165 in `tests/`, 345 in `tests/e2e/`).

### 5.2 Individual Module Test Commands
```bash
python3 -m unittest tests/test_scanner.py -v
```
Expected: 20 tests passing (17 original + 3 new).

```bash
python3 -m unittest tests/test_ui_and_build.py -v
```
Expected: 24 tests passing (20 original + 4 new).

### 5.3 Invalidation Conditions
- If any of the existing 503 tests fail, the change is invalid.
- If scanning an invalid or permission-denied directory returns HTTP 200, the test must fail.
- If `tempfile` cleanup fails due to unreleased `0o000` permissions, the test is invalid.
