# Handoff Report: Backend File Scanning & TCC Error Handling Survey

**From**: `explorer_survey_1`  
**To**: `orchestrator` (parent id: `e21f5569-9a5c-4ba2-987c-97f42180e634`)  
**Task**: Survey investigation of silent folder scanning failures, macOS TCC permissions, `FileScanner`, `AnalysisEngine`, and UI error surfacing.  
**Working Directory**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_survey_1`  
**Survey Report**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_survey_1/survey_report.md`  

---

## 1. Observation

### Obs 1. Directory Permissions & macOS TCC Denial on `/Users/narayan/Desktop/NEWSLETTER`
- **Command**: `ls -ld /Users/narayan/Desktop /Users/narayan/Desktop/NEWSLETTER`
  - **Output**:
    ```text
    drwx------@ 130 narayan  staff  4160 Sep  8 14:14 /Users/narayan/Desktop
    drwxr-xr-x   16 narayan  staff   512 Sep  7 17:23 /Users/narayan/Desktop/NEWSLETTER
    ```
- **Command**: `ls -la /Users/narayan/Desktop/NEWSLETTER`
  - **Result**: Exited with code 1.
  - **Output**: `ls: /Users/narayan/Desktop/NEWSLETTER: Operation not permitted`
- **Command**: `xattr -l /Users/narayan/Desktop`
  - **Result**: Exited with code 1.
  - **Output**: `xattr: [Errno 1] Operation not permitted: '/Users/narayan/Desktop'`
- **Python Inspection**:
  ```python
  import os
  path = '/Users/narayan/Desktop/NEWSLETTER'
  os.listdir(path)  # Raises: PermissionError: [Errno 1] Operation not permitted: '/Users/narayan/Desktop/NEWSLETTER'
  os.access(path, os.R_OK)  # Returns: False
  ```

### Obs 2. `FileScanner.scan()` Silently Returns 0 Items on TCC Rejection
- **File**: `src/services/scanner.py:292`
  ```python
  for root, dirs, files in os.walk(self._active_path, followlinks=False):
  ```
- **Execution**: Calling `FileScanner().request_access('/Users/narayan/Desktop/NEWSLETTER')` followed by `scanner.scan()`:
  - Exited with 0 exceptions.
  - `len(items)` returned `0`.
  - Python's standard `os.walk` defaults to `onerror=None`, which catches and discards `OSError` (including `PermissionError: Operation not permitted`), terminating the iteration immediately with 0 files yielded.

### Obs 3. `FileScanner.request_access()` Omits Readability Check
- **File**: `src/services/scanner.py:226-234`
  ```python
  resolved = os.path.abspath(os.path.expanduser(folder_path))
  if not os.path.exists(resolved):
      raise FileNotFoundError(f"Selected folder does not exist: {folder_path}")
  if not os.path.isdir(resolved):
      raise NotADirectoryError(f"Selected path is not a directory: {folder_path}")

  self._active_path = resolved
  self._session_only = session_only
  self._state = ScanState.ACCESS_ACTIVE_SCOPED
  ```
  `os.path.exists()` and `os.path.isdir()` evaluate to `True` for `/Users/narayan/Desktop/NEWSLETTER` even though the current process has no permission to read the directory. `request_access()` never tests `os.access(resolved, os.R_OK)`.

### Obs 4. `AnalysisEngine.scan()` Swallows `ValidationError`
- **File**: `src/analyzer/engine.py:41-44`
  ```python
  # Security: Validate and sanitize the scan directory
  try:
      directory = validate_scan_request(str(directory))
  except ValidationError as e:
      return ScanResult(directory=directory, scan_duration=0.0)
  ```
- **Validation**: `validate_scan_request('/Users/narayan/Desktop/NEWSLETTER')` calls `sanitize_directory()`, which executes `if not os.access(path, os.R_OK): raise ValidationError("directory", ...)`. `AnalysisEngine.scan` catches this `ValidationError` and silently returns an empty `ScanResult` with 0 issues.

### Obs 5. `src/app/server.py` Intercepts Scan Exceptions and Returns HTTP 200 `"status": "completed"`
- **File**: `src/app/server.py:315-327`
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
  Regardless of whether `e` is `FileNotFoundError` or `PermissionError`, `server.py` catches it, sets internal state to `"ERROR"`, prints to console, and sends HTTP 200 with `"status": "completed"` and `"files_found": 0`. No error string is provided to the caller.

