# Milestone 1 Fix Strategy: FileScanner, AnalysisEngine, and Path Sanitization

**Target Audience**: Worker Agent (`worker_m1_1` / subsequent implementers)  
**Author**: `explorer_m1_1` (Teamwork Preview Explorer)  
**Date**: 2026-09-08  
**Scope**: `src/services/scanner.py`, `src/analyzer/engine.py`, `src/security/sanitizer.py`, `src/app/server.py`, `src/ui/js/views/student.js`, and test suites.

---

## 1. Executive Summary

When scanning directories such as `/Users/narayan/Desktop/NEWSLETTER`, the application returns `0 files indexed` without surfacing any error. The root cause is a **multi-tier silent failure cascade**:
1. **macOS TCC / Filesystem Restriction**: Access to `Desktop` and its child folders is restricted by macOS Transparency, Consent, and Control (TCC) unless explicit permission is granted to the running shell/process. Attempting `opendir()` or `scandir()` raises `PermissionError: [Errno 1] Operation not permitted`.
2. **Missing Readability Validation in `FileScanner.request_access()`**: `request_access()` checks `os.path.exists()` and `os.path.isdir()`, which succeed via `stat` on parent directories, but never verifies if the directory can actually be read.
3. **Silent Directory Swallowing in `FileScanner.scan()`**: `os.walk(self._active_path, followlinks=False)` defaults to `onerror=None`. When `os.scandir()` inside `os.walk` hits `PermissionError` on the root directory, it catches and suppresses the error, terminating the generator with 0 iterations and leaving state as `COMPLETED`.
4. **Swallowed Validation in `AnalysisEngine.scan()`**: `AnalysisEngine.scan()` catches `ValidationError` from `validate_scan_request()` and returns an empty `ScanResult(directory=directory, scan_duration=0.0)`.
5. **Path Sanitizer Deficiencies**: `sanitize_path()` does not strip surrounding quotes (e.g. from copy-pasting or drag-and-drop: `"/path"`) and does not expand tildes (`~/Desktop`). `Path('~/Desktop').resolve()` resolves to `<cwd>/~/Desktop` which does not exist.
6. **API Swallowing in `src/app/server.py`**: `api_scan_request()` catches `Exception as e:`, sets state to `ERROR`, prints to stdout, but unconditionally returns HTTP 200 with `"status": "completed"`, `files_found: 0`, and no `error` message.
7. **Frontend Blind Assumption in `student.js`**: `student.js` never checks HTTP response status or `res.status === "error"`. It renders `✅ Access Active: Scoped to ... (0 files indexed)` and plays a victory audio chime.

Below is the exact, step-by-step fix strategy with ready-to-apply code changes.

---

## 2. Component 1: `FileScanner` in `src/services/scanner.py`

### 2.1 Fix Strategy for `request_access()` (`src/services/scanner.py:217-236`)

#### Objectives:
1. Strip leading/trailing whitespace and surrounding single or double quotes (`"..."` or `'...'`).
2. Expand tildes (`os.path.expanduser`) and resolve to canonical absolute path.
3. Verify existence and directory status.
4. **Test directory readability using `os.scandir()`**. If `PermissionError` or `OSError` is raised, raise an informative `PermissionError` that includes diagnostic guidance for macOS TCC.
5. Mutate `self._state` to `ScanState.ACCESS_ACTIVE_SCOPED` **only after** all checks succeed.

#### Implementation Proposal:

