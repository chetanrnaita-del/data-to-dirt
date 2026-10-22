# Fix Strategy & Recommendations: Server Error Handling & UI Error Surfacing (Milestone 1)

**Agent**: `explorer_m1_2` (Teamwork Explorer)  
**Target Files**:
1. `src/app/server.py` — Flask REST API Server (`api_scan_request`, `api_scan_revoke`, default state)
2. `src/ui/js/views/student.js` — Frontend Student View (`executeScan`, `renderScannedFiles`, `revokeFolderAccess`)
**Related Requirements**: `ORIGINAL_REQUEST.md` (R1, R2, AC1, AC3), `PROJECT.md` (Feature 4, Feature 5)

---

## 1. Executive Summary

When directory scanning fails due to macOS TCC restrictions, permission denials (`chmod 000`), or non-existent folder paths, the system previously:
1. Caught the exception in `src/app/server.py`, but suppressed it and returned HTTP 200 with hardcoded `"status": "completed"`, `files_found: 0`, and no `"error"` message.
2. In `src/ui/js/views/student.js`, `fetch` resolved on HTTP 200, ignored HTTP status and error properties, blindly displayed `✅ Access Active: Scoped to <folder> (0 files indexed)`, and played a victory coin chime.

To resolve this defect completely, Worker must implement a two-sided coordinated fix:
- **Backend (`src/app/server.py`)**: When an exception occurs during access scoping or traversal, set scanner state to `"ERROR"`, purge in-memory files, record the error string, and return **HTTP 400** with `{"status": "error", "error": str(e), "folder": target_path, "files_found": 0, "files": []}`.
- **Frontend (`src/ui/js/views/student.js`)**: In `executeScan`, inspect `!response.ok || res.status === "error" || res.error`. Upon failure, render a prominent red error banner (`❌ Scan Error: ${errorMsg}`), display an explanatory error card in `#scanned-files-container`, hide `#btn-revoke-scan`, and sound the harsh retro gaming buzzer (`RetroAudio.playGamingBuzzer()`).

---

## 2. Backend Fix: `src/app/server.py`

### 2.1 Problem Analysis
In `src/app/server.py` lines 290–327:
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
- Line 315 catches `Exception as e:`, but lines 321–327 unconditionally return HTTP 200 with `"status": "completed"`.
- The caller receives no error string, and `files_found: 0` is indistinguishable from an empty directory.

### 2.2 Proposed Replacement Snippet for `src/app/server.py`

#### A. Update `get_default_state()` (Lines 87–92):
Ensure `"error": None` is initialized in the scanner state dictionary.
```python
        "scanner": {
            "state": "BLIND",  # BLIND, SCANNING, COMPLETED, REVOKED, ERROR
            "current_folder": None,
            "files": [],
            "confidential_ids": [],
            "error": None,
        },
```

#### B. Update `api_scan_request()` (Lines 290–327):
```python
    @app.route("/api/scan/request", methods=["POST"])
    def api_scan_request():
        data = request.get_json() or {}
        folder_path = data.get("folder_path", "").strip()
        session_only = data.get("session_only", True)

        state = load_state()
        state["scanner"]["state"] = "SCANNING"
        
        # Clean quotes if entered by user (e.g. copied path from terminal)
        target_path = folder_path.strip("\"'") if folder_path else str(Path.home() / "Desktop")
        state["scanner"]["current_folder"] = target_path

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
            print(f"Error scanning: {e}")
            save_state(state)

            return jsonify({
                "status": "error",
                "error": str(e),
                "folder": target_path,
                "files_found": 0,
                "files": []
            }), 400
```

#### C. Update `api_scan_revoke()` (Lines 328–341):
Ensure `state["scanner"]["error"] = None` when access is revoked:
```python
    @app.route("/api/scan/revoke", methods=["POST"])
    def api_scan_revoke():
        state = load_state()
        count = len(state["scanner"]["files"])
        state["scanner"]["state"] = "BLIND"
        state["scanner"]["current_folder"] = None
        state["scanner"]["files"] = []
        state["scanner"]["confidential_ids"] = []
        state["scanner"]["error"] = None
        save_state(state)
        return jsonify({
            "status": "revoked",
            "message": "Access revoked. In-memory file cache purged.",
            "files_purged": count
        })
```

---

## 3. Frontend Fix: `src/ui/js/views/student.js`

### 3.1 Problem Analysis
In `src/ui/js/views/student.js` lines 362–387:
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
1. Calling `.then((r) => r.json())` on `fetch` parses the response on HTTP 400 without throwing, so the `catch` block is bypassed.
2. The code unconditionally sets `this.scannedFiles = res.files || []` (`[]`), displays the green checkmark banner (`✅ Access Active: Scoped to ... (0 files indexed)`), shows the revoke button, and plays the success coin ding chime.
3. `renderScannedFiles()` only checks `this.scannedFiles.length === 0`, displaying the generic `"No active files in memory. System is completely blind."` rather than showing why scanning failed.

