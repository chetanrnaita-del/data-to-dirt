# Handoff Report: Milestone 1 - Scanner, Engine, and Path Sanitization Strategy

**Agent**: `explorer_m1_1` (Teamwork Explorer)  
**To**: `orchestrator` (ID: `e21f5569-9a5c-4ba2-987c-97f42180e634`), `worker_m1_1`  
**Date**: 2026-09-08  
**Working Directory**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_m1_1`  
**Recommendation Document**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_m1_1/recommendation.md`  
**Handoff Type**: Hard Handoff (Investigation & Fix Strategy Complete)

---

## 1. Observation

### 1.1 `FileScanner.request_access()` Missing Readability Check and Quote Stripping
- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/services/scanner.py`, lines 222–235:
  ```python
  if not folder_path:
      raise ValueError("folder_path cannot be empty.")

  resolved = os.path.abspath(os.path.expanduser(folder_path))
  if not os.path.exists(resolved):
      raise FileNotFoundError(f"Selected folder does not exist: {folder_path}")
  if not os.path.isdir(resolved):
      raise NotADirectoryError(f"Selected path is not a directory: {folder_path}")

  self._active_path = resolved
  self._session_only = session_only
  self._state = ScanState.ACCESS_ACTIVE_SCOPED
  self._cancel_requested = False
  return True
  ```
- **Finding**:
  1. `folder_path` is not stripped of wrapping quotes (`"path"` or `'path'`).
  2. `os.path.exists()` and `os.path.isdir()` return `True` on macOS directories protected by TCC (`~/Desktop/NEWSLETTER`), but reading the directory fails.
  3. `request_access()` never tests `os.scandir(resolved)`. As a result, restricted or unreadable paths are erroneously marked `ACCESS_ACTIVE_SCOPED`.

### 1.2 `FileScanner.scan()` Silently Swallowing Traversal Errors in `os.walk`
- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/services/scanner.py`, lines 291–295:
  ```python
  try:
      for root, dirs, files in os.walk(self._active_path, followlinks=False):
          if self._cancel_requested:
              break
  ```
- **Finding**:
  In Python's `os.walk()`, the default parameter is `onerror=None`. When `os.scandir()` inside `os.walk` hits `PermissionError` (such as macOS TCC `Operation not permitted`), `os.walk` discards the exception and yields nothing. The loop terminates immediately, `self._scanned_files = []`, line 389 transitions state to `ScanState.COMPLETED`, and `scan()` returns `[]` with zero errors raised.

### 1.3 `AnalysisEngine.scan()` Swallows `ValidationError`
- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/analyzer/engine.py`, lines 40–44:
  ```python
  # Security: Validate and sanitize the scan directory
  try:
      directory = validate_scan_request(str(directory))
  except ValidationError as e:
      return ScanResult(directory=directory, scan_duration=0.0)
  ```
- **Finding**:
  When `validate_scan_request` detects an unreadable or invalid path, `AnalysisEngine.scan()` catches `ValidationError` and silently returns an empty `ScanResult` with 0 issues and 0 files instead of propagating the error.

### 1.4 `sanitize_path()` and `sanitize_directory()` Path Handling Deficiencies
- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/security/sanitizer.py`, lines 76–137:
  ```python
  def sanitize_path(path_str: str) -> Path:
      ...
      try:
          resolved = Path(path_str).resolve()
      except (OSError, RuntimeError) as e:
          raise ValidationError("path", f"Failed to resolve path: {e}")
      return resolved

  def sanitize_directory(path_str: str) -> Path:
      path = sanitize_path(path_str)
      if not path.exists():
          raise ValidationError("directory", f"Directory does not exist: {path}")
      if not path.is_dir():
          raise ValidationError("directory", f"Path is not a directory: {path}")
      if not os.access(path, os.R_OK):
          raise ValidationError("directory", f"Directory is not readable: {path}")
      return path
  ```
- **Finding**:
  1. `Path('~/Desktop').resolve()` does not expand `~` in Python; it resolves relative to cwd (`<cwd>/~/Desktop`), causing `path.exists()` to fail.
  2. Surrounding quotes (`"/path"`) are not stripped, corrupting the resolved `Path`.
  3. `os.access(path, os.R_OK)` is insufficient for macOS TCC; active `os.scandir(path)` is required to catch `Operation not permitted`.

### 1.5 `server.py` Endpoint Swallowing Exceptions
- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/app/server.py`, lines 315–327:
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
- **Finding**:
  Any error caught during `request_access()` or `scan()` sets internal state to `"ERROR"`, but the HTTP response unconditionally returns HTTP 200 with `"status": "completed"` and `"files_found": 0`, hiding the error completely.

### 1.6 `student.js` Assumes Success and Displays "0 files indexed"
- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/ui/js/views/student.js`, lines 370–384:
  ```javascript
  const res = await fetch("/api/scan/request", { ... }).then((r) => r.json());
  this.scannedFiles = res.files || [];
  if (banner) {
    banner.innerHTML = `<span>✅ <strong>Access Active</strong>: Scoped to <em>${res.folder}</em> (${res.files_found} files indexed)</span>`;
  }
  ```