### Obs 6. Frontend `student.js` Assumes Success and Displays "0 files indexed"
- **File**: `src/ui/js/views/student.js:370-384`
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
  if (btnRevoke) btnRevoke.style.display = "inline-flex";

  if (window.RetroAudio) window.RetroAudio.playCoinDing();
  this.renderScannedFiles();
  ```
  The UI never evaluates `res.status === "error"`, `res.error`, or HTTP status. It unconditionally presents the green checkmark and "0 files indexed", playing the success audio chime. In `renderScannedFiles()`, an empty file list displays: `"No active files in memory. System is completely blind."`

### Obs 7. Existing Test Suite Baseline
- **Command**: `make test`
  - **Result**: Exited with code 0 (`Ran 503 tests in 11.242s, OK, [✓] All tests passed!`).

---

## 2. Logic Chain

1. From **Obs 1**, `/Users/narayan/Desktop` and its child directory `/Users/narayan/Desktop/NEWSLETTER` are protected by macOS TCC. Standard directory listing commands and Python `os.listdir` fail with `PermissionError: [Errno 1] Operation not permitted`.
2. From **Obs 3**, when a user enters `/Users/narayan/Desktop/NEWSLETTER`, `FileScanner.request_access()` only calls `os.path.exists()` and `os.path.isdir()`, which succeed via `stat` on the parent folder. `request_access()` does not test readability, so it erroneously sets `ScanState.ACCESS_ACTIVE_SCOPED`.
3. From **Obs 2**, when `FileScanner.scan()` runs, it calls `os.walk()`. Because `onerror` is `None`, Python's internal `os.scandir()` catches `PermissionError` and silently returns an empty generator. `scan()` terminates with 0 items without raising any exception and marks the state `ScanState.COMPLETED`.
4. From **Obs 4**, when `FileScanner` triggers `AnalysisEngine.scan()`, `sanitize_directory()` checks `os.access(path, os.R_OK)`, which is `False` due to TCC. `validate_scan_request` raises `ValidationError`, but `AnalysisEngine.scan()` swallows it and returns an empty `ScanResult`.
5. From **Obs 5**, even if an exception were raised (such as passing a fake path `/does/not/exist` which triggers `FileNotFoundError`), `server.py` catches all exceptions, sets state to `"ERROR"`, but still returns HTTP 200 with `"status": "completed"` and `"files_found": 0`.
6. From **Obs 6**, the frontend UI receives `"status": "completed"` and `files_found: 0`. It displays `✅ Access Active: Scoped to ... (0 files indexed)` and plays a victory audio chime, hiding the failure completely.
7. Therefore, to resolve R1 and R2, fixes are required across `FileScanner` (readability check + `onerror` handler in `os.walk`), `AnalysisEngine` (validation reporting), `server.py` (return `status: "error"` and error string on exceptions), and `student.js` (inspect `res.status`/`res.error` and display a prominent red error message in banner and list).

---

## 3. Caveats

1. **Operating System Boundaries**: macOS TCC restrictions are enforced by the macOS kernel (`tccd`). Python userland code cannot bypass TCC without the user granting Full Disk Access or Files and Folders permission in macOS System Settings. The app's responsibility is to detect TCC rejections immediately, surface clear diagnostic instructions to the user, and provide a functional fallback (e.g. suggesting or falling back to accessible locations like `~/Downloads` or the project directory).
2. **Alternative Interpretations Considered**: We considered whether the frontend should prevent submitting desktop paths altogether. We rejected this because users who have granted Full Disk Access to their shell/Terminal should be allowed to scan Desktop folders. Proper error detection and surfacing handle both cases correctly.

---

## 4. Conclusion

The root cause of "0 files indexed" on folders like `/Users/narayan/Desktop/NEWSLETTER` is a multi-tier silent failure:
1. macOS TCC denies read access (`[Errno 1] Operation not permitted`).
2. `FileScanner.scan` swallows the error via `os.walk(onerror=None)`.
3. `AnalysisEngine.scan` swallows `ValidationError`.
4. `src/app/server.py` catches exceptions and converts them to HTTP 200 `"status": "completed"`.
5. `student.js` unconditionally renders success with `"0 files indexed"`.

A contained set of targeted edits across `scanner.py`, `engine.py`, `sanitizer.py`, `server.py`, and `student.js` will resolve the root cause, surface clear error messages for restricted/missing directories, and ensure zero regressions in the 503-test suite.

---

## 5. Verification Method

### 1. Automated Test Suite Regression Check
Run from workspace root:
```bash
make test
```
Must exit with code 0 (503 tests passing).

### 2. FileScanner Direct Verification
Run in Python:
```python
import os, tempfile
from src.services.scanner import FileScanner

# Test 1: Fake Path raises FileNotFoundError
scanner = FileScanner()
try:
    scanner.request_access("/fake/nonexistent/path")
    assert False, "Should have raised FileNotFoundError"
except FileNotFoundError:
    pass

# Test 2: Restricted Path raises PermissionError
with tempfile.TemporaryDirectory() as tmpdir:
    test_dir = os.path.join(tmpdir, "restricted")
    os.makedirs(test_dir)
    os.chmod(test_dir, 0o000)
    try:
        scanner.request_access(test_dir)
        scanner.scan()
        assert False, "Should have raised PermissionError"
    except PermissionError:
        pass
    finally:
        os.chmod(test_dir, 0o755)
```

### 3. API & UI Error Surfacing Verification
Test `POST /api/scan/request` with:
- `folder_path: "/fake/path"` -> Verify response returns `status: "error"`, `error` contains `"does not exist"`, and UI banner displays `❌ Scan Error: Selected folder does not exist`.
- `folder_path: "/Users/narayan/Desktop/NEWSLETTER"` -> Verify response returns `status: "error"`, `error` contains `"Permission denied"`, and UI banner displays `❌ Scan Error: Permission denied`.
- `folder_path: "tests"` (valid directory) -> Verify response returns `status: "completed"`, `files_found > 0`, and UI banner displays `✅ Access Active ... (X files indexed)`.
