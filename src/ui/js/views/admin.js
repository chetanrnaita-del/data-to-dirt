/**
 * ==============================================================================
 * DATA-TO-DIRT — Admin Eco-Fund Budget & Environmental Impact View (R4 & R5)
 * Budget allocation widget, Tree-Nation threshold slider, classroom carbon charts,
 * incident audit register, and tamper-evident transaction logs.
 * ==============================================================================
 */

class AdminEcoFundView {
  constructor() {
    this.container = null;
    this.ecofund = null;
    this.analytics = null;
    this.auditData = null;
    this.audioSynth = window.RetroAudio;
  }

  mount(containerId = "view-content") {
    this.container = document.getElementById(containerId);
    if (!this.container) return;
    this.renderLayout();
    this.fetchData();
  }

  renderLayout() {
    this.container.innerHTML = `
      <div class="admin-dashboard" style="display: flex; flex-direction: column; gap: 12px; height: 100%; overflow: hidden;">

        <!-- Top Admin Header Bar -->
        <div class="retro-card" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 16px;">
          <div>
            <div style="font-weight: bold; font-size: 16px; color: var(--c-wood-border); display: flex; align-items: center; gap: 8px;">
              <span>⚙️ Admin Eco-Fund Budget & Environmental Console</span>
              <span class="retro-tag retro-tag-leaf">ADMINISTRATOR ACCESS</span>
            </div>
            <div style="font-size: 11px; color: var(--c-ink-muted); margin-top: 2px;">
              Manage cloud storage savings budget, configure donation triggers, and audit student actions.
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-adm-refresh">
              🔄 Refresh
            </button>
            <button class="retro-btn retro-btn-gold retro-btn-sm" id="btn-adm-analytics">
              📊 City Analytics
            </button>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-adm-teacher-queue">
              👨‍🏫 Teacher Queue
            </button>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-adm-return-student">
              🎒 Student View
            </button>
          </div>
        </div>

        <!-- Two-Column Master Grid -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; overflow: hidden;">

          <!-- Left Column: Eco-Fund Budget & Tree-Nation Threshold Controller -->
          <div style="display: flex; flex-direction: column; gap: 12px; overflow-y: auto; padding-right: 4px;">

            <!-- Eco-Fund Budget Widget -->
            <div class="retro-card" style="display: flex; flex-direction: column; gap: 10px;">
              <div style="font-weight: bold; font-size: 14px; color: var(--c-wood-border); border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 4px;">
                💰 Eco-Fund Budget Controller
              </div>

              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div class="retro-inset" style="padding: 10px;">
                  <div style="font-size: 11px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">Allocated Budget</div>
                  <div id="adm-budget-val" style="font-size: 24px; font-weight: bold; color: var(--c-wood-border);">$100.00</div>
                  <div style="font-size: 10px; color: var(--c-ink-light); margin-top: 2px;">School Eco-Grant</div>
                </div>
                <div class="retro-inset" style="padding: 10px;">
                  <div style="font-size: 11px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">Available Balance</div>
                  <div id="adm-balance-val" style="font-size: 24px; font-weight: bold; color: var(--c-eco-leaf);">$97.00</div>
                  <div id="adm-disbursed-label" style="font-size: 10px; color: var(--c-ink-light); margin-top: 2px;">Disbursed: $3.00</div>
                </div>
              </div>

              <!-- Budget Top-up & Adjust Form -->
              <div class="retro-inset" style="display: flex; align-items: center; gap: 8px; padding: 8px 12px;">
                <label style="font-size: 11px; font-weight: bold; white-space: nowrap;">Set Budget ($):</label>
                <input type="number" id="input-budget-amount" class="retro-input" style="width: 90px; padding: 3px 6px; font-size: 12px;" min="10" step="10" value="100" />
                <button class="retro-btn retro-btn-gold retro-btn-sm" id="btn-save-budget">Save Budget</button>
                <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-add-50-budget">+ $50</button>
              </div>

              <!-- Projected Cloud Savings & Unit Economics -->
              <div class="retro-inset" style="padding: 10px; display: flex; flex-direction: column; gap: 4px;">
                <div style="font-size: 11px; font-weight: bold; color: var(--c-wood-border);">📈 Cloud Storage Savings ROI</div>
                <div style="font-size: 11px; color: var(--c-ink-text);">
                  Storage Cost Baseline: <strong>$0.02 / GB / month</strong> ($0.24/GB/year)
                </div>
                <div id="adm-savings-calc" style="font-size: 12px; color: var(--c-eco-leaf); font-weight: bold;">
                  Projected Annual Savings: $0.00
                </div>
              </div>
            </div>

            <!-- Tree-Nation Threshold Widget -->
            <div class="retro-card" style="display: flex; flex-direction: column; gap: 10px;">
              <div style="font-weight: bold; font-size: 14px; color: var(--c-wood-border); border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 4px;">
                🌲 Reforestation Threshold Trigger (R5)
              </div>

              <p style="font-size: 12px; color: var(--c-ink-text); margin: 0;">
                When classroom cumulative verified dark data crossed this threshold, an automatic micro-donation of <strong>$1.50</strong> (1 real tree) is triggered via the Tree-Nation API.
              </p>

              <div class="retro-inset" style="display: flex; flex-direction: column; gap: 8px; padding: 10px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: bold;">
                  <span>Donation Trigger Threshold:</span>
                  <span id="label-threshold-gb" style="color: var(--c-forest-deep);">1.0 GB</span>
                </div>
                <input type="range" id="slider-threshold-gb" min="0.5" max="5.0" step="0.5" value="1.0" style="width: 100%; cursor: pointer;" />
                <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--c-ink-muted);">
                  <span>0.5 GB</span>
                  <span>1.0 GB (Default)</span>
                  <span>2.5 GB</span>
                  <span>5.0 GB</span>
                </div>
                <button class="retro-btn retro-btn-green retro-btn-sm" id="btn-save-threshold" style="align-self: flex-end; margin-top: 4px;">
                  Update Threshold
                </button>
              </div>

              <!-- Progress to Next Tree -->
              <div class="pixel-progress-wrap">
                <div class="pixel-progress-label">
                  <span>Current Waste Toward Next Tree</span>
                  <span id="adm-threshold-pct">0%</span>
                </div>
                <div class="pixel-progress-bar">
                  <div class="pixel-progress-fill" id="adm-threshold-fill" style="width: 0%;"></div>
                </div>
              </div>
            </div>

          </div>

          <!-- Right Column: School-Wide Impact Metrics & Incident Audit Log -->
          <div style="display: flex; flex-direction: column; gap: 12px; overflow-y: auto; padding-right: 4px;">

            <!-- Environmental Impact Charts & Equivalencies -->
            <div class="retro-card" style="display: flex; flex-direction: column; gap: 10px;">
              <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 4px;">
                <span style="font-weight: bold; font-size: 14px; color: var(--c-wood-border);">
                  🌍 School Environmental Impact
                </span>
                <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-export-csv">
                  📄 Export CSV Report
                </button>
              </div>

              <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                <div class="retro-inset" style="text-align: center; padding: 8px;">
                  <div style="font-size: 10px; color: var(--c-ink-muted);">CAR KM AVOIDED</div>
                  <div id="adm-eq-car" style="font-size: 16px; font-weight: bold; color: var(--c-wood-border);">0.0 km</div>
                </div>
                <div class="retro-inset" style="text-align: center; padding: 8px;">
                  <div style="font-size: 10px; color: var(--c-ink-muted);">PHONE CHARGES</div>
                  <div id="adm-eq-phone" style="font-size: 16px; font-weight: bold; color: var(--c-brass-bright);">0</div>
                </div>
                <div class="retro-inset" style="text-align: center; padding: 8px;">
                  <div style="font-size: 10px; color: var(--c-ink-muted);">ACTIVE STUDENTS</div>
                  <div id="adm-active-students" style="font-size: 16px; font-weight: bold; color: var(--c-eco-leaf);">0</div>
                </div>
              </div>
            </div>

            <!-- Disciplinary Incident Audit Register -->
            <div class="retro-card" style="flex: 1; display: flex; flex-direction: column; gap: 8px; min-height: 220px;">
              <div style="font-weight: bold; font-size: 14px; color: var(--c-danger-bright); border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 4px; display: flex; justify-content: space-between;">
                <span>🚩 Anti-Gaming Incident Register</span>
                <span id="adm-incident-count" class="retro-tag retro-tag-danger" style="font-size: 10px;">0 Flags</span>
              </div>

              <div id="adm-incident-list" class="retro-inset" style="flex: 1; overflow-y: auto; max-height: 180px; display: flex; flex-direction: column; gap: 6px; font-size: 11px;">
                <div style="text-align: center; padding: 20px; color: var(--c-ink-light);">
                  No disciplinary incidents recorded yet. Clean classroom!
                </div>
              </div>
            </div>

            <!-- Reforestation Transaction Certificates -->
            <div class="retro-card" style="display: flex; flex-direction: column; gap: 6px;">
              <div style="font-weight: bold; font-size: 13px; color: var(--c-wood-border);">
                📜 Tree-Nation Certificates Ledger
              </div>
              <div id="adm-tree-ledger" class="retro-inset" style="max-height: 120px; overflow-y: auto; font-size: 11px; display: flex; flex-direction: column; gap: 4px;">
                <div>No trees planted yet.</div>
              </div>
            </div>

          </div>

        </div>

      </div>

      <!-- Admin Toast Notifications -->
      <div id="admin-toast-container" style="position: fixed; bottom: 20px; right: 20px; z-index: 5000; display: flex; flex-direction: column; gap: 8px; pointer-events: none;"></div>
    `;

    this.bindEvents();
  }

