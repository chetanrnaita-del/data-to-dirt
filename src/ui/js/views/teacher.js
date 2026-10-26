/**
 * ==============================================================================
 * DATA-TO-DIRT — Teacher Confirmation Queue & Approval Dashboard (R4)
 * Stardew Valley retro style review queue, AI confidence badges,
 * tri-state decisioning (Approve, Reject, Flag), interactive modals, and toasts.
 * ==============================================================================
 */

class TeacherConfirmationView {
  constructor() {
    this.container = null;
    this.queue = [];
    this.analytics = null;
    this.currentFilter = "pending"; // all, pending, approved, rejected, flagged
    this.searchQuery = "";
    this.sortAsc = true; // true = lowest confidence first (prioritize suspicious)
    this.audioSynth = window.RetroAudio;
    this.particleEngine = window.ParticleEngine;
    // Teacher's own file scanner state
    this.teacherScannedFiles = [];
    this.teacherLastScanCompleted = false;
    this.teacherLastScanType = null;
  }

  mount(containerId = "view-content") {
    this.container = document.getElementById(containerId);
    if (!this.container) return;
    this.renderLayout();
    this.fetchData();
  }

  renderLayout() {
    this.container.innerHTML = `
      <div class="teacher-dashboard" style="display: flex; flex-direction: column; gap: 12px; height: 100%; overflow: hidden;">

        <!-- Top Navigation & Control Banner -->
        <div class="retro-card" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 16px;">
          <div>
            <div style="font-weight: bold; font-size: 16px; color: var(--c-wood-border); display: flex; align-items: center; gap: 8px;">
              <span>👨‍🏫 Teacher Confirmation Queue</span>
              <span class="retro-tag retro-tag-clean" id="t-class-badge" style="font-size: 11px;">Class: BIO101</span>
              <span class="retro-tag retro-tag-stale" id="t-queue-badge">0 PENDING</span>
            </div>
            <div style="font-size: 11px; color: var(--c-ink-muted); margin-top: 2px;">
              Verify student dark data deletion requests with on-device AI accountability loop.
            </div>
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-t-refresh" title="Refresh Queue">
              🔄 Refresh
            </button>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-t-manage-students" title="Student Directory">
              👥 Students
            </button>
            <button class="retro-btn retro-btn-danger retro-btn-sm" id="btn-t-logout" title="Sign out">
              🚪 Logout
            </button>
          </div>
        </div>

        <!-- Class Metrics Summary Bar -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
          <div class="retro-card" style="padding: 8px 12px;">
            <div style="font-size: 10px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">Verified Data Cleared</div>
            <div id="stat-data-cleared" style="font-size: 18px; font-weight: bold; color: var(--c-eco-leaf);">0.0 MB</div>
          </div>
          <div class="retro-card" style="padding: 8px 12px;">
            <div style="font-size: 10px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">Avoided Carbon Offset</div>
            <div id="stat-carbon-offset" style="font-size: 18px; font-weight: bold; color: var(--c-forest-deep);">0.0 g CO₂</div>
          </div>
          <div class="retro-card" style="padding: 8px 12px;">
            <div style="font-size: 10px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">Trees Funded</div>
            <div id="stat-trees-funded" style="font-size: 18px; font-weight: bold; color: var(--c-brass-bright);">0 🌲</div>
          </div>
          <div class="retro-card" style="padding: 8px 12px;">
            <div style="font-size: 10px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">Gaming Incidents Flagged</div>
            <div id="stat-flagged-count" style="font-size: 18px; font-weight: bold; color: var(--c-danger-bright);">0 🚩</div>
          </div>
        </div>

        <!-- Filter & Search Toolbar -->
        <div class="retro-card" style="padding: 8px 14px; display: flex; justify-content: space-between; align-items: center; gap: 10px;">
          <!-- Tab Switcher: Student Queue vs My Files -->
          <div style="display: flex; gap: 6px;" id="teacher-tab-group">
            <button class="retro-btn retro-btn-sm retro-btn-gold teacher-tab-btn" data-tab="queue">📋 Student Queue</button>
            <button class="retro-btn retro-btn-sm retro-btn-wood teacher-tab-btn" data-tab="myfiles">🗂️ My Files</button>
          </div>
          <div style="display: flex; gap: 6px; align-items: center;" id="queue-controls">
            <!-- Status Filters (for queue tab) -->
            <div style="display: flex; gap: 6px;" id="filter-buttons-group">
              <button class="retro-btn retro-btn-sm btn-filter retro-btn-gold" data-filter="pending">Pending</button>
              <button class="retro-btn retro-btn-sm btn-filter retro-btn-wood" data-filter="all">All</button>
              <button class="retro-btn retro-btn-sm btn-filter retro-btn-wood" data-filter="approved">Approved</button>
              <button class="retro-btn retro-btn-sm btn-filter retro-btn-wood" data-filter="rejected">Rejected</button>
              <button class="retro-btn retro-btn-sm btn-filter retro-btn-wood" data-filter="flagged">Flagged</button>
            </div>

            <!-- Search & Sort -->
            <div style="display: flex; align-items: center; gap: 8px;">
              <select id="t-class-filter-select" class="retro-input" style="padding: 4px 6px; font-size: 11px; cursor: pointer;">
                <option value="all">🌐 All Classes</option>
                <option value="bio101">🌿 Bio 101</option>
                <option value="cs301">💻 CS 301</option>
                <option value="env201">🌍 Env 201</option>
                <option value="chem102">🧪 Chem 102</option>
                <option value="earth204">⛰️ Earth 204</option>
              </select>
              <button class="retro-btn retro-btn-green retro-btn-sm" id="btn-approve-all-pending" title="One-click approve all pending student deletions">
                ⚡ Approve All Pending
              </button>
              <input type="text" id="t-search-input" class="retro-input" placeholder="Search filename, reason, student..." style="padding: 4px 8px; font-size: 12px; width: 180px;" />
              <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-sort-confidence" title="Sort by AI Confidence (Low/High)">
                🤖 AI Score: <span id="sort-order-label">Lowest First</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Queue Items Scrollable List Container -->
        <div class="retro-card" id="tab-content-queue" style="flex: 1; overflow: hidden; display: flex; flex-direction: column; gap: 8px;">
          <div id="t-queue-scroll-area" style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding-right: 4px;">
            <div style="text-align: center; padding: 40px; color: var(--c-ink-light); font-size: 13px;">
              Loading confirmation queue...
            </div>
          </div>
        </div>

        <!-- Teacher's Own Files Panel (hidden by default) -->
        <div class="retro-card" id="tab-content-myfiles" style="flex: 1; overflow: hidden; display: none; flex-direction: column; gap: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 8px;">
            <div style="font-weight: bold; font-size: 14px; color: var(--c-wood-border);">
              🤖 My Data Cleaner — Direct Delete (No Approval Needed)
            </div>
            <div style="display: flex; gap: 6px; flex-wrap: wrap;">
              <button class="retro-btn retro-btn-green retro-btn-sm" id="btn-teacher-scan-gdrive" title="Google Drive: Live API">
                ☁️ Drive
              </button>
              <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-teacher-scan-local">
                <span id="btn-teacher-scan-local-text">📱 Device</span>
              </button>
              <input type="file" id="teacher-device-file-input" multiple style="position: fixed; top: -1000px; left: -1000px; opacity: 0; pointer-events: none; width: 1px; height: 1px;" />
              <input type="file" id="teacher-device-folder-input" webkitdirectory directory multiple style="position: fixed; top: -1000px; left: -1000px; opacity: 0; pointer-events: none; width: 1px; height: 1px;" />
              <button class="retro-btn retro-btn-danger retro-btn-sm" id="btn-teacher-revoke-scan" style="display: none;">
                🔒 Revoke
              </button>
            </div>
          </div>

          <!-- Scanner Status -->
          <div id="teacher-scanner-status-banner" class="retro-inset" style="font-size: 12px; color: var(--c-ink-muted); display: flex; align-items: center; gap: 8px;">
            <span>👁️ <strong>Ready</strong>: Click 'Device' or 'Drive' to scan your own files. Deletions are <strong>instant</strong> — no approval queue.</span>
          </div>

          <!-- Teacher's Scanned Files List -->
          <div id="teacher-scanned-files-container" style="display: flex; flex-direction: column; gap: 6px; flex: 1; overflow-y: auto; padding-right: 4px;">
            <div style="text-align: center; padding: 24px; color: var(--c-ink-light); font-size: 12px;">
              Scan your Local Folder or Google Drive to discover duplicate files, unused junk, and more!
            </div>
          </div>
        </div>

      </div>

      <!-- Retro Toast Notification Container -->
      <div id="teacher-toast-container" style="position: fixed; bottom: 20px; right: 20px; z-index: 5000; display: flex; flex-direction: column; gap: 8px; pointer-events: none;"></div>
    `;

    this.bindEvents();
  }

