# Comprehensive Technical Survey Report: Frontend-Backend Communication, Scan Result Formats & Error Surfacing

**Author**: `explorer_survey_2`  
**Date**: 2026-09-08  
**Scope**: Frontend-backend communication, API endpoints, file scanner lifecycle, error handling, macOS TCC permissions, and UI state presentation.

---

## 1. Executive Summary

When a user in Data-to-Dirt attempts to scan a folder that either:
1. Suffers from restricted permissions (such as macOS Transparency, Consent, and Control (TCC) constraints on `~/Desktop` or `chmod 000` directories), or
2. Does not exist (a fake or missing path),

the application silently fails and displays:
```
✅ Access Active: Scoped to <path> (0 files indexed)
```
accompanied by a successful chiptune "coin ding" audio cue. The user is misled into believing the folder was scanned successfully and genuinely contains zero dark data files.

This survey identifies **five distinct failure layers** across the stack that produce this bug:
- **Layer 1 (Frontend)**: `student.js` (`executeScan`) blindly consumes the JSON response without inspecting HTTP status (`response.ok`), `res.status`, or error payloads.
- **Layer 2 (REST API Server)**: `server.py` (`api_scan_request`) wraps scanning in a `try...except Exception as e:`, catches all errors, sets an internal state to `"ERROR"`, but still returns HTTP `200 OK` with hardcoded `"status": "completed"` and `"files_found": 0`.
- **Layer 3 (Scanner Service Traversal)**: `scanner.py` (`scan`) invokes Python's standard `os.walk(self._active_path, followlinks=False)` with default `onerror=None`. When the scoped root directory cannot be opened due to `PermissionError` (including macOS TCC `Operation not permitted`), `os.walk` silently catches the `OSError` internally and yields 0 items without raising an exception.
- **Layer 4 (Scanner Service Access Validation)**: `scanner.py` (`request_access`) checks `os.path.exists()` and `os.path.isdir()`, but never verifies directory readability (`os.access(R_OK)` or `os.scandir()`).
- **Layer 5 (Host OS TCC Constraints)**: On macOS Darwin arm64, protected directories such as `/Users/<user>/Desktop`, `~/Documents`, and `~/Downloads` return `Operation not permitted` (`errno 1`, `EPERM`) upon directory traversal (`opendir`/`scandir`) unless granted Full Disk Access or Files and Folders privileges in macOS System Settings.

---

## 2. End-to-End Scanning Flow & Communication Map

```
+-----------------------------------------------------------------------------------------------+
| FRONTEND: src/ui/js/views/student.js                                                          |
|                                                                                               |
| 1. User clicks "📂 Select Folder" (#btn-scan-folder)                                          |
| 2. Modal (#modal-permission) opens; user inputs path (e.g. ~/Desktop/NEWSLETTER)              |
| 3. User clicks "Grant Access" (#btn-modal-grant)                                              |
| 4. executeScan(folderPath, sessionOnly) triggered:                                            |
|    - Updates #scanner-status-banner: "⏳ Scanning scoped folder: ..."                         |
|    - Dispatches HTTP POST to /api/scan/request                                                |
+-----------------------------------------------------------------------------------------------+
                                            |
                                            | POST /api/scan/request
                                            | Body: {"folder_path": "...", "session_only": true}
                                            v
+-----------------------------------------------------------------------------------------------+
| BACKEND SERVER: src/app/server.py                                                             |
|                                                                                               |
| 5. Endpoint api_scan_request() receives payload:                                              |
|    - Resolves target_path = folder_path or str(Path.home() / "Desktop")                       |
|    - Calls global_scanner.request_access(target_path, session_only)                           |
|    - Calls global_scanner.scan()                                                              |
|    - Saves state to data/app_state.json                                                       |
|    - Returns JSON response                                                                    |
+-----------------------------------------------------------------------------------------------+
                                            |
                                            | Method calls
                                            v
+-----------------------------------------------------------------------------------------------+
| SCANNER SERVICE: src/services/scanner.py & src/analyzer/engine.py                             |
|                                                                                               |
| 6. FileScanner.request_access(folder_path, session_only):                                     |
|    - Expands tilde and resolves abspath: os.path.abspath(os.path.expanduser(folder_path))     |
|    - Validates os.path.exists() and os.path.isdir()                                           |
| 7. FileScanner.scan():                                                                        |
|    - Traverses via os.walk(self._active_path, followlinks=False)                              |
|    - Extracts metadata via os.stat() (size, mtime, atime, extension)                          |
|    - Applies dark data heuristics via _apply_dark_data_heuristics()                           |
|    - Calls AnalysisEngine.scan(Path(self._active_path)) for deep classification               |
+-----------------------------------------------------------------------------------------------+
```

