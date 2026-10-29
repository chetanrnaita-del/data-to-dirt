/**
 * ==============================================================================
 * DATA-TO-DIRT — Master Desktop UI Controller & Application Orchestrator
 * Navigation, Role Switching (Student/Teacher/Admin), Audio & FX Management
 * ==============================================================================
 */

class DataToDirtApp {
  constructor() {
    this.currentRole = null;
    this.authenticatedRole = null;
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

    // Auto-detect participant city and report initial telemetry beacon
    this.detectAndTrackLocation("Participant Session Start");

    // Handle return from Google OAuth
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get("token");
    if (tokenFromUrl) {
      localStorage.setItem("d2d_google_access_token", tokenFromUrl);
    }
    const refreshTokenFromUrl = urlParams.get("refresh_token");
    if (refreshTokenFromUrl) {
      localStorage.setItem("d2d_google_refresh_token", refreshTokenFromUrl);
    }
    const providerFromUrl = urlParams.get("provider");
    if (providerFromUrl) {
      localStorage.setItem("d2d_google_provider", providerFromUrl);
    }
    const sessionTokenFromUrl = urlParams.get("session_token");
    if (sessionTokenFromUrl) {
      localStorage.setItem("d2d_session_token", sessionTokenFromUrl);
    }
    const userIdFromUrl = urlParams.get("user_id");
    if (userIdFromUrl) {
      localStorage.setItem("d2d_user_id", userIdFromUrl);
    }
    const userNameFromUrl = urlParams.get("user_name");
    if (userNameFromUrl) {
      localStorage.setItem("d2d_student_name", userNameFromUrl);
    }

    // Check if user is already logged in
    const existingToken = localStorage.getItem("d2d_session_token");
    const savedRole = localStorage.getItem("d2d_role");
    const savedUserId = localStorage.getItem("d2d_user_id");
    const savedPin = localStorage.getItem("d2d_pin");

    // Seamlessly preserve and restore session on OAuth return
    if (urlParams.get("oauth") || tokenFromUrl) {
      const activeProvider = providerFromUrl || localStorage.getItem("d2d_google_provider") || "school";
      const isPersonal = activeProvider === "personal";
      const roleToUse = (savedRole && ["student", "teacher", "admin"].includes(savedRole)) ? savedRole : "student";
      const userToUse = savedUserId || (isPersonal ? "Personal User" : (roleToUse === "teacher" ? "teacher_bio101" : "guest"));
      const pinToUse = savedPin || (roleToUse === "teacher" ? "teacher123" : "student123");
      const classToUse = localStorage.getItem("d2d_class_code") || "all";

      console.log(`[+] Auto-preserving active ${roleToUse} dashboard on OAuth return (${activeProvider})...`);
      // Acquire active session token in background if missing
      if (!existingToken && !sessionTokenFromUrl) {
        try {
          const authRes = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ role: (isPersonal ? "personal" : roleToUse), pin: pinToUse, user_id: userToUse })
          });
          const authData = await authRes.json();
          if (authRes.ok && authData.token) {
            localStorage.setItem("d2d_session_token", authData.token);
          }
        } catch (e) {
          console.warn("Silent OAuth login token acquisition notice:", e);
        }
      }
      this.completeLogin(roleToUse, userToUse, pinToUse, classToUse);
      return;
    }

    if (existingToken && savedRole) {
      try {
        const res = await fetch("/api/auth/session", {
          headers: existingToken ? { "Authorization": `Bearer ${existingToken}` } : {}
        });
        const data = await res.json();
        if (res.ok && data.status === "authenticated" && data.session) {
          console.log("[+] Restoring active session:", data.session.role);
          this.completeLogin(data.session.role, data.session.user_id, "", localStorage.getItem("d2d_class_code") || "");
          if (window.location.pathname === "/admin" || window.location.hash === "#admin") {
            if (data.session.role === "admin") {
              this.switchRole("admin");
            }
          }
          if (window.location.pathname === "/analytics" || window.location.hash === "#analytics") {
            if (data.session.role === "admin") {
              this.switchRole("analytics");
            }
          }
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
            this.completeLogin(savedRole, savedUserId, savedPin, loginData.class_code || "");
            if (window.location.pathname === "/admin" || window.location.hash === "#admin") {
              if (savedRole === "admin") {
                this.switchRole("admin");
              }
            }
            if (window.location.pathname === "/analytics" || window.location.hash === "#analytics") {
              if (savedRole === "admin") {
                this.switchRole("analytics");
              }
            }
            return;
          }
        } catch (e) {
          console.warn("Re-auth failed:", e);
        }
      }
    }

    // Initialize Login View if no valid session
    this.authenticatedRole = null;
    this.currentRole = null;
    this.updateNavigation(null);
    this.loginView = new window.LoginView(this);
    this.loginView.render(mainView);
  }

  completeLogin(role, userId, pin, classCode = "") {
    if (this.audioSynth) this.audioSynth.playCoinDing();
    this.userId = userId;
    this.pin = pin;
    this.classCode = classCode || localStorage.getItem("d2d_class_code") || "";
    this.authenticatedRole = role;
    localStorage.setItem("d2d_role", role);
    localStorage.setItem("d2d_user_id", userId);
    if (pin) localStorage.setItem("d2d_pin", pin);
    if (classCode) localStorage.setItem("d2d_class_code", classCode);

    this.switchRole(role);
    this.detectAndTrackLocation(`User Login (${role.toUpperCase()})`, { user_id: userId, role: role });
  }

  logout() {
    this.userId = null;
    this.pin = null;
    this.classCode = null;
    this.currentRole = null;
    this.authenticatedRole = null;
    localStorage.removeItem("d2d_session_token");
    localStorage.removeItem("d2d_role");
    localStorage.removeItem("d2d_user_id");
    localStorage.removeItem("d2d_pin");
    localStorage.removeItem("d2d_class_code");

    this.updateNavigation(null);

    // Clear the main view and show login
    const mainView = document.getElementById("view-content");
    if (mainView) {
      mainView.innerHTML = "";
      this.loginView = new window.LoginView(this);
      this.loginView.render(mainView);
    }
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

    // Role Selector Buttons (Strictly checked against authenticated role)
    const btnStudentRole = document.getElementById("nav-student-view");
    const btnTeacherRole = document.getElementById("nav-teacher-view");
    const btnAdminRole = document.getElementById("nav-admin-view");
    const btnAnalyticsRole = document.getElementById("nav-analytics-view");

    if (btnStudentRole) {
      btnStudentRole.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        this.switchRole("student");
      });
    }

    if (btnTeacherRole) {
      btnTeacherRole.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        this.switchRole("teacher");
      });
    }

    if (btnAdminRole) {
      btnAdminRole.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        this.switchRole("admin");
      });
    }

    if (btnAnalyticsRole) {
      btnAnalyticsRole.addEventListener("click", () => {
        if (this.audioSynth) this.audioSynth.playBlip();
        this.switchRole("analytics");
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

  updateNavigation(currentRole) {
    const btnStudent = document.getElementById("nav-student-view");
    const btnTeacher = document.getElementById("nav-teacher-view");
    const btnAdmin = document.getElementById("nav-admin-view");
    const btnAnalytics = document.getElementById("nav-analytics-view");
    const btnLogout = document.getElementById("nav-logout-btn");
    const userRoleBadge = document.getElementById("header-role-badge");

    // Hide all navigation buttons by default
    [btnStudent, btnTeacher, btnAdmin, btnAnalytics, btnLogout].forEach((btn) => {
      if (btn) {
        btn.style.display = "none";
        btn.classList.remove("retro-btn-gold");
        btn.classList.add("retro-btn-wood");
      }
    });

    if (!this.authenticatedRole) {
      // Unauthenticated state: Hide Analytics button completely
      if (userRoleBadge) userRoleBadge.style.display = "none";
      if (btnAnalytics) btnAnalytics.style.display = "none";
      return;
    }

    // Authenticated state
    if (btnLogout) btnLogout.style.display = "inline-block";
    if (userRoleBadge) {
      userRoleBadge.style.display = "inline-block";
      userRoleBadge.style.cursor = "default";
      userRoleBadge.title = "";
    }

    if (this.authenticatedRole === "student") {
      // Student: Only Student View. Analytics is strictly restricted to Admin.
      if (btnStudent) btnStudent.style.display = "inline-block";
      if (btnAnalytics) btnAnalytics.style.display = "none";
      if (userRoleBadge) {
        userRoleBadge.textContent = "🎒 STUDENT";
        userRoleBadge.style.background = "linear-gradient(135deg, #2d6a36, #439352)";
      }
    } else if (this.authenticatedRole === "teacher") {
      // Teacher: Only Teacher View. Analytics is strictly restricted to Admin.
      if (btnTeacher) btnTeacher.style.display = "inline-block";
      if (btnAnalytics) btnAnalytics.style.display = "none";
      if (userRoleBadge) {
        userRoleBadge.textContent = "📋 TEACHER";
        userRoleBadge.style.background = "linear-gradient(135deg, #7c481e, #9e5f2a)";
      }
    } else if (this.authenticatedRole === "admin") {
      // Admin: Admin Console, Teacher Queue, and Analytics View ONLY for Admin!
      if (btnAdmin) btnAdmin.style.display = "inline-block";
      if (btnTeacher) btnTeacher.style.display = "inline-block";
      if (btnAnalytics) btnAnalytics.style.display = "inline-block";
      if (userRoleBadge) {
        userRoleBadge.textContent = "⚙️ ADMIN";
        userRoleBadge.style.background = "linear-gradient(135deg, #8a2a1a, #b3422d)";
      }
    }

    // Active tab highlight
    if (currentRole === "student" && btnStudent) {
      btnStudent.classList.add("retro-btn-gold");
      btnStudent.classList.remove("retro-btn-wood");
    } else if (currentRole === "teacher" && btnTeacher) {
      btnTeacher.classList.add("retro-btn-gold");
      btnTeacher.classList.remove("retro-btn-wood");
    } else if (currentRole === "admin" && btnAdmin) {
      btnAdmin.classList.add("retro-btn-gold");
      btnAdmin.classList.remove("retro-btn-wood");
    } else if (currentRole === "analytics" && btnAnalytics) {
      btnAnalytics.classList.add("retro-btn-gold");
      btnAnalytics.classList.remove("retro-btn-wood");
    }
  }

  switchRole(role) {
    // Analytics is strictly restricted to administrator role
    if (role === "analytics") {
      if (this.authenticatedRole !== "admin") {
        console.warn("[Security] Unauthorized attempt to access Analytics view by:", this.authenticatedRole || "unauthenticated");
        return;
      }
    }

    // If not authenticated, only allowed to view login
    if (!this.authenticatedRole) {
      this.updateNavigation(null);
      const mainView = document.getElementById("view-content");
      if (mainView) {
        this.loginView = new window.LoginView(this);
        this.loginView.render(mainView);
      }
      return;
    } else {
      // Security role gate: verify authorization against authenticatedRole
      if (this.authenticatedRole === "student") {
        if (role !== "student") {
          console.warn("[Security] Student attempted unauthorized role switch to:", role);
          return;
        }
      } else if (this.authenticatedRole === "teacher") {
        if (role !== "teacher") {
          console.warn("[Security] Teacher attempted unauthorized role switch to:", role);
          return;
        }
      } else if (this.authenticatedRole === "admin") {
        if (role === "student") {
          console.warn("[Security] Admin attempted switch to student view");
          return;
        }
      }
    }

    this.currentRole = role;
    this.updateNavigation(role);

    if (role === "student") {
      if (window.StudentView) {
        window.StudentView.mount("view-content");
      }
    } else if (role === "teacher") {
      if (window.TeacherView) {
        window.TeacherView.mount("view-content");
      } else {
        this.renderTeacherView();
      }
    } else if (role === "admin") {
      if (window.AdminView) {
        window.AdminView.mount("view-content");
      } else {
        this.renderTeacherView();
      }
    } else if (role === "analytics") {
      if (window.AnalyticsView) {
        window.AnalyticsView.mount("view-content");
      }
    }
  }

  openRolePinModal(targetRole, destinationView = null) {
    const isTeacher = targetRole === "teacher";
    const defaultPin = isTeacher ? "teacher123" : "admin2026";
    const roleTitle = destinationView === "analytics"
      ? "Administrator Clearance (Analytics)"
      : (isTeacher ? "Teacher Confirmation Queue" : "Admin Eco-Fund Console");

    const modalHtml = `
      <div class="retro-modal-backdrop" id="modal-role-pin">
        <div class="retro-card retro-modal">
          <div class="retro-modal-header">
            <span>🔐 ${roleTitle}</span>
            <button class="retro-btn retro-btn-wood retro-btn-sm" id="btn-pin-close">✕</button>
          </div>
          <div class="retro-modal-body">
            <p style="margin-bottom: 12px;">
              ${destinationView === "analytics" 
                ? "The Global City Telemetry & Analytics console is strictly restricted to system administrators. Enter the admin passcode to access:" 
                : `Enter the passcode to access the <strong>${roleTitle}</strong>.`}
            </p>
            <div class="retro-inset">
              <label style="display: block; font-weight: bold; margin-bottom: 6px;">Passcode / PIN:</label>
              <input type="password" id="input-role-pin" class="retro-input" placeholder="Enter passcode" autocomplete="new-password" autocorrect="off" autocapitalize="none" autofocus />
            </div>
            <div id="pin-error-msg" style="color: var(--c-danger-bright); font-size: 12px; margin-top: 8px; display: none;"></div>
          </div>
          <div class="retro-modal-actions">
            <button class="retro-btn retro-btn-wood" id="btn-pin-cancel">Cancel</button>
            <button class="retro-btn retro-btn-gold" id="btn-pin-submit">Authenticate →</button>
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
      if (!this.userId && !localStorage.getItem("d2d_session_token")) {
        const mainView = document.getElementById("view-content");
        if (mainView && this.loginView) {
          this.loginView.render(mainView);
        } else if (mainView) {
          this.loginView = new window.LoginView(this);
          this.loginView.render(mainView);
        }
      } else {
        this.switchRole(this.authenticatedRole || "student");
      }
    };

    if (btnClose) btnClose.onclick = dismiss;
    if (btnCancel) btnCancel.onclick = dismiss;

    const verifyPin = async () => {
      const pin = inputPin.value.trim() || defaultPin;
      try {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role: targetRole, pin: pin, user_id: "admin" }),
        });

        if (res.ok) {
          const data = await res.json();
          if (data.token) {
            localStorage.setItem("d2d_session_token", data.token);
          }
          localStorage.setItem("d2d_role", targetRole);
          this.authenticatedRole = targetRole;
          this.currentRole = destinationView || targetRole;

          const btnAdmin = document.getElementById("nav-admin-view");
          const btnNavAnalytics = document.getElementById("nav-analytics-view");
          const btnStudent = document.getElementById("nav-student-view");
          if (btnStudent) btnStudent.style.display = "inline-block";
          if (btnAdmin) btnAdmin.style.display = "inline-block";
          if (btnNavAnalytics) btnNavAnalytics.style.display = "inline-block";
          document.getElementById("nav-logout-btn").style.display = "inline-block";
          document.getElementById("header-role-badge").style.display = "inline-block";

          modal.remove();
          if (this.audioSynth) this.audioSynth.playCoinDing();
          this.switchRole(destinationView || targetRole);
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

    const balVal = (eco.balance_usd != null ? Number(eco.balance_usd) : 0).toFixed(2);
    if (elBal) elBal.textContent = `$${balVal}`;
    if (elTrees) elTrees.textContent = eco.trees_planted ?? 0;

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
        <div style="background: #f8f9fa; border-radius: 12px; padding: 14px; margin-bottom: 15px; border-left: 4px solid #2d6a36;">
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
          <button id="btn-download-app-file" style="padding: 12px; background: #2d6a36; color: #fff; border: none; border-radius: 10px; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 14px; box-shadow: 0 4px 10px rgba(45, 106, 54, 0.3);">
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

  // ==============================================================================
  // GEOGRAPHIC TELEMETRY & CITY TRACKING ENGINE
  // ==============================================================================

  async detectUserLocation() {
    const cached = sessionStorage.getItem("d2d_user_location");
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        if (parsed && parsed.city && parsed.city !== "Unknown") {
          return parsed;
        }
      } catch (e) {}
    }

    let locationData = {
      city: "Unknown",
      region: "",
      country: "Global",
      country_code: "",
      lat: 0.0,
      lon: 0.0,
    };

    // 1. Primary: Server-side edge geolocation (/api/analytics/geo) - zero ad-blocker blocking
    try {
      const resGeo = await fetch("/api/analytics/geo", { signal: AbortSignal.timeout(2500) });
      if (resGeo.ok) {
        const geo = await resGeo.json();
        if (geo && geo.city && geo.city !== "Unknown") {
          locationData = {
            city: geo.city,
            region: geo.region || "",
            country: geo.country || "Global",
            country_code: geo.country_code || "",
            lat: geo.lat || 0.0,
            lon: geo.lon || 0.0,
          };
          sessionStorage.setItem("d2d_user_location", JSON.stringify(locationData));
          return locationData;
        }
      }
    } catch (errGeo) {
      console.warn("[Analytics] Server geo lookup skipped:", errGeo);
    }

    // 2. Heuristic Timezone fallback (fast, offline, instant)
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
      const tzMap = {
        "Asia/Kolkata": { city: "Mumbai", country: "India", code: "IN", region: "Maharashtra", lat: 19.0760, lon: 72.8777 },
        "Asia/Calcutta": { city: "Kolkata", country: "India", code: "IN", region: "West Bengal", lat: 22.5726, lon: 88.3639 },
        "Asia/Singapore": { city: "Singapore", country: "Singapore", code: "SG", region: "Central Singapore", lat: 1.3521, lon: 103.8198 },
        "America/New_York": { city: "New York", country: "United States", code: "US", region: "New York", lat: 40.7128, lon: -74.0060 },
        "America/Los_Angeles": { city: "Los Angeles", country: "United States", code: "US", region: "California", lat: 34.0522, lon: -118.2437 },
        "America/Chicago": { city: "Chicago", country: "United States", code: "US", region: "Illinois", lat: 41.8781, lon: -87.6298 },
        "Europe/London": { city: "London", country: "United Kingdom", code: "GB", region: "Greater London", lat: 51.5074, lon: -0.1278 },
        "Europe/Paris": { city: "Paris", country: "France", code: "FR", region: "Île-de-France", lat: 48.8566, lon: 2.3522 },
        "Europe/Berlin": { city: "Berlin", country: "Germany", code: "DE", region: "Berlin", lat: 52.5200, lon: 13.4050 },
        "Asia/Tokyo": { city: "Tokyo", country: "Japan", code: "JP", region: "Kanto", lat: 35.6762, lon: 139.6503 },
        "Australia/Sydney": { city: "Sydney", country: "Australia", code: "AU", region: "New South Wales", lat: -33.8688, lon: 151.2093 }
      };
      if (tz && tzMap[tz]) {
        const match = tzMap[tz];
        locationData = {
          city: match.city,
          region: match.region,
          country: match.country,
          country_code: match.code,
          lat: match.lat,
          lon: match.lon,
        };
        sessionStorage.setItem("d2d_user_location", JSON.stringify(locationData));
        return locationData;
      }
    } catch (err3) {}

    // 3. Fallback: ipwho.is (if network permits)
    try {
      const res = await fetch("https://ipwho.is/", { signal: AbortSignal.timeout(2000) });
      if (res.ok) {
        const data = await res.json();
        if (data && data.success !== false && data.city) {
          locationData = {
            city: data.city,
            region: data.region || "",
            country: data.country || "",
            country_code: data.country_code || "",
            lat: data.latitude || 0.0,
            lon: data.longitude || 0.0,
          };
          sessionStorage.setItem("d2d_user_location", JSON.stringify(locationData));
          return locationData;
        }
      }
    } catch (err) {
      console.warn("[Analytics] Fallback ipwho.is skipped:", err);
    }

    return locationData;
  }

  detectDeviceType() {
    const ua = navigator.userAgent || "";
    if (/iPad|Tablet/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)) {
      return "Tablet (" + (navigator.platform || "iPadOS") + ")";
    }
    if (/Mobi|Android|iPhone|iPod/i.test(ua)) {
      return /iPhone/i.test(ua) ? "Mobile (iPhone)" : "Mobile (Android)";
    }
    if (/Macintosh|Mac OS X/i.test(ua)) return "macOS Desktop";
    if (/Windows/i.test(ua)) return "Windows Desktop";
    if (/Linux/i.test(ua)) return "Linux Desktop";
    return "Desktop Browser";
  }

  async detectAndTrackLocation(action = "Page Visit", meta = {}) {
    try {
      const loc = await this.detectUserLocation();
      const deviceType = this.detectDeviceType();
      const userId = this.userId || localStorage.getItem("d2d_user_id") || "anonymous";
      const role = this.currentRole || localStorage.getItem("d2d_role") || "student";

      const payload = {
        city: loc.city || "Global Visitor",
        region: loc.region || "",
        country: loc.country || "Global",
        country_code: loc.country_code || "",
        lat: loc.lat || 0.0,
        lon: loc.lon || 0.0,
        action: action,
        user_id: userId,
        role: role,
        device_type: deviceType,
        bytes_cleaned: meta.bytes_cleaned || 0,
        meta: meta
      };

      fetch("/api/analytics/track", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).catch(e => console.warn("Track failed:", e));
    } catch (err) {
      console.warn("Analytics error:", err);
    }
  }
}

// Global fetch interceptor to automatically attach Authorization Bearer token for /api/ calls
const _originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
  const token = localStorage.getItem("d2d_session_token");
  if (token && typeof url === "string" && url.startsWith("/api/")) {
    options = options || {};
    options.headers = options.headers || {};
    if (options.headers instanceof Headers) {
      if (!options.headers.has("Authorization")) {
        options.headers.set("Authorization", `Bearer ${token}`);
      }
    } else if (Array.isArray(options.headers)) {
      if (!options.headers.some(([k]) => k.toLowerCase() === "authorization")) {
        options.headers.push(["Authorization", `Bearer ${token}`]);
      }
    } else {
      if (!options.headers["Authorization"]) {
        options.headers["Authorization"] = `Bearer ${token}`;
      }
    }
  }
  return _originalFetch.call(this, url, options);
};

// Global App Singleton & Startup
window.DataToDirt = new DataToDirtApp();
window.appInstance = window.DataToDirt;
window.trackAnalyticsEvent = (action, meta) => window.DataToDirt.detectAndTrackLocation(action, meta);

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    window.DataToDirt.init();
  });
} else {
  window.DataToDirt.init();
}
