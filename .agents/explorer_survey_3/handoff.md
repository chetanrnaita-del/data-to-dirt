# Handoff Report: Test Suite Architecture & Gap Analysis (Survey 3)

**Agent**: `explorer_survey_3` (teamwork_preview_explorer)  
**Date**: 2026-09-08T11:59:00Z  
**Project Workspace**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt`  
**Working Directory**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_survey_3`  
**Handoff Type**: Hard Handoff (Survey Complete)  

---

## 1. Observation

### 1.1 Test Suite Configuration and Execution Command
Direct observation of `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/Makefile` lines 36–44:
```makefile
test:
	@echo "=================================================="
	@echo "  DATA-TO-DIRT: Executing Test Suite              "
	@echo "=================================================="
	@$(PYTHON) -m unittest discover -s tests -p "test_*.py" -v
	@echo "=================================================="
	@echo "  [✓] All tests passed!                           "
	@echo "=================================================="
```
- The test command is: `python3 -m unittest discover -s tests -p "test_*.py" -v`.
- The test suite relies exclusively on Python's built-in `unittest` module without external test dependencies.

### 1.2 Existing Test Files and Coverage Inventory
Observation of `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/tests`:
- Unit/Integration test files in `tests/`:
  - `test_scanner.py` (17 tests): Tests `FileScanner` state machine, blind initial state, basic traversal in temp directories, heuristics (stale, heavy, duplicate, temp cache), confidential patterns, PII redaction, revocation.
  - `test_ui_and_build.py` (20 tests): Lines 193–200 test `/api/scan/request` strictly on `"tests"` folder:
    ```python
    def test_api_scan_and_revoke_workflow(self):
        res = self.client.post("/api/scan/request", json={"folder_path": "tests", "session_only": True})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "completed")
        self.assertGreater(data["files_found"], 0)
    ```
  - `test_carbon.py` (15 tests): Energy/carbon formulas.
  - `test_cloud.py` (15 tests): Mock cloud storage provider.
  - `test_eco_fund.py` (16 tests): Eco-Fund and ledger tests.
  - `test_neural_net.py` (17 tests): Subword tokenizer and MMCRTransformer.
  - `test_teacher_admin.py` (18 tests): RBAC and teacher queue.
  - `test_tree_nation.py` (10 tests): Tree-Nation client.
  - `test_adversarial_challenger2.py` (9 tests): Ledger blockchain tamper resistance, double-entry reconciliation, multi-threaded stress testing.
- Four-Tier E2E Specification tests in `tests/e2e/` (345 tests):
  - `test_tier1_features.py` (150 tests), `test_tier2_boundaries.py` (150 tests), `test_tier3_pairwise.py` (30 tests), `test_tier4_scenarios.py` (15 tests) defined against mock specifications in `tests/e2e/harness.py`.
  - Observed baseline in `tests/e2e/test_results.json`: 345 total tests, 345 passed, 0 failed, duration 5.75s.

### 1.3 Silent Swallowing of Permission and Scanning Errors
Direct observation of:
1. `src/services/scanner.py` line 292:
   ```python
   for root, dirs, files in os.walk(self._active_path, followlinks=False):
   ```
   `os.walk` defaults to `onerror=None`. When attempting to read an unreadable directory (e.g. Unix `chmod 000` or macOS TCC restriction `[Errno 1] Operation not permitted`), `os.walk` silently catches the `OSError`/`PermissionError` and yields nothing, returning an empty list `[]` without error.
2. `src/app/server.py` lines 315–327:
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
   When `global_scanner.request_access()` or `global_scanner.scan()` raises an exception, the server catches it, but responds with HTTP 200, `status: "completed"`, `files_found: 0`, and no `error` field.
3. `src/ui/js/views/student.js` lines 376–379:
   ```javascript
   this.scannedFiles = res.files || [];
   if (banner) {
     banner.innerHTML = `<span>✅ <strong>Access Active</strong>: Scoped to <em>${res.folder}</em> (${res.files_found} files indexed)</span>`;
   }
   ```
   The UI always prints `✅ Access Active: Scoped to ... (0 files indexed)` when `res.status` is `"completed"`.
4. macOS TCC Execution Failure:
   Attempting `list_dir` on `/Users/narayan/Desktop/NEWSLETTER` failed verbatim with:
   `open /Users/narayan/Desktop/NEWSLETTER: operation not permitted`

---

## 2. Logic Chain

1. **Premise**: `ORIGINAL_REQUEST.md` requires:
   - AC1: Scanning a valid local directory with files populates the frontend UI successfully.
   - AC2: `make test` continues to pass without regressions.
   - AC3: Scanning a directory with restricted permissions (or a fake path) displays a visible error string in the UI rather than "0 files indexed".
