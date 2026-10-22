# Comprehensive Survey Report: File Scanning Silent Failures & macOS TCC Root Cause Analysis

**Agent**: explorer_survey_1 (teamwork_preview_explorer)  
**Date**: 2026-09-08  
**Project**: Data-to-Dirt (`/Users/narayan/.gemini/antigravity/scratch/data-to-dirt`)  
**Scope**: Backend `FileScanner`, `AnalysisEngine`, directory traversal, macOS TCC/permissions handling, API error propagation, and frontend UI error surfacing.

---

## 1. Executive Summary

When a user attempts to scan a directory in Data-to-Dirt—including valid directories such as `/Users/narayan/Desktop/NEWSLETTER` or non-existent/permission-restricted paths—the application frequently reports:
> `✅ Access Active: Scoped to /path/to/folder (0 files indexed)`  
> `No active files in memory. System is completely blind.`

This behavior is caused by a **chain of silent exception suppression and improper state handling across six distinct layers** of the stack:
1. `FileScanner.scan` relies on `os.walk()` without an `onerror` callback, causing Python to silently suppress `PermissionError` (including macOS TCC `Operation not permitted`).
2. `FileScanner.request_access` only validates `os.path.exists()` and `os.path.isdir()`, without testing read accessibility (`os.R_OK` or directory enumeration).
3. `AnalysisEngine.scan` catches `ValidationError` (raised when `os.access(path, os.R_OK)` is false) and silently returns an empty `ScanResult(issues=[])`.
4. `src/app/server.py` intercepts any scanning exceptions in `POST /api/scan/request`, prints to stdout, but still returns HTTP 200 with `"status": "completed"` and `"files_found": 0`.
5. Frontend `src/ui/js/views/student.js` never inspects error fields or HTTP status codes, rendering a green success checkmark with `"0 files indexed"` even when the backend failed completely.
6. Path sanitization and resolution in `sanitizer.py` fail to expand tilde (`~`) paths, and neither backend nor frontend strips wrapping quotation marks from pasted/dragged paths.

When directories on macOS like `~/Desktop` are protected by macOS TCC (Transparency, Consent, and Control), access fails with `[Errno 1] Operation not permitted`. Because every layer suppresses this error, the user is never informed that macOS TCC blocked the scan or that permissions are required.

---

## 2. Component Architecture & End-to-End Traversal Flow

```
+-------------------------------------------------------------------------------+
| 1. Frontend UI (student.js)                                                  |
|    - User inputs path (e.g. /Users/narayan/Desktop/NEWSLETTER or ~/Desktop)   |
|    - Calls executeScan(folderPath, sessionOnly)                               |
|    - Dispatches POST /api/scan/request                                        |
+---------------------------------------+---------------------------------------+
                                        | JSON: {"folder_path": "...", ...}
                                        v
+-------------------------------------------------------------------------------+
| 2. Local HTTP Server (server.py: api_scan_request)                           |
|    - Resolves target_path = folder_path or str(Path.home() / "Desktop")       |
|    - Calls global_scanner.request_access(target_path, session_only)           |
|    - Calls global_scanner.scan()                                              |
|    - Swallows exceptions in try/except; always returns "status": "completed"  |
+---------------------------------------+---------------------------------------+
                                        | Calls
                                        v
+-------------------------------------------------------------------------------+
| 3. Privacy-First Scanner Engine (scanner.py: FileScanner)                    |
|    - request_access(): checks os.path.exists() and isdir(), sets active_path  |
|    - scan(): invokes os.walk(self._active_path, followlinks=False)            |
|      * BUG: onerror=None causes os.walk to silently drop PermissionError      |
|    - _apply_dark_data_heuristics():                                           |
|      * Applies base rules (stale relic, heavy bloat, duplicate sizes)         |
|      * Invokes self.analysis_engine.scan(Path(self._active_path))             |
+---------------------------------------+---------------------------------------+
                                        | Calls
                                        v
+-------------------------------------------------------------------------------+
| 4. Security & Sanitization Layer (sanitizer.py & sandbox.py)                  |
|    - validate_scan_request(path) -> sanitize_directory(path)                  |
|    - Checks sanitize_path(): BUG: Path(path).resolve() fails on ~            |
|    - Checks os.access(path, os.R_OK) -> raises ValidationError                |
+---------------------------------------+---------------------------------------+
                                        | Calls
                                        v
+-------------------------------------------------------------------------------+
| 5. Advanced Analysis Engine (engine.py: AnalysisEngine)                      |
|    - scan(directory):                                                         |
|      * BUG: try: validate_scan_request except ValidationError: return empty!  |
|      * walk_dir(): catch (PermissionError, FileNotFoundError): pass           |
+-------------------------------------------------------------------------------+
```

