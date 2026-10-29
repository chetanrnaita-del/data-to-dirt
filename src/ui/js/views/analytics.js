/**
 * ==============================================================================
 * DATA-TO-DIRT — Geographic City Telemetry & Master Analytics Console
 * Real-time city tracking, global visitor metrics, device distribution,
 * rolling live activity ticker, and dark data environmental impact reports.
 * ==============================================================================
 */

class AnalyticsDashboardView {
  constructor() {
    this.container = null;
    this.data = null;
    this.autoRefresh = true;
    this.refreshTimer = null;
    this.searchQuery = "";
    this.audioSynth = window.RetroAudio;
  }

  mount(containerId = "view-content") {
    this.container = document.getElementById(containerId);
    if (!this.container) return;
    this.renderLayout();
    this.fetchData();
    this.startAutoRefresh();
  }

  unmount() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  startAutoRefresh() {
    this.unmount();
    if (this.autoRefresh) {
      this.refreshTimer = setInterval(() => {
        if (document.getElementById("an-cities-tbody")) {
          this.fetchData(true);
        } else {
          this.unmount();
        }
      }, 5000);
    }
  }

  getAuthHeaders(extra = {}) {
    const token = localStorage.getItem("d2d_session_token") || "";
    const headers = { ...extra };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }

  async fetchData(silent = false) {
    try {
      const headers = this.getAuthHeaders();
      const res = await fetch("/api/analytics/dashboard", { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load analytics dashboard`);
      this.data = await res.json();
      this.updateView();
      if (!silent && this.audioSynth) {
        this.audioSynth.playBlip();
      }
    } catch (err) {
      console.warn("[Analytics] Fetch failed:", err);
      const tbody = document.getElementById("an-cities-tbody");
      if (tbody) {
        tbody.innerHTML = `
          <tr>
            <td colspan="8" style="text-align: center; padding: 24px; color: var(--c-danger-bright);">
              ⚠️ Failed to load telemetry data: ${err.message}. 
              <button class="retro-btn retro-btn-wood retro-btn-sm" onclick="window.AnalyticsView.fetchData()" style="margin-left: 8px;">Retry 🔄</button>
            </td>
          </tr>
        `;
      }
    }
  }

  renderLayout() {
    this.container.innerHTML = `
      <div class="analytics-dashboard" style="display: flex; flex-direction: column; gap: 12px; height: 100%; overflow-y: auto; -webkit-overflow-scrolling: touch; padding: 12px; box-sizing: border-box;">

        <!-- Top Header & Controls Banner -->
        <div class="retro-card" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; flex-wrap: wrap; gap: 10px;">
          <div>
            <div style="font-weight: bold; font-size: 16px; color: var(--c-wood-border); display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <span>📊 Global City Telemetry & Environmental Analytics</span>
              <span class="retro-tag retro-tag-leaf" style="font-size: 10px;">GLOBAL METRICS</span>
              <span class="retro-tag retro-tag-clean" id="an-live-badge" style="font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
                <span class="pulse-dot" style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #2ecc71;"></span>
                LIVE TRACKING ACTIVE
              </span>
              <span class="retro-tag retro-tag-stale" id="an-cities-count-badge" style="font-size: 11px;">0 CITIES</span>
            </div>
            <div style="font-size: 11px; color: var(--c-ink-muted); margin-top: 2px;">
              Track real-time participant cities, device form factors, active scans, and cumulative carbon savings.
            </div>
          </div>
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-an-autorefresh" title="Toggle Auto-Refresh">
              ⏱️ Auto-Refresh: ON
            </button>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-an-refresh" title="Refresh Now">
              🔄 Refresh
            </button>
            <button class="retro-btn retro-btn-gold retro-btn-sm" id="btn-an-export" title="Export CSV Report">
              📥 Export CSV
            </button>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-an-return-home" title="Return to Application">
              ← Return
            </button>
          </div>
        </div>

        <!-- Master KPI Strip (5 Global Impact Metrics) -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px;">
          <div class="retro-card" style="padding: 8px 12px;">
            <div style="font-size: 10px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">🌍 Tracked Cities</div>
            <div id="an-kpi-cities" style="font-size: 19px; font-weight: bold; color: var(--c-wood-border); margin-top: 2px;">--</div>
            <div id="an-kpi-cities-sub" style="font-size: 10px; color: var(--c-ink-light); margin-top: 2px;">Across 0 Countries</div>
          </div>
          <div class="retro-card" style="padding: 8px 12px;">
            <div style="font-size: 10px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">👥 Visitors & Active</div>
            <div id="an-kpi-visitors" style="font-size: 19px; font-weight: bold; color: #2980b9; margin-top: 2px;">--</div>
            <div id="an-kpi-visitors-sub" style="font-size: 10px; color: var(--c-ink-light); margin-top: 2px;">0 Active Sessions</div>
          </div>
          <div class="retro-card" style="padding: 8px 12px;">
            <div style="font-size: 10px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">🔍 Scans Executed</div>
            <div id="an-kpi-scans" style="font-size: 19px; font-weight: bold; color: #b87714; margin-top: 2px;">--</div>
            <div id="an-kpi-scans-sub" style="font-size: 10px; color: var(--c-ink-light); margin-top: 2px;">Device & Cloud</div>
          </div>
          <div class="retro-card" style="padding: 8px 12px;">
            <div style="font-size: 10px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">💾 Storage Cleaned</div>
            <div id="an-kpi-storage" style="font-size: 19px; font-weight: bold; color: var(--c-eco-leaf); margin-top: 2px;">--</div>
            <div id="an-kpi-storage-sub" style="font-size: 10px; color: var(--c-ink-light); margin-top: 2px;">Dark Data Reclaimed</div>
          </div>
          <div class="retro-card" style="padding: 8px 12px;">
            <div style="font-size: 10px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">🌲 Avoided Carbon</div>
            <div id="an-kpi-carbon" style="font-size: 19px; font-weight: bold; color: var(--c-forest-deep); margin-top: 2px;">--</div>
            <div id="an-kpi-trees-sub" style="font-size: 10px; color: var(--c-ink-light); margin-top: 2px;">0 Trees Funded</div>
          </div>
        </div>

        <!-- Master Two-Column Operational Layout -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 12px; flex: 1;">

          <!-- Left Column: City Geographic Leaderboard & Telemetry Grid -->
          <div class="retro-card" style="display: flex; flex-direction: column; gap: 10px; padding: 12px;">
            
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 8px; flex-wrap: wrap; gap: 8px;">
              <div style="font-weight: bold; font-size: 14px; color: var(--c-wood-border); display: flex; align-items: center; gap: 6px;">
                <span>🏙️ Participant Cities Telemetry Matrix</span>
              </div>
              <div style="display: flex; align-items: center; gap: 6px;">
                <input type="text" id="an-city-search" placeholder="🔍 Search city, country, or code..." 
                       style="padding: 4px 8px; font-size: 11px; border: 1.5px solid var(--c-parchment-border); border-radius: 4px; background: var(--c-parchment-light); width: 220px;" />
              </div>
            </div>

            <!-- Table Container -->
            <div style="overflow-x: auto; max-height: 420px; border: 1px solid var(--c-parchment-border); border-radius: 4px; background: #fff;">
              <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: left;">
                <thead style="position: sticky; top: 0; background: var(--c-parchment-dark); color: var(--c-wood-border); font-weight: bold; z-index: 2; border-bottom: 2px solid var(--c-parchment-border);">
                  <tr>
                    <th style="padding: 8px 10px;"># Rank</th>
                    <th style="padding: 8px 10px;">City & Country</th>
                    <th style="padding: 8px 10px;">Coordinates</th>
                    <th style="padding: 8px 10px;">Active Sessions</th>
                    <th style="padding: 8px 10px;">Scans</th>
                    <th style="padding: 8px 10px;">Cleaned (GB)</th>
                    <th style="padding: 8px 10px;">CO₂ (kg)</th>
                    <th style="padding: 8px 10px;">Status</th>
                  </tr>
                </thead>
                <tbody id="an-cities-tbody">
                  <tr>
                    <td colspan="8" style="text-align: center; padding: 30px; color: var(--c-ink-muted);">
                      Loading geographic telemetry...
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Telemetry Footer Note -->
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: var(--c-ink-light); padding-top: 4px; flex-wrap: wrap; gap: 4px;">
              <span>🔒 Zero personal file content or PII stored. Aggregated city and carbon stats.</span>
              <span id="an-server-time">Server Sync: --</span>
            </div>

          </div>

          <!-- Right Column: Live Event Stream & Distribution Meters -->
          <div style="display: flex; flex-direction: column; gap: 12px;">

            <!-- Real-Time Rolling Event Stream -->
            <div class="retro-card" style="display: flex; flex-direction: column; gap: 8px; max-height: 280px;">
              <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 4px;">
                <div style="font-weight: bold; font-size: 13px; color: var(--c-wood-border); display: flex; align-items: center; gap: 6px;">
                  <span>⚡ Live Activity Telemetry Feed</span>
                </div>
                <span class="retro-tag retro-tag-clean" style="font-size: 9px; padding: 2px 6px;">ROLLING</span>
              </div>

              <div id="an-event-stream" style="overflow-y: auto; display: flex; flex-direction: column; gap: 6px; padding: 4px; max-height: 220px;">
                <div style="text-align: center; padding: 16px; font-size: 11px; color: var(--c-ink-muted);">
                  Listening for real-time participant events...
                </div>
              </div>
            </div>

            <!-- Device Form Factor Breakdown -->
            <div class="retro-card" style="display: flex; flex-direction: column; gap: 8px;">
              <div style="font-weight: bold; font-size: 13px; color: var(--c-wood-border); border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 4px;">
                💻 Client Device Form Factors
              </div>

              <div id="an-devices-container" style="display: flex; flex-direction: column; gap: 8px; padding-top: 4px;">
                <!-- Populated dynamically -->
              </div>
            </div>

            <!-- Dark Data Waste Categorization -->
            <div class="retro-card" style="display: flex; flex-direction: column; gap: 8px;">
              <div style="font-weight: bold; font-size: 13px; color: var(--c-wood-border); border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 4px;">
                🗂️ Staged Dark Data Categories
              </div>

              <div id="an-waste-container" style="display: flex; flex-direction: column; gap: 8px; padding-top: 4px;">
                <!-- Populated dynamically -->
              </div>
            </div>

          </div>

        </div>

      </div>
    `;

    this.bindEvents();
  }

  bindEvents() {
    const btnRefresh = document.getElementById("btn-an-refresh");
    if (btnRefresh) {
      btnRefresh.addEventListener("click", () => this.fetchData(false));
    }

    const btnAuto = document.getElementById("btn-an-autorefresh");
    if (btnAuto) {
      btnAuto.addEventListener("click", () => {
        this.autoRefresh = !this.autoRefresh;
        btnAuto.textContent = this.autoRefresh ? "⏱️ Auto-Refresh: ON" : "⏱️ Auto-Refresh: OFF";
        btnAuto.classList.toggle("retro-btn-gold", this.autoRefresh);
        if (this.autoRefresh) {
          this.startAutoRefresh();
        } else {
          this.unmount();
        }
      });
    }

    const btnExport = document.getElementById("btn-an-export");
    if (btnExport) {
      btnExport.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playCoinDing();
        const token = localStorage.getItem("d2d_session_token");
        const exportUrl = "/api/analytics/export" + (token ? `?token=${encodeURIComponent(token)}` : "");
        window.open(exportUrl, "_blank");
      });
    }

    const btnReturnHome = document.getElementById("btn-an-return-home");
    if (btnReturnHome) {
      btnReturnHome.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        const app = window.DataToDirt || window.appInstance;
        if (!app) return;
        if (app.authenticatedRole) {
          app.switchRole(app.authenticatedRole);
        } else {
          app.logout();
        }
      });
    }

    const searchInput = document.getElementById("an-city-search");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.searchQuery = (e.target.value || "").toLowerCase().trim();
        this.renderCitiesTable();
      });
    }
  }

  updateView() {
    if (!this.data) return;

    const kpis = this.data.kpis || {};
    const cities = this.data.cities || [];

    // Unique countries count
    const uniqueCountries = new Set(cities.map(c => c.country || c.country_code).filter(Boolean)).size;

    // KPI 1: Cities
    const elCities = document.getElementById("an-kpi-cities");
    const elCitiesSub = document.getElementById("an-kpi-cities-sub");
    if (elCities) elCities.textContent = `${cities.length} Cities`;
    if (elCitiesSub) elCitiesSub.textContent = `Across ${uniqueCountries} Countries`;

    const elCountBadge = document.getElementById("an-cities-count-badge");
    if (elCountBadge) elCountBadge.textContent = `${cities.length} CITIES`;

    // KPI 2: Visitors & Active
    const elVisitors = document.getElementById("an-kpi-visitors");
    const elVisitorsSub = document.getElementById("an-kpi-visitors-sub");
    if (elVisitors) elVisitors.textContent = `${kpis.total_visitors || 0} Total`;
    if (elVisitorsSub) elVisitorsSub.textContent = `🟢 ${kpis.active_sessions || 0} Active Now`;

    // KPI 3: Scans
    const elScans = document.getElementById("an-kpi-scans");
    if (elScans) elScans.textContent = `${kpis.total_scans || 0} Scans`;

    // KPI 4: Storage Cleaned
    const elStorage = document.getElementById("an-kpi-storage");
    if (elStorage) {
      const bytes = Number(kpis.total_bytes_cleaned || 0);
      if (bytes >= 1024 ** 3) {
        elStorage.textContent = `${(bytes / (1024 ** 3)).toFixed(2)} GB`;
      } else if (bytes >= 1024 ** 2) {
        elStorage.textContent = `${(bytes / (1024 ** 2)).toFixed(2)} MB`;
      } else if (bytes >= 1024) {
        elStorage.textContent = `${(bytes / 1024).toFixed(1)} KB`;
      } else {
        elStorage.textContent = `${bytes} B`;
      }
    }

    // KPI 5: Carbon Avoided & Trees Funded
    const elCarbon = document.getElementById("an-kpi-carbon");
    const elTreesSub = document.getElementById("an-kpi-trees-sub");
    if (elCarbon) {
      const co2Kg = Number(kpis.total_carbon_offset_kg || 0);
      if (co2Kg >= 1.0) {
        elCarbon.textContent = `${co2Kg.toFixed(2)} kg CO₂`;
      } else if (co2Kg > 0) {
        const grams = co2Kg * 1000.0;
        elCarbon.textContent = `${grams >= 1 ? grams.toFixed(1) : grams.toFixed(2)} g CO₂`;
      } else {
        elCarbon.textContent = `0.00 kg CO₂`;
      }
    }
    if (elTreesSub) elTreesSub.textContent = `🌲 ${kpis.total_trees_funded || 0} Trees Funded`;

    // Server Sync time
    const elSync = document.getElementById("an-server-time");
    if (elSync) elSync.textContent = `Server Sync: ${this.data.server_time || new Date().toLocaleTimeString()}`;

    // Render Table, Event Feed, and Meters
    this.renderCitiesTable();
    this.renderEventStream();
    this.renderDevices();
    this.renderWasteCategories();
  }

  renderCitiesTable() {
    const tbody = document.getElementById("an-cities-tbody");
    if (!tbody || !this.data) return;

    let cities = this.data.cities || [];
    if (this.searchQuery) {
      cities = cities.filter(c => {
        const query = this.searchQuery;
        return (
          (c.city && c.city.toLowerCase().includes(query)) ||
          (c.country && c.country.toLowerCase().includes(query)) ||
          (c.country_code && c.country_code.toLowerCase().includes(query)) ||
          (c.region && c.region.toLowerCase().includes(query))
        );
      });
    }

    if (cities.length === 0) {
      const msg = this.searchQuery
        ? `No cities match the filter query "${this.searchQuery}".`
        : "No participant cities tracked yet. Real visitor locations will stream here as users access the app.";
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; padding: 24px; color: var(--c-ink-muted);">
            ${msg}
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = cities.map((c, idx) => {
      const bytes = Number(c.bytes_cleaned || 0);
      let cleanedStr = "0 B";
      if (bytes >= 1024 ** 3) cleanedStr = `${(bytes / (1024 ** 3)).toFixed(2)} GB`;
      else if (bytes >= 1024 ** 2) cleanedStr = `${(bytes / (1024 ** 2)).toFixed(2)} MB`;
      else if (bytes >= 1024) cleanedStr = `${(bytes / 1024).toFixed(1)} KB`;
      else if (bytes > 0) cleanedStr = `${bytes} B`;

      const isLive = Number(c.active_users || 0) > 0;
      const rankBadge = idx === 0 ? "🥇" : idx === 1 ? "🥈" : idx === 2 ? "🥉" : `#${idx + 1}`;
      const latLon = (c.lat != null && c.lon != null && (c.lat !== 0 || c.lon !== 0))
        ? `${Number(c.lat).toFixed(2)}°, ${Number(c.lon).toFixed(2)}°`
        : "GPS Auto";
      const scans = Number(c.scans || 0);
      const visitors = Number(c.visitors || 0);
      const co2Kg = Number(c.co2_avoided_kg || 0);
      let co2Str = "0.00 kg";
      if (co2Kg >= 1.0) co2Str = `${co2Kg.toFixed(2)} kg`;
      else if (co2Kg > 0) {
        const grams = co2Kg * 1000.0;
        co2Str = `${grams >= 1 ? grams.toFixed(1) : grams.toFixed(2)} g`;
      }

      return `
        <tr style="border-bottom: 1px solid var(--c-parchment-border); transition: background 0.15s ease;">
          <td style="padding: 8px 10px; font-weight: bold; color: var(--c-wood-border);">${rankBadge}</td>
          <td style="padding: 8px 10px;">
            <div style="font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 6px;">
              <span>${c.flag || "🌐"}</span>
              <span>${c.city || "Global"}</span>
              <span class="retro-tag retro-tag-clean" style="font-size: 9px; padding: 1px 5px;">${c.country_code || "XX"}</span>
            </div>
            <div style="font-size: 10px; color: var(--c-ink-light); margin-top: 2px;">
              ${c.region ? c.region + ", " : ""}${c.country || "Global"}
            </div>
          </td>
          <td style="padding: 8px 10px; font-family: monospace; font-size: 11px; color: var(--c-ink-muted);">${latLon}</td>
          <td style="padding: 8px 10px;">
            <div style="display: flex; align-items: center; gap: 4px; font-weight: bold; color: ${isLive ? '#27ae60' : 'var(--c-ink-muted)'};">
              <span style="display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: ${isLive ? '#2ecc71' : '#bdc3c7'};"></span>
              <span>${c.active_users || 0} online</span>
            </div>
            <div style="font-size: 9px; color: var(--c-ink-light);">${visitors} total visits</div>
          </td>
          <td style="padding: 8px 10px; font-weight: bold; color: #8e44ad;">${scans}</td>
          <td style="padding: 8px 10px; font-weight: bold; color: var(--c-eco-leaf);">${cleanedStr}</td>
          <td style="padding: 8px 10px; font-weight: bold; color: var(--c-forest-deep);">${co2Str}</td>
          <td style="padding: 8px 10px;">
            <span class="retro-tag ${isLive ? 'retro-tag-clean' : 'retro-tag-wood'}" style="font-size: 9px; padding: 2px 6px;">
              ${isLive ? 'LIVE' : 'IDLE'}
            </span>
          </td>
        </tr>
      `;
    }).join("");
  }

  formatEventTime(evt) {
    if (!evt) return "Just now";
    let date = null;
    if (evt.timestamp_epoch) {
      date = new Date(evt.timestamp_epoch * 1000);
    } else if (evt.timestamp) {
      const s = String(evt.timestamp).trim();
      if (s.endsWith("Z") || s.includes("T")) {
        date = new Date(s);
      } else if (s.includes(" ")) {
        // Parse UTC timestamp: "YYYY-MM-DD HH:MM:SS" -> Date in UTC
        date = new Date(s.replace(" ", "T") + "Z");
      } else {
        date = new Date(s);
      }
    }

    if (!date || isNaN(date.getTime())) {
      return evt.timestamp ? String(evt.timestamp).split(" ")[1] || String(evt.timestamp) : "Just now";
    }

    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSec >= 0 && diffSec < 15) {
      return "Just now";
    }
    if (diffSec >= 15 && diffSec < 60) {
      return `${diffSec}s ago`;
    }
    if (diffSec >= 60 && diffSec < 3600) {
      return `${Math.floor(diffSec / 60)}m ago`;
    }

    // Format in authentic local browser time
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit", hour12: true });
  }