```python
<<<<
    def request_access(self, folder_path: str, session_only: bool = True) -> bool:
        """Prompt user and record explicit folder grant.

        Transitions state from BLIND -> ACCESS_ACTIVE_SCOPED.
        """
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
====
    def request_access(self, folder_path: str, session_only: bool = True) -> bool:
        """Prompt user and record explicit folder grant.

        Transitions state from BLIND -> ACCESS_ACTIVE_SCOPED.
        """
        if not folder_path or not str(folder_path).strip():
            raise ValueError("folder_path cannot be empty.")

        # Strip surrounding quotes and whitespace
        clean_path = str(folder_path).strip().strip("'\"")
        if not clean_path:
            raise ValueError("folder_path cannot be empty.")

        resolved = os.path.abspath(os.path.expanduser(clean_path))
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Selected folder does not exist: {folder_path}")
        if not os.path.isdir(resolved):
            raise NotADirectoryError(f"Selected path is not a directory: {folder_path}")

        # Actively test directory readability to catch permission and macOS TCC restrictions early
        try:
            with os.scandir(resolved) as it:
                pass
        except PermissionError as err:
            raise PermissionError(
                f"Permission denied accessing '{resolved}'. "
                f"Please verify folder permissions or grant terminal/app access in "
                f"macOS System Settings -> Privacy & Security -> Files and Folders: {err}"
            ) from err
        except OSError as err:
            raise PermissionError(
                f"Cannot read directory '{resolved}': {err}"
            ) from err

        self._active_path = resolved
        self._session_only = session_only
        self._state = ScanState.ACCESS_ACTIVE_SCOPED
        self._cancel_requested = False
        return True
>>>>
```

---

### 2.2 Fix Strategy for `scan()` (`src/services/scanner.py:291-321`)

#### Objectives:
1. Provide an `onerror` handler to `os.walk` so that root directory and subdirectory traversal errors are not silently discarded.
2. In the `onerror` handler:
   - Check if the error is `PermissionError` or has `errno in (1, 13)` (`EPERM`, `EACCES`).
   - Construct a descriptive diagnostic error message referencing the path and macOS TCC.
   - Re-raise the exception to abort the walk.
3. In the outer `except Exception as exc:` block (line 392):
   - Set `self._state = ScanState.ERROR`.
   - Re-raise `exc` so callers (`server.py`, tests) receive the failure.

#### Implementation Proposal:

```python
<<<<
        try:
            for root, dirs, files in os.walk(self._active_path, followlinks=False):
                if self._cancel_requested:
                    break
====
        try:
            def on_walk_error(err: OSError):
                # Detect permission and TCC denial on root or subdirectories
                if isinstance(err, PermissionError) or getattr(err, "errno", None) in (1, 13):
                    target_name = getattr(err, "filename", None) or self._active_path
                    raise PermissionError(
                        f"Permission denied during scan of '{target_name}'. "
                        f"Please check directory permissions or macOS TCC access: {err}"
                    ) from err
                raise err

            for root, dirs, files in os.walk(self._active_path, followlinks=False, onerror=on_walk_error):
                if self._cancel_requested:
                    break
>>>>
```

---

## 3. Component 2: `AnalysisEngine` in `src/analyzer/engine.py`

### 3.1 Fix Strategy for `AnalysisEngine.scan()` (`src/analyzer/engine.py:37-75`)

#### Objectives:
1. Do **not** silently swallow `ValidationError` into `ScanResult(directory=directory, scan_duration=0.0)`.
2. When `validate_scan_request(str(directory))` raises `ValidationError`, propagate the exception (or re-raise it) so the caller receives the failure.
3. In `walk_dir(path, current_depth)`: if `path.iterdir()` fails on the root directory (`current_depth == 0`), raise `PermissionError` rather than silently passing.

#### Implementation Proposal:

```python
<<<<
    def scan(self, directory: Path, progress_callback: Optional[Callable] = None) -> ScanResult:
        start_time = time.time()
        
        # Security: Validate and sanitize the scan directory
        try:
            directory = validate_scan_request(str(directory))
        except ValidationError as e:
            return ScanResult(directory=directory, scan_duration=0.0)
        
        # Security: Authorize this directory as a scan root in the sandbox
        self.sandbox.authorize_scan_root(directory)
        self.sandbox.reset_session_limits()
====
    def scan(self, directory: Path, progress_callback: Optional[Callable] = None) -> ScanResult:
        start_time = time.time()
        
        # Security: Validate and sanitize the scan directory
        # Propagate ValidationError so invalid/unreadable scan requests are not silently treated as empty folders
        directory = validate_scan_request(str(directory))
        
        # Security: Authorize this directory as a scan root in the sandbox
        self.sandbox.authorize_scan_root(directory)
        self.sandbox.reset_session_limits()
>>>>
```

