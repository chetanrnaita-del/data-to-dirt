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
            <button class="retro-btn retro-btn-gold retro-btn-sm" id="btn-t-admin" title="Admin Panel">
              ⚙️ Admin
            </button>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-t-return-student" title="Student View">
              🎒 Student
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
          <!-- Status Filters -->
          <div style="display: flex; gap: 6px;" id="filter-buttons-group">
            <button class="retro-btn retro-btn-sm btn-filter retro-btn-gold" data-filter="pending">Pending</button>
            <button class="retro-btn retro-btn-sm btn-filter retro-btn-wood" data-filter="all">All</button>
            <button class="retro-btn retro-btn-sm btn-filter retro-btn-wood" data-filter="approved">Approved</button>
            <button class="retro-btn retro-btn-sm btn-filter retro-btn-wood" data-filter="rejected">Rejected</button>
            <button class="retro-btn retro-btn-sm btn-filter retro-btn-wood" data-filter="flagged">Flagged</button>
          </div>

          <!-- Search & Sort -->
          <div style="display: flex; align-items: center; gap: 8px;">
            <input type="text" id="t-search-input" class="retro-input" placeholder="Search filename, reason, student..." style="padding: 4px 8px; font-size: 12px; width: 220px;" />
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-sort-confidence" title="Sort by AI Confidence (Low/High)">
              🤖 AI Score: <span id="sort-order-label">Lowest First</span>
            </button>
          </div>
        </div>

        <!-- Queue Items Scrollable List Container -->
        <div class="retro-card" style="flex: 1; overflow: hidden; display: flex; flex-direction: column; gap: 8px;">
          <div id="t-queue-scroll-area" style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding-right: 4px;">
            <div style="text-align: center; padding: 40px; color: var(--c-ink-light); font-size: 13px;">
              Loading confirmation queue...
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
    // Return to student view
    document.getElementById("btn-t-return-student")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      if (window.DataToDirt) window.DataToDirt.switchRole("student");
    });

    // Student directory & creation
    document.getElementById("btn-t-manage-students")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      this.openStudentDirectoryModal();
    });

    // Admin panel switch
    document.getElementById("btn-t-admin")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      if (window.DataToDirt) {
        window.DataToDirt.switchRole("admin");
      } else if (window.AdminView) {
        window.AdminView.mount("view-content");
      }
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
  }

  async fetchData() {
    try {
      const [queueRes, analyticsRes] = await Promise.all([
        fetch("/api/teacher/queue").then((r) => r.json()),
        fetch("/api/teacher/analytics").then((r) => r.json()),
      ]);

      this.queue = queueRes.queue || [];
      this.analytics = analyticsRes || {};

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
    let defaultClassCode = (window.DataToDirt?.classCode || "").toLowerCase();
    if (!defaultClassCode) {
      const u = (window.DataToDirt?.userId || "").toLowerCase();
      for (const c of ["bio101", "env201", "cs301", "chem102", "earth204"]) {
        if (u.includes(c)) {
          defaultClassCode = c;
          break;
        }
      }
    }
    if (!defaultClassCode) defaultClassCode = "bio101";

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
                  <input type="text" id="stu-input-name" class="retro-input" placeholder="e.g. Alex Johnson" style="width: 100%; box-sizing: border-box; font-size: 12px; padding: 6px 8px; border: 1.5px solid #a27848; border-radius: 4px;" />
                </div>
                <div>
                  <label style="display: block; font-size: 11px; font-weight: bold; margin-bottom: 4px; color: #4a2e18;">Class Code *</label>
                  <input type="text" id="stu-input-class" class="retro-input" value="${defaultClassCode}" placeholder="e.g. bio101" style="width: 100%; box-sizing: border-box; font-size: 12px; padding: 6px 8px; border: 1.5px solid #a27848; border-radius: 4px;" />
                </div>
              </div>

              <div style="margin-bottom: 12px;">
                <label style="display: block; font-size: 11px; font-weight: bold; margin-bottom: 4px; color: #4a2e18;">Student ID (Login Identifier)</label>
                <div style="display: flex; gap: 6px;">
                  <input type="text" id="stu-input-id" class="retro-input" value="${genId()}" placeholder="e.g. STU-001 or STU-A7F9B1" style="flex: 1; font-size: 12px; font-family: monospace; font-weight: bold; padding: 6px 8px; border: 1.5px solid #a27848; border-radius: 4px;" />
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
                <div style="display: flex; gap: 6px; align-items: center;">
                  <input type="text" id="stu-search-filter" class="retro-input" placeholder="Search by name or ID..." style="font-size: 11px; padding: 4px 8px; width: 180px; border: 1px solid #ccc; border-radius: 4px;" />
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
              ${currentStudents.length === 0 ? "No student records found. Create one above!" : "No students match your search filter."}
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
        return `
          <tr style="border-bottom: 1px solid #f0e6d6;">
            <td style="padding: 7px 10px; font-family: monospace; font-weight: bold; color: #2980b9;">
              ${sid}
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

    const loadStudents = async () => {
      try {
        const res = await fetch(`/api/teacher/students?class_code=${encodeURIComponent(defaultClassCode)}`);
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
        if (this.audioSynth) this.audioSynth.playCoinDing();
        if (this.particleEngine) this.particleEngine.emitConfetti();

        if (msgEl) {
          msgEl.style.display = "block";
          msgEl.style.background = "#e8f8f5";
          msgEl.style.color = "#27ae60";
          msgEl.textContent = `✓ ${result.message || "Student created successfully!"}`;
        }

        this.showToast(result.message || `Student ID ${studentId} saved!`, "success");

        // Clear input name and auto-gen next ID for quick entry
        if (nameInput) nameInput.value = "";
        if (idInput) idInput.value = genId();

        // Refresh directory
        await loadStudents();
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
}

// Global Singleton Instance
window.TeacherView = new TeacherConfirmationView();