  renderEventStream() {
    const stream = document.getElementById("an-event-stream");
    if (!stream || !this.data) return;

    const events = this.data.recent_events || [];
    if (events.length === 0) {
      stream.innerHTML = `<div style="text-align: center; padding: 16px; font-size: 11px; color: var(--c-ink-muted);">No activity recorded yet. Live participant events will appear here in real-time.</div>`;
      return;
    }

    stream.innerHTML = events.slice(0, 15).map(evt => {
      const timeStr = this.formatEventTime(evt);
      const fullTimeStr = evt.timestamp ? String(evt.timestamp) : "";
      return `
        <div class="retro-inset" style="padding: 6px 8px; font-size: 11px; display: flex; flex-direction: column; gap: 2px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-weight: 600; color: var(--c-wood-border); display: flex; align-items: center; gap: 5px;">
              <span>${evt.flag || "🌐"}</span>
              <span>${evt.city || "Global"}</span>
              <span class="retro-tag retro-tag-clean" style="font-size: 8px; padding: 1px 4px;">${evt.role || "user"}</span>
            </div>
            <span style="font-size: 9px; color: var(--c-ink-light); font-weight: 600;" title="${fullTimeStr}">${timeStr}</span>
          </div>
          <div style="color: var(--c-ink); font-size: 10.5px; line-height: 1.3;">
            ${evt.action || "Activity"}
          </div>
          <div style="font-size: 9px; color: var(--c-ink-light); display: flex; justify-content: space-between;">
            <span>ID: ${evt.user_id || "visitor"}</span>
            <span style="font-weight: 600;">${evt.device_type || "macOS Desktop"}</span>
          </div>
        </div>
      `;
    }).join("");
  }