And in `walk_dir` (lines 71-73):
```python
<<<<
            except (PermissionError, FileNotFoundError):
                pass
====
            except (PermissionError, FileNotFoundError) as exc:
                if current_depth == 0:
                    raise PermissionError(f"Cannot read directory '{path}': {exc}") from exc
                pass
>>>>
```

---

## 4. Component 3: Path Sanitization in `src/security/sanitizer.py`

### 4.1 Fix Strategy for `sanitize_path()` (`src/security/sanitizer.py:56-111`)

#### Objectives:
1. Strip leading and trailing quotes (both single `'` and double `"`). Users often copy paths from shells or drag-and-drop into text fields.
2. Support tilde expansion via `os.path.expanduser(path_str)` so `~/Desktop` resolves to the user's actual home directory rather than `<cwd>/~/Desktop`.
3. Preserve all security checks: null bytes, directory traversal `..`, shell metacharacters, Unicode homoglyphs.

#### Implementation Proposal:

```python
<<<<
def sanitize_path(path_str: str) -> Path:
    if not path_str or not path_str.strip():
        raise ValidationError("path", "Path cannot be empty")

    path_str = path_str.strip()

    # Length check
    if len(path_str) > MAX_PATH_LENGTH:
        raise ValidationError("path", f"Path exceeds maximum length ({MAX_PATH_LENGTH} chars)",
                            path_str[:50] + "...")

    # Null byte injection
    if _NULL_BYTE_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains null bytes — possible injection attack")

    # Path traversal
    if _PATH_TRAVERSAL_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains traversal sequence '..' — not allowed",
                            path_str)

    # Shell injection characters
    if _SHELL_INJECTION_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains shell metacharacters — not allowed",
                            path_str)

    # Unicode homoglyph attacks
    if _UNICODE_HOMOGLYPH_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains invisible Unicode characters — possible homoglyph attack")

    # Resolve and validate
    try:
        resolved = Path(path_str).resolve()
    except (OSError, RuntimeError) as e:
        raise ValidationError("path", f"Failed to resolve path: {e}")

    return resolved
====
def sanitize_path(path_str: str) -> Path:
    if not path_str or not str(path_str).strip():
        raise ValidationError("path", "Path cannot be empty")

    path_str = str(path_str).strip()

    # Strip surrounding single or double quotes
    if (path_str.startswith('"') and path_str.endswith('"')) or \
       (path_str.startswith("'") and path_str.endswith("'")):
        path_str = path_str[1:-1].strip()

    if not path_str:
        raise ValidationError("path", "Path cannot be empty")

    # Length check
    if len(path_str) > MAX_PATH_LENGTH:
        raise ValidationError("path", f"Path exceeds maximum length ({MAX_PATH_LENGTH} chars)",
                            path_str[:50] + "...")

    # Null byte injection
    if _NULL_BYTE_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains null bytes — possible injection attack")

    # Path traversal
    if _PATH_TRAVERSAL_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains traversal sequence '..' — not allowed",
                            path_str)

    # Shell injection characters
    if _SHELL_INJECTION_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains shell metacharacters — not allowed",
                            path_str)

    # Unicode homoglyph attacks
    if _UNICODE_HOMOGLYPH_PATTERN.search(path_str):
        raise ValidationError("path", "Path contains invisible Unicode characters — possible homoglyph attack")

    # Resolve and validate with tilde expansion
    try:
        expanded = os.path.expanduser(path_str)
        resolved = Path(expanded).resolve()
    except (OSError, RuntimeError) as e:
        raise ValidationError("path", f"Failed to resolve path: {e}")

    return resolved
>>>>
```

### 4.2 Fix Strategy for `sanitize_directory()` (`src/security/sanitizer.py:113-138`)

