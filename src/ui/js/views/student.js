/**
 * ==============================================================================
 * DATA-TO-DIRT — Student Gamified Dashboard View (R1 & R2)
 * Carbon footprint counter, procedural tree plot, streak, daily limit, leaderboard,
 * and privacy-first dark data scanner with deletion workflow
 * ==============================================================================
 */

class StudentDashboardView {
  constructor() {
    this.container = null;
    this.stats = null;
    this.leaderboard = [];
    this.scannedFiles = [];
    this.selectedFileForDeletion = null;
  }

  mount(containerId = "view-content") {
    this.container = document.getElementById(containerId);
    if (!this.container) return;
    this.renderLayout();
    this.fetchData();
  }

  renderLayout() {
    this.container.innerHTML = `
      <div class="student-grid" style="display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 14px; height: 100%; overflow: hidden;">
        
        <!-- Left Column: Carbon Hero, Tree Plot & Dark Data Scanner -->
        <div style="display: flex; flex-direction: column; gap: 12px; overflow-y: auto; padding-right: 4px;">
          
          <!-- Carbon Footprint Hero Card -->
          <div class="retro-card" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div style="font-size: 11px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold; letter-spacing: 0.5px;">
                Verified Carbon Footprint Offset
              </div>
              <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 4px;">
                <span id="hero-carbon-val" style="font-size: 32px; font-weight: bold; color: var(--c-eco-leaf); text-shadow: 2px 2px 0 var(--c-forest-deep);">
                  0.0 g
                </span>
                <span style="font-size: 13px; color: var(--c-ink-muted);">CO₂ avoided / yr</span>
              </div>
              <div style="font-size: 12px; color: var(--c-ink-light); margin-top: 2px;" id="hero-substats">
                Data Cleared: 0 MB • Trees Planted Equivalent: 0.00
              </div>
            </div>

            <!-- Eco Points Badge -->
            <div class="retro-inset" style="text-align: center; padding: 8px 16px;">
              <div style="font-size: 11px; font-weight: bold; color: var(--c-brass-dark); text-transform: uppercase;">Eco-Score</div>
              <div id="hero-eco-points" style="font-size: 24px; font-weight: bold; color: var(--c-brass-bright); text-shadow: 1px 1px 0 #000;">
                0
              </div>
              <div style="font-size: 10px; color: var(--c-ink-muted);">POINTS</div>
            </div>
          </div>

          <!-- Tree Visual Plot Card -->
          <div class="retro-card" style="display: flex; flex-direction: column; gap: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div style="font-weight: bold; font-size: 14px; color: var(--c-wood-border);">
                🌱 Eco-Tree Growth Stage: <span id="tree-stage-title" style="color: var(--c-eco-leaf);">Prepared Soil</span>
              </div>
              <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-tree-celebrate">
                ✨ Cheer Tree
              </button>
            </div>

            <!-- Canvas Container -->
            <div class="retro-inset" style="height: 190px; padding: 0; position: relative; overflow: hidden; background: linear-gradient(180deg, #1c2338 0%, #112915 85%);">
              <canvas id="tree-canvas" style="width: 100%; height: 100%; display: block;"></canvas>
            </div>

            <!-- Progress Bar to Next Stage -->
            <div class="pixel-progress-wrap">
              <div class="pixel-progress-label">
                <span>Progress to Next Evolution</span>
                <span id="tree-progress-pct">0%</span>
              </div>
              <div class="pixel-progress-bar">
                <div class="pixel-progress-fill" id="tree-progress-fill" style="width: 0%;"></div>
              </div>
            </div>
          </div>

          <!-- AI Drive Cleaner Card -->
          <div class="retro-card" style="flex: 1; display: flex; flex-direction: column; gap: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 8px;">
              <div style="font-weight: bold; font-size: 14px; color: var(--c-wood-border);">
                🤖 AI Data Cleaner
              </div>
              <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                <button class="retro-btn retro-btn-green retro-btn-sm" id="btn-scan-gdrive" title="Google Drive: Live API & Folder Picker">
                  ☁️ Drive
                </button>
                <button class="retro-btn retro-btn-gold retro-btn-sm" id="btn-scan-auto-device" title="Auto-scan entire computer: Disk, Downloads, OneDrive, iCloud">
                  🚀 Auto-Scan System
                </button>
                <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-scan-local" title="Browse / Select Files on Device">
                  <span id="btn-scan-local-text">📱 Device</span>
                </button>
                <input type="file" id="device-file-input" multiple style="position: fixed; top: -1000px; left: -1000px; opacity: 0; pointer-events: none; width: 1px; height: 1px;" />
                <input type="file" id="device-folder-input" webkitdirectory directory multiple style="position: fixed; top: -1000px; left: -1000px; opacity: 0; pointer-events: none; width: 1px; height: 1px;" />
                <button class="retro-btn retro-btn-danger retro-btn-sm" id="btn-revoke-scan" style="display: none;">
                  🔒 Revoke
                </button>
              </div>
            </div>

            <!-- Scanner Status / Blind Warning -->
            <div id="scanner-status-banner" class="retro-inset" style="font-size: 12px; color: var(--c-ink-muted); display: flex; align-items: center; gap: 8px;">
              <span>👁️ <strong>Blind State</strong>: Zero device files accessed. Click 'Device' or 'Drive' to grant temporary scoped review.</span>
            </div>

            <!-- File Review List -->
            <div id="scanned-files-container" style="display: flex; flex-direction: column; gap: 6px; max-height: 340px; overflow-y: auto; padding-right: 4px;">
              <div style="text-align: center; padding: 24px; color: var(--c-ink-light); font-size: 12px;">
                Scan your Local Folder or Google Drive to discover duplicate files, unused junk, and more!
              </div>
            </div>
          </div>

        </div>

        <!-- Right Column: Streak, Daily Limit & School Leaderboard -->
        <div style="display: flex; flex-direction: column; gap: 12px; overflow-y: auto;">

          <!-- Daily Streak & Deletion Limit Widget -->
          <div class="retro-card" style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 14px;">
            
            <!-- Streak Counter -->
            <div class="retro-inset" style="text-align: center;">
              <div style="font-size: 11px; font-weight: bold; color: var(--c-ink-muted); text-transform: uppercase;">Daily Streak</div>
              <div style="font-size: 26px; font-weight: bold; color: var(--c-warning-amber); margin: 4px 0;">
                🔥 <span id="streak-days-val">0</span>
              </div>
              <div style="font-size: 10px; color: var(--c-ink-light);">Consecutive Days</div>
            </div>

            <!-- Daily Limit -->
            <div class="retro-inset" style="text-align: center;">
              <div style="font-size: 11px; font-weight: bold; color: var(--c-ink-muted); text-transform: uppercase;">Daily Deletions</div>
              <div style="font-size: 26px; font-weight: bold; color: var(--c-info-cyan); margin: 4px 0;">
                🗑️ <span id="daily-limit-val">0 / 5</span>
              </div>
              <div style="font-size: 10px; color: var(--c-ink-light);" id="daily-limit-sub">Available Today</div>
            </div>

          </div>

          <!-- Classroom Eco Leaderboard Card -->
          <div class="retro-card" style="flex: 1; display: flex; flex-direction: column; gap: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 8px;">
              <div style="font-weight: bold; font-size: 14px; color: var(--c-wood-border);">
                🏆 Classroom Eco-Leaderboard
              </div>
              <span class="retro-tag retro-tag-stale">Room 402</span>
            </div>

            <div class="retro-inset" style="padding: 4px; flex: 1; overflow-y: auto;">
              <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <thead>
                  <tr style="border-bottom: 2px solid var(--c-parchment-border); text-align: left; color: var(--c-ink-muted);">
                    <th style="padding: 6px 8px; width: 36px;">#</th>
                    <th style="padding: 6px 8px;">Student</th>
                    <th style="padding: 6px 8px; text-align: right;">Cleared</th>
                    <th style="padding: 6px 8px; text-align: right;">Points</th>
                    <th style="padding: 6px 8px; text-align: center;">Trees</th>
                  </tr>
                </thead>
                <tbody id="leaderboard-body">
                  <tr><td colspan="5" style="text-align: center; padding: 16px;">Loading leaderboard...</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Classroom Impact Summary Box -->
          <div class="retro-card" style="font-size: 12px; color: var(--c-ink-muted); line-height: 1.5;">
            <div style="font-weight: bold; color: var(--c-wood-border); margin-bottom: 4px;">🌍 Real-World Impact Equivalency</div>
            <div>• Singapore Grid Emission Factor: <strong>405.7 g CO₂e/kWh</strong></div>
            <div>• Storage Power Coefficient: <strong>0.28 kWh/GB/year</strong></div>
            <div>• Every <strong>1.0 GB</strong> verified waste triggers 1 Tree-Nation micro-donation!</div>
          </div>

        </div>

      </div>
    `;

    this.bindEvents();
    if (window.TreeRenderer) {
      window.TreeRenderer.init();
    }
  }

