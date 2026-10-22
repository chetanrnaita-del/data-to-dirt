# Dispatch to Worker M1-1

## 2026-09-08T12:07:00Z

**Assigned Agent**: worker_m1_1 (teamwork_preview_worker)
**Working Directory**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/worker_m1_1`
**Project Workspace Root**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt`
**Original Request Path**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/ORIGINAL_REQUEST.md`
**Project Plan Path**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/orchestrator/PROJECT.md`

### Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### File Ownership
You exclusively own and may edit the following files:
- `src/services/scanner.py`
- `src/analyzer/engine.py`
- `src/analyzer/sanitizer.py`
- `src/app/server.py`
- `src/ui/js/views/student.js`
- `tests/test_scanner.py`
- `tests/test_ui_and_build.py`

### Strategy Blueprints to Read
Carefully read the detailed recommendations from the Explorers:
- `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_m1_1/recommendation.md`
- `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_m1_2/recommendation.md`
- `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_m1_3/recommendation.md`

### Implementation Tasks
1. **`src/services/scanner.py`**:
   - In `request_access()`: Strip wrapping whitespace and single/double quotes from `folder_path`. Expand `~` using `os.path.expanduser()`. Test directory readability using `with os.scandir(resolved) as it: pass`. If `PermissionError` or `OSError` occurs (e.g. macOS TCC restriction or `chmod 000`), raise an informative `PermissionError` detailing that access is denied / macOS TCC permissions are required.
   - In `scan()`: Provide an `onerror` handler in `os.walk(self._active_path, followlinks=False, onerror=...)`. If permission errors occur and no items could be read from root, set `self._state = ScanState.ERROR` and re-raise `PermissionError`.
2. **`src/analyzer/sanitizer.py` & `src/analyzer/engine.py`**:
   - In `sanitizer.py`: Strip wrapping quotes and expand `~` via `os.path.expanduser()` before resolving paths. In `sanitize_directory()`, verify readability with `os.scandir()`.
   - In `engine.py`: Ensure `validate_scan_request()` errors propagate appropriately so that callers are informed of invalid or inaccessible directories.
3. **`src/app/server.py`**:
   - In `api_scan_request()`: In the `except Exception as e:` block, set `state["scanner"]["state"] = "ERROR"`, `state["scanner"]["files"] = []`, `state["scanner"]["error"] = str(e)`, save state, and return HTTP 400 with `jsonify({"status": "error", "error": str(e), "folder": target_path, "files_found": 0, "files": [], "session_only": session_only}), 400`.
4. **`src/ui/js/views/student.js`**:
   - In `executeScan()`: Catch errors and inspect response status (`!response.ok || res.status === "error" || res.error`).
   - If an error occurs:
     - Display `❌ Scan Error: ${errorMsg}` with prominent error styling in `#scanner-status-banner`.
     - Clear `this.scannedFiles = []`.
     - Hide `#btn-revoke-scan`.
     - Render an informative error message in `#scanned-files-container`.
     - Trigger `RetroAudio.playGamingBuzzer()`.
5. **Automated Tests**:
   - Implement the test cases specified by `explorer_m1_3`:
     - In `tests/test_scanner.py`: add tests for non-existent path raising `FileNotFoundError`, restricted path raising `PermissionError`, and unreadable root setting `ScanState.ERROR`.
     - In `tests/test_ui_and_build.py`: add tests for fake path returning HTTP 400 with `status: "error"`, restricted path returning HTTP 400 with `status: "error"`, valid populated directory returning HTTP 200 with populated metadata, and static check for `student.js` error handling.
6. **Build & Test Verification**:
   - Run `make test` (or `python3 -m unittest discover -s tests -p "test_*.py" -v`).
   - Ensure all tests (existing 503 + new tests) pass with 100% success rate (exit code 0).
7. **Handoff**:
   - Write your implementation report to `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/worker_m1_1/handoff.md`.
   - Notify orchestrator via `send_message`.