### Detailed Frontend Code Path (`src/ui/js/views/student.js`)

1. **Trigger**: Line 94:
   ```html
   <button class="retro-btn retro-btn-green retro-btn-sm" id="btn-scan-folder">
     📂 Select Folder
   </button>
   ```
2. **Event Binding**: Line 195:
   ```javascript
   if (btnScan) {
     btnScan.addEventListener("click", () => {
       if (window.RetroAudio) window.RetroAudio.playBlip();
       this.openFolderPermissionModal();
     });
   }
   ```
3. **Modal & Execution**: Line 353:
   ```javascript
   if (btnGrant) {
     btnGrant.onclick = async () => {
       const folder = document.getElementById("modal-folder-path").value;
       const sessionOnly = document.getElementById("modal-session-only").checked;
       dismiss();
       await this.executeScan(folder, sessionOnly);
     };
   }
   ```
4. **Execution & Network Call**: Lines 362–387:
   ```javascript
   async executeScan(folderPath, sessionOnly) {
     const banner = document.getElementById("scanner-status-banner");
     const btnRevoke = document.getElementById("btn-revoke-scan");
     if (banner) {
       banner.innerHTML = `<span>⏳ Scanning scoped folder: <strong>${folderPath}</strong>...</span>`;
     }

     try {
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
     } catch (e) {
       if (banner) banner.innerHTML = `<span>❌ Scan failed: ${e.message}</span>`;
     }
   }
   ```

---

## 3. Deep-Dive: Root Causes of Silent Failures ("0 files indexed")

### Root Cause 1: Backend Exception Swallowing in `server.py`
**File**: `src/app/server.py`, lines 290–327
```python
    @app.route("/api/scan/request", methods=["POST"])
    def api_scan_request():
        data = request.get_json() or {}
        folder_path = data.get("folder_path", "").strip()
        session_only = data.get("session_only", True)

        state = load_state()
        state["scanner"]["state"] = "SCANNING"
        
        target_path = folder_path or str(Path.home() / "Desktop")
        state["scanner"]["current_folder"] = target_path

        try:
            global_scanner.request_access(target_path, session_only)
            scanned_items = global_scanner.scan()
            
            files = [item.to_dict() for item in scanned_items]
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
- When `global_scanner.request_access()` raises `FileNotFoundError` (e.g. for `/fake/path/does/not/exist`) or `PermissionError`:
  - `except Exception as e:` sets `state["scanner"]["state"] = "ERROR"`.
  - The error string `str(e)` is printed to server console stdout/stderr, but **never stored in state and never returned in the JSON response**.
  - The return statement **unconditionally returns HTTP 200** with `"status": "completed"`.
  - `state["scanner"]["files"]` is `[]` (or contains stale files from an earlier scan).
  - The client receives `{"status": "completed", "files_found": 0, "files": []}`.

### Root Cause 2: Root Directory Permission Swallowing in `scanner.py`
**File**: `src/services/scanner.py`, lines 291–306
```python
        try:
            for root, dirs, files in os.walk(self._active_path, followlinks=False):
                ...