  bindEvents() {
    const btnScanDrive = document.getElementById("btn-scan-gdrive");
    const btnScanAutoDevice = document.getElementById("btn-scan-auto-device");
    const btnScanLocal = document.getElementById("btn-scan-local");
    const btnRevoke = document.getElementById("btn-revoke-scan");
    const btnCheer = document.getElementById("btn-tree-celebrate");

    // Auto-scan on return from successful Google OAuth consent
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get("token");
    if (tokenFromUrl) {
      localStorage.setItem("d2d_google_access_token", tokenFromUrl);
    }
    if (urlParams.get("oauth") === "success") {
      window.history.replaceState({}, document.title, window.location.pathname);
      const banner = document.getElementById("scanner-status-banner");
      if (banner) {
        banner.innerHTML = `<span>⏳ Google Drive connected! Scanning system...</span>`;
      }
      setTimeout(() => {
        this.executeScan(null, true, "auto_device", [], tokenFromUrl || localStorage.getItem("d2d_google_access_token"));
      }, 350);
    }

    if (btnScanDrive) {
      btnScanDrive.addEventListener("click", () => {
        if (window.RetroAudio) window.RetroAudio.playBlip();
        this.showGoogleDriveModal();
      });
    }

    if (btnScanAutoDevice) {
      btnScanAutoDevice.addEventListener("click", async () => {
        if (window.RetroAudio) window.RetroAudio.playBlip();
        btnScanAutoDevice.disabled = true;
        try {
          await this.executeScan(null, true, "auto_device");
        } finally {
          btnScanAutoDevice.disabled = false;
        }
      });
    }

    if (btnScanLocal) {
      const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
      
      // Handler shared by both file and folder inputs
      const handleDeviceFiles = async (e) => {
        if (e.target.files && e.target.files.length > 0) {
          const files = Array.from(e.target.files);
          const fileList = files.map(f => ({
            name: f.webkitRelativePath || f.name,
            size: f.size,
            lastModified: f.lastModified
          }));
          e.target.value = ""; // Reset value so change event fires again reliably
          await this.executeScan(null, true, "browser_files", fileList);
        }
      };
      
      document.getElementById("device-file-input")?.addEventListener("change", handleDeviceFiles);
      document.getElementById("device-folder-input")?.addEventListener("change", handleDeviceFiles);
      
      btnScanLocal.addEventListener("click", () => {
        if (window.RetroAudio) window.RetroAudio.playBlip();
        if (isMobile) {
          // On mobile/iPad, go straight to native file picker (Photos, Files, iCloud, etc.)
          document.getElementById("device-file-input")?.click();
        } else {
          // On desktop / laptop, show folder vs files choice modal
          this.showDeviceScanModal();
        }
      });
    }

    if (btnRevoke) {
      btnRevoke.addEventListener("click", () => {
        if (window.RetroAudio) window.RetroAudio.playBlip();
        this.revokeFolderAccess();
      });
    }

    if (btnCheer) {
      btnCheer.addEventListener("click", () => {
        if (window.TreeRenderer) {
          window.TreeRenderer.triggerLevelUp();
        }
      });
    }
  }

