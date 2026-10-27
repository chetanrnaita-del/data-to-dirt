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
      <div class="admin-dashboard" style="display: flex; flex-direction: column; gap: 12px; height: 100%; overflow-y: auto; -webkit-overflow-scrolling: touch; padding: 12px; box-sizing: border-box;">

        <!-- Top Admin Header Bar -->
        <div class="retro-card" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; flex-wrap: wrap; gap: 10px;">
          <div>
            <div style="font-weight: bold; font-size: 16px; color: var(--c-wood-border); display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <span>⚙️ Admin Eco-Fund Budget & Environmental Console</span>
              <span class="retro-tag retro-tag-leaf">ADMINISTRATOR ACCESS</span>
            </div>
            <div style="font-size: 11px; color: var(--c-ink-muted); margin-top: 2px;">
              Manage cloud storage savings budget, configure donation triggers, and audit student actions.
            </div>
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <button class="retro-btn retro-btn-green retro-btn-sm" id="btn-adm-manage-teachers" title="Create & Manage Teacher Accounts">
              👨‍🏫 Manage Teachers
            </button>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-adm-refresh">
              🔄 Refresh
            </button>
            <button class="retro-btn retro-btn-gold retro-btn-sm" id="btn-adm-analytics">
              📊 City Analytics
            </button>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-adm-teacher-queue">
              👨‍🏫 Teacher Queue
            </button>
            <button class="retro-btn retro-btn-danger retro-btn-sm" id="btn-adm-logout">
              🚪 Logout
            </button>
          </div>
        </div>

        <!-- Responsive Master Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; flex: 1;">

          <!-- Left Column: Eco-Fund Budget & Tree-Nation Threshold Controller -->
          <div style="display: flex; flex-direction: column; gap: 12px;">

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
                  <div id="adm-balance-val" style="font-size: 24px; font-weight: bold; color: var(--c-eco-leaf);">$100.00</div>
                  <div id="adm-disbursed-label" style="font-size: 10px; color: var(--c-ink-light); margin-top: 2px;">Disbursed: $0.00</div>
                </div>
              </div>

              <!-- Budget Top-up & Adjust Form -->
              <div class="retro-inset" style="display: flex; align-items: center; gap: 8px; padding: 8px 12px; flex-wrap: wrap;">
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
          <div style="display: flex; flex-direction: column; gap: 12px;">

            <!-- Environmental Impact Charts & Equivalencies -->
            <div class="retro-card" style="display: flex; flex-direction: column; gap: 10px;">
              <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 4px; flex-wrap: wrap; gap: 6px;">
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
            <div class="retro-card" style="display: flex; flex-direction: column; gap: 8px; min-height: 200px;">
              <div style="font-weight: bold; font-size: 14px; color: var(--c-danger-bright); border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 4px; display: flex; justify-content: space-between;">
                <span>🚩 Anti-Gaming Incident Register</span>
                <span id="adm-incident-count" class="retro-tag retro-tag-danger" style="font-size: 10px;">0 Flags</span>
              </div>

              <div id="adm-incident-list" class="retro-inset" style="max-height: 180px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; font-size: 11px;">
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
              <div id="adm-tree-ledger" class="retro-inset" style="max-height: 140px; overflow-y: auto; font-size: 11px; display: flex; flex-direction: column; gap: 4px;">
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
    document.getElementById("btn-adm-manage-teachers")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      this.openTeacherDirectoryModal();
    });

    document.getElementById("btn-adm-teacher-queue")?.addEventListener("click", () => {
      if (this.audioSynth) this.audioSynth.playBlip();
      if (window.DataToDirt) {
        window.DataToDirt.switchRole("teacher");
      } else if (window.TeacherView) {
        window.TeacherView.mount("view-content");
      }
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

  getAuthHeaders(extra = {}) {
    const token = localStorage.getItem("d2d_session_token") || "";
    const headers = { ...extra };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }

  async fetchData() {
    try {
      const headers = this.getAuthHeaders();
      const [ecoRes, analyticsRes, auditRes] = await Promise.all([
        fetch("/api/admin/ecofund", { headers }).then((r) => r.ok ? r.json() : {}).catch(() => ({})),
        fetch("/api/teacher/analytics", { headers }).then((r) => r.ok ? r.json() : {}).catch(() => ({})),
        fetch("/api/admin/audit", { headers }).then((r) => r.ok ? r.json() : {}).catch(() => ({})),
      ]);

      this.ecofund = ecoRes && Object.keys(ecoRes).length > 0
        ? ecoRes
        : { budget_usd: 100, balance_usd: 100, trees_planted: 0, cumulative_waste_bytes: 0, donations_history: [] };
      this.analytics = analyticsRes || {};
      this.auditData = auditRes || {};

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

    const budget = Number(this.ecofund.budget_usd != null ? this.ecofund.budget_usd : 100);
    const balance = Number(this.ecofund.balance_usd != null ? this.ecofund.balance_usd : 100);

    if (elBudget) elBudget.textContent = `$${budget.toFixed(2)}`;
    if (elBalance) elBalance.textContent = `$${balance.toFixed(2)}`;
    if (inputBudget) inputBudget.value = budget;

    const disbursed = Math.max(0, budget - balance);
    const treesPlanted = Number(this.ecofund.trees_planted || 0);
    if (elDisbursed) elDisbursed.textContent = `Disbursed: $${disbursed.toFixed(2)} (${treesPlanted} trees)`;

    // Projected Savings ROI
    const elSavings = document.getElementById("adm-savings-calc");
    const clearedGb = Number(this.analytics?.total_data_cleaned_gb || 0) || (Number(this.ecofund.cumulative_waste_bytes || 0) / (1024 ** 3));
    const annualSavings = clearedGb * 0.02 * 12.0;
    if (elSavings) {
      elSavings.textContent = `Projected Annual Cloud Savings: $${annualSavings.toFixed(2)} (Net ROI: +$${Math.max(0, annualSavings - disbursed).toFixed(2)})`;
    }

    // Threshold & Progress
    const threshBytes = Number(this.ecofund.threshold_bytes) || 1073741824;
    const threshGb = threshBytes / (1024 ** 3);
    const slider = document.getElementById("slider-threshold-gb");
    const label = document.getElementById("label-threshold-gb");
    if (slider) slider.value = threshGb;
    if (label) label.textContent = `${threshGb.toFixed(1)} GB`;

    const cumulative = Number(this.ecofund.cumulative_waste_bytes) || 0;
    const prevTarget = treesPlanted * threshBytes;
    const progress = Math.min(100, Math.max(0, Math.round(((cumulative - prevTarget) / threshBytes) * 100)));

    const elPct = document.getElementById("adm-threshold-pct");
    const elFill = document.getElementById("adm-threshold-fill");
    if (elPct) elPct.textContent = `${progress}%`;
    if (elFill) elFill.style.width = `${progress}%`;

    // Equivalencies
    const elCar = document.getElementById("adm-eq-car");
    const elPhone = document.getElementById("adm-eq-phone");
    const elActive = document.getElementById("adm-active-students");
    if (elCar) elCar.textContent = `${Number(this.analytics?.car_km_avoided || 0).toFixed(1)} km`;
    if (elPhone) elPhone.textContent = `${Math.round(Number(this.analytics?.smartphone_charges_avoided || 0))}`;
    if (elActive) elActive.textContent = `${Number(this.analytics?.active_students_count || 0)}`;

    // Incident Log
    const elIncidentCount = document.getElementById("adm-incident-count");
    const elIncidentList = document.getElementById("adm-incident-list");
    const incidents = Array.isArray(this.auditData?.incident_log)
      ? this.auditData.incident_log
      : (Array.isArray(this.analytics?.incident_log) ? this.analytics.incident_log : []);
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
          <div style="border-left: 3px solid var(--c-danger-bright); padding: 4px 8px; background: rgba(255,255,255,0.4); margin-bottom: 4px;">
            <div style="font-weight: bold; color: var(--c-danger-bright); display: flex; justify-content: space-between;">
              <span>Student: ${inc.student_id || 'Unknown'}</span>
              <span style="font-size: 10px; color: var(--c-ink-muted);">${inc.request_id || ''}</span>
            </div>
            <div>File: <strong>${inc.file_name || 'unknown'}</strong> • AI Score: ${Math.round(Number(inc.ai_score || 0) * 100)}%</div>
            <div style="font-style: italic; color: var(--c-ink-muted);">"${inc.reason || 'Flagged by Teacher'}"</div>
            <div style="color: var(--c-ink-text);">Action Note: ${inc.feedback || "Strike applied"}</div>
          </div>
        `).join("");
      }
    }

    // Tree Certificates
    const elLedger = document.getElementById("adm-tree-ledger");
    const history = Array.isArray(this.ecofund.donations_history) ? this.ecofund.donations_history : [];
    if (elLedger) {
      if (history.length === 0) {
        elLedger.innerHTML = `
          <div style="text-align: center; color: var(--c-ink-muted); font-size: 11px; padding: 12px;">
            No tree certificates issued yet. Trees are funded automatically as participants clean storage.
          </div>
        `;
      } else {
        elLedger.innerHTML = history.map((d) => `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 3px 0; border-bottom: 1px dashed var(--c-parchment-border);">
            <span>🌲 <strong>${d.tree_id || d.id || 'TN-TREE'}</strong>: ${d.species || 'Mangrove'}</span>
            <span style="color: var(--c-eco-leaf); font-weight: bold;">+${Number(d.co2_offset_kg || 250).toFixed(0)} kg CO₂</span>
          </div>
        `).join("");
      }
    }
  }

  async updateEcoFundSettings(payload) {
    try {
      const res = await fetch("/api/admin/ecofund", {
        method: "POST",
        headers: this.getAuthHeaders({ "Content-Type": "application/json" }),
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

  openTeacherDirectoryModal() {
    const existingModal = document.getElementById("modal-teacher-directory");
    if (existingModal) existingModal.remove();

    const genId = () => "teacher_" + Math.random().toString(36).substring(2, 7);

    const modalHtml = `
      <div class="retro-modal-backdrop" id="modal-teacher-directory" style="position: fixed; inset: 0; background: rgba(0,0,0,0.65); display: flex; align-items: center; justify-content: center; z-index: 6000; padding: 12px; backdrop-filter: blur(2px);">
        <div class="retro-card retro-modal" style="max-width: 720px; width: 100%; max-height: 90vh; display: flex; flex-direction: column; overflow: hidden; padding: 0; border: 3px solid var(--c-wood-border, #4a2e18); box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
          
          <!-- Modal Header -->
          <div class="retro-modal-header" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 18px; background: #3e2714; color: #f5eedc; border-bottom: 2px solid #231308;">
            <div style="font-weight: bold; font-size: 15px; display: flex; align-items: center; gap: 10px;">
              <span>👨‍🏫 Teacher Account Manager & Directory</span>
              <span class="retro-tag retro-tag-clean" style="font-size: 10px; padding: 2px 6px;">ADMINISTRATOR CONSOLE</span>
            </div>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-adm-tch-close" style="padding: 2px 8px; font-weight: bold; cursor: pointer;">✕</button>
          </div>

          <!-- Scrollable Content -->
          <div class="retro-modal-body" style="padding: 16px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 14px; background: #fbf8f0;">
            
            <!-- Section 1: Create Teacher Form -->
            <div class="retro-card" style="padding: 14px; background: #fff9ed; border: 2px solid #b8860b;">
              <div style="font-weight: bold; font-size: 13px; margin-bottom: 10px; color: #5c381e; display: flex; justify-content: space-between; align-items: center;">
                <span>➕ Create & Enroll New Teacher Account</span>
                <span style="font-size: 11px; font-weight: normal; color: #7f5539;">Allows teacher to review student deletions and direct-clean files</span>
              </div>

              <div style="display: grid; grid-template-columns: 1.2fr 1fr; gap: 10px; margin-bottom: 8px;">
                <div>
                  <label style="display: block; font-size: 11px; font-weight: bold; margin-bottom: 4px; color: #3e2714;">Teacher Full Name *</label>
                  <input type="text" id="input-adm-tch-name" class="retro-input" placeholder="Enter Teacher Full Name" style="width: 100%; box-sizing: border-box; font-size: 12px; padding: 6px 8px;" />
                </div>
                <div>
                  <label style="display: block; font-size: 11px; font-weight: bold; margin-bottom: 4px; color: #3e2714;">Teacher ID / Username *</label>
                  <div style="display: flex; gap: 4px;">
                    <input type="text" id="input-adm-tch-id" class="retro-input" placeholder="Enter Teacher ID / Username" style="flex: 1; font-size: 12px; padding: 6px 8px;" />
                    <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-adm-tch-gen-id" type="button" title="Generate ID">🎲</button>
                  </div>
                </div>
              </div>

              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
                <div>
                  <label style="display: block; font-size: 11px; font-weight: bold; margin-bottom: 4px; color: #3e2714;">Assigned Class Code *</label>
                  <select id="select-adm-tch-class" class="retro-input" style="width: 100%; box-sizing: border-box; font-size: 12px; padding: 6px 8px; cursor: pointer;">
                    <option value="all">🌐 All Classes (School-Wide)</option>
                    <option value="bio101">🌿 Bio 101</option>
                    <option value="cs301">💻 CS 301</option>
                    <option value="env201">🌍 Env 201</option>
                    <option value="chem102">🧪 Chem 102</option>
                    <option value="earth204">⛰️ Earth 204</option>
                    <option value="custom">✏️ Other / Custom Class Code...</option>
                  </select>
                  <input type="text" id="input-adm-tch-custom-class" class="retro-input" placeholder="Enter custom class code (e.g. phys201)" style="width: 100%; box-sizing: border-box; font-size: 12px; padding: 6px 8px; margin-top: 4px; display: none;" />
                </div>
                <div>
                  <label style="display: block; font-size: 11px; font-weight: bold; margin-bottom: 4px; color: #3e2714;">Password / PIN *</label>
                  <input type="text" id="input-adm-tch-pin" class="retro-input" value="teacher123" placeholder="Default: teacher123" style="width: 100%; box-sizing: border-box; font-size: 12px; padding: 6px 8px;" />
                </div>
              </div>

              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div id="adm-tch-feedback" style="font-size: 11px; font-weight: bold; display: none; padding: 4px 8px; border-radius: 4px;"></div>
                <button class="retro-btn retro-btn-green" id="btn-adm-save-teacher" style="padding: 6px 14px; font-weight: bold; cursor: pointer; margin-left: auto;">
                  💾 Save & Enroll Teacher
                </button>
              </div>
            </div>

            <!-- Section 2: Teacher Directory List -->
            <div class="retro-card" style="padding: 14px; display: flex; flex-direction: column; gap: 8px;">
              <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px dashed #dcdde1; padding-bottom: 6px;">
                <div style="font-weight: bold; font-size: 13px; color: #2d3436; display: flex; align-items: center; gap: 8px;">
                  <span>📋 Registered Teacher Directory</span>
                  <span id="adm-tch-count-badge" class="retro-tag retro-tag-clean" style="font-size: 10px;">0 Teachers</span>
                </div>
                <input type="text" id="input-adm-tch-search" class="retro-input" placeholder="Search teacher or class..." style="font-size: 11px; padding: 3px 6px; width: 170px;" />
              </div>

              <!-- Directory Table -->
              <div class="retro-inset" style="max-height: 240px; overflow-y: auto; padding: 4px; background: #fff;">
                <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                  <thead>
                    <tr style="border-bottom: 2px solid #dfe6e9; text-align: left; color: #636e72;">
                      <th style="padding: 6px 8px;">Teacher Name</th>
                      <th style="padding: 6px 8px;">Username / ID</th>
                      <th style="padding: 6px 8px;">Class</th>
                      <th style="padding: 6px 8px;">Password</th>
                      <th style="padding: 6px 8px;">Enrolled</th>
                      <th style="padding: 6px 8px; text-align: right;">Action</th>
                    </tr>
                  </thead>
                  <tbody id="adm-tch-table-body">
                    <tr><td colspan="6" style="text-align: center; padding: 16px; color: #b2bec3;">Loading teacher directory...</td></tr>
                  </tbody>
                </table>
              </div>
            </div>

          </div>
          
          <div class="retro-modal-actions" style="padding: 10px 18px; background: #ede3d1; border-top: 2px solid #d4c2a5; display: flex; justify-content: flex-end;">
            <button class="retro-btn retro-btn-wood" id="btn-adm-tch-close-footer" style="padding: 6px 16px; cursor: pointer;">Close Directory</button>
          </div>

        </div>
      </div>
    `;

    document.body.insertAdjacentHTML("beforeend", modalHtml);
    const modal = document.getElementById("modal-teacher-directory");

    let allTeachers = [];

    const loadTeachers = async () => {
      const tbody = document.getElementById("adm-tch-table-body");
      const badge = document.getElementById("adm-tch-count-badge");
      try {
        const token = localStorage.getItem("d2d_session_token") || "";
        const res = await fetch("/api/admin/teachers", {
          headers: token ? { "Authorization": `Bearer ${token}` } : {}
        });
        const data = await res.json();
        allTeachers = data.teachers || [];
        renderTable(allTeachers);
        if (badge) badge.textContent = `${allTeachers.length} Teachers`;
      } catch (e) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:16px; color:#e74c3c;">Failed to load teachers: ${e.message}</td></tr>`;
      }
    };

    const renderTable = (list) => {
      const tbody = document.getElementById("adm-tch-table-body");
      if (!tbody) return;
      if (!list || list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 16px; color: #636e72;">No teacher accounts found matching filter.</td></tr>`;
        return;
      }
      tbody.innerHTML = list.map((t) => {
        const cCode = (t.class_code || "all").toUpperCase();
        const tid = t.teacher_id || t.user_id || "";
        const isBuiltIn = ["teacher_bio101", "teacher_env201", "teacher_cs301", "teacher_chem102", "teacher_earth204"].includes(tid.toLowerCase());
        const actionHtml = isBuiltIn ? `<span style="font-size: 10px; color: #b2bec3;">System</span>` : `
          <button type="button" class="btn-delete-teacher" data-tid="${tid}" style="background: #ff7675; color: white; border: none; border-radius: 4px; padding: 2px 7px; font-size: 10px; cursor: pointer; font-weight: bold; transition: background 0.2s;">
            🗑️ Delete
          </button>
        `;
        return `
          <tr style="border-bottom: 1px solid #f1f2f6;">
            <td style="padding: 6px 8px; font-weight: bold; color: #2d3436;">🧑‍🏫 ${t.name || t.teacher_id}</td>
            <td style="padding: 6px 8px; font-family: monospace; color: #2d6a36;"><code>${tid}</code></td>
            <td style="padding: 6px 8px;"><span class="retro-tag retro-tag-clean" style="font-size: 9.5px; padding: 1px 5px;">${cCode}</span></td>
            <td style="padding: 6px 8px; font-family: monospace; color: #636e72;">${t.pin || "teacher123"}</td>
            <td style="padding: 6px 8px; color: #95a5a6; font-size: 10px;">${t.created_at_iso || "Pre-installed"}</td>
            <td style="padding: 6px 8px; text-align: right;">${actionHtml}</td>
          </tr>
        `;
      }).join("");

      tbody.querySelectorAll('.btn-delete-teacher').forEach(btn => {
        btn.addEventListener('click', async () => {
          const tid = btn.dataset.tid;
          if (!confirm(`Are you sure you want to delete teacher account '${tid}'?`)) return;
          try {
            btn.disabled = true;
            btn.textContent = '...';
            const token = localStorage.getItem('d2d_session_token') || '';
            const res = await fetch('/api/admin/teachers/delete', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': token ? `Bearer ${token}` : ''
              },
              body: JSON.stringify({ teacher_id: tid })
            });
            const d = await res.json();
            if (d.status === 'deleted') {
              loadTeachers();
            } else {
              alert(d.message || 'Failed to delete teacher.');
              btn.disabled = false;
              btn.textContent = '🗑️ Delete';
            }
          } catch (err) {
            alert('Network error while deleting teacher: ' + err.message);
            btn.disabled = false;
            btn.textContent = '🗑️ Delete';
          }
        });
      });
    };

    // Auto-generate ID when name is typed
    const nameInput = document.getElementById("input-adm-tch-name");
    const idInput = document.getElementById("input-adm-tch-id");
    const classSelect = document.getElementById("select-adm-tch-class");
    const customClassInput = document.getElementById("input-adm-tch-custom-class");

    nameInput?.addEventListener("input", () => {
      if (!idInput.dataset.manual) {
        const slug = nameInput.value.trim().toLowerCase().replace(/[^a-z0-9]/g, "");
        idInput.value = slug ? `teacher_${slug}` : "";
      }
    });

    idInput?.addEventListener("input", () => {
      idInput.dataset.manual = "true";
    });

    document.getElementById("btn-adm-tch-gen-id")?.addEventListener("click", () => {
      idInput.value = genId();
      idInput.dataset.manual = "true";
    });

    classSelect?.addEventListener("change", () => {
      if (classSelect.value === "custom") {
        customClassInput.style.display = "block";
        customClassInput.focus();
      } else {
        customClassInput.style.display = "none";
      }
    });

    // Search filter
    document.getElementById("input-adm-tch-search")?.addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase().trim();
      if (!q) {
        renderTable(allTeachers);
        return;
      }
      const filtered = allTeachers.filter(t => 
        (t.name || "").toLowerCase().includes(q) ||
        (t.teacher_id || "").toLowerCase().includes(q) ||
        (t.class_code || "").toLowerCase().includes(q)
      );
      renderTable(filtered);
    });

    // Save Teacher
    const saveBtn = document.getElementById("btn-adm-save-teacher");
    saveBtn?.addEventListener("click", async () => {
      const name = nameInput?.value.trim();
      let teacherId = idInput?.value.trim();
      let classCode = classSelect?.value;
      if (classCode === "custom") {
        classCode = customClassInput?.value.trim().toLowerCase();
      }
      const pin = document.getElementById("input-adm-tch-pin")?.value.trim() || "teacher123";
      const feedback = document.getElementById("adm-tch-feedback");

      if (!name) {
        if (feedback) {
          feedback.style.display = "block";
          feedback.style.background = "#ffeaa7";
          feedback.style.color = "#d63031";
          feedback.textContent = "[-] Please enter the teacher's full name.";
        }
        nameInput?.focus();
        return;
      }

      if (!teacherId) {
        teacherId = genId();
      }

      saveBtn.disabled = true;
      saveBtn.textContent = "Creating...";

      try {
        const token = localStorage.getItem("d2d_session_token") || "";
        const res = await fetch("/api/admin/teachers/create", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": token ? `Bearer ${token}` : ""
          },
          body: JSON.stringify({
            name: name,
            teacher_id: teacherId,
            class_code: classCode || "all",
            pin: pin
          })
        });

        const data = await res.json();
        if (!res.ok || data.status === "error") {
          if (feedback) {
            feedback.style.display = "block";
            feedback.style.background = "#ffeaa7";
            feedback.style.color = "#d63031";
            feedback.textContent = `[-] ${data.message || data.error || "Failed to create teacher"}`;
          }
          if (this.audioSynth) this.audioSynth.playGamingBuzzer();
          return;
        }

        // Success!
        if (feedback) {
          feedback.style.display = "block";
          feedback.style.background = "#e8f8f5";
          feedback.style.color = "#27ae60";
          feedback.textContent = `✓ Teacher '${name}' (${data.teacher.teacher_id}) created successfully!`;
        }
        if (this.audioSynth) this.audioSynth.playCoinDing();
        this.showToast(`Teacher '${name}' enrolled!`, "success");

        // Reset form
        nameInput.value = "";
        idInput.value = "";
        delete idInput.dataset.manual;
        if (customClassInput) customClassInput.value = "";

        // Reload table
        await loadTeachers();
      } catch (err) {
        if (feedback) {
          feedback.style.display = "block";
          feedback.style.background = "#ffeaa7";
          feedback.style.color = "#d63031";
          feedback.textContent = `[-] Network error: ${err.message}`;
        }
      } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "💾 Save & Enroll Teacher";
      }
    });

    // Dismiss modal
    const dismiss = () => modal.remove();
    document.getElementById("btn-adm-tch-close")?.addEventListener("click", dismiss);
    document.getElementById("btn-adm-tch-close-footer")?.addEventListener("click", dismiss);
    modal.addEventListener("click", (e) => {
      if (e.target === modal) dismiss();
    });

    // Initial load
    loadTeachers();
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