### 3.2 Proposed Replacement Snippet for `src/ui/js/views/student.js`

#### A. Rewrite `executeScan` (Lines 362–387):
```javascript
  async executeScan(folderPath, sessionOnly) {
    const banner = document.getElementById("scanner-status-banner");
    const btnRevoke = document.getElementById("btn-revoke-scan");
    if (banner) {
      banner.style.borderColor = "";
      banner.style.backgroundColor = "";
      banner.innerHTML = `<span>⏳ Scanning scoped folder: <strong>${folderPath}</strong>...</span>`;
    }

    try {
      const response = await fetch("/api/scan/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder_path: folderPath, session_only: sessionOnly }),
      });

      let res;
      try {
        res = await response.json();
      } catch {
        res = {};
      }

      if (!response.ok || res.status === "error" || res.error) {
        const errorMsg = res.error || res.message || (!response.ok ? `HTTP ${response.status}: Scan failed` : "Failed to scan folder");
        this.scannedFiles = [];
        if (banner) {
          banner.style.borderColor = "var(--c-danger-red)";
          banner.style.backgroundColor = "rgba(168, 36, 36, 0.15)";
          banner.innerHTML = `<span style="color: var(--c-danger-bright); font-weight: bold;">❌ Scan Error: ${errorMsg}</span>`;
        }
        if (btnRevoke) btnRevoke.style.display = "none";

        if (window.RetroAudio) window.RetroAudio.playGamingBuzzer();
        this.renderScannedFiles(errorMsg);
        return;
      }

      this.scannedFiles = res.files || [];
      if (banner) {
        banner.style.borderColor = "";
        banner.style.backgroundColor = "";
        banner.innerHTML = `<span>✅ <strong>Access Active</strong>: Scoped to <em>${res.folder}</em> (${res.files_found} files indexed)</span>`;
      }
      if (btnRevoke) btnRevoke.style.display = "inline-flex";

      if (window.RetroAudio) window.RetroAudio.playCoinDing();
      this.renderScannedFiles();
    } catch (e) {
      const errorMsg = e.message || "Failed to communicate with scanner service";
      this.scannedFiles = [];
      if (banner) {
        banner.style.borderColor = "var(--c-danger-red)";
        banner.style.backgroundColor = "rgba(168, 36, 36, 0.15)";
        banner.innerHTML = `<span style="color: var(--c-danger-bright); font-weight: bold;">❌ Scan Error: ${errorMsg}</span>`;
      }
      if (btnRevoke) btnRevoke.style.display = "none";

      if (window.RetroAudio) window.RetroAudio.playGamingBuzzer();
      this.renderScannedFiles(errorMsg);
    }
  }
```

#### B. Update `renderScannedFiles` (Lines 408–450):
Support an optional `errorMessage` parameter to render an error card inside `#scanned-files-container`:
```javascript
  renderScannedFiles(errorMessage = null) {
    const container = document.getElementById("scanned-files-container");
    if (!container) return;

    if (errorMessage) {
      container.innerHTML = `
        <div class="retro-inset" style="text-align: center; padding: 18px 12px; border-color: var(--c-danger-red); background-color: rgba(168, 36, 36, 0.08);">
          <div style="font-size: 20px; margin-bottom: 6px;">⚠️</div>
          <div style="font-weight: bold; font-size: 13px; color: var(--c-danger-bright); margin-bottom: 4px;">
            Directory Access / Scan Failed
          </div>
          <div style="font-size: 11px; color: var(--c-ink-muted); word-break: break-word; margin-bottom: 8px;">
            ${errorMessage}
          </div>
          <div style="font-size: 10px; color: var(--c-ink-light);">
            Please verify that the directory exists and permissions (e.g. macOS Full Disk Access) are granted.
          </div>
        </div>
      `;
      return;
    }

    if (this.scannedFiles.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 24px; color: var(--c-ink-light); font-size: 12px;">
          No active files in memory. System is completely blind.
        </div>
      `;
      return;
    }

    container.innerHTML = this.scannedFiles
      .map((file) => {
        const tagClass = file.category === "heavy_media" ? "retro-tag-heavy" : file.category === "transient_trash" ? "retro-tag-stale" : file.is_confidential ? "retro-tag-confidential" : "retro-tag-duplicate";

        return `
          <div class="retro-inset" style="display: flex; justify-content: space-between; align-items: center; padding: 8px 10px;">
            <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 68%;">
              <div style="font-weight: bold; font-size: 13px; color: var(--c-ink-text);">
                ${file.is_confidential ? "🔒 [CONFIDENTIAL] " : ""}${file.file_name}
              </div>
              <div style="font-size: 11px; color: var(--c-ink-muted);">
                ${file.size_formatted} • ${file.age_days} days old • <span class="retro-tag ${tagClass}">${file.dark_data_tag}</span>
              </div>
            </div>

            <div style="display: flex; gap: 6px;">
              ${
                file.is_confidential
                  ? `<span style="font-size: 11px; color: var(--c-ink-light); font-style: italic;">Protected</span>`
                  : `<button class="retro-btn retro-btn-danger retro-btn-sm btn-delete-file" data-id="${file.file_id}">
                      🗑️ Clean
                    </button>`
              }
            </div>
          </div>
        `;
      })
      .join("");

    // Bind clean buttons
    container.querySelectorAll(".btn-delete-file").forEach((btn) => {
      btn.onclick = () => {
        const fileId = btn.getAttribute("data-id");
        const file = this.scannedFiles.find((f) => f.file_id === fileId);
        if (file) {
          if (window.RetroAudio) window.RetroAudio.playBlip();
          this.openDeletionModal(file);
        }
      };
    });
  }