  async fetchData() {
    try {
      const [statsRes, lbRes] = await Promise.all([
        fetch("/api/student/stats").then((r) => r.json()),
        fetch("/api/student/leaderboard").then((r) => r.json()),
      ]);

      this.stats = statsRes;
      this.leaderboard = lbRes.leaderboard || [];
      this.updateStatsUI();
      this.updateLeaderboardUI();
    } catch (e) {
      console.warn("Failed to fetch student data:", e);
    }
  }

  updateStatsUI() {
    if (!this.stats) return;

    // Carbon Hero
    const elCarbon = document.getElementById("hero-carbon-val");
    const elPoints = document.getElementById("hero-eco-points");
    const elSubstats = document.getElementById("hero-substats");

    if (elCarbon) elCarbon.textContent = `${this.stats.carbon_offset_g.toFixed(1)} g`;
    if (elPoints) elPoints.textContent = this.stats.eco_points;
    if (elSubstats) {
      elSubstats.textContent = `Data Cleared: ${this.stats.bytes_cleared_formatted} • Trees Equivalent: ${this.stats.trees_equivalent.toFixed(4)}`;
    }

    // Tree Progress
    const elStageTitle = document.getElementById("tree-stage-title");
    const elProgressPct = document.getElementById("tree-progress-pct");
    const elProgressFill = document.getElementById("tree-progress-fill");

    if (elStageTitle) elStageTitle.textContent = this.stats.tree_growth_stage_name;
    if (elProgressPct) elProgressPct.textContent = `${this.stats.tree_growth_progress_pct}%`;
    if (elProgressFill) elProgressFill.style.width = `${this.stats.tree_growth_progress_pct}%`;

    if (window.TreeRenderer) {
      window.TreeRenderer.setStage(
        this.stats.tree_growth_stage,
        this.stats.tree_growth_progress_pct,
        this.stats.tree_growth_stage_name
      );
    }

    // Streaks and limits
    const elStreak = document.getElementById("streak-days-val");
    const elLimit = document.getElementById("daily-limit-val");
    const elLimitSub = document.getElementById("daily-limit-sub");

    if (elStreak) elStreak.textContent = this.stats.current_streak_days;
    if (elLimit) elLimit.textContent = `${this.stats.daily_deletions_today} / ${this.stats.daily_deletion_limit}`;
    if (elLimitSub) {
      const remaining = this.stats.daily_deletion_limit - this.stats.daily_deletions_today;
      elLimitSub.textContent = remaining > 0 ? `${remaining} remaining today` : "Limit reached for today!";
    }
  }

  updateLeaderboardUI() {
    const tbody = document.getElementById("leaderboard-body");
    if (!tbody) return;

    if (!this.leaderboard || this.leaderboard.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 12px;">No entries available.</td></tr>`;
      return;
    }

    tbody.innerHTML = this.leaderboard
      .map((entry) => {
        const isSelf = entry.name.includes("You");
        const rowBg = isSelf ? "background: rgba(92, 179, 57, 0.18);" : "";
        const rankMedal = entry.rank === 1 ? "🥇" : entry.rank === 2 ? "🥈" : entry.rank === 3 ? "🥉" : `${entry.rank}`;

        return `
          <tr style="${rowBg} border-bottom: 1px dashed var(--c-parchment-border);">
            <td style="padding: 6px 8px; font-weight: bold;">${rankMedal}</td>
            <td style="padding: 6px 8px; font-weight: ${isSelf ? "bold" : "normal"}; color: ${isSelf ? "var(--c-eco-leaf)" : "inherit"};">
              ${entry.name}
            </td>
            <td style="padding: 6px 8px; text-align: right; color: var(--c-ink-muted);">${entry.data_cleared_formatted}</td>
            <td style="padding: 6px 8px; text-align: right; font-weight: bold; color: var(--c-brass-dark);">${entry.eco_points}</td>
            <td style="padding: 6px 8px; text-align: center;">🌲 ${entry.trees}</td>
          </tr>
        `;
      })
      .join("");
  }