```
- In Python's standard library `os.walk(top, topdown=True, onerror=None, followlinks=False)`:
  - If `onerror` is `None` (the default), any `OSError` (including `PermissionError: [Errno 1] Operation not permitted` or `[Errno 13] Permission denied`) during `os.scandir(top)` is **silently caught and ignored by `os.walk`**, and `walk` immediately terminates.
  - When `self._active_path` is permission-restricted (such as `chmod 000` or macOS TCC restricted `/Users/narayan/Desktop`), `os.walk` yields 0 directories and 0 files.
  - `scanned_items` remains `[]`.
  - `self._state = ScanState.COMPLETED` is set at line 389.
  - No exception is raised at all!
  - `server.py` considers this a 100% successful scan with 0 files found.

### Root Cause 3: Missing Permission/Readability Checks in `request_access()`
**File**: `src/services/scanner.py`, lines 217–235
```python
    def request_access(self, folder_path: str, session_only: bool = True) -> bool:
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
- `request_access()` verifies existence and directory type, but **does not check if the directory is readable**.
- A directory with permissions `000` or a macOS TCC-restricted folder passes `os.path.exists()` and `os.path.isdir()`.
- The scanner transitions to `ACCESS_ACTIVE_SCOPED` even though reading directory contents is impossible.

### Root Cause 4: Silent Fallback in `AnalysisEngine.scan()` & `sanitizer.py`
**File**: `src/analyzer/engine.py`, lines 40–44 and 71–72
```python
        # Security: Validate and sanitize the scan directory
        try:
            directory = validate_scan_request(str(directory))
        except ValidationError as e:
            return ScanResult(directory=directory, scan_duration=0.0)
```
and lines 71–72:
```python
            except (PermissionError, FileNotFoundError):
                pass
```
- When `validate_scan_request` fails (e.g. `sanitize_directory` detects `not os.access(path, os.R_OK)`), it raises `ValidationError`.
- `AnalysisEngine.scan` catches `ValidationError` and silently returns an empty `ScanResult(directory=directory, scan_duration=0.0)`.
- In `scanner.py` line 487:
  ```python
  except Exception as e:
      print(f"AnalysisEngine failed, using basic rules only: {e}")
  ```
  This further swallows engine-level scan failures.

### Root Cause 5: Frontend `executeScan` Absence of Error Checks
**File**: `src/ui/js/views/student.js`, lines 370–386
```javascript
  const res = await fetch("/api/scan/request", { ... }).then((r) => r.json());

  this.scannedFiles = res.files || [];
  if (banner) {
    banner.innerHTML = `<span>✅ <strong>Access Active</strong>: Scoped to <em>${res.folder}</em> (${res.files_found} files indexed)</span>`;
  }
  if (btnRevoke) btnRevoke.style.display = "inline-flex";

  if (window.RetroAudio) window.RetroAudio.playCoinDing();
  this.renderScannedFiles();
```
- `fetch` in JavaScript does **not** reject promises on HTTP 4xx or 5xx responses.
- `executeScan` never checks `response.ok`, `res.status === "error"`, or `res.error`.
- Even if the server returned `{ "status": "error", "error": "Permission denied" }`, the current frontend code would execute:
  `banner.innerHTML = "✅ Access Active: Scoped to undefined (undefined files indexed)"` and play `playCoinDing()`.
- If `this.scannedFiles` is empty, `renderScannedFiles()` simply writes:
  `No active files in memory. System is completely blind.`
  There is no error state presentation whatsoever in the container or banner.

### Root Cause 6: macOS TCC (Transparency, Consent, and Control) Constraints
- Observed on host system:
  Executing `list_dir` on `/Users/narayan/Desktop`:
  `Encountered error in tool execution: open /Users/narayan/Desktop: operation not permitted`
- On macOS, user folders under `/Users/<username>/Desktop`, `/Users/<username>/Documents`, and `/Users/<username>/Downloads` are guarded by the TCC subsystem.
- Any process without explicit TCC entitlement will fail with `EPERM` (`Operation not permitted` / `PermissionError`) when attempting `opendir()`.
- When users specify `/Users/narayan/Desktop/NEWSLETTER` (or default to `/Users/narayan/Desktop`), TCC blocks traversal. Because of Root Causes 1, 2, 3, and 5, this manifests as silent completion with "0 files indexed".

---

## 4. Scan Result & Error State Formats

### 4.1 Current Formats