#### Objectives:
1. Verify directory readability using both `os.access()` and active `os.scandir()` opening.
2. If `PermissionError` or `OSError` occurs, raise `ValidationError("directory", ...)`.

#### Implementation Proposal:

```python
<<<<
    # Check readability
    if not os.access(path, os.R_OK):
        raise ValidationError("directory", f"Directory is not readable: {path}")

    return path
====
    # Check readability and active directory descriptor access (catches macOS TCC EPERM)
    if not os.access(path, os.R_OK):
        raise ValidationError("directory", f"Directory is not readable: {path}")

    try:
        with os.scandir(path) as it:
            pass
    except (PermissionError, OSError) as e:
        raise ValidationError("directory", f"Directory is not accessible (permission denied or macOS TCC restriction): {e}")

    return path
>>>>
```

---

## 5. Component 4: API & UI Error Surfacing Integration

### 5.1 `src/app/server.py: api_scan_request()` (`src/app/server.py:290-327`)

#### Contract Requirement:
- On error, return HTTP 400 with payload:
  ```json
  {
    "status": "error",
    "error": "<descriptive_error_message>",
    "folder": "<target_path>",
    "files_found": 0,
    "files": [],
    "session_only": <bool>
  }
  ```
- On success, return HTTP 200 with `status: "completed"`.

#### Implementation Proposal:

```python
<<<<
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
====
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
            state["scanner"]["current_folder"] = global_scanner._active_path or target_path
            state["scanner"]["state"] = "COMPLETED"
            state["scanner"]["error"] = None
            save_state(state)

            return jsonify({
                "status": "completed",
                "folder": state["scanner"]["current_folder"],
                "files_found": len(state["scanner"]["files"]),
                "files": state["scanner"]["files"],
                "session_only": session_only
            })
        except Exception as e:
            state["scanner"]["state"] = "ERROR"
            state["scanner"]["files"] = []
            state["scanner"]["error"] = str(e)
            save_state(state)
            print(f"Error scanning: {e}")
            
            return jsonify({
                "status": "error",
                "error": str(e),
                "folder": target_path,
                "files_found": 0,
                "files": [],
                "session_only": session_only
            }), 400
>>>>
```

### 5.2 `src/ui/js/views/student.js: requestFolderAccess()` (`src/ui/js/views/student.js:369-387`)

#### Objectives:
1. Handle both non-200 HTTP responses and `res.status === "error"`.
2. Present a red banner error with clear text: `❌ Scan Error: ${errorMsg}`.
3. Hide the `#btn-revoke-scan` button.
4. Render an error card in `#scanned-files-container`.
5. Play `RetroAudio.playGamingBuzzer()`.

#### Implementation Proposal:

```javascript
<<<<
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
====
    try {
      const response = await fetch("/api/scan/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder_path: folderPath, session_only: sessionOnly }),
      });
      const res = await response.json();

      if (!response.ok || res.status === "error") {
        const errorMsg = res.error || `HTTP error ${response.status}`;
        this.scannedFiles = [];
        if (banner) {
          banner.innerHTML = `<span style="color: var(--c-danger, #ef4444);">❌ <strong>Scan Error</strong>: ${errorMsg}</span>`;
        }
        if (btnRevoke) btnRevoke.style.display = "none";
        if (window.RetroAudio && window.RetroAudio.playGamingBuzzer) {
          window.RetroAudio.playGamingBuzzer();
        }
        const container = document.getElementById("scanned-files-container");
        if (container) {
          container.innerHTML = `
            <div style="text-align: center; padding: 24px; color: var(--c-danger, #ef4444); font-size: 13px;">
              <strong>Scanning Failed:</strong> ${errorMsg}
            </div>
          `;
        }
        return;
      }

      this.scannedFiles = res.files || [];
      if (banner) {
        banner.innerHTML = `<span>✅ <strong>Access Active</strong>: Scoped to <em>${res.folder}</em> (${res.files_found} files indexed)</span>`;
      }
      if (btnRevoke) btnRevoke.style.display = "inline-flex";

      if (window.RetroAudio) window.RetroAudio.playCoinDing();
      this.renderScannedFiles();
    } catch (e) {
      if (banner) {
        banner.innerHTML = `<span style="color: var(--c-danger, #ef4444);">❌ <strong>Scan failed</strong>: ${e.message}</span>`;
      }
      if (window.RetroAudio && window.RetroAudio.playGamingBuzzer) {
        window.RetroAudio.playGamingBuzzer();
      }
    }
>>>>
```