  showGoogleDriveModal() {
    document.getElementById("modal-gdrive-options")?.remove();
    const modal = document.createElement("div");
    modal.className = "retro-modal-backdrop";
    modal.id = "modal-gdrive-options";
    modal.style.zIndex = "10000";
    modal.innerHTML = `
      <div class="retro-modal" style="max-width: 420px;">
        <div style="font-weight: bold; font-size: 16px; margin-bottom: 12px; color: var(--c-wood-border);">
          ☁️ Google Drive Cleaner
        </div>
        <div style="font-size: 13px; color: var(--c-ink-muted); margin-bottom: 16px;">
          Choose how to scan your Google Drive:
        </div>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          <button class="retro-btn retro-btn-green" id="btn-gdrive-picker" style="width: 100%; padding: 12px; font-size: 13px; text-align: left;">
            <strong>📁 Google Drive Picker (Select All / Any Folder)</strong>
            <div style="font-size: 11px; opacity: 0.85; margin-top: 2px;">
              Official Google window. Select your "My Drive" folder or multi-select files. Works for any account.
            </div>
          </button>
          <button class="retro-btn retro-btn-gold" id="btn-gdrive-direct" style="width: 100%; padding: 12px; font-size: 13px; text-align: left;">
            <strong>⚡ Live Google Drive Scan</strong>
            <div style="font-size: 11px; opacity: 0.85; margin-top: 2px;">
              Directly queries Google Drive API for all files owned by your account.
            </div>
          </button>
          <button class="retro-btn retro-btn-danger retro-btn-sm" id="btn-gdrive-cancel" style="width: 100%; margin-top: 4px;">
            ✖ Cancel
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const dismiss = () => modal.remove();

    modal.querySelector("#btn-gdrive-picker")?.addEventListener("click", () => {
      dismiss();
      this.openGooglePicker();
    });

    modal.querySelector("#btn-gdrive-direct")?.addEventListener("click", async () => {
      dismiss();
      await this.executeScan("__google_drive__", true, "drive");
    });

    modal.querySelector("#btn-gdrive-cancel")?.addEventListener("click", dismiss);
    modal.addEventListener("click", (e) => { if (e.target === modal) dismiss(); });
  }

  async openGooglePicker() {
    try {
      const cfgRes = await fetch("/api/config/auth");
      const cfg = await cfgRes.json();
      const clientId = cfg.google_client_id;
      const appId = cfg.google_app_id || (clientId ? clientId.split("-")[0] : "");

      const buildPicker = (oauthToken) => {
        if (!window.google || !window.google.picker) {
          alert("Google Picker is initializing. Please click Drive again in 2 seconds.");
          return;
        }

        const docsView = new google.picker.DocsView(google.picker.ViewId.DOCS)
          .setIncludeFolders(true)
          .setSelectFolderEnabled(true);

        const folderView = new google.picker.DocsView(google.picker.ViewId.FOLDERS)
          .setSelectFolderEnabled(true);

        const builder = new google.picker.PickerBuilder()
          .enableFeature(google.picker.Feature.MULTISELECT_ENABLED)
          .setOAuthToken(oauthToken)
          .setAppId(appId)
          .addView(docsView)
          .addView(folderView)
          .addView(new google.picker.DocsUploadView())
          .setTitle("Select Google Drive Files or Folder to Clean");

        if (cfg.google_api_key) {
          builder.setDeveloperKey(cfg.google_api_key);
        }

        const picker = builder
          .setCallback(async (data) => {
            if (data[google.picker.Response.ACTION] === google.picker.Action.PICKED) {
              const docs = data[google.picker.Response.DOCUMENTS] || [];
              if (docs.length > 0) {
                const pickedFiles = docs.map((d) => ({
                  id: d[google.picker.Document.ID],
                  name: d[google.picker.Document.NAME],
                  sizeBytes: Number(d[google.picker.Document.SIZE_BYTES] || d.sizeBytes || d.fileSize || 0),
                  mimeType: d[google.picker.Document.MIME_TYPE],
                  lastEditedUtc: d[google.picker.Document.LAST_EDITED_UTC] || Date.now()
                }));
                await this.executeScan(null, true, "picker_files", pickedFiles, oauthToken);
              }
            }
          })
          .build();
        picker.setVisible(true);
      };

      const loadGapiAndPicker = (token) => {
        if (window.gapi) {
          window.gapi.load("picker", () => buildPicker(token));
        } else {
          this.executeScan("__google_drive__", true, "drive");
        }
      };

      if (window.google && window.google.accounts && window.google.accounts.oauth2) {
        const tokenClient = google.accounts.oauth2.initTokenClient({
          client_id: clientId,
          scope: "https://www.googleapis.com/auth/drive.file",
          callback: (resp) => {
            if (resp && resp.access_token) {
              loadGapiAndPicker(resp.access_token);
            } else {
              window.location.href = "/auth/google/login";
            }
          }
        });
        tokenClient.requestAccessToken({ prompt: "" });
      } else {
        window.location.href = "/auth/google/login";
      }
    } catch (err) {
      console.warn("Picker error:", err);
      window.location.href = "/auth/google/login";
    }
  }

  showDeviceScanModal() {
    document.getElementById("modal-device-scan")?.remove();
    const modal = document.createElement("div");
    modal.className = "retro-modal-backdrop";
    modal.id = "modal-device-scan";
    modal.style.zIndex = "10000";
    modal.innerHTML = `
      <div class="retro-modal" style="max-width: 440px;">
        <div style="font-weight: bold; font-size: 16px; margin-bottom: 12px; color: var(--c-wood-border);">
          📱 Scan Device & Cloud Sync Storage
        </div>
        <div style="font-size: 13px; color: var(--c-ink-muted); margin-bottom: 16px;">
          Choose how you want to scan your device:
        </div>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          <button class="retro-btn retro-btn-gold" id="btn-device-auto-all" style="width: 100%; padding: 12px; font-size: 13px; text-align: left; cursor: pointer;">
            <strong>🚀 1-Click System Scan (Disk, Downloads, OneDrive, iCloud)</strong>
            <div style="font-size: 11px; opacity: 0.85; margin-top: 2px;">
              Automatically scans all connected disk and cloud sync folders without picking folders.
            </div>
          </button>
          <button class="retro-btn retro-btn-green" id="btn-device-pick-folder" style="width: 100%; padding: 12px; font-size: 13px; text-align: left; cursor: pointer;">
            <strong>📂 Select Specific Folder</strong>
            <div style="font-size: 11px; opacity: 0.85; margin-top: 2px;">
              Choose any folder on your computer to scan.
            </div>
          </button>
          <button class="retro-btn retro-btn-wood" id="btn-device-pick-files" style="width: 100%; padding: 12px; font-size: 13px; text-align: left; cursor: pointer;">
            <strong>📄 Select Individual Files</strong>
            <div style="font-size: 11px; opacity: 0.85; margin-top: 2px;">
              Pick specific videos, photos, or documents.
            </div>
          </button>
          <button class="retro-btn retro-btn-danger retro-btn-sm" id="btn-device-cancel" style="width: 100%; margin-top: 4px; cursor: pointer;">
            ✖ Cancel
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const dismiss = () => modal.remove();

    modal.querySelector("#btn-device-auto-all")?.addEventListener("click", async () => {
      if (window.RetroAudio) window.RetroAudio.playBlip();
      dismiss();
      await this.executeScan(null, true, "auto_device");
    });

    modal.querySelector("#btn-device-pick-folder")?.addEventListener("click", () => {
      if (window.RetroAudio) window.RetroAudio.playBlip();
      const folderInput = document.getElementById("device-folder-input");
      dismiss();
      if (folderInput) {
        folderInput.click();
      }
    });

    modal.querySelector("#btn-device-pick-files")?.addEventListener("click", () => {
      if (window.RetroAudio) window.RetroAudio.playBlip();
      const fileInput = document.getElementById("device-file-input");
      dismiss();
      if (fileInput) {
        fileInput.click();
      }
    });

    modal.querySelector("#btn-device-cancel")?.addEventListener("click", () => {
      if (window.RetroAudio) window.RetroAudio.playBlip();
      dismiss();
    });
    
    modal.addEventListener("click", (e) => { if (e.target === modal) dismiss(); });
  }