2. **Observation 1.1 & 1.2**: Current tests only execute valid directory scanning on synthetic temp directories or `"tests"`. `test_api_scan_and_revoke_workflow` asserts `status == "completed"` and `files_found > 0`. There are zero tests in `tests/` or `tests/e2e/` testing non-existent folders or permission-restricted folders through the REST API or UI.
3. **Observation 1.3 (1)**: `os.walk` without `onerror` suppresses `PermissionError` when reading directory handles. Therefore, an unreadable directory (such as a TCC-restricted folder) returns `files = []` with zero exceptions raised by `scan()`.
4. **Observation 1.3 (2)**: Even if `request_access` or another step raises `FileNotFoundError` or `PermissionError`, `server.py` catches `Exception`, logs to console, but sends HTTP 200 with `status: "completed"` and `files_found: 0`.
5. **Observation 1.3 (3)**: `student.js` receives `status: "completed"` and `files_found: 0`, and renders `✅ Access Active: Scoped to ... (0 files indexed)`.
6. **Inference**: The current test suite has a total gap regarding error conditions and permission failures. It passed 100% because no test ever exercised an invalid path, a permission-restricted folder, or asserted that `/api/scan/request` produces an error response.
7. **Deduction**: To verify AC1, AC2, and AC3, new tests must be added to `tests/test_scanner.py` (verifying `PermissionError` detection) and `tests/test_ui_and_build.py` (verifying `/api/scan/request` error response with status code 400/403 and error message payload). The existing valid scan test in `test_ui_and_build.py` must continue to pass to guarantee AC2.

---

## 3. Caveats

1. **Interactive UI Testing**: The project does not have a browser automation framework (e.g. Playwright, Cypress, Selenium). UI testing is performed via static asset validation, JavaScript file inspection in `test_ui_and_build.py`, and manual testing in the electron/browser desktop shell.
2. **macOS TCC in Automated Environments**: Automated tests running in CI or headless sandboxes cannot simulate user TCC GUI prompts. TCC constraints must be tested by checking `PermissionError` / `errno.EPERM` handling or creating restricted directories (`chmod 000`).
3. **E2E Test Decoupling**: `tests/e2e/test_tier[1-4]_*.py` tests against `harness.py` specification classes rather than `src/app/server.py`. Adding live API error tests should be targeted at `tests/test_ui_and_build.py` and `tests/test_scanner.py`.

---

## 4. Conclusion

1. **Baseline Health**: The existing test suite executed by `make test` contains 119 unit/integration tests and 345 E2E tests, which all pass in the baseline state.
2. **Identified Test Gaps**:
   - `FileScanner`: Missing tests for unreadable directories (`chmod 000`), permission check failures, and `os.walk` error propagation.
   - `server.py` `/api/scan/request`: Missing tests for invalid paths, non-existent folders, and permission-denied folders returning HTTP 400/403 with `status: "error"` and a diagnostic error message.
   - `student.js`: Missing checks for error response handling and visible banner error display.
3. **Required Action Plan**:
   - Update `src/services/scanner.py` to check directory readability in `request_access` and handle `onerror` in `os.walk` so `PermissionError` is not swallowed.
   - Update `src/app/server.py` to return `{"status": "error", "error": str(e)}` with HTTP 400/403 when scanning fails.
   - Update `src/ui/js/views/student.js` to render `❌ Scan failed: ${res.error}` on error.
   - Add unit tests to `tests/test_scanner.py` and integration tests to `tests/test_ui_and_build.py`.
   - Run `make test` to verify zero regressions.

---

## 5. Verification Method

To independently verify the test suite baseline and gaps:

1. **Run Master Test Command**:
   ```bash
   make test
   # Or directly:
   python3 -m unittest discover -s tests -p "test_*.py" -v
   ```
   Expected: All existing tests pass.

2. **Run E2E Master Runner**:
   ```bash
   python3 tests/e2e/run_all_e2e.py
   ```
   Expected: 345/345 tests pass.

3. **Verify Existing Endpoint Test**:
   Inspect `tests/test_ui_and_build.py` lines 193–200 to confirm that only a valid folder (`"tests"`) is tested.

4. **Verify Silent Failure in Server**:
   Inspect `src/app/server.py` lines 315–327 to confirm that exceptions return `status: "completed"` with 0 files.

5. **Invalidation Conditions**:
   - If `make test` fails on a clean checkout, the test baseline is invalid.
   - If `/api/scan/request` already returns an error code on invalid paths, our gap finding on `server.py` would be invalidated (confirmed present by inspecting `server.py`).