---

## 6. Component 5: Unit & Regression Test Strategy

Worker must implement tests in `tests/test_scanner.py` and `tests/test_ui_and_build.py`.

### 6.1 Tests in `tests/test_scanner.py`
Add test methods to `TestFileScanner`:

1. **`test_request_access_unreadable_directory`**:
   Create a directory in `self.temp_dir`, call `os.chmod(dir, 0o000)`.
   Assert `self.scanner.request_access(dir)` raises `PermissionError`.
   Verify state remains `ScanState.BLIND` (or not `ACCESS_ACTIVE_SCOPED`).
   In a `finally` block, restore permissions with `os.chmod(dir, 0o755)`.

2. **`test_request_access_tilde_and_quotes`**:
   Verify passing `'"' + self.root_path + '"'` strips quotes and succeeds.
   Verify passing `"~"` resolves to `os.path.expanduser("~")`.

3. **`test_scan_permission_error_propagation`**:
   Use `unittest.mock.patch("os.walk")` to simulate `os.walk` calling `onerror(PermissionError(1, "Operation not permitted"))`.
   Assert `self.scanner.scan()` raises `PermissionError`.
   Assert `self.scanner.get_state() == ScanState.ERROR`.

4. **`test_sanitizer_directory_unreadable`**:
   Test `sanitize_directory` and `validate_scan_request` on an unreadable path raise `ValidationError`.

### 6.2 Tests in `tests/test_ui_and_build.py`
Add test methods to `TestUIAndBuild`:

1. **`test_api_scan_request_nonexistent_directory`**:
   `POST /api/scan/request` with `{"folder_path": "/path/does/not/exist"}`.
   Assert `res.status_code == 400`.
   Assert `res.get_json()["status"] == "error"`.
   Assert `"error"` in `res.get_json()`.

2. **`test_api_scan_request_permission_denied`**:
   `POST /api/scan/request` with a path that triggers `PermissionError`.
   Assert `res.status_code == 400`.
   Assert `res.get_json()["status"] == "error"`.

3. **Regression Check**:
   Existing `test_api_scan_and_revoke_workflow` continues to pass with HTTP 200 and `status == "completed"`.

---

## 7. Actionable Checklist for Worker

- [ ] Modify `src/services/scanner.py`:
  - [ ] Add quote stripping, tilde expansion, and `os.scandir()` check in `request_access()`.
  - [ ] Add `onerror` handler in `scan()` `os.walk` call.
- [ ] Modify `src/analyzer/engine.py`:
  - [ ] Stop swallowing `ValidationError` in `AnalysisEngine.scan()`.
  - [ ] Propagate root-level directory errors in `walk_dir()`.
- [ ] Modify `src/security/sanitizer.py`:
  - [ ] Strip quotes and expand `~` in `sanitize_path()`.
  - [ ] Add `os.scandir()` check in `sanitize_directory()`.
- [ ] Modify `src/app/server.py`:
  - [ ] In `api_scan_request()`, return HTTP 400 with `status: "error"` on exceptions.
- [ ] Modify `src/ui/js/views/student.js`:
  - [ ] Check `!response.ok || res.status === "error"`.
  - [ ] Display red error banner and trigger error buzzer sound.
- [ ] Add unit & integration tests to `tests/test_scanner.py` and `tests/test_ui_and_build.py`.
- [ ] Run `make test` to ensure all 503 baseline tests + new tests pass.