#### Current Success Response (HTTP 200)
```json
{
  "status": "completed",
  "folder": "/path/to/folder",
  "files_found": 3,
  "files": [
    {
      "file_id": "f_1234567890abcdef",
      "file_name": "stale_data.csv",
      "absolute_path": "/path/to/folder/stale_data.csv",
      "relative_path": "stale_data.csv",
      "size_bytes": 1024,
      "size_formatted": "1.0 KB",
      "category": "dark_data",
      "dark_data_tag": "Stale relic (age: 200 days > 180d)",
      "is_confidential": false,
      "is_dark_data_candidate": true,
      "preview_blurred": true
    }
  ],
  "session_only": true
}
```

#### Current Failure Response on Error/Missing Path/Permission (HTTP 200 - BUG!)
```json
{
  "status": "completed",
  "folder": "/nonexistent/or/restricted/path",
  "files_found": 0,
  "files": [],
  "session_only": true
}
```
*Note: Status code is 200, status is "completed", error message is absent.*

### 4.2 Proposed Standards-Compliant Error Formats

#### Proposed Success Response (HTTP 200 OK)
```json
{
  "status": "completed",
  "folder": "/path/to/folder",
  "files_found": 3,
  "files": [ ... ],
  "session_only": true
}
```
*(Remains backward-compatible with existing tests in `tests/test_ui_and_build.py` line 195).*

#### Proposed Error Response (HTTP 400 Bad Request or 403 Forbidden)
```json
{
  "status": "error",
  "error": "Permission denied: cannot access folder '/Users/narayan/Desktop'. Please grant folder permissions in macOS System Settings > Privacy & Security > Files and Folders.",
  "folder": "/Users/narayan/Desktop",
  "files_found": 0,
  "files": [],
  "session_only": true
}
```
Or for missing paths:
```json
{
  "status": "error",
  "error": "Selected folder does not exist: /fake/path/does/not/exist",
  "folder": "/fake/path/does/not/exist",
  "files_found": 0,
  "files": [],
  "session_only": true
}
```

---

## 5. Exact Files Requiring Modification & Remediation Plan

### 1. `src/services/scanner.py`
**Changes**:
1. In `request_access(self, folder_path, session_only)`:
   - Normalize and expand: `resolved = os.path.abspath(os.path.expanduser(os.path.expandvars(folder_path.strip())))`
   - Validate existence (`FileNotFoundError`) and directory (`NotADirectoryError`).
   - Validate accessibility: attempt `with os.scandir(resolved) as it: pass` to immediately detect `PermissionError` (including macOS TCC `Operation not permitted`) and `OSError`.
   - Provide informative error text indicating macOS TCC context if path is in Desktop/Documents/Downloads and permission is denied.
2. In `scan(self, progress_callback=None, reference_time=None)`:
   - Pass an `onerror` handler to `os.walk`:
     ```python
     root_error = None
     def on_walk_error(err):
         nonlocal root_error
         if os.path.abspath(getattr(err, "filename", "")) == os.path.abspath(self._active_path):
             root_error = err

     for root, dirs, files in os.walk(self._active_path, onerror=on_walk_error, followlinks=False):
         ...
     if root_error:
         self._state = ScanState.ERROR
         raise root_error
     ```
   - If the root directory traversal itself fails with `PermissionError`, raise it rather than returning `[]`.

### 2. `src/app/server.py`
**Changes**:
In `api_scan_request()`:
- In the `try:` block:
  - If successful:
    `state["scanner"]["files"] = files`
    `state["scanner"]["state"] = "COMPLETED"`
    `state["scanner"]["error"] = None`
    Return HTTP 200 with `status: "completed"`.
- In the `except Exception as e:` block:
  - Extract `error_msg = str(e)`.
  - Format user-friendly message for TCC / permission issues if applicable.
  - Set `state["scanner"]["state"] = "ERROR"`.
  - Clear `state["scanner"]["files"] = []`.
  - Set `state["scanner"]["error"] = error_msg`.
  - Save state.
  - Return HTTP 400 with:
    ```python
    return jsonify({
        "status": "error",
        "error": error_msg,
        "folder": target_path,
        "files_found": 0,
        "files": [],
        "session_only": session_only
    }), 400
    ```