---

## 3. Root Cause Investigation: The 6 Silent Failure Mechanisms

### Root Cause 1: `FileScanner.scan` Silently Swallows `PermissionError` in `os.walk`

- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/services/scanner.py`
- **Lines**: 291–306
- **Code**:
  ```python
  try:
      for root, dirs, files in os.walk(self._active_path, followlinks=False):
          if self._cancel_requested:
              break
  ```
- **Analysis**:
  In Python's `os.walk(top, topdown=True, onerror=None, followlinks=False)`:
  ```python
  try:
      scandir_it = os.scandir(top)
  except OSError as error:
      if onerror is not None:
          onerror(error)
      return
  ```
  When `onerror` is `None` (the default), any `OSError` raised during `os.scandir(top)` is **silently discarded**, and `os.walk` immediately returns an empty generator.
  On macOS, when accessing a TCC-restricted path (such as `/Users/narayan/Desktop/NEWSLETTER` without Full Disk Access), the system call fails with `PermissionError: [Errno 1] Operation not permitted`.
  Because `onerror=None`, `os.walk` yields zero directories and zero files. The loop terminates immediately without setting `self._state = ScanState.ERROR`.
  The method then executes:
  ```python
  self._scanned_files = scanned_items  # []
  self._file_map = {item.file_id: item for item in scanned_items}
  self._state = ScanState.COMPLETED
  return list(self._scanned_files)
  ```
  `FileScanner.scan()` successfully returns an empty list `[]` instead of raising an error.

---

### Root Cause 2: `FileScanner.request_access` Does Not Verify Directory Readability

- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/services/scanner.py`
- **Lines**: 225–235
- **Code**:
  ```python
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
- **Analysis**:
  `os.path.exists()` and `os.path.isdir()` check directory inode metadata via `stat()`. On macOS, a process can frequently `stat()` a directory entry within a parent path even when the process does not have permission to list or read the directory's contents.
  `request_access()` never verifies `os.access(resolved, os.R_OK)` or attempts to verify directory readability (e.g. via `os.scandir(resolved)`). As a result, it blindly transitions from `BLIND` to `ACCESS_ACTIVE_SCOPED` even for folders with zero read permissions (`chmod 000`) or folders blocked by macOS TCC.

---

### Root Cause 3: `AnalysisEngine.scan` Silently Absorbs `ValidationError` and `PermissionError`

- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/analyzer/engine.py`
- **Lines**: 40–44 and 71–73
- **Code**:
  ```python
  # Security: Validate and sanitize the scan directory
  try:
      directory = validate_scan_request(str(directory))
  except ValidationError as e:
      return ScanResult(directory=directory, scan_duration=0.0)
  ```
  And inside `walk_dir`:
  ```python
  except (PermissionError, FileNotFoundError):
      pass
  ```
- **Analysis**:
  When `AnalysisEngine.scan` runs on `/Users/narayan/Desktop/NEWSLETTER`, `validate_scan_request` runs `sanitize_directory`:
  ```python
  if not os.access(path, os.R_OK):
      raise ValidationError("directory", f"Directory is not readable: {path}")
  ```
  Since `os.access('/Users/narayan/Desktop/NEWSLETTER', os.R_OK)` returns `False`, `ValidationError` is raised.
  Instead of propagating the validation error, `AnalysisEngine.scan` intercepts it and returns:
  `ScanResult(directory=directory, scan_duration=0.0, total_files=0, issues=[])`.
  In `src/services/scanner.py`, `_apply_dark_data_heuristics` receives this empty `ScanResult` and quietly finishes.

---

### Root Cause 4: `src/app/server.py` Catches Exceptions and Returns HTTP 200 Success

- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/app/server.py`
- **Lines**: 302–327
- **Code**:
  ```python
  try:
      global_scanner.request_access(target_path, session_only)
      scanned_items = global_scanner.scan()
      
      files = [item.to_dict() for item in scanned_items]
      # Map dark data reasoning
      for f in files:
          f["size_formatted"] = format_bytes(f["size_bytes"])
          f["category"] = "dark_data" if f["is_dark_data_candidate"] else "normal"
          f["dark_data_tag"] = f["dark_data_reason"] or "Normal"
          
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
- **Analysis**:
  If `request_access()` or `scan()` raises an exception (for example `FileNotFoundError` for a non-existent directory, or `PermissionError` for an unreadable directory):
  1. `state["scanner"]["state"]` is set to `"ERROR"`.
  2. The error is logged to standard output (`print(f"Error scanning: {e}")`).
  3. The route proceeds directly to `return jsonify(...)` and returns HTTP 200 with `"status": "completed"`!
  4. The returned payload contains `"files_found": 0`, `"files": []`, and contains **no error message** field whatsoever.

