/**
 * ==============================================================================
 * DATA-TO-DIRT — Master Desktop UI Controller & Application Orchestrator
 * Navigation, Role Switching (Student/Teacher/Admin), Audio & FX Management
 * ==============================================================================
 */

class DataToDirtApp {
  constructor() {
    this.currentRole = "student"; // student, teacher, admin
    this.audioSynth = window.RetroAudio;
    this.particleEngine = window.ParticleEngine;
    this.activeView = null;
  }

  async init() {
    console.log("[+] Initializing Data-to-Dirt Retro Desktop Engine...");
    this.bindGlobalControls();
    this.startClock();

    // Intercept fetch to add Authorization and Localtunnel bypass headers automatically
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      args[1] = args[1] || {};
      args[1].headers = args[1].headers || {};
      if (typeof args[1].headers.set === 'function') {
        args[1].headers.set('bypass-tunnel-reminder', 'true');
        args[1].headers.set('Bypass-Tunnel-Reminder', 'true');
      } else {
        args[1].headers['bypass-tunnel-reminder'] = 'true';
        args[1].headers['Bypass-Tunnel-Reminder'] = 'true';
      }

      const token = localStorage.getItem("d2d_session_token");
      if (token && typeof args[0] === 'string' && args[0].startsWith('/api/')) {
        if (typeof args[1].headers.set === 'function') {
          args[1].headers.set('Authorization', `Bearer ${token}`);
        } else {
          args[1].headers['Authorization'] = `Bearer ${token}`;
        }
      }
      return originalFetch(...args);
    };

    const mainView = document.getElementById("view-content");
    
    // Check if user is already logged in
    const existingToken = localStorage.getItem("d2d_session_token");
    const savedRole = localStorage.getItem("d2d_role");
    const savedUserId = localStorage.getItem("d2d_user_id");
    const savedPin = localStorage.getItem("d2d_pin");