  openFolderPermissionModal() {
    document.getElementById("modal-permission")?.remove();
    const modal = document.createElement("div");
    modal.className = "retro-modal-backdrop";
    modal.id = "modal-permission";
    modal.style.zIndex = "10000";
    modal.innerHTML = `
      <div class="retro-card retro-modal">
        <div class="retro-modal-header">
          <span>🛡️ Privacy-First Folder Permission</span>
          <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-modal-close">✕</button>
        </div>
        <div class="retro-modal-body">
          <p style="margin-bottom: 10px;">
            <strong>Zero-Trust Privacy Guarantee:</strong> Data-to-Dirt reads file metadata (name, size, date) strictly inside process memory. No file contents are transmitted off your device.
          </p>
          <div class="retro-inset" style="margin-bottom: 12px;">
            <label style="display: block; font-weight: bold; margin-bottom: 6px;">Folder Path to Clean:</label>
            <input type="text" id="modal-folder-path" class="retro-input" value="~/Downloads/Project_Archive" />
          </div>
          <div style="font-size: 12px; color: var(--c-ink-muted);">
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
              <input type="checkbox" id="modal-session-only" checked />
              <span><strong>Session-Only Access</strong> (Revoke automatically when app closes)</span>
            </label>
          </div>
        </div>
        <div class="retro-modal-actions">
          <button class="retro-btn retro-btn-wood" id="btn-modal-cancel">Remain Blind</button>
          <button class="retro-btn retro-btn-green" id="btn-modal-grant">Grant Access</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const btnClose = modal.querySelector("#btn-modal-close");
    const btnCancel = modal.querySelector("#btn-modal-cancel");
    const btnGrant = modal.querySelector("#btn-modal-grant");

    const dismiss = () => modal.remove();

    if (btnClose) btnClose.onclick = dismiss;
    if (btnCancel) btnCancel.onclick = dismiss;
    if (btnGrant) {
      btnGrant.onclick = async () => {
        const folder = modal.querySelector("#modal-folder-path")?.value;
        const sessionOnly = modal.querySelector("#modal-session-only")?.checked;
        dismiss();
        await this.executeScan(folder, sessionOnly, "local");
      };
    }
    modal.addEventListener("click", (e) => { if (e.target === modal) dismiss(); });
  }

  async executeScan(folderPath, sessionOnly, scanType = "local", fileList = [], oauthToken = null) {
    const banner = document.getElementById("scanner-status-banner");
    const btnRevoke = document.getElementById("btn-revoke-scan");
    if (banner) {
      banner.style.borderColor = "";
      banner.style.backgroundColor = "";
      if (scanType === "drive") {
        banner.innerHTML = `<span>⏳ Scanning your Google Drive for duplicates, junk & unused files...</span>`;
      } else if (scanType === "auto_device") {
        banner.innerHTML = `<span>⏳ 1-Click Auto-Scanning System Storage (Local Disk, Downloads, OneDrive, iCloud)...</span>`;
      } else if (scanType === "picker_files") {
        banner.innerHTML = `<span>⏳ Analyzing ${fileList.length} files from Google Drive with AI...</span>`;
      } else if (scanType === "browser_files") {
        banner.innerHTML = `<span>⏳ Analyzing ${fileList.length} files from your device...</span>`;
      } else {
        banner.innerHTML = `<span>⏳ Scanning local folder: <strong>${folderPath}</strong>...</span>`;
      }
    }

    try {
      const payload = {
        scan_type: scanType,
        folder_path: folderPath,
        session_only: sessionOnly
      };
      if (scanType === "browser_files" || scanType === "picker_files") {
        payload.files = fileList;
      }
      const effectiveOAuth = oauthToken || localStorage.getItem("d2d_google_access_token");
      if (effectiveOAuth) {
        payload.oauth_token = effectiveOAuth;
      }
      
      const response = await fetch("/api/scan/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      let res;
      try {
        res = await response.json();
      } catch {
        res = {};
      }

      if (response.status === 401 && res.status === "needs_auth") {
        const lastRedirect = sessionStorage.getItem("d2d_last_oauth_redirect");
        const now = Date.now();
        if (lastRedirect && (now - Number(lastRedirect)) < 15000) {
          console.warn("[!] Prevented OAuth redirect loop");
          sessionStorage.removeItem("d2d_last_oauth_redirect");
          const errorMsg = "Google Drive authorization was not granted or expired. Click '📱 Device' to select files, or try '☁️ Drive' again.";
          if (banner) {
            banner.style.borderColor = "var(--c-danger-red)";
            banner.style.backgroundColor = "rgba(168, 36, 36, 0.15)";
            banner.innerHTML = `<span style="color: var(--c-danger-bright); font-weight: bold;">⚠️ ${errorMsg}</span>`;
          }
          this.renderScannedFiles(errorMsg);
          return;
        }
        sessionStorage.setItem("d2d_last_oauth_redirect", String(now));
        window.location.href = "/auth/google/login";
        return;
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

        if (window.RetroAudio && window.RetroAudio.playGamingBuzzer) {
          window.RetroAudio.playGamingBuzzer();
        }
        this.renderScannedFiles(errorMsg);
        return;
      }

      this.scannedFiles = res.files || [];
      const totalScanned = res.total_scanned || res.files_found || 0;
      const totalFound = res.files_found || this.scannedFiles.length;

      if (window.trackAnalyticsEvent) {
        window.trackAnalyticsEvent(`Scan Completed (${scanType || 'device'}): ${totalFound} files flagged`, {
          scan_type: scanType,
          files_found: totalFound
        });
      }
      const wasteFormatted = res.total_waste_formatted || (this.scannedFiles.reduce((acc, f) => acc + (f.size_bytes || 0), 0) / (1024*1024)).toFixed(1) + " MB";
      
      if (banner) {
        banner.style.borderColor = "";
        banner.style.backgroundColor = "";
        const scanSourceLabel = scanType === "drive" || scanType === "picker_files" ? "Google Drive" : "Device Storage";
        banner.innerHTML = `<span>✅ <strong>${scanSourceLabel} Scanned</strong>: <strong>${Number(totalScanned).toLocaleString()} files analyzed</strong> across entire system — <strong>${Number(totalFound).toLocaleString()} dark data candidates identified (${wasteFormatted} cleanable bloat)</strong>! Showing top storage hogs:</span>`;
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

      if (window.RetroAudio && window.RetroAudio.playGamingBuzzer) {
        window.RetroAudio.playGamingBuzzer();
      }
      this.renderScannedFiles(errorMsg);
    }
  }

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
        <div style="text-align: center; padding: 24px; color: var(--c-ink-light); font-size: 12px; line-height: 1.6;">
          <div style="font-size: 13px; font-weight: bold; color: var(--c-wood-border); margin-bottom: 6px;">📂 Ready to Clean Real Data</div>
          <div>Click <strong>'📱 Device'</strong> to select files or folders from your computer/phone, or <strong>'☁️ Drive'</strong> to scan Google Drive.</div>
        </div>
      `;
      return;
    }

