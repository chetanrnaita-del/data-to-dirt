# Handoff Report: Server Error API Response & Frontend Error Surfacing

**From**: `explorer_m1_2` (Teamwork Explorer)  
**To**: `orchestrator` (parent id: `e21f5569-9a5c-4ba2-987c-97f42180e634`)  
**Milestone**: Milestone 1 (Directory Scanning & Error Surfacing Fix)  
**Assigned Scope**: `src/app/server.py` and `src/ui/js/views/student.js`  
**Working Directory**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_m1_2`  
**Recommendation File**: `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/.agents/explorer_m1_2/recommendation.md`  
**Handoff Type**: Hard (Investigation complete, actionable code recommendations provided)  

---

## 1. Observation

### 1.1 Backend Error Interception in `src/app/server.py`
In `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/app/server.py`, lines 290–327:
```python
290:     @app.route("/api/scan/request", methods=["POST"])
291:     def api_scan_request():
292:         data = request.get_json() or {}
293:         folder_path = data.get("folder_path", "").strip()
294:         session_only = data.get("session_only", True)
295: 
296:         state = load_state()
297:         state["scanner"]["state"] = "SCANNING"
298:         
299:         target_path = folder_path or str(Path.home() / "Desktop")
300:         state["scanner"]["current_folder"] = target_path
301: 
302:         try:
303:             global_scanner.request_access(target_path, session_only)
304:             scanned_items = global_scanner.scan()
305:             
306:             files = [item.to_dict() for item in scanned_items]
307:             # Map dark data reasoning
308:             for f in files:
309:                 f["size_formatted"] = format_bytes(f["size_bytes"])
310:                 f["category"] = "dark_data" if f["is_dark_data_candidate"] else "normal"
311:                 f["dark_data_tag"] = f["dark_data_reason"] or "Normal"
312:                 
313:             state["scanner"]["files"] = files
314:             state["scanner"]["state"] = "COMPLETED"
315:         except Exception as e:
316:             state["scanner"]["state"] = "ERROR"
317:             print(f"Error scanning: {e}")
318:             
319:         save_state(state)
320: 
321:         return jsonify({
322:             "status": "completed",
323:             "folder": state["scanner"]["current_folder"],
324:             "files_found": len(state["scanner"]["files"]),
325:             "files": state["scanner"]["files"],
326:             "session_only": session_only
327:         })
```
- Direct code inspection confirms that when `global_scanner.request_access()` or `global_scanner.scan()` raises any exception (`FileNotFoundError`, `PermissionError`, etc.), the exception is caught on line 315.
- On line 316, `state["scanner"]["state"] = "ERROR"` is set, but `files` was never set. Execution falls through lines 319–327.
- Line 321 returns HTTP 200 with hardcoded `"status": "completed"`, `files_found: len(state["scanner"]["files"])` (evaluates to 0), and completely omits `error` from the JSON body.

### 1.2 Frontend Missing Error Validation in `src/ui/js/views/student.js`
In `/Users/narayan/.gemini/antigravity/scratch/data-to-dirt/src/ui/js/views/student.js`, lines 362–387:
```javascript
362:   async executeScan(folderPath, sessionOnly) {
363:     const banner = document.getElementById("scanner-status-banner");
364:     const btnRevoke = document.getElementById("btn-revoke-scan");
365:     if (banner) {
366:       banner.innerHTML = `<span>⏳ Scanning scoped folder: <strong>${folderPath}</strong>...</span>`;
367:     }
368: 
369:     try {
370:       const res = await fetch("/api/scan/request", {
371:         method: "POST",
372:         headers: { "Content-Type": "application/json" },
373:         body: JSON.stringify({ folder_path: folderPath, session_only: sessionOnly }),
374:       }).then((r) => r.json());
375: 
376:       this.scannedFiles = res.files || [];
377:       if (banner) {
378:         banner.innerHTML = `<span>✅ <strong>Access Active</strong>: Scoped to <em>${res.folder}</em> (${res.files_found} files indexed)</span>`;
379:       }
380:       if (btnRevoke) btnRevoke.style.display = "inline-flex";
381: 
382:       if (window.RetroAudio) window.RetroAudio.playCoinDing();
383:       this.renderScannedFiles();
384:     } catch (e) {
385:       if (banner) banner.innerHTML = `<span>❌ Scan failed: ${e.message}</span>`;
386:     }
387:   }
```
- Line 370–374: `fetch().then(r => r.json())` resolves on any HTTP status code as long as valid JSON is returned (including HTTP 400 or 500).
- Lines 376–383: The code never inspects `response.ok`, `res.status === "error"`, or `res.error`. It assumes success, assigns `this.scannedFiles = res.files || []` (`[]`), sets the banner to `✅ Access Active: Scoped to ... (0 files indexed)`, displays the revoke button, and plays the victory chime `window.RetroAudio.playCoinDing()`.
- In `renderScannedFiles()` (lines 412–419), when `this.scannedFiles.length === 0`, it displays `No active files in memory. System is completely blind.`, offering no clue to the student that an error occurred.

### 1.3 Audio Synthesizer and CSS Assets
- In `src/ui/js/audio.js` lines 176–205, `window.RetroAudio.playGamingBuzzer()` already exists and synthesizes a harsh 130 Hz sawtooth bass with a 22 Hz tremolo LFO.
- In `src/ui/css/retro_base.css` lines 45–46, `--c-danger-red: #a82424;` and `--c-danger-bright: #e04848;` are defined for error states.
- In `src/ui/css/stardew.css` lines 57–65, `.retro-inset` provides the standard panel inset style.