    if (existingToken && savedRole) {
      try {
        const res = await fetch("/api/auth/session");
        const data = await res.json();
        if (res.ok && data.status === "authenticated" && data.session) {
          console.log("[+] Restoring active session:", data.session.role);
          this.completeLogin(data.session.role, data.session.user_id, "");
          return;
        }
      } catch (e) {
        console.warn("Session check failed:", e);
      }

      // Server token expired (e.g. server restart) but we have saved credentials — re-login silently
      if (savedUserId && savedPin !== null) {
        try {
          console.log("[+] Re-authenticating saved session...");
          const loginRes = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ role: savedRole, pin: savedPin, user_id: savedUserId })
          });
          const loginData = await loginRes.json();
          if (loginRes.ok && loginData.status === "authenticated") {
            localStorage.setItem("d2d_session_token", loginData.token);
            this.completeLogin(savedRole, savedUserId, savedPin);
            return;
          }
        } catch (e) {
          console.warn("Re-auth failed:", e);
        }
      }
    }

    // Initialize Login View if no valid session
    document.getElementById("header-role-badge").style.display = "none";
    this.loginView = new window.LoginView(this);
    this.loginView.render(mainView);
  }

  completeLogin(role, userId, pin, classCode = "") {
    if (this.audioSynth) this.audioSynth.playCoinDing();
    this.userId = userId;
    this.pin = pin;
    this.classCode = classCode || localStorage.getItem("d2d_class_code") || "";
    document.getElementById("nav-logout-btn").style.display = "inline-block";
    document.getElementById("header-role-badge").style.display = "inline-block";
    this.switchRole(role);
  }

  logout() {
    this.userId = null;
    this.pin = null;
    this.classCode = null;
    this.currentRole = null;
    localStorage.removeItem("d2d_session_token");
    localStorage.removeItem("d2d_role");
    localStorage.removeItem("d2d_user_id");
    localStorage.removeItem("d2d_pin");
    localStorage.removeItem("d2d_class_code");
    document.getElementById("nav-logout-btn").style.display = "none";
    document.getElementById("header-role-badge").style.display = "none";
    
    // Clear the main view and show login
    const mainView = document.getElementById("view-content");
    mainView.innerHTML = "";
    this.loginView = new window.LoginView(this);
    this.loginView.render(mainView);
  }

  bindGlobalControls() {
    // Audio Mute Toggle
    const btnMute = document.getElementById("btn-toggle-sound");
    if (btnMute) {
      btnMute.addEventListener("click", () => {
        if (this.audioSynth) {
          const isMuted = this.audioSynth.toggleMute();
          btnMute.textContent = isMuted ? "🔇 Sound Off" : "🔊 Sound On";
          if (!isMuted) this.audioSynth.playBlip();
        }
      });
    }

    // CRT Scanlines Toggle
    const btnScanlines = document.getElementById("btn-toggle-scanlines");
    const scanlinesOverlay = document.getElementById("scanlines-overlay");
    if (btnScanlines && scanlinesOverlay) {
      btnScanlines.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        const isDisabled = scanlinesOverlay.classList.toggle("disabled");
        btnScanlines.textContent = isDisabled ? "📺 CRT: Off" : "📺 CRT: On";
      });
    }

    const btnLogout = document.getElementById("nav-logout-btn");
    if (btnLogout) {
      btnLogout.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        this.logout();
      });
    }

    // PWA Install Button & Prompt Handlers
    const btnInstall = document.getElementById("nav-install-btn");
    if (btnInstall) {
      btnInstall.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        this.promptInstall();
      });
    }

    window.addEventListener("beforeinstallprompt", (e) => {
      e.preventDefault();
      window.deferredInstallPrompt = e;
      this.showInstallButtons(true);
    });

    window.addEventListener("appinstalled", () => {
      window.deferredInstallPrompt = null;
      this.showInstallButtons(false);
      console.log("[+] Data-to-Dirt installed successfully!");
    });

    // Check standalone mode (if in standalone, hide install buttons)
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    if (!isStandalone) {
      this.showInstallButtons(true);
    }

    // Role Selector Buttons
    const btnStudentRole = document.getElementById("nav-student-view");
    const btnTeacherRole = document.getElementById("nav-teacher-view");
    const btnAdminRole = document.getElementById("nav-admin-view");

    if (btnStudentRole) {
      btnStudentRole.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        this.switchRole("student");
      });
    }

    if (btnTeacherRole) {
      btnTeacherRole.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        if (this.currentRole === "student") {
          this.openRolePinModal("teacher");
        } else {
          this.switchRole("teacher");
        }
      });
    }

    if (btnAdminRole) {
      btnAdminRole.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        if (this.currentRole !== "admin") {
          this.openRolePinModal("admin");
        } else {
          this.switchRole("admin");
        }
      });
    }
  }

  startClock() {
    const elClock = document.getElementById("retro-clock");
    if (!elClock) return;

    const update = () => {
      const now = new Date();
      const timeStr = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      elClock.textContent = `⏰ ${timeStr}`;
    };
    update();
    setInterval(update, 1000);
  }

  switchRole(role) {
    this.currentRole = role;
    const btnStudent = document.getElementById("nav-student-view");
    const btnTeacher = document.getElementById("nav-teacher-view");
    const btnAdmin = document.getElementById("nav-admin-view");
    const userRoleBadge = document.getElementById("header-role-badge");

    // Reset button styles
    [btnStudent, btnTeacher, btnAdmin].forEach((btn) => {
      if (btn) {
        btn.classList.remove("retro-btn-gold");
        btn.classList.add("retro-btn-wood");
      }
    });

    if (role === "student") {
      if (btnStudent) {
        btnStudent.classList.add("retro-btn-gold");
        btnStudent.classList.remove("retro-btn-wood");
      }
      if (userRoleBadge) {
        userRoleBadge.textContent = "🎒 STUDENT";
        userRoleBadge.style.background = "linear-gradient(135deg, #6c5ce7, #a29bfe)";
      }
      if (window.StudentView) {
        window.StudentView.mount("view-content");
      }
    } else if (role === "teacher") {
      if (btnTeacher) {
        btnTeacher.classList.add("retro-btn-gold");
        btnTeacher.classList.remove("retro-btn-wood");
      }
      if (userRoleBadge) {
        userRoleBadge.textContent = "📋 TEACHER";
        userRoleBadge.style.background = "linear-gradient(135deg, #00b894, #55efc4)";
      }
      if (window.TeacherView) {
        window.TeacherView.mount("view-content");
      } else {
        this.renderTeacherView();
      }
    } else if (role === "admin") {
      if (btnAdmin) {
        btnAdmin.classList.add("retro-btn-gold");
        btnAdmin.classList.remove("retro-btn-wood");
      }
      if (userRoleBadge) {
        userRoleBadge.textContent = "⚙️ ADMIN";
        userRoleBadge.style.background = "linear-gradient(135deg, #e17055, #fab1a0)";
      }
      if (window.AdminView) {
        window.AdminView.mount("view-content");
      } else {
        this.renderTeacherView();
      }
    }
  }

  openRolePinModal(targetRole) {
    const isTeacher = targetRole === "teacher";
    const defaultPin = isTeacher ? "teacher123" : "admin2026";
    const roleTitle = isTeacher ? "Teacher Confirmation Queue" : "Admin Eco-Fund Console";

    const modalHtml = `
      <div class="retro-modal-backdrop" id="modal-role-pin">
        <div class="retro-card retro-modal">
          <div class="retro-modal-header">
            <span>🔐 ${roleTitle} (R4)</span>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-pin-close">✕</button>
          </div>
          <div class="retro-modal-body">
            <p style="margin-bottom: 12px;">
              Enter the passcode to access the <strong>${roleTitle}</strong>.
            </p>
            <div class="retro-inset">
              <label style="display: block; font-weight: bold; margin-bottom: 6px;">Passcode / PIN:</label>
              <input type="password" id="input-role-pin" class="retro-input" placeholder="Default: ${defaultPin}" autofocus />
            </div>
            <div id="pin-error-msg" style="color: var(--c-danger-bright); font-size: 12px; margin-top: 8px; display: none;"></div>
          </div>
          <div class="retro-modal-actions">
            <button class="retro-btn retro-btn-wood" id="btn-pin-cancel">Cancel</button>
            <button class="retro-btn retro-btn-gold" id="btn-pin-submit">Authenticate</button>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML("beforeend", modalHtml);

    const modal = document.getElementById("modal-role-pin");
    const btnClose = document.getElementById("btn-pin-close");
    const btnCancel = document.getElementById("btn-pin-cancel");
    const btnSubmit = document.getElementById("btn-pin-submit");
    const inputPin = document.getElementById("input-role-pin");
    const errEl = document.getElementById("pin-error-msg");

    const dismiss = () => {
      if (modal) modal.remove();
    };

    if (btnClose) btnClose.onclick = dismiss;
    if (btnCancel) btnCancel.onclick = dismiss;

    const verifyPin = async () => {
      const pin = inputPin.value.trim();
      try {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role: targetRole, pin: pin }),
        });

        if (res.ok) {
          const data = await res.json();
          if (data.token) {
            localStorage.setItem("d2d_session_token", data.token);
          }
          dismiss();
          if (this.audioSynth) this.audioSynth.playCoinDing();
          this.switchRole(targetRole);
        } else {
          errEl.style.display = "block";
          errEl.textContent = `[-] Invalid Passcode. Try '${defaultPin}'`;
          if (this.audioSynth) this.audioSynth.playGamingBuzzer();
        }
      } catch (e) {
        errEl.style.display = "block";
        errEl.textContent = `[-] Error: ${e.message}`;
      }
    };

    if (btnSubmit) btnSubmit.onclick = verifyPin;
    if (inputPin) {
      inputPin.onkeydown = (e) => {
        if (e.key === "Enter") verifyPin();
      };
    }
  }


  async renderTeacherView() {
    const container = document.getElementById("view-content");
    if (!container) return;

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 14px; height: 100%; overflow: hidden;">
        
        <!-- Teacher Top Summary Banner -->
        <div class="retro-card" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 18px;">
          <div>
            <div style="font-weight: bold; font-size: 16px; color: var(--c-wood-border);">
              👨‍🏫 Classroom Confirmation & Eco-Fund Dashboard
            </div>
            <div style="font-size: 12px; color: var(--c-ink-muted); margin-top: 2px;">
              Review student deletion requests with verified on-device AI confidence summaries.
            </div>
          </div>
          <div style="display: flex; gap: 10px;">
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-refresh-queue">
              🔄 Refresh Queue
            </button>
            <button class="retro-btn retro-btn-gold retro-btn-sm" id="btn-return-student">
              ← Return to Student View
            </button>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 14px; flex: 1; overflow: hidden;">
          
          <!-- Pending Queue Card -->
          <div class="retro-card" style="display: flex; flex-direction: column; gap: 10px; overflow: hidden;">
            <div style="font-weight: bold; font-size: 14px; color: var(--c-wood-border); border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 6px;">
              📬 Pending Student Requests Queue (<span id="teacher-queue-count">0</span>)
            </div>
            <div id="teacher-queue-items" style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding-right: 4px;">
              <div style="text-align: center; padding: 30px; color: var(--c-ink-light);">Loading confirmation queue...</div>
            </div>
          </div>

          <!-- Eco-Fund Ledger & Settings Card -->
          <div class="retro-card" style="display: flex; flex-direction: column; gap: 12px; overflow-y: auto;">
            <div style="font-weight: bold; font-size: 14px; color: var(--c-wood-border); border-bottom: 2px dashed var(--c-parchment-border); padding-bottom: 6px;">
              🌳 Eco-Fund & Tree-Nation Reforestation Status (R5)
            </div>

            <!-- Eco-Fund Balance Box -->
            <div class="retro-inset" style="display: flex; justify-content: space-between; align-items: center; padding: 12px;">
              <div>
                <div style="font-size: 11px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">Eco-Fund Balance</div>
                <div id="ecofund-balance-val" style="font-size: 26px; font-weight: bold; color: var(--c-eco-leaf);">$0.00</div>
              </div>
              <div style="text-align: right;">
                <div style="font-size: 11px; text-transform: uppercase; color: var(--c-ink-muted); font-weight: bold;">Trees Funded</div>
                <div id="ecofund-trees-val" style="font-size: 26px; font-weight: bold; color: var(--c-brass-bright);">0</div>
              </div>
            </div>

            <!-- Cumulative Waste Progress to 1 GB -->
            <div class="pixel-progress-wrap">
              <div class="pixel-progress-label">
                <span>Next Tree Milestone (1.0 GB Threshold)</span>
                <span id="ecofund-thresh-pct">0%</span>
              </div>
              <div class="pixel-progress-bar">
                <div class="pixel-progress-fill" id="ecofund-thresh-fill" style="width: 0%;"></div>
              </div>
            </div>

            <!-- Certificate History List -->
            <div style="font-weight: bold; font-size: 13px; color: var(--c-wood-border); margin-top: 4px;">
              📜 Reforestation Certificates Log:
            </div>
            <div id="ecofund-donations-log" class="retro-inset" style="max-height: 140px; overflow-y: auto; font-size: 11px; display: flex; flex-direction: column; gap: 6px;">
              <div>No trees planted yet.</div>
            </div>
          </div>

        </div>

      </div>
    `;

    document.getElementById("btn-return-student")?.addEventListener("click", () => {
      this.switchRole("student");
    });

    document.getElementById("btn-refresh-queue")?.addEventListener("click", () => {
      this.fetchTeacherData();
    });

    await this.fetchTeacherData();
  }

  async fetchTeacherData() {
    try {
      const [qRes, ecoRes] = await Promise.all([
        fetch("/api/teacher/queue").then((r) => r.json()),
        fetch("/api/admin/ecofund").then((r) => r.json()),
      ]);

      this.renderQueueList(qRes.queue || []);
      this.renderEcoFund(ecoRes);
    } catch (e) {
      console.warn("Failed to fetch teacher data:", e);
    }
  }

  renderQueueList(queue) {
    const elCount = document.getElementById("teacher-queue-count");
    const elContainer = document.getElementById("teacher-queue-items");
    if (elCount) elCount.textContent = queue.length;
    if (!elContainer) return;

    if (queue.length === 0) {
      elContainer.innerHTML = `
        <div style="text-align: center; padding: 36px; color: var(--c-ink-light); font-size: 13px;">
          ✨ All caught up! No pending student deletion requests.
        </div>
      `;
      return;
    }

    elContainer.innerHTML = queue
      .map((item) => {
        const scorePct = Math.round((item.ai_evaluation?.confidence_score ?? 0.8) * 100);
        return `
          <div class="retro-inset" style="padding: 10px; display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <span style="font-weight: bold; color: var(--c-wood-border); font-size: 13px;">${item.student_name}</span>
                <span style="font-size: 11px; color: var(--c-ink-muted);">(${item.student_id})</span>
              </div>
              <span class="retro-tag retro-tag-heavy">AI Confidence: ${scorePct}%</span>
            </div>

            <div style="font-size: 12px; color: var(--c-ink-text);">
              File: <strong>${item.file_name}</strong> (${Math.round(item.file_size_bytes / (1024 * 1024))} MB)
            </div>

            <div style="font-size: 12px; font-style: italic; color: var(--c-ink-muted); background: rgba(255, 255, 255, 0.6); padding: 6px; border: 1px dashed var(--c-parchment-border);">
              "${item.reason}"
            </div>

            <div style="font-size: 11px; color: var(--c-eco-leaf); font-weight: bold;">
              🤖 AI Summary: ${item.ai_evaluation?.summary || "Verified"}
            </div>

            <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px;">
              <button class="retro-btn retro-btn-danger retro-btn-sm btn-action-flag" data-id="${item.request_id}">
                🚩 Flag Gaming
              </button>
              <button class="retro-btn retro-btn-wood retro-btn-sm btn-action-reject" data-id="${item.request_id}">
                ✕ Reject
              </button>
              <button class="retro-btn retro-btn-green retro-btn-sm btn-action-approve" data-id="${item.request_id}">
                ✓ Approve Deletion
              </button>
            </div>
          </div>
        `;
      })
      .join("");

    // Bind action buttons
    elContainer.querySelectorAll(".btn-action-approve").forEach((btn) => {
      btn.onclick = () => this.handleTeacherAction(btn.getAttribute("data-id"), "approve");
    });
    elContainer.querySelectorAll(".btn-action-reject").forEach((btn) => {
      btn.onclick = () => this.handleTeacherAction(btn.getAttribute("data-id"), "reject");
    });
    elContainer.querySelectorAll(".btn-action-flag").forEach((btn) => {
      btn.onclick = () => this.handleTeacherAction(btn.getAttribute("data-id"), "flag");
    });
  }

  async handleTeacherAction(requestId, action) {
    try {
      const res = await fetch("/api/teacher/decide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request_id: requestId, action: action }),
      }).then((r) => r.json());

      if (action === "approve") {
        if (this.audioSynth) this.audioSynth.playDeletionPoof();
        if (res.donation_triggered) {
          if (this.audioSynth) this.audioSynth.playVictoryFanfare();
          if (this.particleEngine) this.particleEngine.emitConfetti();
        }
      } else if (action === "flag") {
        if (this.audioSynth) this.audioSynth.playGamingBuzzer();
      } else {
        if (this.audioSynth) this.audioSynth.playBlip();
      }

      await this.fetchTeacherData();
    } catch (e) {
      console.warn("Teacher decision error:", e);
    }
  }

  renderEcoFund(eco) {
    if (!eco) return;
    const elBal = document.getElementById("ecofund-balance-val");
    const elTrees = document.getElementById("ecofund-trees-val");
    const elPct = document.getElementById("ecofund-thresh-pct");
    const elFill = document.getElementById("ecofund-thresh-fill");
    const elLog = document.getElementById("ecofund-donations-log");

    if (elBal) elBal.textContent = `$${eco.balance_usd.toFixed(2)}`;
    if (elTrees) elTrees.textContent = eco.trees_planted;

    // Calculate progress to next 1 GB
    const thresh = eco.threshold_bytes || 1073741824;
    const currentWaste = eco.cumulative_waste_bytes || 0;
    const nextTarget = (eco.trees_planted + 1) * thresh;
    const prevTarget = eco.trees_planted * thresh;
    const progress = Math.min(100, Math.max(0, Math.round(((currentWaste - prevTarget) / thresh) * 100)));

    if (elPct) elPct.textContent = `${progress}%`;
    if (elFill) elFill.style.width = `${progress}%`;

    if (elLog && eco.donations_history) {
      elLog.innerHTML = eco.donations_history
        .map((d) => `<div>🌲 <strong>${d.tree_id}</strong>: ${d.species} (${d.co2_offset_kg} kg CO₂ offset) - <em>${d.planted_at}</em></div>`)
        .join("");
    }
  }

  showInstallButtons(show) {
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    if (isStandalone) show = false;
    const navBtn = document.getElementById("nav-install-btn");
    if (navBtn) navBtn.style.display = show ? "inline-block" : "none";
    const loginBtn = document.getElementById("btn-login-install");
    if (loginBtn) loginBtn.style.display = show ? "inline-flex" : "none";
  }

  promptInstall() {
    if (window.deferredInstallPrompt) {
      window.deferredInstallPrompt.prompt();
      window.deferredInstallPrompt.userChoice.then((choiceResult) => {
        if (choiceResult.outcome === "accepted") {
          console.log("[+] User accepted PWA install");
          this.showInstallButtons(false);
        }
        window.deferredInstallPrompt = null;
      });
    } else {
      this.showInstallInstructionsModal();
    }
  }

  showInstallInstructionsModal() {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    const isAndroid = /Android/.test(navigator.userAgent);
    
    let instructionsHtml = '';
    if (isIOS) {
      instructionsHtml = `
        <div style="background: #f8f9fa; border-radius: 12px; padding: 14px; margin-bottom: 15px; border-left: 4px solid #0984e3;">
          <div style="font-weight: 700; color: #2d3436; margin-bottom: 8px; font-size: 14px;">🍏 Install on iPhone / iPad (Safari)</div>
          <ol style="margin: 0; padding-left: 20px; line-height: 1.6; font-size: 13px; color: #636e72;">
            <li>Tap the <strong>Share</strong> button <span style="font-size: 16px;">⎋</span> (in the bottom or top Safari bar).</li>
            <li>Scroll down and tap <strong>Add to Home Screen</strong> <span style="font-size: 15px;">➕</span>.</li>
            <li>Tap <strong>Add</strong> in the top-right corner.</li>
          </ol>
          <div style="margin-top: 10px; font-size: 12px; color: #00b894; font-weight: 600;">
            ✨ Launches full-screen like a native app from your home screen!
          </div>
        </div>
      `;
    } else if (isAndroid) {
      instructionsHtml = `
        <div style="background: #f8f9fa; border-radius: 12px; padding: 14px; margin-bottom: 15px; border-left: 4px solid #00b894;">
          <div style="font-weight: 700; color: #2d3436; margin-bottom: 8px; font-size: 14px;">🤖 Install on Android (Chrome)</div>
          <ol style="margin: 0; padding-left: 20px; line-height: 1.6; font-size: 13px; color: #636e72;">
            <li>Tap the three dots menu (<strong style="font-size: 16px;">⋮</strong>) in Chrome.</li>
            <li>Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li>
            <li>Tap <strong>Install</strong> to confirm.</li>
          </ol>
        </div>
      `;
    } else {
      instructionsHtml = `
        <div style="background: #f8f9fa; border-radius: 12px; padding: 14px; margin-bottom: 15px; border-left: 4px solid #6c5ce7;">
          <div style="font-weight: 700; color: #2d3436; margin-bottom: 8px; font-size: 14px;">💻 Install on Desktop (Chrome / Edge / Safari)</div>
          <ol style="margin: 0; padding-left: 20px; line-height: 1.6; font-size: 13px; color: #636e72;">
            <li>Look for the <strong>Install App</strong> icon (🖥️ / ⬇️) in your browser address bar.</li>
            <li>Or open browser menu (⋮) &rarr; <strong>Install Data-to-Dirt</strong>.</li>
            <li>Launches in a distraction-free dedicated desktop window!</li>
          </ol>
        </div>
      `;
    }

    const modalBackdrop = document.createElement("div");
    modalBackdrop.className = "retro-modal-backdrop";
    modalBackdrop.style.cssText = "position: fixed; inset: 0; background: rgba(0,0,0,0.65); display: flex; align-items: center; justify-content: center; z-index: 10000; padding: 20px;";
    modalBackdrop.innerHTML = `
      <div style="background: #fff; border-radius: 18px; max-width: 440px; width: 100%; padding: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.3); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; position: relative;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 14px;">
          <img src="/logo.png" alt="Data-to-Dirt Logo" style="width: 44px; height: 44px; border-radius: 12px; object-fit: cover; border: 1.5px solid #e2b77a; box-shadow: 0 4px 10px rgba(0,0,0,0.15);" />
          <div>
            <div style="font-weight: 800; font-size: 18px; color: #2d3436;">Download & Install App</div>
            <div style="font-size: 12px; color: #b2bec3;">Data-to-Dirt PWA</div>
          </div>
        </div>

        <p style="font-size: 13px; color: #636e72; line-height: 1.5; margin-bottom: 16px;">
          Install Data-to-Dirt to run it as a standalone app with offline support, full-screen view, and quick access from your home screen.
        </p>

        ${instructionsHtml}

        <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 15px;">
          <button id="btn-download-app-file" style="padding: 12px; background: #00b894; color: #fff; border: none; border-radius: 10px; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 14px; box-shadow: 0 4px 10px rgba(0, 184, 148, 0.3);">
            <span>⬇️</span> Download App Desktop Launcher
          </button>
          <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px;">
            <button id="modal-install-close" style="padding: 8px 16px; background: #dfe6e9; color: #2d3436; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">Close</button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modalBackdrop);
    const dismiss = () => {
      if (modalBackdrop.parentNode) modalBackdrop.parentNode.removeChild(modalBackdrop);
    };

    modalBackdrop.querySelector("#btn-download-app-file")?.addEventListener("click", () => {
      const targetUrl = window.location.origin;
      const htmlContent = `<!DOCTYPE html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=${targetUrl}"><title>Data-to-Dirt</title><script>window.location.href="${targetUrl}";<\/script></head><body style="font-family:sans-serif;text-align:center;padding:50px;"><h2>Data-to-Dirt</h2><p>Redirecting to <a href="${targetUrl}">${targetUrl}</a>...</p></body></html>`;
      const blob = new Blob([htmlContent], { type: "text/html" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "Data-to-Dirt.html";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    });

    modalBackdrop.querySelector("#modal-install-close")?.addEventListener("click", dismiss);
    modalBackdrop.addEventListener("click", (e) => {
      if (e.target === modalBackdrop) dismiss();
    });
  }
}

// Global App Singleton & Startup
window.DataToDirt = new DataToDirtApp();
window.addEventListener("DOMContentLoaded", () => {
  window.DataToDirt.init();
});