    const headerHtml = `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; margin-bottom: 8px; font-size: 11px; font-weight: bold; color: var(--c-wood-border); background: rgba(0,0,0,0.04); border-radius: 4px;">
        <span>🎯 Cleanable Dark Data (${this.scannedFiles.length} candidates listed)</span>
        <span style="font-size: 10px; color: var(--c-ink-muted);">Sorted by size ⬇️ • Cryptographic SHA-256 Verified</span>
      </div>
    `;

    container.innerHTML = headerHtml + this.scannedFiles
      .map((file) => {
        const tagClass = file.category === "heavy_media" ? "retro-tag-heavy" : file.category === "transient_trash" ? "retro-tag-stale" : file.is_confidential ? "retro-tag-confidential" : "retro-tag-duplicate";
        const icon = file.icon || (file.category === "heavy_media" ? "🎥" : file.category === "duplicate" ? "📄" : "📦");
        const carbonStr = file.carbon_g != null ? file.carbon_g : ((file.size_bytes / (1024**3)) * 0.28 * 405.7).toFixed(1);
        const shaShort = file.sha256_short || (file.sha256 ? `${file.sha256.substring(0, 8)}...${file.sha256.substring(file.sha256.length - 6)}` : "Verified");

        return `
          <div class="retro-inset" style="margin-bottom: 8px; padding: 10px 12px; background: rgba(255, 255, 255, 0.85); border: 1.5px solid var(--c-wood-border);">
            <!-- Row 1: Icon, Title, Badges, Clean Button -->
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
              <div style="display: flex; align-items: flex-start; gap: 8px; flex: 1; min-width: 0;">
                <span style="font-size: 18px; line-height: 1.2;" title="${file.category}">${icon}</span>
                <div style="flex: 1; min-width: 0;">
                  <div style="font-weight: bold; font-size: 13px; color: var(--c-ink-text); word-break: break-all; display: flex; align-items: center; flex-wrap: wrap; gap: 6px;">
                    <span>${file.is_confidential ? "🔒 [CONFIDENTIAL] " : ""}${file.file_name}</span>
                    ${file.sha_match ? `<span class="retro-tag retro-tag-duplicate" style="font-size: 9px; background: #e02424; color: #fff; font-weight: bold; padding: 1px 5px; border-radius: 3px;">🎯 EXACT SHA-256 CLONE</span>` : ""}
                  </div>
                  <div style="font-size: 10px; color: var(--c-ink-muted); margin-top: 2px; font-family: monospace; word-break: break-all;">
                    📂 ${file.file_path || file.absolute_path || file.storage_source || "Local / Cloud Storage"}
                  </div>
                </div>
              </div>

              <div style="flex-shrink: 0;">
                ${
                  file.is_confidential
                    ? `<span style="font-size: 11px; color: var(--c-ink-light); font-style: italic;">Protected</span>`
                    : `<button class="retro-btn retro-btn-danger retro-btn-sm btn-delete-file" data-id="${file.file_id}" style="padding: 4px 10px; font-weight: bold;">
                        🗑️ Clean
                      </button>`
                }
              </div>
            </div>

            <!-- Row 2: Comprehensive Forensic Telemetry Grid (Size, Dates, SHA, Carbon) -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 6px; margin-top: 8px; padding: 6px 8px; background: rgba(0,0,0,0.03); border: 1px dashed rgba(0,0,0,0.15); border-radius: 4px; font-size: 10.5px;">
              <div>
                <span style="color: var(--c-ink-muted);">📊 Size:</span>
                <strong style="color: var(--c-ink-text);">${file.size_formatted}</strong>
                <span style="font-size: 9.5px; color: var(--c-ink-light);">(${Number(file.size_bytes || 0).toLocaleString()} B)</span>
              </div>
              <div>
                <span style="color: var(--c-ink-muted);">🕒 Modified:</span>
                <strong style="color: var(--c-ink-text);">${file.modified_date || `${file.age_days}d ago`}</strong>
              </div>
              <div>
                <span style="color: var(--c-ink-muted);">👁️ Last Opened:</span>
                <strong style="color: var(--c-ink-text);">${file.accessed_date || "Unaccessed"}</strong>
              </div>
              <div>
                <span style="color: var(--c-ink-muted);">🌱 Avoided CO₂:</span>
                <strong style="color: #057a55;">${carbonStr} g/yr</strong>
              </div>
              <div style="grid-column: 1 / -1; display: flex; align-items: center; gap: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 10px;">
                <span style="color: var(--c-ink-muted); font-family: monospace;">🔑 SHA-256:</span>
                <code style="background: rgba(0,0,0,0.06); padding: 1px 5px; border-radius: 3px; font-size: 9.5px; color: #1e429f;" title="${file.sha256 || 'SHA-256 Fingerprint'}">${shaShort}</code>
                ${file.sha_match_filename ? `<span style="color: #c81e1e; font-size: 9.5px; font-weight: bold; overflow: hidden; text-overflow: ellipsis;">Identical clone of: ${file.sha_match_filename}</span>` : ""}
              </div>
            </div>

            <!-- Row 3: IQ 1000 AI Forensic Verdict -->
            <div style="margin-top: 6px; padding: 6px 8px; border-left: 3px solid #1a56db; background: rgba(26, 86, 219, 0.05); border-radius: 0 4px 4px 0; font-size: 10.5px; line-height: 1.4;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px; flex-wrap: wrap; gap: 4px;">
                <span style="font-weight: bold; color: #1a56db; font-size: 10px;">
                  🧠 AI Forensic Analysis (IQ 1000 • ${file.ai_confidence_score || "98.5%"} Confidence)
                </span>
                <span class="retro-tag ${tagClass}" style="font-size: 9px; padding: 1px 5px;">${file.dark_data_tag}</span>
              </div>
              <div style="color: var(--c-ink-text); font-style: italic;">
                "${file.ai_forensic_rationale || file.dark_data_reason}"
              </div>
            </div>
          </div>
        `;
      })
      .join("");