```

#### C. Update `revokeFolderAccess` (Lines 389–406):
Ensure banner styling is reset to neutral when user revokes access:
```javascript
  async revokeFolderAccess() {
    const banner = document.getElementById("scanner-status-banner");
    const btnRevoke = document.getElementById("btn-revoke-scan");

    try {
      await fetch("/api/scan/revoke", { method: "POST" });
      this.scannedFiles = [];
      this.renderScannedFiles();

      if (banner) {
        banner.style.borderColor = "";
        banner.style.backgroundColor = "";
        banner.innerHTML = `<span>👁️ <strong>Blind State</strong>: Access revoked. All in-memory records purged.</span>`;
      }
      if (btnRevoke) btnRevoke.style.display = "none";
      if (window.RetroAudio) window.RetroAudio.playBlip();
    } catch (e) {
      console.warn("Revoke error:", e);
    }
  }
```

---

## 4. Interaction Contract Matrix

| Condition | `POST /api/scan/request` HTTP Code | Response JSON `status` | Response JSON `error` | UI Banner (`#scanner-status-banner`) | UI File List (`#scanned-files-container`) | Audio Chime | Revoke Button |
|---|---|---|---|---|---|---|---|
| **Valid readable folder** (e.g. `"tests"`) | 200 OK | `"completed"` | *omitted* | `✅ Access Active: Scoped to ... (N files indexed)` | Rendered file entries with Clean buttons | `playCoinDing()` | Visible (`inline-flex`) |
| **Non-existent folder** (e.g. `"/fake/path"`) | 400 Bad Request | `"error"` | `"Selected folder does not exist: ..."` | `❌ Scan Error: Selected folder does not exist: ...` | Error card: `Directory Access / Scan Failed` | `playGamingBuzzer()` | Hidden (`none`) |
| **Restricted permissions** (`chmod 000`) | 400 Bad Request | `"error"` | `"Permission denied: ..."` | `❌ Scan Error: Permission denied: ...` | Error card: `Directory Access / Scan Failed` | `playGamingBuzzer()` | Hidden (`none`) |
| **macOS TCC denial** (`NEWSLETTER`) | 400 Bad Request | `"error"` | `"Permission denied: [Errno 1] Operation not permitted ..."` | `❌ Scan Error: Permission denied: ...` | Error card with macOS settings guidance | `playGamingBuzzer()` | Hidden (`none`) |
| **Network failure / crash** | N/A | N/A | N/A | `❌ Scan Error: Failed to communicate ...` | Error card: `Directory Access / Scan Failed` | `playGamingBuzzer()` | Hidden (`none`) |

---

## 5. Verification Checklist for Worker

1. **Verify Backend Error Status Code**:
   - `res = client.post("/api/scan/request", json={"folder_path": "/fake/nonexistent/dir"})`
   - Assert `res.status_code == 400`
   - Assert `res.get_json()["status"] == "error"`
   - Assert `"error"` in `res.get_json()`
2. **Verify Backend Valid Scan Unchanged**:
   - `res = client.post("/api/scan/request", json={"folder_path": "tests"})`
   - Assert `res.status_code == 200`
   - Assert `res.get_json()["status"] == "completed"`
   - Assert `res.get_json()["files_found"] > 0`
3. **Verify Existing Tests**:
   - Run `python3 -m unittest discover -s tests -p "test_*.py" -v`
   - All 503 baseline tests must continue to pass with 0 regressions.
4. **Verify UI Error Rendering**:
   - Scan invalid path in browser:
     - Banner turns red with `❌ Scan Error: ...`
     - `#scanned-files-container` displays the error card
     - `#btn-revoke-scan` remains hidden
     - Harsh buzzer sound plays instead of ding