  bindEvents() {
    // Navigation
    document.getElementById("btn-adm-return-student")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      if (window.DataToDirt) window.DataToDirt.switchRole("student");
    });

    document.getElementById("btn-adm-teacher-queue")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      if (window.TeacherView) window.TeacherView.mount("view-content");
    });

    document.getElementById("btn-adm-analytics")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      if (window.DataToDirt) window.DataToDirt.switchRole("analytics");
    });

    document.getElementById("btn-adm-refresh")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      this.fetchData();
    });

    // Logout
    document.getElementById("btn-adm-logout")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      if (window.DataToDirt) window.DataToDirt.logout();
    });

    // Save Budget
    document.getElementById("btn-save-budget")?.addEventListener("click", async () => {
      const input = document.getElementById("input-budget-amount");
      const val = parseFloat(input?.value || "100");
      if (val <= 0) return;
      await this.updateEcoFundSettings({ budget_usd: val });
    });

    // Add $50 quick topup
    document.getElementById("btn-add-50-budget")?.addEventListener("click", async () => {
      const current = this.ecofund?.budget_usd || 100.0;
      await this.updateEcoFundSettings({ budget_usd: current + 50.0 });
    });

    // Slider label update
    const slider = document.getElementById("slider-threshold-gb");
    const label = document.getElementById("label-threshold-gb");
    if (slider && label) {
      slider.addEventListener("input", (e) => {
        label.textContent = `${parseFloat(e.target.value).toFixed(1)} GB`;
      });
    }

    // Save Threshold
    document.getElementById("btn-save-threshold")?.addEventListener("click", async () => {
      const sliderEl = document.getElementById("slider-threshold-gb");
      const gbVal = parseFloat(sliderEl?.value || "1.0");
      const bytesVal = Math.round(gbVal * 1024 * 1024 * 1024);
      await this.updateEcoFundSettings({ threshold_bytes: bytesVal });
    });

    // Export CSV
    document.getElementById("btn-export-csv")?.addEventListener("click", () => {
      this.exportCsvReport();
    });
  }

  async fetchData() {
    try {
      const [ecoRes, analyticsRes, auditRes] = await Promise.all([
        fetch("/api/admin/ecofund").then((r) => r.json()),
        fetch("/api/teacher/analytics").then((r) => r.json()),
        fetch("/api/admin/audit").then((r) => r.json()).catch(() => ({})),
      ]);

      this.ecofund = ecoRes;
      this.analytics = analyticsRes;
      this.auditData = auditRes;

      this.updateView();
    } catch (e) {
      console.warn("Failed to fetch admin data:", e);
      this.showToast(`Failed to load admin data: ${e.message}`, "error");
    }
  }

  updateView() {
    if (!this.ecofund) return;

    // Budget & Balance
    const elBudget = document.getElementById("adm-budget-val");
    const elBalance = document.getElementById("adm-balance-val");
    const elDisbursed = document.getElementById("adm-disbursed-label");
    const inputBudget = document.getElementById("input-budget-amount");

    if (elBudget) elBudget.textContent = `$${this.ecofund.budget_usd.toFixed(2)}`;
    if (elBalance) elBalance.textContent = `$${this.ecofund.balance_usd.toFixed(2)}`;
    if (inputBudget) inputBudget.value = this.ecofund.budget_usd;

    const disbursed = Math.max(0, this.ecofund.budget_usd - this.ecofund.balance_usd);
    if (elDisbursed) elDisbursed.textContent = `Disbursed: $${disbursed.toFixed(2)} (${this.ecofund.trees_planted} trees)`;

    // Projected Savings ROI
    const elSavings = document.getElementById("adm-savings-calc");
    const clearedGb = this.analytics?.total_data_cleaned_gb || (this.ecofund.cumulative_waste_bytes / (1024 ** 3));
    const annualSavings = clearedGb * 0.02 * 12.0;
    if (elSavings) {
      elSavings.textContent = `Projected Annual Cloud Savings: $${annualSavings.toFixed(2)} (Net ROI: +$${Math.max(0, annualSavings - disbursed).toFixed(2)})`;
    }

    // Threshold & Progress
    const threshBytes = this.ecofund.threshold_bytes || 1073741824;
    const threshGb = threshBytes / (1024 ** 3);
    const slider = document.getElementById("slider-threshold-gb");
    const label = document.getElementById("label-threshold-gb");
    if (slider) slider.value = threshGb;
    if (label) label.textContent = `${threshGb.toFixed(1)} GB`;

    const cumulative = this.ecofund.cumulative_waste_bytes || 0;
    const prevTarget = (this.ecofund.trees_planted || 0) * threshBytes;
    const progress = Math.min(100, Math.max(0, Math.round(((cumulative - prevTarget) / threshBytes) * 100)));

    const elPct = document.getElementById("adm-threshold-pct");
    const elFill = document.getElementById("adm-threshold-fill");
    if (elPct) elPct.textContent = `${progress}%`;
    if (elFill) elFill.style.width = `${progress}%`;

    // Equivalencies
    const elCar = document.getElementById("adm-eq-car");
    const elPhone = document.getElementById("adm-eq-phone");
    const elActive = document.getElementById("adm-active-students");
    if (elCar) elCar.textContent = `${(this.analytics?.car_km_avoided || 0).toFixed(1)} km`;
    if (elPhone) elPhone.textContent = `${Math.round(this.analytics?.smartphone_charges_avoided || 0)}`;
    if (elActive) elActive.textContent = `${this.analytics?.active_students_count || 0}`;

    // Incident Log
    const elIncidentCount = document.getElementById("adm-incident-count");
    const elIncidentList = document.getElementById("adm-incident-list");
    const incidents = this.auditData?.incident_log || this.analytics?.incident_log || [];
    if (elIncidentCount) elIncidentCount.textContent = `${incidents.length} Flags`;

    if (elIncidentList) {
      if (incidents.length === 0) {
        elIncidentList.innerHTML = `
          <div style="text-align: center; padding: 20px; color: var(--c-ink-light);">
            ✨ No disciplinary incidents recorded yet. Clean classroom!
          </div>
        `;
      } else {
        elIncidentList.innerHTML = incidents.map((inc) => `
          <div style="border-left: 3px solid var(--c-danger-bright); padding: 4px 8px; background: rgba(255,255,255,0.4);">
            <div style="font-weight: bold; color: var(--c-danger-bright); display: flex; justify-content: space-between;">
              <span>Student: ${inc.student_id}</span>
              <span style="font-size: 10px; color: var(--c-ink-muted);">${inc.request_id}</span>
            </div>
            <div>File: <strong>${inc.file_name}</strong> • AI Score: ${Math.round((inc.ai_score || 0) * 100)}%</div>
            <div style="font-style: italic; color: var(--c-ink-muted);">"${inc.reason}"</div>
            <div style="color: var(--c-ink-text);">Action Note: ${inc.feedback || "Strike applied"}</div>
          </div>
        `).join("");
      }
    }

    // Tree Certificates
    const elLedger = document.getElementById("adm-tree-ledger");
    if (elLedger && this.ecofund.donations_history) {
      if (this.ecofund.donations_history.length === 0) {
        elLedger.innerHTML = `
          <div style="text-align: center; color: var(--c-ink-muted); font-size: 11px; padding: 12px;">
            No tree certificates issued yet. Trees are funded automatically as participants clean storage.
          </div>
        `;
      } else {
        elLedger.innerHTML = this.ecofund.donations_history.map((d) => `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 3px 0; border-bottom: 1px dashed var(--c-parchment-border);">
            <span>🌲 <strong>${d.tree_id}</strong>: ${d.species}</span>
            <span style="color: var(--c-eco-leaf); font-weight: bold;">+${d.co2_offset_kg} kg CO₂</span>
          </div>
        `).join("");
      }
    }
  }

  async updateEcoFundSettings(payload) {
    try {
      const res = await fetch("/api/admin/ecofund", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).then((r) => r.json());

      if (res.status === "updated") {
        if (this.audioSynth) this.audioSynth.playCoinDing();
        this.showToast("✓ Eco-Fund settings successfully updated!", "success");
        await this.fetchData();
      }
    } catch (e) {
      this.showToast(`Failed to update settings: ${e.message}`, "error");
    }
  }

  exportCsvReport() {
    if (!this.analytics) return;
    const rows = [
      ["Metric", "Value", "Unit"],
      ["Total Requests", this.analytics.total_requests || 0, "count"],
      ["Approved Deletions", this.analytics.approved_count || 0, "count"],
      ["Rejected Requests", this.analytics.rejected_count || 0, "count"],
      ["Flagged Incidents", this.analytics.flagged_count || 0, "count"],
      ["Total Data Cleared", (this.analytics.total_data_cleaned_gb || 0).toFixed(4), "GB"],
      ["Total Carbon Offset", (this.analytics.total_carbon_offset_kg || 0).toFixed(4), "kg CO2e"],
      ["Trees Funded", this.analytics.total_trees_funded || 0, "trees"],
      ["Active Students", this.analytics.active_students_count || 0, "students"],
      ["Car Travel Avoided", (this.analytics.car_km_avoided || 0).toFixed(2), "km"],
      ["Smartphone Charges Avoided", Math.round(this.analytics.smartphone_charges_avoided || 0), "charges"],
    ];

    const csvContent = "data:text/csv;charset=utf-8," + rows.map((e) => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `data_to_dirt_audit_report_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    this.showToast("📄 Audit CSV Report downloaded successfully!", "success");
  }

  showToast(message, type = "info") {
    const container = document.getElementById("admin-toast-container");
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
    } else if (type === "error" || type === "warning") {
      toast.style.border = "3px solid var(--c-danger-bright)";
      toast.style.color = "var(--c-danger-bright)";
    }

    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.4s";
      setTimeout(() => toast.remove(), 400);
    }, 3500);
  }
}

// Global Singleton Instance
window.AdminView = new AdminEcoFundView();