---

## 2. Logic Chain

1. **Premise 1 (Obs 1.1)**: When scanning a restricted directory, a TCC-blocked directory, or a non-existent path, Python raises an exception in `request_access()` or `scan()`.
2. **Premise 2 (Obs 1.1)**: `src/app/server.py` catches this exception, but bypasses error response generation and returns HTTP 200 with `"status": "completed"`, `files_found: 0`, and no `"error"` attribute.
3. **Premise 3 (Obs 1.2)**: `src/ui/js/views/student.js` performs `fetch(...).then(r => r.json())`. Because HTTP 200 is returned, `fetch` does not throw. Moreover, `student.js` never checks HTTP status or `res.status`.
4. **Premise 4 (Obs 1.2)**: As a result, `student.js` unconditionally treats the response as a successful scan of 0 files, displays the green `✅ Access Active` banner, enables the revoke button, and sounds the coin ding.
5. **Inference**: Even if the backend fix is applied to return HTTP 400, if `student.js` does not check `!response.ok || res.status === "error"`, `fetch().then(r => r.json())` would still parse the JSON and fall through to render `✅ Access Active: Scoped to ... (0 files indexed)`.
6. **Deduction**: A synchronized fix is mandatory:
   - `server.py` must return HTTP 400 with `{"status": "error", "error": str(e), "folder": target_path, "files_found": 0, "files": []}` in the `except` block.
   - `student.js` must check `!response.ok || res.status === "error" || res.error`, render a red error banner (`❌ Scan Error: ${errorMsg}`), render an error card in `#scanned-files-container`, hide `#btn-revoke-scan`, and invoke `RetroAudio.playGamingBuzzer()`.

---

## 3. Caveats

1. **Coordination with Explorer M1-1 (Backend Core)**: `server.py` relies on `FileScanner` and `AnalysisEngine` raising exceptions when permissions or paths fail. If `scanner.py` swallowed errors, `server.py` would never enter its `except` block. Explorer M1-1 is addressing `scanner.py` and `sanitizer.py`.
2. **Coordination with Explorer M1-3 (Test Suite)**: Existing tests only test `"tests"` (which succeeds). Explorer M1-3 is adding test cases in `test_ui_and_build.py` asserting that invalid paths return HTTP 400 with `status: "error"`.
3. **Browser Audio Context Autoplay Policy**: Web browsers (Chrome, Safari, Electron) may suspend `AudioContext` until the user interacts with the page. Since directory scanning is triggered by a user click on "Grant Access", `RetroAudio.ensureContext()` is safely invoked within a user gesture.

---

## 4. Conclusion

The strategy to eliminate the "0 files indexed" silent failure across `server.py` and `student.js` is fully specified and documented in `recommendation.md`:
1. In `src/app/server.py` (`api_scan_request`):
   - Catch `Exception as e:`.
   - Set `state["scanner"]["state"] = "ERROR"`.
   - Set `state["scanner"]["files"] = []`.
   - Set `state["scanner"]["error"] = str(e)`.
   - Persist state via `save_state(state)`.
   - Return `jsonify({"status": "error", "error": str(e), "folder": target_path, "files_found": 0, "files": []}), 400`.
2. In `src/ui/js/views/student.js`:
   - In `executeScan`: inspect `!response.ok || res.status === "error" || res.error`.
   - On error: display red banner `❌ Scan Error: ${errorMsg}`, hide `#btn-revoke-scan`, sound `playGamingBuzzer()`, and display error card in `#scanned-files-container`.
   - In `renderScannedFiles(errorMessage = null)`: render dedicated error card when `errorMessage` is present.
   - In `revokeFolderAccess()`: reset banner styling and borders back to neutral.

---

## 5. Verification Method

### 5.1 Project Test Command
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
# or
make test
```
All existing 503 tests must pass without regressions.

### 5.2 Server API Verification
In Python test client or curl:
```python
from src.app.server import create_flask_app

app = create_flask_app()
client = app.test_client()

# 1. Invalid folder -> HTTP 400 with status: "error"
res = client.post("/api/scan/request", json={"folder_path": "/nonexistent/fake/folder"})
assert res.status_code == 400, f"Expected 400, got {res.status_code}"
data = res.get_json()
assert data["status"] == "error"
assert "error" in data and len(data["error"]) > 0
assert data["files_found"] == 0

# 2. Valid folder -> HTTP 200 with status: "completed"
res = client.post("/api/scan/request", json={"folder_path": "tests"})
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
data = res.get_json()
assert data["status"] == "completed"
assert data["files_found"] > 0
```

### 5.3 UI Error Surfacing Verification
1. Launch UI (`./run.sh` or web server on port 5001).
2. Click **📂 Select Folder**, enter `/fake/nonexistent/directory`, and click **Grant Access**.
3. **Verify UI State**:
   - `#scanner-status-banner` displays `❌ Scan Error: Selected folder does not exist: /fake/nonexistent/directory` in red text with a red inset border.
   - `#scanned-files-container` displays the `Directory Access / Scan Failed` warning card.
   - `#btn-revoke-scan` is hidden (`display: none`).
   - Audio buzzer (`RetroAudio.playGamingBuzzer()`) sounds.
   - UI does NOT say "0 files indexed" or display the green checkmark.

### 5.4 Invalidation Conditions
- If scanning an unreadable or non-existent folder returns HTTP 200 or `status: "completed"`, this fix is invalidated.
- If the UI displays `✅ Access Active` on a failed scan, this fix is invalidated.
- If existing tests in `make test` fail, this fix is invalidated.