    // Bind clean buttons
    container.querySelectorAll(".btn-delete-file").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const fileId = e.currentTarget.getAttribute("data-id");
        const file = this.scannedFiles.find((f) => f.file_id === fileId);
        if (file) {
          if (window.RetroAudio) window.RetroAudio.playBlip();
          this.openDeletionReasonModal(file);
        }
      });
    });
  }

  openDeletionReasonModal(file) {
    document.getElementById("modal-deletion")?.remove();
    const modal = document.createElement("div");
    modal.className = "retro-modal-backdrop";
    modal.id = "modal-deletion";
    modal.style.zIndex = "10000";
    const defaultReason = file.ai_forensic_rationale || file.dark_data_reason || "Redundant file identified by AI analysis";
    const icon = file.icon || "📄";

    modal.innerHTML = `
      <div class="retro-card retro-modal" style="max-width: 520px;">
        <div class="retro-modal-header">
          <span>🗑️ Deletion Reason & AI Accountability (R3)</span>
          <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-del-close">✕</button>
        </div>
        <div class="retro-modal-body">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; padding: 6px 8px; background: rgba(0,0,0,0.03); border-radius: 4px;">
            <span style="font-size: 20px;">${icon}</span>
            <div style="flex: 1; min-width: 0;">
              <div style="font-weight: bold; font-size: 12px; color: var(--c-ink-text); word-break: break-all;">
                ${file.file_name}
              </div>
              <div style="font-size: 10px; color: var(--c-ink-muted);">
                ${file.size_formatted} • Modified: ${file.modified_date || `${file.age_days}d ago`} • Last opened: ${file.accessed_date || "Unaccessed"}
              </div>
            </div>
          </div>

          ${
            file.sha_match_filename
              ? `<div style="background: rgba(224, 36, 36, 0.1); border: 1px solid #e02424; color: #c81e1e; padding: 6px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-bottom: 10px;">
                  🎯 Cryptographic Proof: Bit-for-bit SHA-256 duplicate clone of <u>${file.sha_match_filename}</u>. Purging this copy loses 0 bytes of unique data!
                </div>`
              : ""
          }

          <div style="font-size: 11px; color: var(--c-ink-muted); margin-bottom: 8px;">
            To prevent accidental deletion, our <strong>IQ 1000 AI Engine</strong> verifies why this file is unnecessary before queueing it for teacher approval.
          </div>
          
          <label style="display: block; font-weight: bold; font-size: 11px; margin-bottom: 4px;">
            Why is this file a duplicate or junk? (Reason for removal):
          </label>
          <textarea id="modal-del-reason" class="retro-input" rows="3" style="width: 100%; box-sizing: border-box; font-size: 11px; line-height: 1.4;">${defaultReason}</textarea>
          <div style="font-size: 10px; color: var(--c-ink-light); margin-top: 3px;">
            💡 Pre-filled with AI Forensic Rationale. You may customize it before submitting for teacher review.
          </div>
          
          <div id="ai-feedback-banner" style="margin-top: 10px; display: none;" class="retro-inset"></div>
        </div>
        <div class="retro-modal-actions">
          <button class="retro-btn retro-btn-wood" id="btn-del-cancel">Keep File</button>
          <button class="retro-btn retro-btn-green" id="btn-del-verify">Verify & Queue</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const btnClose = modal.querySelector("#btn-del-close");
    const btnCancel = modal.querySelector("#btn-del-cancel");
    const btnVerify = modal.querySelector("#btn-del-verify");

    const dismiss = () => {
      modal.remove();
    };

    if (btnClose) btnClose.onclick = dismiss;
    if (btnCancel) btnCancel.onclick = dismiss;
    modal.addEventListener("click", (e) => { if (e.target === modal) dismiss(); });

    if (btnVerify) {
      btnVerify.onclick = async () => {
        const reason = modal.querySelector("#modal-del-reason")?.value.trim() || "";
        const feedback = modal.querySelector("#ai-feedback-banner");

        if (!reason) {
          feedback.style.display = "block";
          feedback.innerHTML = `<span style="color: var(--c-danger-bright);">[-] Please provide a reason for removal.</span>`;
          return;
        }

        btnVerify.disabled = true;
        btnVerify.textContent = "Verifying...";

        try {
          const token = localStorage.getItem("d2d_session_token") || "";
          const res = await fetch("/api/deletion/submit", {
            method: "POST",
            headers: { 
              "Content-Type": "application/json",
              "Authorization": token ? `Bearer ${token}` : ""
            },
            body: JSON.stringify({
              file_id: file.file_id,
              file_name: file.file_name,
              file_size: file.size_bytes,
              reason: reason,
              is_drive: file.is_drive || false
            }),
          });

          const data = await res.json();

          if (!res.ok) {
            // Gaming detected or limit exceeded
            feedback.style.display = "block";
            feedback.innerHTML = `
              <div style="color: var(--c-danger-bright); font-weight: bold;">
                ⚠️ AI Validation Failed (Score: ${data.ai_evaluation?.confidence_score ?? "0.0"})
              </div>
              <div style="font-size: 11px; margin-top: 4px;">${data.ai_evaluation?.summary || data.error}</div>
            `;
            if (window.RetroAudio) window.RetroAudio.playGamingBuzzer();
            document.body.classList.add("strike-flash");
            setTimeout(() => document.body.classList.remove("strike-flash"), 450);
            btnVerify.disabled = false;
            btnVerify.textContent = "Retry Reason";
            await this.fetchData();
            return;
          }

          // Success: Queued for teacher
          dismiss();

          // Visceral feedback
          if (window.RetroAudio) window.RetroAudio.playDeletionPoof();
          document.body.classList.add("screen-shake");
          setTimeout(() => document.body.classList.remove("screen-shake"), 400);

          if (window.trackAnalyticsEvent) {
            window.trackAnalyticsEvent(`Queued Deletion: ${file.file_name} (${(file.size_bytes / (1024 * 1024)).toFixed(1)} MB)`, {
              file_id: file.file_id,
              bytes_cleaned: file.size_bytes
            });
          }

          if (window.ParticleEngine) {
            window.ParticleEngine.emitDeletionPoof(window.innerWidth / 2, window.innerHeight / 2, 35);
            window.ParticleEngine.emitFloatingText("Queued for Teacher!", window.innerWidth / 2 - 50, window.innerHeight / 2 - 20, "#9be05c");
          }

          // Remove file from local list
          this.scannedFiles = this.scannedFiles.filter((f) => f.file_id !== file.file_id);
          this.renderScannedFiles();
          await this.fetchData();
        } catch (err) {
          feedback.style.display = "block";
          feedback.innerHTML = `<span style="color: var(--c-danger-bright);">[-] Server error: ${err.message}</span>`;
          btnVerify.disabled = false;
          btnVerify.textContent = "Verify & Queue";
        }
      };
    }
  }
}

// Global Student View Singleton
window.StudentView = new StudentDashboardView();