- **Finding**:
  The UI unconditionally formats the green banner with "0 files indexed" without verifying `response.ok` or `res.status === "error"`.

---

## 2. Logic Chain

1. **Obs 1.1**: `FileScanner.request_access()` does not test directory readability or strip quotes. A restricted path (like a macOS TCC-blocked `~/Desktop` or `0o000` directory) passes validation and transitions scanner state to `ACCESS_ACTIVE_SCOPED`.
2. **Obs 1.2**: When `FileScanner.scan()` runs, `os.walk` without `onerror` encounters `PermissionError` when opening the directory stream. Because `onerror=None`, Python discards the exception and terminates iteration. `FileScanner.scan()` records 0 files, marks state `COMPLETED`, and returns `[]`.
3. **Obs 1.3 & 1.4**: `AnalysisEngine.scan()` swallows `ValidationError` from `sanitizer.py`, and `sanitizer.py` fails to expand tildes or strip quotes.
4. **Obs 1.5**: Even if an exception is raised (e.g. `FileNotFoundError` on a missing path), `server.py` catches all exceptions and sends HTTP 200 with `"status": "completed"` and `"files_found": 0`.
5. **Obs 1.6**: The frontend UI receives `"status": "completed"`, assumes complete success, and renders `✅ Access Active: Scoped to ... (0 files indexed)` with a coin chime.
6. **Conclusion**: To resolve R1 and R2, fixes must be coordinated across `FileScanner`, `AnalysisEngine`, `sanitizer.py`, `server.py`, and `student.js`.

---

## 3. Caveats

1. **Operating System Boundaries**: macOS TCC constraints (`[Errno 1] Operation not permitted`) are enforced by the macOS kernel security daemon (`tccd`). Userland applications cannot bypass TCC without the user granting Full Disk Access or Files and Folders permissions in macOS System Settings. The application must detect TCC errors immediately, surface diagnostic instructions to the user, and report the failure clearly.
2. **Mocking in Automated Tests**: In headless or non-interactive environments, simulating macOS TCC EPERM is reliably achieved using `unittest.mock.patch("os.scandir", side_effect=PermissionError(1, "Operation not permitted"))` or temporary directories with `os.chmod(path, 0o000)`.

---

## 4. Conclusion

The exact fix strategy has been formulated and documented in `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_m1_1/recommendation.md`.

Summary of required Worker changes:
1. **`src/services/scanner.py`**:
   - In `request_access()`: Strip quotes/whitespace, expand `~`, and test readability with `os.scandir(resolved)`. Raise `PermissionError` with diagnostic message on failure.
   - In `scan()`: Pass `onerror=on_walk_error` to `os.walk()`. Re-raise permission errors, set `self._state = ScanState.ERROR`.
2. **`src/analyzer/engine.py`**:
   - In `scan()`: Propagate `ValidationError` from `validate_scan_request()`. In `walk_dir()`, raise permission errors on the root directory (`current_depth == 0`).
3. **`src/security/sanitizer.py`**:
   - In `sanitize_path()`: Strip quotes and call `os.path.expanduser(path_str)` before `Path.resolve()`.
   - In `sanitize_directory()`: Check readability with `os.access()` and `os.scandir()`.
4. **`src/app/server.py`**:
   - In `api_scan_request()`: On exception, return HTTP 400 with `status: "error"`, `error: str(e)`, `files_found: 0`.
5. **`src/ui/js/views/student.js`**:
   - In `requestFolderAccess()`: Check `!response.ok || res.status === "error"`. Display red banner `❌ Scan Error: ${errorMsg}`, play buzzer, and hide revoke button.
6. **Tests**:
   - Add unit tests in `tests/test_scanner.py` and API error tests in `tests/test_ui_and_build.py`.
   - Verify `make test` passes without regression.

---

## 5. Verification Method

### 5.1 Project Test Command
```bash
make test
# Equivalent to: python3 -m unittest discover -s tests -p "test_*.py" -v
```
**Passing criteria**: All existing 503 tests must continue to pass, plus newly added test cases.

### 5.2 Specific Inspection Points
1. **Unreadable Directory Handling**:
   - Calling `FileScanner().request_access()` on a `chmod 000` directory must raise `PermissionError`.
   - State must remain `BLIND` (not `ACCESS_ACTIVE_SCOPED`).
2. **Tilde and Quoted Path Handling**:
   - Calling `FileScanner().request_access('"' + path + '"')` or `"~"` must succeed without error.
3. **API Error Contract**:
   - `POST /api/scan/request` with non-existent path -> HTTP 400, `status: "error"`, `error` contains `"does not exist"`.
   - `POST /api/scan/request` with permission-denied path -> HTTP 400, `status: "error"`, `error` contains `"Permission denied"`.
4. **UI Behavior**:
   - Response status `"error"` displays red banner and does not display "0 files indexed".

### 5.3 Invalidation Conditions
- If scanning an invalid or permission-denied directory still returns HTTP 200 or displays `0 files indexed`, the fix is invalid.
- If existing tests in `make test` fail or regress, the fix is invalid.