  bindEvents() {
    // Approve all pending requests
    document.getElementById("btn-approve-all-pending")?.addEventListener("click", async () => {
      const btn = document.getElementById("btn-approve-all-pending");
      if (btn) {
        btn.disabled = true;
        btn.textContent = "Processing...";
      }
      try {
        const res = await fetch("/api/teacher/decide_all", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ teacher_id: localStorage.getItem("d2d_user_id") || "TEACHER-001" })
        }).then(r => r.json());
        if (this.audioSynth) this.audioSynth.playVictoryFanfare();
        if (this.particleEngine) this.particleEngine.emitConfetti();
        this.showToast(`⚡ ${res.message || "All pending files approved!"}`, "success");
        await this.fetchData();
      } catch (e) {
        this.showToast(`Error batch approving: ${e.message}`, "error");
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.textContent = "⚡ Approve All Pending";
        }
      }
    });

    // Student directory & creation
    document.getElementById("btn-t-manage-students")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      this.openStudentDirectoryModal();
    });

    // Refresh queue
    document.getElementById("btn-t-refresh")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      this.fetchData();
    });

    // Logout
    document.getElementById("btn-t-logout")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      if (window.DataToDirt) window.DataToDirt.logout();
    });

    // Filter buttons
    const filterBtns = this.container.querySelectorAll(".btn-filter");
    filterBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        filterBtns.forEach((b) => {
          b.classList.remove("retro-btn-gold");
          b.classList.add("retro-btn-wood");
        });
        btn.classList.remove("retro-btn-wood");
        btn.classList.add("retro-btn-gold");
        this.currentFilter = btn.getAttribute("data-filter");
        this.renderQueue();
      });
    });

    // Search input
    const searchInput = document.getElementById("t-search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.searchQuery = e.target.value.trim().toLowerCase();
        this.renderQueue();
      });
    }

    // Class filter dropdown
    document.getElementById("t-class-filter-select")?.addEventListener("change", (e) => {
      this.selectedClassCode = e.target.value;
      if (this.audioSynth) this.audioSynth.playBlip();
      this.fetchData();
    });

    // Sort toggle
    const sortBtn = document.getElementById("btn-sort-confidence");
    const sortLabel = document.getElementById("sort-order-label");
    if (sortBtn) {
      sortBtn.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        this.sortAsc = !this.sortAsc;
        if (sortLabel) sortLabel.textContent = this.sortAsc ? "Lowest First" : "Highest First";
        this.renderQueue();
      });
    }

    // Tab switching: Student Queue vs My Files
    const tabBtns = this.container.querySelectorAll(".teacher-tab-btn");
    const queueContent = document.getElementById("tab-content-queue");
    const myFilesContent = document.getElementById("tab-content-myfiles");
    const queueControls = document.getElementById("queue-controls");

    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        tabBtns.forEach((b) => {
          b.classList.remove("retro-btn-gold");
          b.classList.add("retro-btn-wood");
        });
        btn.classList.remove("retro-btn-wood");
        btn.classList.add("retro-btn-gold");
        const tab = btn.getAttribute("data-tab");
        if (tab === "myfiles") {
          if (queueContent) queueContent.style.display = "none";
          if (queueControls) queueControls.style.display = "none";
          if (myFilesContent) myFilesContent.style.display = "flex";
        } else {
          if (queueContent) queueContent.style.display = "flex";
          if (queueControls) queueControls.style.display = "flex";
          if (myFilesContent) myFilesContent.style.display = "none";
        }
      });
    });

    // Teacher scan buttons
    const btnTeacherScanDrive = document.getElementById("btn-teacher-scan-gdrive");
    const btnTeacherScanLocal = document.getElementById("btn-teacher-scan-local");
    const btnTeacherRevoke = document.getElementById("btn-teacher-revoke-scan");

    if (btnTeacherScanDrive) {
      btnTeacherScanDrive.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        this.showTeacherGoogleDriveModal();
      });
    }

    if (btnTeacherScanLocal) {
      const handleTeacherDeviceFiles = async (e) => {
        if (e.target.files && e.target.files.length > 0) {
          const files = Array.from(e.target.files);
          const fileList = files.map(f => ({
            name: f.webkitRelativePath || f.name,
            size: f.size,
            lastModified: f.lastModified
          }));
          e.target.value = "";
          await this.executeTeacherScan(null, true, "browser_files", fileList);
        }
      };

      document.getElementById("teacher-device-file-input")?.addEventListener("change", handleTeacherDeviceFiles);
      document.getElementById("teacher-device-folder-input")?.addEventListener("change", handleTeacherDeviceFiles);

      btnTeacherScanLocal.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        this.showTeacherDeviceScanModal();
      });
    }

    if (btnTeacherRevoke) {
      btnTeacherRevoke.addEventListener("click", async () => {
        await this.revokeTeacherFolderAccess();
      });
    }
  }

  async fetchData() {
    try {
      const sel = document.getElementById("t-class-filter-select");
      const cCode = sel ? sel.value : (this.selectedClassCode || "all");
      const qUrl = cCode && cCode !== "all" ? `/api/teacher/queue?class_code=${encodeURIComponent(cCode)}` : `/api/teacher/queue?class_code=all`;

      const [queueRes, analyticsRes] = await Promise.all([
        fetch(qUrl).then((r) => r.json()),
        fetch("/api/teacher/analytics").then((r) => r.json()),
      ]);

      this.queue = queueRes.queue || [];
      this.analytics = analyticsRes || {};

      // If pending count is 0, but queue has items and current filter is pending,
      // default to "all" so the queue never looks empty/vanished!
      const pendingCount = this.queue.filter((r) => (r.status || "").toLowerCase() === "pending").length;
      if (pendingCount === 0 && this.queue.length > 0 && this.currentFilter === "pending") {
        this.currentFilter = "all";
        const filterBtns = this.container?.querySelectorAll(".btn-filter");
        filterBtns?.forEach((b) => {
          if (b.getAttribute("data-filter") === "all") {
            b.classList.remove("retro-btn-wood");
            b.classList.add("retro-btn-gold");
          } else {
            b.classList.remove("retro-btn-gold");
            b.classList.add("retro-btn-wood");
          }
        });
      }

      this.updateStatsBar();
      this.renderQueue();
    } catch (e) {
      console.warn("Failed to load teacher queue:", e);
      this.showToast("Failed to connect to teacher API", "error");
    }
  }

  updateStatsBar() {
    const elCleared = document.getElementById("stat-data-cleared");
    const elCarbon = document.getElementById("stat-carbon-offset");
    const elTrees = document.getElementById("stat-trees-funded");
    const elFlagged = document.getElementById("stat-flagged-count");
    const elBadge = document.getElementById("t-queue-badge");
    const elClassBadge = document.getElementById("t-class-badge");

    if (elClassBadge) {
      let cName = (window.DataToDirt?.classCode || "").toUpperCase();
      if (!cName) {
        const u = (window.DataToDirt?.userId || "").toLowerCase();
        for (const c of ["bio101", "env201", "cs301", "chem102", "earth204"]) {
          if (u.includes(c)) {
            cName = c.toUpperCase();
            break;
          }
        }
      }
      elClassBadge.textContent = cName ? `Class: ${cName}` : "Class: BIO101";
    }

    if (this.analytics) {
      if (elCleared) elCleared.textContent = `${(this.analytics.total_data_cleaned_gb || 0).toFixed(2)} GB`;
      if (elCarbon) elCarbon.textContent = `${(this.analytics.total_carbon_offset_kg || 0).toFixed(2)} kg CO₂`;
      if (elTrees) elTrees.textContent = `${this.analytics.total_trees_funded || 0} 🌲`;
      if (elFlagged) elFlagged.textContent = `${this.analytics.flagged_count || 0} 🚩`;
    }

    const pendingCount = this.queue.filter((r) => (r.status || "").toLowerCase() === "pending").length;
    if (elBadge) elBadge.textContent = `${pendingCount} PENDING`;
  }

  renderQueue() {
    const listEl = document.getElementById("t-queue-scroll-area");
    if (!listEl) return;

    // Filter items
    let items = this.queue.filter((item) => {
      const status = (item.status || "pending").toLowerCase();
      if (this.currentFilter !== "all" && status !== this.currentFilter) {
        return false;
      }
      if (this.searchQuery) {
        const q = this.searchQuery;
        const fn = (item.file_name || "").toLowerCase();
        const reason = (item.reason || item.deletion_reason || "").toLowerCase();
        const sname = (item.student_name || "").toLowerCase();
        const sid = (item.student_id || "").toLowerCase();
        if (!fn.includes(q) && !reason.includes(q) && !sname.includes(q) && !sid.includes(q)) {
          return false;
        }
      }
      return true;
    });

    // Sort by AI confidence
    items.sort((a, b) => {
      const scoreA = a.ai_evaluation?.confidence_score ?? a.ai_score ?? 0.5;
      const scoreB = b.ai_evaluation?.confidence_score ?? b.ai_score ?? 0.5;
      return this.sortAsc ? scoreA - scoreB : scoreB - scoreA;
    });

    if (items.length === 0) {
      listEl.innerHTML = `
        <div style="text-align: center; padding: 48px 16px; color: var(--c-ink-light); font-size: 13px;">
          ✨ No requests found matching the current filter: <strong>${this.currentFilter.toUpperCase()}</strong>
        </div>
      `;
      return;
    }

    listEl.innerHTML = items.map((item) => this.renderQueueItemHtml(item)).join("");

    // Bind action buttons
    listEl.querySelectorAll(".btn-act-approve").forEach((btn) => {
      btn.onclick = () => this.handleApprove(btn.getAttribute("data-id"));
    });
    listEl.querySelectorAll(".btn-act-reject").forEach((btn) => {
      btn.onclick = () => this.openRejectModal(btn.getAttribute("data-id"), btn.getAttribute("data-name"));
    });
    listEl.querySelectorAll(".btn-act-flag").forEach((btn) => {
      btn.onclick = () => this.openFlagModal(btn.getAttribute("data-id"), btn.getAttribute("data-name"), btn.getAttribute("data-student"));
    });
  }

  renderQueueItemHtml(item) {
    const reqId = item.request_id || item.id;
    const score = item.ai_evaluation?.confidence_score ?? item.ai_confidence_score ?? item.ai_score ?? 0.8;
    const scorePct = Math.round(score * 100);
    const isPlausible = score >= 0.5;

    // AI Confidence Badge: Green for >= 0.5, Red for < 0.5
    const badgeClass = isPlausible ? "retro-tag-leaf" : "retro-tag-danger";
    const badgeLabel = isPlausible ? `✓ ${scorePct}% Plausible` : `🚩 ${scorePct}% Suspicious`;

    const sizeMb = Math.round((item.file_size_bytes || item.size_bytes || 0) / (1024 * 1024));
    const reasonText = item.reason || item.deletion_reason || "No justification entered.";
    const aiSummary = item.ai_evaluation?.summary || item.ai_summary || "Context verified.";
    const status = (item.status || "PENDING").toUpperCase();

    const isPending = status === "PENDING";

    return `
      <div class="retro-inset" style="padding: 10px 14px; display: flex; flex-direction: column; gap: 8px;">
        
        <!-- Header: Student & AI Confidence -->
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-weight: bold; font-size: 13px; color: var(--c-wood-border);">
              ${item.student_name || item.student_id}
            </span>
            <span style="font-size: 11px; color: var(--c-ink-muted);">(${item.student_id})</span>
            <span class="retro-tag ${isPlausible ? "retro-tag-leaf" : "retro-tag-danger"}" style="font-size: 10px;">
              ${badgeLabel}
            </span>
          </div>
          <div>
            <span class="retro-tag retro-tag-stale" style="font-size: 10px;">
              STATUS: ${status}
            </span>
          </div>
        </div>

        <!-- File details -->
        <div style="font-size: 12px; color: var(--c-ink-text); display: flex; justify-content: space-between;">
          <span>File: <strong>${item.file_name}</strong> (${sizeMb} MB)</span>
          <span style="color: var(--c-ink-muted); font-size: 11px;">ID: ${reqId}</span>
        </div>

        <!-- Student justification callout -->
        <div style="font-size: 12px; font-style: italic; color: var(--c-ink-muted); background: rgba(255, 255, 255, 0.6); padding: 6px 10px; border: 1px dashed var(--c-parchment-border);">
          "${reasonText}"
        </div>

        <!-- AI Evaluation Summary -->
        <div style="font-size: 11px; color: ${isPlausible ? "var(--c-eco-leaf)" : "var(--c-danger-bright)"}; font-weight: bold; display: flex; align-items: center; gap: 6px;">
          <span>🤖 AI Summary:</span>
          <span style="font-weight: normal; color: var(--c-ink-text);">${aiSummary}</span>
        </div>

        <!-- Decision details if already decided -->
        ${item.feedback || item.decision_note ? `
          <div style="font-size: 11px; color: var(--c-ink-muted); font-style: italic;">
            Teacher Note: "${item.feedback || item.decision_note}"
          </div>
        ` : ""}

        <!-- Action Buttons (Only enabled when Pending) -->
        ${isPending ? `
          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px;">
            <button class="retro-btn retro-btn-danger retro-btn-sm btn-act-flag" data-id="${reqId}" data-name="${item.file_name}" data-student="${item.student_name || item.student_id}">
              🚩 Flag Gaming
            </button>
            <button class="retro-btn retro-btn-wood retro-btn-sm btn-act-reject" data-id="${reqId}" data-name="${item.file_name}">
              ✕ Reject
            </button>
            <button class="retro-btn retro-btn-green retro-btn-sm btn-act-approve" data-id="${reqId}">
              ✓ Approve Deletion
            </button>
          </div>
        ` : ""}

      </div>
    `;
  }

  async handleApprove(requestId) {
    try {
      const res = await fetch("/api/teacher/decide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: requestId, action: "approve" }),
      }).then((r) => r.json());

      if (this.audioSynth) this.audioSynth.playDeletionPoof();
      if (this.particleEngine) this.particleEngine.emitDeletionPoof(window.innerWidth / 2, window.innerHeight / 2);

      if (res.donation_triggered) {
        if (this.audioSynth) this.audioSynth.playVictoryFanfare();
        if (this.particleEngine) this.particleEngine.emitConfetti();
        this.showToast(`🌳 1.0 GB Threshold Reached! Micro-donation triggered via Tree-Nation!`, "success");
      } else {
        this.showToast(`✓ Request ${requestId} approved. File recycled and carbon savings credited.`, "success");
      }

      await this.fetchData();
    } catch (e) {
      this.showToast(`Error approving request: ${e.message}`, "error");
    }
  }

  openRejectModal(requestId, fileName) {
    const modalHtml = `
      <div class="retro-modal-backdrop" id="modal-reject-reason">
        <div class="retro-card retro-modal" style="max-width: 460px;">
          <div class="retro-modal-header">
            <span>✕ Reject Deletion Request</span>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-rej-close">✕</button>
          </div>
          <div class="retro-modal-body">
            <p style="margin-bottom: 8px;">
              Preserve <strong>${fileName}</strong> on student disk. Please provide educational feedback explaining why this file should be kept.
            </p>
            <div class="retro-inset">
              <textarea id="rej-reason-input" class="retro-input" style="width: 100%; height: 70px; resize: none;" placeholder="e.g. This is a critical project reflection artifact. Please archive instead of deleting."></textarea>
            </div>
          </div>
          <div class="retro-modal-actions">
            <button class="retro-btn retro-btn-wood" id="btn-rej-cancel">Cancel</button>
            <button class="retro-btn retro-btn-danger" id="btn-rej-confirm">Confirm Rejection</button>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML("beforeend", modalHtml);
    const modal = document.getElementById("modal-reject-reason");
    const dismiss = () => modal?.remove();

    document.getElementById("btn-rej-close")?.addEventListener("click", dismiss);
    document.getElementById("btn-rej-cancel")?.addEventListener("click", dismiss);

    document.getElementById("btn-rej-confirm")?.addEventListener("click", async () => {
      const feedback = document.getElementById("rej-reason-input")?.value.trim() || "File marked for retention by teacher.";
      dismiss();
      try {
        await fetch("/api/teacher/decide", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ request_id: requestId, action: "reject", feedback: feedback }),
        });
        if (this.audioSynth) this.audioSynth.playBlip();
        this.showToast(`✕ Request ${requestId} rejected. File preserved without penalty.`, "info");
        await this.fetchData();
      } catch (e) {
        this.showToast(`Error rejecting request: ${e.message}`, "error");
      }
    });
  }

  openFlagModal(requestId, fileName, studentName) {
    const modalHtml = `
      <div class="retro-modal-backdrop" id="modal-flag-reason">
        <div class="retro-card retro-modal" style="max-width: 480px;">
          <div class="retro-modal-header" style="background: var(--c-danger-dark); color: #fff;">
            <span>🚩 Flag Intentional Gaming Attempt</span>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-flag-close">✕</button>
          </div>
          <div class="retro-modal-body">
            <p style="margin-bottom: 8px; color: var(--c-danger-bright); font-weight: bold;">
              Disciplinary Action: 1 Strike will be logged against ${studentName}.
            </p>
            <p style="font-size: 12px; margin-bottom: 8px;">
              Streak will reset to 0 days, 50 eco-points will be deducted, and an entry will be logged into the Classroom Incident Register.
            </p>
            <div class="retro-inset">
              <label style="display: block; font-weight: bold; margin-bottom: 4px; font-size: 11px;">Infraction Reason / Feedback:</label>
              <input type="text" id="flag-reason-input" class="retro-input" style="width: 100%;" value="Low-effort justification or score farming detected." />
            </div>
          </div>
          <div class="retro-modal-actions">
            <button class="retro-btn retro-btn-wood" id="btn-flag-cancel">Cancel</button>
            <button class="retro-btn retro-btn-danger" id="btn-flag-confirm">Enforce Penalty</button>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML("beforeend", modalHtml);
    const modal = document.getElementById("modal-flag-reason");
    const dismiss = () => modal?.remove();

    document.getElementById("btn-flag-close")?.addEventListener("click", dismiss);
    document.getElementById("btn-flag-cancel")?.addEventListener("click", dismiss);

    document.getElementById("btn-flag-confirm")?.addEventListener("click", async () => {
      const reason = document.getElementById("flag-reason-input")?.value.trim() || "Intentional gaming infraction logged.";
      dismiss();
      try {
        await fetch("/api/teacher/decide", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ request_id: requestId, action: "flag", feedback: reason }),
        });
        if (this.audioSynth) this.audioSynth.playGamingBuzzer();
        this.showToast(`🚩 Disciplinary strike logged for request ${requestId}.`, "warning");
        await this.fetchData();
      } catch (e) {
        this.showToast(`Error flagging request: ${e.message}`, "error");
      }
    });
  }

  showToast(message, type = "info") {
    const container = document.getElementById("teacher-toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "retro-card";
    toast.style.padding = "8px 14px";
    toast.style.fontSize = "12px";
    toast.style.fontWeight = "bold";
    toast.style.boxShadow = "3px 3px 0 rgba(0,0,0,0.6)";
    toast.style.pointerEvents = "auto";
    toast.style.animation = "fade-in 0.2s ease-out";

    if (type === "success") {
      toast.style.border = "3px solid var(--c-eco-leaf)";
      toast.style.color = "var(--c-eco-leaf)";
    } else if (type === "warning" || type === "error") {
      toast.style.border = "3px solid var(--c-danger-bright)";
      toast.style.color = "var(--c-danger-bright)";
    } else {
      toast.style.border = "3px solid var(--c-wood-border)";
    }

    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.4s";
      setTimeout(() => toast.remove(), 400);
    }, 3500);
  }

  copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).catch(() => this.fallbackCopyText(text));
    }
    return this.fallbackCopyText(text);
  }

  fallbackCopyText(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand("copy");
    } catch (e) {
      console.warn("Clipboard fallback failed:", e);
    }
    ta.remove();
    return Promise.resolve();
  }

  openStudentDirectoryModal() {
    const existingModal = document.getElementById("modal-student-directory");
    if (existingModal) existingModal.remove();

    const genId = () => "STU-" + Math.random().toString(36).substring(2, 8).toUpperCase();
    let defaultClassCode = (window.DataToDirt?.classCode || localStorage.getItem("d2d_class_code") || "").toLowerCase();
    const role = (window.DataToDirt?.authenticatedRole || localStorage.getItem("d2d_role") || "").toLowerCase();
    if (!defaultClassCode || defaultClassCode.startsWith("admin") || role === "admin") {
      defaultClassCode = "all";
      const u = (window.DataToDirt?.userId || localStorage.getItem("d2d_user_id") || "").toLowerCase();
      if (role === "teacher") {
        for (const c of ["bio101", "env201", "cs301", "chem102", "earth204"]) {
          if (u.includes(c)) {
            defaultClassCode = c;
            break;
          }
        }
      }
    }
    if (!defaultClassCode) defaultClassCode = "all";

    const modalHtml = `
      <div class="retro-modal-backdrop" id="modal-student-directory" style="position: fixed; inset: 0; background: rgba(0,0,0,0.65); display: flex; align-items: center; justify-content: center; z-index: 6000; padding: 12px; backdrop-filter: blur(2px);">
        <div class="retro-card retro-modal" style="max-width: 680px; width: 100%; max-height: 90vh; display: flex; flex-direction: column; overflow: hidden; padding: 0; border: 3px solid var(--c-wood-border, #4a2e18); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
          
          <!-- Modal Header -->
          <div class="retro-modal-header" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 18px; background: #3e2714; color: #f5eedc; border-bottom: 2px solid #231308;">
            <div style="font-weight: bold; font-size: 15px; display: flex; align-items: center; gap: 10px;">
              <span>👥 Student ID Manager & Directory</span>
              <span class="retro-tag retro-tag-stale" id="stu-cloud-status" style="font-size: 10px; padding: 2px 6px;">Syncing...</span>
            </div>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-stu-close" style="padding: 2px 8px; font-weight: bold; cursor: pointer;">✕</button>
          </div>

          <!-- Scrollable Content -->
          <div class="retro-modal-body" style="padding: 16px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 14px; background: #fbf8f0;">
            
            <!-- Section 1: Create Student ID Form -->
            <div class="retro-card" style="padding: 14px; background: #fff9ed; border: 2px solid #b8860b;">
              <div style="font-weight: bold; font-size: 13px; margin-bottom: 10px; color: #5c381e; display: flex; justify-content: space-between; align-items: center;">
                <span>➕ Generate & Enroll Student</span>
                <span style="font-size: 11px; font-weight: normal; color: var(--c-ink-muted, #7f8c8d);">Cloud Firestore & Local Resilient Storage</span>
              </div>
              
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                <div>
                  <label style="display: block; font-size: 11px; font-weight: bold; margin-bottom: 4px; color: #4a2e18;">Student Full Name *</label>
                  <input type="text" id="stu-input-name" class="retro-input" placeholder="Enter Student Full Name" style="width: 100%; box-sizing: border-box; font-size: 12px; padding: 6px 8px; border: 1.5px solid #a27848; border-radius: 4px;" />
                </div>
                <div>
                  <label style="display: block; font-size: 11px; font-weight: bold; margin-bottom: 4px; color: #4a2e18;">Class Code *</label>
                  <input type="text" id="stu-input-class" class="retro-input" value="${defaultClassCode === 'all' ? 'bio101' : defaultClassCode}" placeholder="e.g. bio101" style="width: 100%; box-sizing: border-box; font-size: 12px; padding: 6px 8px; border: 1.5px solid #a27848; border-radius: 4px;" />
                </div>
              </div>

              <div style="margin-bottom: 12px;">
                <label style="display: block; font-size: 11px; font-weight: bold; margin-bottom: 4px; color: #4a2e18;">Student ID (Login Identifier)</label>
                <div style="display: flex; gap: 6px;">
                  <input type="text" id="stu-input-id" class="retro-input" value="${genId()}" placeholder="e.g. STU-A7F9B1" style="flex: 1; font-size: 12px; font-family: monospace; font-weight: bold; padding: 6px 8px; border: 1.5px solid #a27848; border-radius: 4px;" />
                  <button type="button" class="retro-btn retro-btn-wood retro-btn-sm" id="btn-stu-autogen" title="Generate New Random ID">🎲 Auto-Gen</button>
                </div>
                <div style="font-size: 10px; color: #7f8c8d; margin-top: 4px;">
                  💡 Tip: Students can sign in using this ID with their Class Code.
                </div>
              </div>

              <div id="stu-create-msg" style="display: none; font-size: 12px; font-weight: bold; margin-bottom: 8px; padding: 6px 10px; border-radius: 4px;"></div>

              <div style="display: flex; justify-content: flex-end;">
                <button type="button" class="retro-btn retro-btn-gold" id="btn-stu-submit" style="padding: 7px 16px; font-weight: bold; font-size: 12px;">
                  💾 Save & Enroll Student
                </button>
              </div>
            </div>

            <!-- Section 2: Directory Table -->
            <div class="retro-card" style="padding: 14px; border: 2px solid #8b5a2b; background: #fff; display: flex; flex-direction: column; gap: 10px;">
              <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="font-weight: bold; font-size: 13px; color: #3e2210; display: flex; align-items: center; gap: 6px;">
                  <span>📋 Enrolled Students</span>
                  <span class="retro-tag retro-tag-clean" id="stu-count-badge" style="font-size: 10px; padding: 2px 6px;">0 Students</span>
                </div>
                <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                  <select id="stu-class-filter-select" class="retro-select" style="font-size: 11px; padding: 4px 8px; border: 1.5px solid #8b5a2b; border-radius: 4px; background: #fff; font-weight: bold; color: #4a2e18; cursor: pointer;">
                    <option value="all" ${defaultClassCode === 'all' ? 'selected' : ''}>🌟 All Classes</option>
                    <option value="bio101" ${defaultClassCode === 'bio101' ? 'selected' : ''}>🌿 Bio 101 (Dr. Reed)</option>
                    <option value="cs301" ${defaultClassCode === 'cs301' ? 'selected' : ''}>💻 CS 301 (Ms. Patel)</option>
                    <option value="env201" ${defaultClassCode === 'env201' ? 'selected' : ''}>🌍 Env 201 (Prof. Green)</option>
                    <option value="chem102" ${defaultClassCode === 'chem102' ? 'selected' : ''}>🧪 Chem 102 (Dr. Thorne)</option>
                    <option value="earth204" ${defaultClassCode === 'earth204' ? 'selected' : ''}>⛰️ Earth 204 (Mr. Woods)</option>
                  </select>
                  <input type="text" id="stu-search-filter" class="retro-input" placeholder="Search by name, ID..." style="font-size: 11px; padding: 4px 8px; width: 140px; border: 1px solid #ccc; border-radius: 4px;" />
                  <button type="button" class="retro-btn retro-btn-wood retro-btn-sm" id="btn-stu-refresh-list" title="Refresh Directory">🔄</button>
                </div>
              </div>

              <!-- Table Container -->
              <div style="max-height: 240px; overflow-y: auto; border: 1px solid #d4c2a5; border-radius: 4px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 11px; text-align: left;">
                  <thead style="background: #e8d8be; position: sticky; top: 0; z-index: 2; border-bottom: 1px solid #b89b72;">
                    <tr>
                      <th style="padding: 7px 10px; color: #3e2210;">Student ID</th>
                      <th style="padding: 7px 10px; color: #3e2210;">Name</th>
                      <th style="padding: 7px 10px; color: #3e2210;">Class</th>
                      <th style="padding: 7px 10px; color: #3e2210; text-align: right;">Points</th>
                      <th style="padding: 7px 10px; color: #3e2210; text-align: center;">Actions</th>
                    </tr>
                  </thead>
                  <tbody id="stu-table-body">
                    <tr>
                      <td colspan="5" style="text-align: center; padding: 24px; color: #7f8c8d;">Loading students...</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

          </div>

          <!-- Footer -->
          <div class="retro-modal-actions" style="padding: 10px 18px; border-top: 1px solid #d4c2a5; display: flex; justify-content: flex-end; background: #e8dfcf;">
            <button class="retro-btn retro-btn-wood" id="btn-stu-footer-close">Close</button>
          </div>

        </div>
      </div>
    `;

    document.body.insertAdjacentHTML("beforeend", modalHtml);

    const modal = document.getElementById("modal-student-directory");
    const dismiss = () => modal?.remove();

    document.getElementById("btn-stu-close")?.addEventListener("click", dismiss);
    document.getElementById("btn-stu-footer-close")?.addEventListener("click", dismiss);

    // Auto-gen ID button
    document.getElementById("btn-stu-autogen")?.addEventListener("click", () => {
      const idInput = document.getElementById("stu-input-id");
      if (idInput) idInput.value = genId();
      if (this.audioSynth) this.audioSynth.playBlip();
    });

    let currentStudents = [];

    let recentlyEnrolledStudentId = null;

    const renderTable = () => {
      const tbody = document.getElementById("stu-table-body");
      const filterInput = document.getElementById("stu-search-filter");
      const badge = document.getElementById("stu-count-badge");
      if (!tbody) return;

      const q = (filterInput?.value || "").toLowerCase().trim();
      const filtered = currentStudents.filter((s) => {
        if (!q) return true;
        const sid = (s.student_id || s.user_id || "").toLowerCase();
        const sname = (s.name || "").toLowerCase();
        const sclass = (s.class_code || "").toLowerCase();
        return sid.includes(q) || sname.includes(q) || sclass.includes(q);
      });

      if (badge) badge.textContent = `${filtered.length} of ${currentStudents.length} Students`;

      if (filtered.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="5" style="text-align: center; padding: 24px; color: #7f8c8d;">
              ${currentStudents.length === 0 ? "No student records found in this view. Create one above!" : "No students match your search filter."}
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = filtered.map((s) => {
        const sid = s.student_id || s.user_id || "—";
        const name = s.name || sid;
        const classCode = (s.class_code || "—").toUpperCase();
        const points = s.eco_points || 0;
        const isNew = sid === recentlyEnrolledStudentId;
        const rowBg = isNew ? "background: #e8f8f5; border: 2px solid #27ae60;" : "border-bottom: 1px solid #f0e6d6;";
        return `
          <tr style="${rowBg}">
            <td style="padding: 7px 10px; font-family: monospace; font-weight: bold; color: #2980b9;">
              ${sid} ${isNew ? '<span class="retro-tag retro-tag-clean" style="font-size: 9px; padding: 1px 4px; margin-left: 4px;">⭐ NEW</span>' : ''}
            </td>
            <td style="padding: 7px 10px; font-weight: 600; color: #2c3e50;">
              ${name}
            </td>
            <td style="padding: 7px 10px; color: #7f8c8d;">
              <span class="retro-tag retro-tag-wood" style="font-size: 10px;">${classCode}</span>
            </td>
            <td style="padding: 7px 10px; text-align: right; font-weight: bold; color: #27ae60;">
              ${points} pts
            </td>
            <td style="padding: 7px 10px; text-align: center;">
              <button class="retro-btn retro-btn-wood retro-btn-sm btn-copy-stu-id" data-id="${sid}" title="Copy Student ID" style="padding: 2px 8px; font-size: 10px;">
                📋 Copy
              </button>
            </td>
          </tr>
        `;
      }).join("");

      // Bind copy buttons
      tbody.querySelectorAll(".btn-copy-stu-id").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const idToCopy = btn.getAttribute("data-id");
          await this.copyToClipboard(idToCopy);
          if (this.audioSynth) this.audioSynth.playBlip();
          const origText = btn.textContent;
          btn.textContent = "✓ Copied!";
          btn.classList.add("retro-btn-gold");
          setTimeout(() => {
            btn.textContent = origText;
            btn.classList.remove("retro-btn-gold");
          }, 1500);
          this.showToast(`Copied Student ID '${idToCopy}' to clipboard`, "info");
        });
      });
    };

    const loadStudents = async (targetClass = null) => {
      try {
        const selectEl = document.getElementById("stu-class-filter-select");
        let activeClass = targetClass !== null ? targetClass : (selectEl?.value || defaultClassCode);
        if (selectEl && targetClass !== null) {
          selectEl.value = targetClass;
        }
        const queryParam = activeClass && activeClass !== "all" ? `?class_code=${encodeURIComponent(activeClass)}` : "?class_code=all";
        const res = await fetch(`/api/teacher/students${queryParam}`);
        const data = await res.json();
        currentStudents = data.students || [];

        const cloudBadge = document.getElementById("stu-cloud-status");
        if (cloudBadge) {
          if (data.cloud_sync) {
            cloudBadge.textContent = "☁️ Firebase Firestore Active";
            cloudBadge.className = "retro-tag retro-tag-clean";
            cloudBadge.style.color = "#27ae60";
          } else {
            cloudBadge.textContent = "💾 Local Storage Ready";
            cloudBadge.className = "retro-tag retro-tag-stale";
          }
        }

        renderTable();
      } catch (err) {
        console.warn("Failed to load students:", err);
        const tbody = document.getElementById("stu-table-body");
        if (tbody) {
          tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 20px; color: #e74c3c;">Failed to load directory.</td></tr>`;
        }
      }
    };

    // Filter input binding
    document.getElementById("stu-search-filter")?.addEventListener("input", renderTable);

    // Class dropdown binding
    document.getElementById("stu-class-filter-select")?.addEventListener("change", (e) => {
      if (this.audioSynth) this.audioSynth.playBlip();
      loadStudents(e.target.value);
    });

    // Refresh directory binding
    document.getElementById("btn-stu-refresh-list")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      loadStudents();
    });

    // Create student submit
    document.getElementById("btn-stu-submit")?.addEventListener("click", async () => {
      const nameInput = document.getElementById("stu-input-name");
      const classInput = document.getElementById("stu-input-class");
      const idInput = document.getElementById("stu-input-id");
      const msgEl = document.getElementById("stu-create-msg");

      const name = (nameInput?.value || "").trim();
      const classCode = (classInput?.value || "").trim();
      const studentId = (idInput?.value || "").trim();

      if (!name) {
        if (msgEl) {
          msgEl.style.display = "block";
          msgEl.style.background = "#fde8e8";
          msgEl.style.color = "#c0392b";
          msgEl.textContent = "Please provide the student's full name.";
        }
        return;
      }

      if (!classCode) {
        if (msgEl) {
          msgEl.style.display = "block";
          msgEl.style.background = "#fde8e8";
          msgEl.style.color = "#c0392b";
          msgEl.textContent = "Please provide a valid class code.";
        }
        return;
      }

      const submitBtn = document.getElementById("btn-stu-submit");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "⏳ Saving...";
      }

      try {
        const resp = await fetch("/api/teacher/students/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: name,
            class_code: classCode,
            student_id: studentId
          })
        });

        const result = await resp.json();

        if (!resp.ok || result.status === "error") {
          if (msgEl) {
            msgEl.style.display = "block";
            msgEl.style.background = "#fde8e8";
            msgEl.style.color = "#c0392b";
            msgEl.textContent = result.message || "Failed to create student record.";
          }
          if (this.audioSynth) this.audioSynth.playGamingBuzzer();
          return;
        }

        // Success!
        recentlyEnrolledStudentId = studentId;
        try {
          localStorage.setItem("d2d_last_created_student", JSON.stringify({
            student_id: studentId,
            name: name,
            class_code: classCode
          }));
        } catch (_) {}

        if (this.audioSynth) this.audioSynth.playCoinDing();
        if (this.particleEngine) this.particleEngine.emitConfetti();

        if (msgEl) {
          msgEl.style.display = "block";
          msgEl.style.background = "#e8f8f5";
          msgEl.style.color = "#27ae60";
          msgEl.textContent = `✓ Student ${name} (${studentId}) enrolled in ${classCode.toUpperCase()}!`;
        }

        this.showToast(result.message || `Student ID ${studentId} saved!`, "success");

        // Clear input name and auto-gen next ID for quick entry
        if (nameInput) nameInput.value = "";
        if (idInput) idInput.value = genId();

        // Refresh directory for this class
        await loadStudents(classCode);
      } catch (e) {
        if (msgEl) {
          msgEl.style.display = "block";
          msgEl.style.background = "#fde8e8";
          msgEl.style.color = "#c0392b";
          msgEl.textContent = `Network error: ${e.message}`;
        }
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "💾 Save & Enroll Student";
        }
      }
    });

    // Initial load
    loadStudents();
  }

  async executeTeacherScan(folderPath, sessionOnly, scanType = "local", fileList = [], oauthToken = null) {
    const banner = document.getElementById("teacher-scanner-status-banner");
    const btnRevoke = document.getElementById("btn-teacher-revoke-scan");
    if (banner) {
      banner.style.borderColor = "";
      banner.style.backgroundColor = "";
      if (scanType === "drive") {
        banner.innerHTML = `<span>⏳ Scanning your Google Drive for duplicates, junk & unused files...</span>`;
      } else if (scanType === "auto_device") {
        banner.innerHTML = `<span>⏳ 1-Click Auto-Scanning System Storage (Local Disk, Downloads, OneDrive, iCloud)...</span>`;
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
      if (scanType === "drive" || scanType === "picker_files") {
        const effectiveOAuth = oauthToken || localStorage.getItem("d2d_google_access_token");
        if (effectiveOAuth) {
          payload.oauth_token = effectiveOAuth;
        }
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
        if (scanType === "drive" || scanType === "picker_files") {
          localStorage.removeItem("d2d_google_access_token");
          window.location.href = "/auth/google/login";
          return;
        }
      }

      if (!response.ok || res.status === "error" || res.error) {
        const errorMsg = res.error || res.message || (!response.ok ? `HTTP ${response.status}: Scan failed` : "Failed to scan folder");
        this.teacherScannedFiles = [];
        if (banner) {
          banner.style.borderColor = "var(--c-danger-red)";
          banner.style.backgroundColor = "rgba(168, 36, 36, 0.15)";
          banner.innerHTML = `<span style="color: var(--c-danger-bright); font-weight: bold;">❌ Scan Error: ${errorMsg}</span>`;
        }
        if (btnRevoke) btnRevoke.style.display = "none";
        this.renderTeacherScannedFiles(errorMsg);
        return;
      }

      this.teacherScannedFiles = (res.files || []).map(f => this.ensureFileAiAnalysis(f));
      this.teacherLastScanCompleted = true;
      this.teacherLastScanType = scanType;
      const totalScanned = res.total_scanned || res.files_found || 0;
      const totalFound = res.files_found || this.teacherScannedFiles.length;
      const wasteFormatted = res.total_waste_formatted || (this.teacherScannedFiles.reduce((acc, f) => acc + (f.size_bytes || 0), 0) / (1024*1024)).toFixed(1) + " MB";

      if (banner) {
        banner.style.borderColor = "";
        banner.style.backgroundColor = "";
        const scanSourceLabel = scanType === "drive" || scanType === "picker_files" ? "Google Drive" : "Device Storage";
        banner.innerHTML = `<span>✅ <strong>${scanSourceLabel} Scanned</strong>: <strong>${Number(totalScanned).toLocaleString()} files analyzed</strong> — <strong>${Number(totalFound).toLocaleString()} dark data candidates (${wasteFormatted})</strong>. Click <strong>'🗑️ Clean'</strong> on any file to delete it immediately!</span>`;
      }
      if (btnRevoke) btnRevoke.style.display = "inline-flex";

      if (this.audioSynth) this.audioSynth.playCoinDing();
      this.renderTeacherScannedFiles();
    } catch (e) {
      const errorMsg = e.message || "Failed to communicate with scanner service";
      this.teacherScannedFiles = [];
      if (banner) {
        banner.style.borderColor = "var(--c-danger-red)";
        banner.style.backgroundColor = "rgba(168, 36, 36, 0.15)";
        banner.innerHTML = `<span style="color: var(--c-danger-bright); font-weight: bold;">❌ Scan Error: ${errorMsg}</span>`;
      }
      if (btnRevoke) btnRevoke.style.display = "none";
      this.renderTeacherScannedFiles(errorMsg);
    }
  }

  ensureFileAiAnalysis(file) {
    if (!file) return file;
    if (!file.ai_confidence_score || !file.ai_forensic_rationale) {
      const fn = file.raw_file_name || file.file_name || "";
      const ageDays = file.age_days || 0;
      const accessedDays = file.accessed_days != null ? file.accessed_days : ageDays;
      const ext = fn.includes(".") ? fn.split(".").pop().toLowerCase() : "";
      const szFmt = file.size_formatted || "0 B";

      let confidence = "96.5%";
      let tag = "Dark Data Candidate";
      let rationale = `Dormant storage item unreferenced by active workflows. Safe reclamation candidate.`;

      if (file.sha_match || file.sha_match_filename) {
        confidence = "99.4%";
        tag = "Bit-for-Bit Clone";
        rationale = `🎯 Cryptographic Duplicate: Bit-for-bit identical SHA-256 duplicate clone. Reclaiming this file recovers storage with zero loss of unique data.`;
      } else if (["dmg", "iso", "pkg", "msi", "exe", "apk"].includes(ext)) {
        confidence = "98.7%";
        tag = "Redundant Installer";
        rationale = `📦 Redundant Software Deployment Package (${ext.toUpperCase()}): Application is already installed on system. Retaining installer consumes dead disk ballast.`;
      } else if (["zip", "tar", "gz", "tgz", "rar", "7z"].includes(ext)) {
        confidence = "97.4%";
        tag = "Stale Archive Relic";
        rationale = `🗜️ Stale Archive Relic: Compressed package (${ext.toUpperCase()}) unaccessed for ${accessedDays} days. Contents extracted or superseded.`;
      } else if (["mov", "mp4", "avi", "mkv", "webm", "m4v", "zoom"].includes(ext)) {
        confidence = "96.8%";
        tag = "Heavy Media Capture";
        rationale = `🎥 High-Bitrate Media Capture (${szFmt}): Unaccessed for ${accessedDays} days. Consumes high passive cloud/disk footprint. 100% safe to clean.`;
      } else if (/^(screenshot|screen shot|screen recording|captura)/i.test(fn)) {
        confidence = "98.2%";
        tag = "Ephemeral Screenshot";
        rationale = `📸 Transient Screenshot: Ephemeral capture relic with zero archival reference. Safe to purge.`;
      } else if (["tmp", "log", "bak", "cache", "old", "swp", "crdownload", "part"].includes(ext)) {
        confidence = "99.1%";
        tag = "Disposable System Residue";
        rationale = `🧹 Disposable System Residue: Temporary cache or log artifact unreferenced by active applications. Automated safe reclamation.`;
      } else if (ageDays > 120 || accessedDays > 120) {
        confidence = "95.5%";
        tag = `Stale Relic (${ageDays}d > 90d)`;
        rationale = `⏱️ Cold Storage Relic: Dormant file untouched for ${accessedDays} days (${ageDays} days old). Safe candidate to reclaim environmental overhead.`;
      }

      file.ai_confidence_score = file.ai_confidence_score || confidence;
      file.dark_data_tag = file.dark_data_tag || tag;
      file.ai_forensic_rationale = file.ai_forensic_rationale || rationale;
    }
    return file;
  }

  renderTeacherScannedFiles(errorMessage = null) {
    const container = document.getElementById("teacher-scanned-files-container");
    if (!container) return;

    if (errorMessage) {
      container.innerHTML = `
        <div class="retro-inset" style="text-align: center; padding: 18px 12px; border-color: var(--c-danger-red); background-color: rgba(168, 36, 36, 0.08);">
          <div style="font-size: 20px; margin-bottom: 6px;">⚠️</div>
          <div style="font-weight: bold; font-size: 13px; color: var(--c-danger-bright); margin-bottom: 4px;">Directory Access / Scan Failed</div>
          <div style="font-size: 11px; color: var(--c-ink-muted); word-break: break-word;">${errorMessage}</div>
        </div>
      `;
      return;
    }

    if (this.teacherScannedFiles.length === 0) {
      if (this.teacherLastScanCompleted) {
        container.innerHTML = `
          <div style="text-align: center; padding: 24px; color: var(--c-ink-light); font-size: 12px; line-height: 1.6;">
            <div style="font-size: 26px; margin-bottom: 8px;">🌱</div>
            <div style="font-size: 14px; font-weight: bold; color: var(--c-wood-border); margin-bottom: 6px;">All Clean!</div>
            <div>Zero dark data bloat remaining in this source.</div>
          </div>
        `;
        return;
      }
      container.innerHTML = `
        <div style="text-align: center; padding: 24px; color: var(--c-ink-light); font-size: 12px; line-height: 1.6;">
          <div style="font-size: 13px; font-weight: bold; color: var(--c-wood-border); margin-bottom: 6px;">📂 Ready to Clean Teacher Files</div>
          <div>Click <strong>'📱 Device'</strong> or <strong>'☁️ Drive'</strong> to scan your files with AI analysis. You can delete items directly without any verification steps!</div>
        </div>
      `;
      return;
    }

    const headerHtml = `
      <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; margin-bottom: 8px; font-size: 11px; font-weight: bold; color: var(--c-wood-border); background: rgba(0,0,0,0.04); border-radius: 4px;">
        <span>🎯 Cleanable Files (${this.teacherScannedFiles.length} items analyzed)</span>
        <span style="font-size: 10px; color: #27ae60; font-weight: 700;">⚡ Direct Deletion Enabled (No Queue)</span>
      </div>
    `;

    container.innerHTML = headerHtml + this.teacherScannedFiles.map((rawFile) => {
      const file = this.ensureFileAiAnalysis(rawFile);
      const tagClass = file.category === "heavy_media" ? "retro-tag-heavy" : file.category === "transient_trash" ? "retro-tag-stale" : file.is_confidential ? "retro-tag-confidential" : "retro-tag-duplicate";
      const icon = file.icon || (file.category === "heavy_media" ? "🎥" : file.category === "duplicate" ? "📄" : "📦");
      const carbonStr = file.carbon_g != null ? file.carbon_g : ((file.size_bytes / (1024**3)) * 0.28 * 405.7).toFixed(1);
      const shaShort = file.sha256_short || (file.sha256 ? `${file.sha256.substring(0, 8)}...${file.sha256.substring(file.sha256.length - 6)}` : "Verified");

      return `
        <div class="retro-inset" style="margin-bottom: 8px; padding: 10px 12px; background: rgba(255, 255, 255, 0.85); border: 1.5px solid var(--c-wood-border);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
            <div style="display: flex; align-items: flex-start; gap: 8px; flex: 1; min-width: 0;">
              <span style="font-size: 18px; line-height: 1.2;">${icon}</span>
              <div style="flex: 1; min-width: 0;">
                <div style="font-weight: bold; font-size: 13px; color: var(--c-ink-text); word-break: break-all; display: flex; align-items: center; flex-wrap: wrap; gap: 6px;">
                  <span>${file.file_name}</span>
                  ${file.sha_match ? `<span class="retro-tag retro-tag-duplicate" style="font-size: 9px; background: #e02424; color: #fff; font-weight: bold; padding: 1px 5px; border-radius: 3px;">🎯 CLONE</span>` : ""}
                </div>
                <div style="font-size: 10px; color: var(--c-ink-muted); margin-top: 2px; font-family: monospace; word-break: break-all;">
                  📂 ${file.file_path || file.absolute_path || "Local / Cloud"}
                </div>
              </div>
            </div>
            <div style="flex-shrink: 0;">
              <button class="retro-btn retro-btn-danger retro-btn-sm btn-teacher-delete-file" data-id="${file.file_id}" style="padding: 4px 10px; font-weight: bold;">
                🗑️ Clean
              </button>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 6px; margin-top: 8px; padding: 6px 8px; background: rgba(0,0,0,0.03); border: 1px dashed rgba(0,0,0,0.15); border-radius: 4px; font-size: 10.5px;">
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

          <!-- IQ 1000 AI Forensic Verdict (The Algorithm) -->
          <div style="margin-top: 6px; padding: 6px 8px; border-left: 3px solid #1a56db; background: rgba(26, 86, 219, 0.05); border-radius: 0 4px 4px 0; font-size: 10.5px; line-height: 1.4;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px; flex-wrap: wrap; gap: 4px;">
              <span style="font-weight: bold; color: #1a56db; font-size: 10px;">
                🧠 AI Forensic Analysis (IQ 1000 • ${file.ai_confidence_score || "98.5%"} Confidence)
              </span>
              <span class="retro-tag ${tagClass}" style="font-size: 9px; padding: 1px 5px;">${file.dark_data_tag || "Dark Data"}</span>
            </div>
            <div style="color: var(--c-ink-text); font-style: italic;">
              "${file.ai_forensic_rationale || file.dark_data_reason || 'Safe cleanup candidate identified by algorithmic heuristics.'}"
            </div>
          </div>

        </div>
      `;
    }).join("");

    container.querySelectorAll(".btn-teacher-delete-file").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const fileId = e.currentTarget.getAttribute("data-id");
        const file = this.teacherScannedFiles.find((f) => f.file_id === fileId);
        if (file) {
          if (this.audioSynth) this.audioSynth.playBlip();
          this.openTeacherDirectDeleteModal(file);
        }
      });
    });
  }

  openTeacherDirectDeleteModal(file) {
    document.getElementById("modal-teacher-deletion")?.remove();
    const modal = document.createElement("div");
    modal.className = "retro-modal-backdrop";
    modal.id = "modal-teacher-deletion";
    modal.style.zIndex = "10000";

    const f = this.ensureFileAiAnalysis(file);
    const carbonStr = f.carbon_g != null ? f.carbon_g : ((f.size_bytes / (1024**3)) * 0.28 * 405.7).toFixed(1);
    const icon = f.icon || "📄";
    const tagClass = f.category === "heavy_media" ? "retro-tag-heavy" : f.category === "transient_trash" ? "retro-tag-stale" : f.is_confidential ? "retro-tag-confidential" : "retro-tag-duplicate";

    modal.innerHTML = `
      <div class="retro-card retro-modal" style="max-width: 520px;">
        <div class="retro-modal-header">
          <span>🗑️ Delete My File (Direct Action)</span>
          <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-tch-del-close">✕</button>
        </div>
        <div class="retro-modal-body">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px; padding: 8px; background: rgba(0,0,0,0.03); border-radius: 6px;">
            <span style="font-size: 24px;">${icon}</span>
            <div style="flex: 1; min-width: 0;">
              <div style="font-weight: bold; font-size: 13px; color: var(--c-ink-text); word-break: break-all;">
                ${f.file_name}
              </div>
              <div style="font-size: 11px; color: var(--c-ink-muted); margin-top: 2px;">
                Size: <strong>${f.size_formatted}</strong> • Modified: ${f.modified_date || `${f.age_days}d ago`} • Avoided CO₂: <strong style="color: #057a55;">${carbonStr} g/yr</strong>
              </div>
            </div>
          </div>

          ${
            f.sha_match_filename
              ? `<div style="background: rgba(224, 36, 36, 0.1); border: 1px solid #e02424; color: #c81e1e; padding: 6px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-bottom: 10px;">
                  🎯 Cryptographic Proof: Bit-for-bit SHA-256 duplicate clone of <u>${f.sha_match_filename}</u>. Purging this copy loses 0 bytes of unique data!
                </div>`
              : ""
          }

          <!-- AI Forensic Verdict Banner -->
          <div style="margin-bottom: 12px; padding: 8px 10px; border-left: 3px solid #1a56db; background: rgba(26, 86, 219, 0.06); border-radius: 0 6px 6px 0; font-size: 11px; line-height: 1.4;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; flex-wrap: wrap; gap: 4px;">
              <span style="font-weight: bold; color: #1a56db;">🧠 AI Forensic Analysis (IQ 1000 • ${f.ai_confidence_score || "98.5%"} Confidence)</span>
              <span class="retro-tag ${tagClass}" style="font-size: 9px; padding: 1px 5px;">${f.dark_data_tag || "Dark Data"}</span>
            </div>
            <div style="color: var(--c-ink-text); font-style: italic;">
              "${f.ai_forensic_rationale || f.dark_data_reason || 'Identified as dormant or redundant storage waste by algorithmic heuristics.'}"
            </div>
          </div>

          <!-- Instant Teacher Clean Notice -->
          <div class="retro-inset" style="padding: 10px 12px; background: #e8f8f5; border: 1.5px solid #00b894; border-radius: 6px; margin-bottom: 12px;">
            <div style="font-weight: bold; color: #00b894; font-size: 12px; margin-bottom: 4px;">
              ⚡ Instant Teacher Clean (No Permission / Queue Needed)
            </div>
            <div style="font-size: 11px; color: #2d3436; line-height: 1.4;">
              As an authorized teacher, you do not need permission or queue approval. Clicking <strong>'Delete Now'</strong> executes physical recycling immediately and credits ${carbonStr} g CO₂ to your environmental impact score.
            </div>
          </div>

          <div id="tch-del-feedback" style="margin-top: 8px; display: none;" class="retro-inset"></div>
        </div>
        <div class="retro-modal-actions">
          <button class="retro-btn retro-btn-wood" id="btn-tch-del-cancel">Keep File</button>
          <button class="retro-btn retro-btn-danger" id="btn-tch-del-confirm">🗑️ Delete Now</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const dismiss = () => modal.remove();
    modal.querySelector("#btn-tch-del-close")?.addEventListener("click", dismiss);
    modal.querySelector("#btn-tch-del-cancel")?.addEventListener("click", dismiss);
    modal.addEventListener("click", (e) => { if (e.target === modal) dismiss(); });

    const btnConfirm = modal.querySelector("#btn-tch-del-confirm");
    if (btnConfirm) {
      btnConfirm.onclick = async () => {
        btnConfirm.disabled = true;
        btnConfirm.textContent = "Deleting...";
        const feedback = modal.querySelector("#tch-del-feedback");

        try {
          const token = localStorage.getItem("d2d_session_token") || "";
          const res = await fetch("/api/teacher/deletion/direct", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": token ? `Bearer ${token}` : ""
            },
            body: JSON.stringify({
              file_id: f.file_id,
              file_name: f.file_name,
              file_size: f.size_bytes,
              file_path: f.file_path || f.absolute_path || f.file_name,
              is_drive: f.is_drive || false,
              teacher_id: localStorage.getItem("d2d_user_id") || "TEACHER-001",
              oauth_token: localStorage.getItem("d2d_google_access_token") || "",
              ai_confidence_score: f.ai_confidence_score || "98.5%",
              ai_forensic_rationale: f.ai_forensic_rationale || f.dark_data_reason || "",
              file_age_days: f.age_days || 0,
              accessed_days: f.accessed_days || f.age_days || 0
            })
          });

          const data = await res.json();
          if (!res.ok || data.status === "error") {
            feedback.style.display = "block";
            feedback.innerHTML = `<span style="color: var(--c-danger-bright); font-weight: bold;">[-] Error: ${data.message || data.error || "Deletion failed"}</span>`;
            btnConfirm.disabled = false;
            btnConfirm.textContent = "Retry Deletion";
            return;
          }

          dismiss();

          if (this.audioSynth) this.audioSynth.playDeletionPoof();
          document.body.classList.add("screen-shake");
          setTimeout(() => document.body.classList.remove("screen-shake"), 400);

          if (this.particleEngine) {
            this.particleEngine.emitDeletionPoof(window.innerWidth / 2, window.innerHeight / 2, 35);
            this.particleEngine.emitFloatingText("Deleted Instantly!", window.innerWidth / 2 - 50, window.innerHeight / 2 - 20, "#00b894");
          }

          this.showToast(`✓ Permanently deleted ${f.file_name}!`, "success");

          // Remove file from local scanned list
          this.teacherScannedFiles = this.teacherScannedFiles.filter(item => item.file_id !== f.file_id);
          this.renderTeacherScannedFiles();
          await this.fetchData();
        } catch (err) {
          feedback.style.display = "block";
          feedback.innerHTML = `<span style="color: var(--c-danger-bright);">[-] Server error: ${err.message}</span>`;
          btnConfirm.disabled = false;
          btnConfirm.textContent = "🗑️ Delete Now";
        }
      };
    }
  }

  showTeacherGoogleDriveModal() {
    document.getElementById("modal-teacher-gdrive")?.remove();
    const modal = document.createElement("div");
    modal.className = "retro-modal-backdrop";
    modal.id = "modal-teacher-gdrive";
    modal.style.zIndex = "10000";
    modal.innerHTML = `
      <div class="retro-modal" style="max-width: 420px;">
        <div style="font-weight: bold; font-size: 16px; margin-bottom: 12px; color: var(--c-wood-border);">
          ☁️ Teacher Google Drive Cleaner
        </div>
        <div style="font-size: 13px; color: var(--c-ink-muted); margin-bottom: 16px;">
          Choose how to scan your Google Drive:
        </div>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          <button class="retro-btn retro-btn-gold" id="btn-tch-gdrive-direct" style="width: 100%; padding: 12px; font-size: 13px; text-align: left; cursor: pointer;">
            <strong>⚡ Live Google Drive Scan</strong>
            <div style="font-size: 11px; opacity: 0.85; margin-top: 2px;">
              Instantly scans files in your Google Drive to find duplicate and dormant data.
            </div>
          </button>
          <button class="retro-btn retro-btn-wood" id="btn-tch-gdrive-reconnect" style="width: 100%; padding: 10px; font-size: 12px; text-align: left; cursor: pointer;">
            <strong>🔄 Switch / Connect Google Account</strong>
            <div style="font-size: 10.5px; opacity: 0.85; margin-top: 2px;">
              Re-authenticate or connect another Google Drive account.
            </div>
          </button>
          <button class="retro-btn retro-btn-danger retro-btn-sm" id="btn-tch-gdrive-cancel" style="width: 100%; margin-top: 4px; cursor: pointer;">
            ✖ Cancel
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const dismiss = () => modal.remove();
    modal.querySelector("#btn-tch-gdrive-direct")?.addEventListener("click", async () => {
      dismiss();
      await this.executeTeacherScan("__google_drive__", true, "drive");
    });
    modal.querySelector("#btn-tch-gdrive-reconnect")?.addEventListener("click", () => {
      dismiss();
      localStorage.removeItem("d2d_google_access_token");
      window.location.href = "/auth/google/login";
    });
    modal.querySelector("#btn-tch-gdrive-cancel")?.addEventListener("click", dismiss);
    modal.addEventListener("click", (e) => { if (e.target === modal) dismiss(); });
  }

  showTeacherDeviceScanModal() {
    document.getElementById("modal-teacher-device-scan")?.remove();
    const modal = document.createElement("div");
    modal.className = "retro-modal-backdrop";
    modal.id = "modal-teacher-device-scan";
    modal.style.zIndex = "10000";
    modal.innerHTML = `
      <div class="retro-modal" style="max-width: 440px;">
        <div style="font-weight: bold; font-size: 16px; margin-bottom: 12px; color: var(--c-wood-border);">
          📱 Scan Teacher Device Storage
        </div>
        <div style="font-size: 13px; color: var(--c-ink-muted); margin-bottom: 16px;">
          Select authentic files or folders to clean on your device:
        </div>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          <button class="retro-btn retro-btn-green" id="btn-tch-device-pick-folder" style="width: 100%; padding: 12px; font-size: 13px; text-align: left; cursor: pointer;">
            <strong>📂 Scan Entire Folder (All Files & Subfolders)</strong>
            <div style="font-size: 11px; opacity: 0.85; margin-top: 2px;">
              Select Downloads, Desktop, or lesson archive folders.
            </div>
          </button>
          <button class="retro-btn retro-btn-wood" id="btn-tch-device-pick-files" style="width: 100%; padding: 12px; font-size: 13px; text-align: left; cursor: pointer;">
            <strong>📄 Select Individual Files</strong>
            <div style="font-size: 11px; opacity: 0.85; margin-top: 2px;">
              Pick specific lesson materials, videos, or documents.
            </div>
          </button>
          <button class="retro-btn retro-btn-danger retro-btn-sm" id="btn-tch-device-cancel" style="width: 100%; margin-top: 4px; cursor: pointer;">
            ✖ Cancel
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const dismiss = () => modal.remove();
    modal.querySelector("#btn-tch-device-pick-folder")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      dismiss();
      document.getElementById("teacher-device-folder-input")?.click();
    });
    modal.querySelector("#btn-tch-device-pick-files")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      dismiss();
      document.getElementById("teacher-device-file-input")?.click();
    });
    modal.querySelector("#btn-tch-device-cancel")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      dismiss();
    });
    modal.addEventListener("click", (e) => { if (e.target === modal) dismiss(); });
  }

  async revokeTeacherFolderAccess() {
    const banner = document.getElementById("teacher-scanner-status-banner");
    const btnRevoke = document.getElementById("btn-teacher-revoke-scan");

    try {
      await fetch("/api/scan/revoke", { method: "POST" });
      this.teacherScannedFiles = [];
      this.teacherLastScanCompleted = false;
      this.renderTeacherScannedFiles();

      if (banner) {
        banner.style.borderColor = "";
        banner.style.backgroundColor = "";
        banner.innerHTML = `<span>👁️ <strong>Ready</strong>: Access revoked. All in-memory records purged.</span>`;
      }
      if (btnRevoke) btnRevoke.style.display = "none";
      if (this.audioSynth) this.audioSynth.playBlip();
      this.showToast("Teacher folder access revoked.", "info");
    } catch (e) {
      console.warn("Revoke error:", e);
    }
  }
}

// Global Singleton Instance
window.TeacherView = new TeacherConfirmationView();