  renderDevices() {
    const container = document.getElementById("an-devices-container");
    if (!container || !this.data) return;

    const devices = this.data.devices || {};
    const counts = devices.counts || { desktop: 0, mobile: 0, tablet: 0 };
    const pcts = devices.percentages || { desktop: 0.0, mobile: 0.0, tablet: 0.0 };

    const items = [
      { name: "Desktop Computer", icon: "💻", count: counts.desktop || 0, pct: pcts.desktop || 0, color: "#3498db" },
      { name: "Smartphone / Mobile", icon: "📱", count: counts.mobile || 0, pct: pcts.mobile || 0, color: "#2ecc71" },
      { name: "Tablet / iPad", icon: "📟", count: counts.tablet || 0, pct: pcts.tablet || 0, color: "#e67e22" },
    ];

    container.innerHTML = items.map(item => `
      <div style="display: flex; flex-direction: column; gap: 3px;">
        <div style="display: flex; justify-content: space-between; font-size: 11px;">
          <span style="font-weight: 600;">${item.icon} ${item.name}</span>
          <span style="color: var(--c-ink-muted); font-weight: bold;">${item.pct}% (${item.count} sessions)</span>
        </div>
        <div style="width: 100%; height: 8px; background: var(--c-parchment-border); border-radius: 4px; overflow: hidden;">
          <div style="width: ${item.pct}%; height: 100%; background: ${item.color}; border-radius: 4px; transition: width 0.3s ease;"></div>
        </div>
      </div>
    `).join("");
  }