### 3. `src/ui/js/views/student.js`
**Changes**:
1. In `executeScan(folderPath, sessionOnly)`:
   - Perform fetch and check both HTTP status and JSON payload:
     ```javascript
     const response = await fetch("/api/scan/request", {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify({ folder_path: folderPath, session_only: sessionOnly }),
     });

     const res = await response.json().catch(() => ({ status: "error", error: "Invalid server response." }));

     if (!response.ok || res.status === "error" || res.error) {
       const errorMsg = res.error || `Scan failed (Status ${response.status}).`;
       if (banner) {
         banner.innerHTML = `<span style="color: var(--c-danger-bright);">❌ <strong>Scan Error</strong>: ${errorMsg}</span>`;
       }
       if (btnRevoke) btnRevoke.style.display = "none";
       this.scannedFiles = [];
       this.renderScannedFiles(errorMsg);
       if (window.RetroAudio) window.RetroAudio.playGamingBuzzer();
       return;
     }
     ```
2. In `renderScannedFiles(errorMsg = null)`:
   - If `errorMsg` is provided, render a prominent pixelated error card in `#scanned-files-container`:
     ```javascript
     if (errorMsg) {
       container.innerHTML = `
         <div class="retro-inset" style="text-align: center; padding: 24px; color: var(--c-danger-bright); font-size: 12px; border-color: var(--c-danger-red);">
           ⚠️ <strong>Folder Scan Failed</strong>: ${errorMsg}
         </div>
       `;
       return;
     }
     ```
   - On success, render files as before and play `playCoinDing()`.

### 4. `tests/` Test Suite
**Changes**:
1. In `tests/test_ui_and_build.py`:
   - Keep existing `test_api_scan_and_revoke_workflow` passing (`"folder_path": "tests"`).
   - Add `test_api_scan_missing_path_returns_error`:
     Verify `POST /api/scan/request` with non-existent path returns HTTP 400 and `data["status"] == "error"` and `data["error"]` is non-empty.
   - Add `test_api_scan_restricted_permission_returns_error`:
     Create a directory with `chmod 000` (or mock permission error), verify endpoint returns HTTP 400, `data["status"] == "error"`.
2. In `tests/test_scanner.py`:
   - Add test verifying that requesting access to an unreadable directory raises `PermissionError`.
   - Add test verifying that `scan()` on an unreadable directory raises `PermissionError` and sets `ScanState.ERROR`.

---

## 6. Verification Plan & Test Strategy

| Test Case | Description | Target Component | Expected Result |
|---|---|---|---|
| **TC-01** | Valid local directory scan | `POST /api/scan/request` with `"tests"` | HTTP 200, `status: "completed"`, `files_found > 0`, UI displays `✅ Access Active: Scoped to ... (N files indexed)` |
| **TC-02** | Fake / non-existent directory scan | `POST /api/scan/request` with `"/path/does/not/exist"` | HTTP 400, `status: "error"`, `error` contains `"does not exist"`, UI displays `❌ Scan Error: Selected folder does not exist: ...` |
| **TC-03** | Restricted permissions directory scan | `POST /api/scan/request` with `chmod 000` directory | HTTP 400, `status: "error"`, `error` contains `"Permission denied"`, UI displays `❌ Scan Error: Permission denied ...` |
| **TC-04** | macOS TCC protected folder scan | `POST /api/scan/request` with inaccessible `~/Desktop` | HTTP 400, `status: "error"`, UI surfaces visible error string rather than `"0 files indexed"` |
| **TC-05** | Regression Suite (`make test`) | Full test suite execution | 100% pass rate across all existing unit and integration tests |

---

## 7. Conclusion

The survey confirms the exact mechanisms causing the silent "0 files indexed" bug and provides a straightforward, robust remediation plan spanning `src/services/scanner.py`, `src/app/server.py`, and `src/ui/js/views/student.js`. All changes maintain strict adherence to project specifications, preserve existing API contracts for valid scans, and satisfy every acceptance criterion in `ORIGINAL_REQUEST.md`.