---

### Root Cause 5: Frontend UI (`student.js`) Assumes Every Request Succeeds

- **File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/ui/js/views/student.js`
- **Lines**: 370–386
- **Code**:
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
- **Analysis**:
  The frontend UI assumes any response with JSON is a successful scan:
  - It does not check `res.status === "error"` or `res.error`.
  - It does not check `response.ok` or HTTP status code.
  - It unconditionally renders the green success badge: `✅ Access Active: Scoped to ... (0 files indexed)`.
  - It plays the success coin sound (`RetroAudio.playCoinDing()`).
  - In `renderScannedFiles()`, because `this.scannedFiles.length === 0`, it renders:
    `"No active files in memory. System is completely blind."`
  The user is given no indication that a permission failure, TCC denial, or invalid path occurred.

---

### Root Cause 6: Path Normalization & Default Path Flaws

1. **Missing Tilde (`~`) Expansion in `sanitizer.py`**:
   - In `src/security/sanitizer.py:106`:
     ```python
     resolved = Path(path_str).resolve()
     ```
     `Path.resolve()` does NOT expand `~`. If a user inputs `~/Desktop/NEWSLETTER`, `Path("~/Desktop/NEWSLETTER").resolve()` evaluates to `/Users/narayan/.../scratch/data-to-dirt/~/Desktop/NEWSLETTER`, which triggers `Directory does not exist`.
2. **Quotation Marks in Pasted Paths**:
   - Dragging a folder into a text field in macOS or copying a path from Terminal frequently wraps paths in single or double quotes (`"/Users/..."`). Neither the frontend nor the backend strips enclosing quotes, causing `os.path.exists()` to fail.
3. **Flawed Fallback Default**:
   - In `src/app/server.py:299`:
     ```python
     target_path = folder_path or str(Path.home() / "Desktop")
     ```
     Defaulting an empty path to `~/Desktop` ensures failure on modern macOS systems where Terminal/Python does not possess explicit Desktop TCC privileges.

---

## 4. macOS TCC Analysis & Verification

### What is macOS TCC?
macOS Transparency, Consent, and Control (TCC) protects sensitive user directories (`~/Desktop`, `~/Documents`, `~/Downloads`, Network Volumes, etc.) under sandbox policies managed by `tccd`. Even if standard POSIX file permissions (`rwxr-xr-x`) permit access, an application or command-line process without the required TCC entitlement or Full Disk Access privilege receives an immediate kernel rejection:
`[Errno 1] Operation not permitted (EPERM)`.

### Direct Verification on the Target System:
1. **Target Directory Inspection**:
   - `/Users/narayan/Desktop`:
     `drwx------@ 130 narayan staff 4160 Sep 8 14:14 /Users/narayan/Desktop`
     The `@` symbol denotes extended security/quarantine attributes.
   - `/Users/narayan/Desktop/NEWSLETTER`:
     `drwxr-xr-x 16 narayan staff 512 Sep 7 17:23 /Users/narayan/Desktop/NEWSLETTER`
     Directory contains 16 items.
2. **Access Attempts**:
   - Running `ls /Users/narayan/Desktop/NEWSLETTER`:
     `ls: /Users/narayan/Desktop/NEWSLETTER: Operation not permitted`
   - In Python:
     `os.listdir('/Users/narayan/Desktop/NEWSLETTER')` raises:
     `PermissionError: [Errno 1] Operation not permitted: '/Users/narayan/Desktop/NEWSLETTER'`
   - `os.access('/Users/narayan/Desktop/NEWSLETTER', os.R_OK)` returns `False`.
3. **Comparison with Unrestricted User Directory**:
   - `/Users/narayan/Downloads`:
     Listing directory succeeds without restriction (hundreds of user files enumerated).
   - Local project workspace (`/Users/narayan/.../scratch/data-to-dirt`):
     Listing and scanning succeed without restriction.

---

## 5. Required Implementation Plan & Fix Strategy

To satisfy Requirements R1 and R2 and all Acceptance Criteria, the following coordinated fixes must be implemented:

### Component 1: `src/services/scanner.py` (FileScanner)
1. **Path Normalization**:
   Strip enclosing quotes and expand user tildes:
   ```python
   clean_path = folder_path.strip().strip("'\"")
   resolved = os.path.abspath(os.path.expanduser(clean_path))
   ```
2. **Readability Validation in `request_access()`**:
   Verify readability prior to transitioning state:
   ```python
   if not os.access(resolved, os.R_OK):
       raise PermissionError(f"Permission denied accessing '{resolved}'. Check macOS Privacy & Security permissions.")
   ```
3. **`os.walk` Error Handling in `scan()`**:
   Provide an `onerror` callback to `os.walk()` to catch and surface permission errors on root and child directories:
   ```python
   walk_errors: List[Exception] = []
   def handle_walk_error(err: OSError):
       walk_errors.append(err)
   for root, dirs, files in os.walk(self._active_path, onerror=handle_walk_error, followlinks=False):
       ...
   if walk_errors and not scanned_items:
       first_err = walk_errors[0]
       raise PermissionError(f"Cannot read '{self._active_path}': {first_err}")
   ```

### Component 2: `src/analyzer/engine.py` (AnalysisEngine) & `sanitizer.py`
1. In `src/security/sanitizer.py`:
   Update `sanitize_path` to call `os.path.expanduser(path_str.strip().strip("'\""))` before resolving.
2. In `src/analyzer/engine.py`:
   If `validate_scan_request` raises `ValidationError`, log the specific error and return or raise appropriately instead of returning empty results without telemetry.

### Component 3: `src/app/server.py` (REST API)
1. In `@app.route("/api/scan/request")`:
   When an exception occurs during `request_access` or `scan`:
   - Store error state: `state["scanner"]["state"] = "ERROR"`
   - Return an explicit error payload with `status: "error"`, error description, and HTTP 400 (or 200 with status "error" for UI compatibility):
   ```python
   except Exception as e:
       state["scanner"]["state"] = "ERROR"
       save_state(state)
       return jsonify({
           "status": "error",
           "error": f"Scan failed: {str(e)}",
           "folder": target_path,
           "files_found": 0,
           "files": [],
           "session_only": session_only
       }), 400
   ```
2. **Default Path Fallback**:
   If `folder_path` is empty or defaults to `~/Desktop` which is blocked by TCC:
   Provide an intelligent fallback to `~/Downloads` or the project directory, or inform the user with a specific guidance prompt for macOS TCC.

### Component 4: `src/ui/js/views/student.js` (Frontend UI)
1. Inspect `res.status` and `res.error` in `executeScan`:
   ```javascript
   if (res.status === "error" || res.error) {
       this.scannedFiles = [];
       if (banner) {
           banner.innerHTML = `<span>❌ <strong>Scan Error</strong>: ${res.error || "Permission denied or folder inaccessible"}</span>`;
       }
       this.renderScannedFiles(res.error);
       return;
   }
   ```
2. In `renderScannedFiles(errorMessage)`:
   If an error occurred, render an error card in the container:
   ```javascript
   if (errorMessage) {
       container.innerHTML = `
           <div class="retro-error-card" style="padding: 16px; color: #d9534f; text-align: center;">
               <strong>⚠️ Scan Error</strong><br>
               <span style="font-size: 11px;">${errorMessage}</span>
           </div>
       `;
       return;
   }
   ```
3. Do not play positive audio feedback (`RetroAudio.playCoinDing()`) on error; optionally play buzzer/blip.

---

## 6. Verification Matrix

| Test Scenario | Input Path | Expected Backend Response | Expected UI Output |
|---|---|---|---|
| **Valid Project Directory** | `tests` or `./tests` | HTTP 200, `status: "completed"`, `files_found > 0` | Banner: `✅ Access Active: Scoped to ... (X files indexed)`, file list displayed |
| **Valid User Directory** | `/Users/narayan/Downloads` | HTTP 200, `status: "completed"`, `files_found > 0` | Banner: `✅ Access Active: Scoped to ... (X files indexed)`, file list displayed |
| **Fake / Missing Directory** | `/path/to/nonexistent/folder` | HTTP 400, `status: "error"`, `error: "Selected folder does not exist: ..."` | Banner: `❌ Scan Error: Selected folder does not exist...` (No "0 files indexed") |
| **Restricted Directory (TCC)** | `/Users/narayan/Desktop/NEWSLETTER` | HTTP 400, `status: "error"`, `error: "Permission denied accessing ..."` | Banner: `❌ Scan Error: Permission denied...` (No "0 files indexed") |
| **Regression Suite** | `make test` (503 unit/integration tests) | Exit Code 0 | All 503 tests pass with 0 failures |

---

## 7. Conclusion

The scanning failure on `/Users/narayan/Desktop/NEWSLETTER` and similar folders is not a single bug, but a multi-layer failure to handle and propagate I/O permissions:
- macOS TCC blocks directory enumeration at the system call level.
- `FileScanner.scan` silently suppresses the error via default `os.walk` behavior.
- `AnalysisEngine` silently catches `ValidationError`.
- `server.py` catches all exceptions and converts them into HTTP 200 `"status": "completed"`.
- `student.js` unconditionally displays success and `"0 files indexed"`.

Implementing explicit permission checks, `os.walk` error propagation, API error responses, path normalization, and UI error handling will fully resolve the issue and satisfy all requirements.