  renderWasteCategories() {
    const container = document.getElementById("an-waste-container");
    if (!container || !this.data) return;

    const waste = this.data.waste_categories || {};
    const entries = Object.entries(waste);

    if (entries.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 12px; font-size: 11px; color: var(--c-ink-muted);">
          No dark data categories recorded yet. Categories will appear as files are analyzed.
        </div>
      `;
      return;
    }

    const colors = ["#e74c3c", "#f39c12", "#9b59b6", "#1abc9c"];
    let idx = 0;

    container.innerHTML = entries.map(([cat, pct]) => {
      const color = colors[idx % colors.length];
      idx++;
      return `
        <div style="display: flex; flex-direction: column; gap: 3px;">
          <div style="display: flex; justify-content: space-between; font-size: 11px;">
            <span style="font-weight: 600;">📁 ${cat}</span>
            <span style="color: var(--c-ink-muted); font-weight: bold;">${pct}%</span>
          </div>
          <div style="width: 100%; height: 8px; background: var(--c-parchment-border); border-radius: 4px; overflow: hidden;">
            <div style="width: ${pct}%; height: 100%; background: ${color}; border-radius: 4px; transition: width 0.3s ease;"></div>
          </div>
        </div>
      `;
    }).join("");
  }
}

// Global Singleton for easy mounting
window.AnalyticsView = new AnalyticsDashboardView();
