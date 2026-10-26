class LoginView {
  constructor(app) {
    this.app = app;
    this.selectedRole = 'student';
  }

  async render(container) {
    container.innerHTML = `
      <div style="display: flex; height: 100%; background-color: #f4f6fb; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
        
        <!-- Left Pane (Illustration) -->
        <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; background: linear-gradient(135deg, #e0e8ff 0%, #f4f6fb 100%); position: relative; overflow: hidden;">
          <div style="z-index: 10; text-align: center;">
            <div style="width: 130px; height: 130px; background: #fff; border-radius: 24px; margin: 0 auto 20px auto; display: flex; align-items: center; justify-content: center; border: 3px solid #e2b77a; box-shadow: 0 12px 32px rgba(0,0,0,0.12); overflow: hidden;">
              <img src="/logo.png" alt="Data-to-Dirt Logo" style="width: 100%; height: 100%; object-fit: cover;" />
            </div>
            <h1 style="color: #2c3e50; font-size: 28px; margin: 0; font-weight: 800;">DATA-TO-DIRT</h1>
            <p style="color: #7f8c8d; font-size: 14px; margin-top: 5px;">Powered by Retro Engine</p>
          </div>
          
          <!-- Abstract shapes for illustration -->
          <div style="position: absolute; bottom: -50px; left: -10%; right: -10%; height: 180px; background: rgba(255, 154, 158, 0.4); border-radius: 50%; z-index: 1;"></div>
          <div style="position: absolute; bottom: -80px; left: 10%; right: -20%; height: 200px; background: rgba(254, 207, 239, 0.5); border-radius: 50%; z-index: 2;"></div>
        </div>

        <!-- Right Pane (Login Form) -->
        <div style="width: 480px; background: #fff; border-radius: 30px 0 0 30px; box-shadow: -10px 0 30px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: center; padding: 40px; z-index: 10; box-sizing: border-box; overflow-y: auto;">
          <h2 style="color: #34495e; font-size: 18px; font-weight: 600; margin-bottom: 20px;">Please select your role</h2>
          
          <div style="display: flex; gap: 10px; margin-bottom: 24px;">
            <button class="role-btn active" data-role="student" style="flex: 1; padding: 12px 10px; border: 2px solid #6c5ce7; border-radius: 12px; background: #f0edff; color: #6c5ce7; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.2s;">
              <span style="font-size: 20px;">🧑‍🎓</span> Student
            </button>
            <button class="role-btn" data-role="teacher" style="flex: 1; padding: 12px 10px; border: 1px solid #dfe6e9; border-radius: 12px; background: #fff; color: #636e72; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.2s;">
              <span style="font-size: 20px;">👨‍🏫</span> Staff
            </button>
            <button class="role-btn" data-role="admin" style="flex: 1; padding: 12px 10px; border: 1px solid #dfe6e9; border-radius: 12px; background: #fff; color: #636e72; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: all 0.2s;">
              <span style="font-size: 20px;">⚙️</span> Admin
            </button>
          </div>

          <!-- Recently Created Banner (if available) -->
          <div id="recent-account-banner" style="display: none; margin-bottom: 16px; padding: 10px 12px; border-radius: 10px; background: #e8f8f5; border: 1.5px solid #27ae60; font-size: 12px; color: #1e824c;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span id="recent-account-text" style="font-weight: 600;">⭐ Recent Account</span>
              <button type="button" id="btn-use-recent" style="background: #27ae60; color: #fff; border: none; border-radius: 6px; padding: 4px 8px; font-size: 11px; font-weight: bold; cursor: pointer;">⚡ Auto-Fill</button>
            </div>
          </div>

          <div style="margin-bottom: 18px;">
            <label style="display: block; font-size: 13px; font-weight: 700; color: #2d3436; margin-bottom: 6px;">
              <span id="label-user">Student ID / Name</span> <span style="color: #e74c3c;">*</span>
            </label>
            <input type="text" id="login-user" placeholder="Enter Student ID (e.g. STU-001) or Name" style="width: 100%; padding: 13px 15px; border: 1px solid #dfe6e9; border-radius: 10px; font-size: 14px; outline: none; transition: border 0.2s; box-sizing: border-box;" />
            <div id="hint-user" style="font-size: 11px; color: #7f8c8d; margin-top: 4px;">
              💡 Enter your Full Name (e.g. Alex River) or Student ID (e.g. STU-001).
            </div>
          </div>

          <div style="margin-bottom: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <label style="font-size: 13px; font-weight: 700; color: #2d3436;">
                <span id="label-pass">Class Code or Password</span> <span style="color: #e74c3c;">*</span>
              </label>
            </div>
            <input type="password" id="login-pass" placeholder="Enter class code (e.g., bio101)" style="width: 100%; padding: 13px 15px; border: 1px solid #dfe6e9; border-radius: 10px; font-size: 14px; outline: none; transition: border 0.2s; box-sizing: border-box;" />
            <div id="hint-pass" style="font-size: 11px; color: #7f8c8d; margin-top: 4px;">
              💡 Enter class code (e.g. bio101, cs301) or student123.
            </div>
          </div>

          <!-- Quick Select Shortcuts for Students -->
          <div id="student-quick-select" style="display: block; margin-bottom: 18px;">
            <div style="font-size: 11px; font-weight: bold; color: #636e72; margin-bottom: 6px;">Quick Class Presets:</div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
              <button type="button" class="stu-class-pill" data-class="bio101" style="font-size: 11px; padding: 5px 8px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; font-weight: 600;">🌿 Bio 101</button>
              <button type="button" class="stu-class-pill" data-class="cs301" style="font-size: 11px; padding: 5px 8px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; font-weight: 600;">💻 CS 301</button>
              <button type="button" class="stu-class-pill" data-class="env201" style="font-size: 11px; padding: 5px 8px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; font-weight: 600;">🌍 Env 201</button>
              <button type="button" class="stu-class-pill" data-class="chem102" style="font-size: 11px; padding: 5px 8px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; font-weight: 600;">🧪 Chem 102</button>
              <button type="button" class="stu-class-pill" data-class="earth204" style="font-size: 11px; padding: 5px 8px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; font-weight: 600;">⛰️ Earth 204</button>
            </div>
          </div>

          <!-- Quick Select Shortcuts for Staff/Teachers -->
          <div id="teacher-quick-select" style="display: none; margin-bottom: 18px;">
            <div style="font-size: 11px; font-weight: bold; color: #636e72; margin-bottom: 6px;">Select Teacher Account:</div>
            <div id="teacher-pills-list" style="display: flex; flex-direction: column; gap: 5px; max-height: 160px; overflow-y: auto;">
              <button type="button" class="t-pill" data-tid="teacher_bio101" data-pass="teacher123" style="font-size: 11px; padding: 6px 10px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; text-align: left; font-weight: 600;">🌿 Dr. Evelyn Reed — Bio 101</button>
              <button type="button" class="t-pill" data-tid="teacher_env201" data-pass="teacher123" style="font-size: 11px; padding: 6px 10px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; text-align: left; font-weight: 600;">🌍 Prof. Marcus Green — Env 201</button>
              <button type="button" class="t-pill" data-tid="teacher_cs301" data-pass="teacher123" style="font-size: 11px; padding: 6px 10px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; text-align: left; font-weight: 600;">💻 Ms. Clara Patel — CS 301</button>
              <button type="button" class="t-pill" data-tid="teacher_chem102" data-pass="teacher123" style="font-size: 11px; padding: 6px 10px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; text-align: left; font-weight: 600;">🧪 Dr. Arthur Thorne — Chem 102</button>
              <button type="button" class="t-pill" data-tid="teacher_earth204" data-pass="teacher123" style="font-size: 11px; padding: 6px 10px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; text-align: left; font-weight: 600;">⛰️ Mr. Samuel Woods — Earth 204</button>
            </div>
          </div>

          <!-- Quick Select Shortcuts for Admin -->
          <div id="admin-quick-select" style="display: none; margin-bottom: 18px;">
            <div style="font-size: 11px; font-weight: bold; color: #636e72; margin-bottom: 6px;">Administrator Credentials:</div>
            <button type="button" id="btn-admin-pill" style="width: 100%; font-size: 11px; padding: 8px 12px; border: 1.5px solid #fab1a0; border-radius: 8px; background: #fff5f5; cursor: pointer; text-align: left; font-weight: 600; color: #d63031; transition: all 0.2s;">
              ⚙️ Auto-fill Administrator (admin / admin2026)
            </button>
          </div>
          
          <div id="login-error" style="color: #e74c3c; font-size: 13px; margin-bottom: 15px; display: none; font-weight: 600;"></div>

          <button id="btn-proceed" style="width: 100%; padding: 15px; background: #5f27cd; color: #fff; border: none; border-radius: 12px; font-size: 15px; font-weight: 700; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 10px; transition: background 0.2s; box-shadow: 0 4px 15px rgba(95, 39, 205, 0.3);">
            Proceed →
          </button>

          <!-- PWA Install Option on Login -->
          <div style="margin-top: 16px; text-align: center; display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
            <button id="btn-login-install" type="button" style="background: #f8f9fa; border: 1.5px solid #dcdde1; border-radius: 10px; padding: 8px 12px; font-size: 12px; font-weight: 600; color: #2f3640; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.04);">
              <span>📲</span> Install App
            </button>
          </div>

        </div>
      </div>
    `;

    this.bindEvents(container);
    this.loadRecentAccounts(container);
    this.fetchTeacherDirectory(container);
  }

  loadRecentAccounts(container) {
    const banner = container.querySelector('#recent-account-banner');
    const textEl = container.querySelector('#recent-account-text');
    const btnUse = container.querySelector('#btn-use-recent');
    const inputUser = container.querySelector('#login-user');
    const inputPass = container.querySelector('#login-pass');
    if (!banner || !textEl || !btnUse) return;

    if (this.selectedRole === 'student') {
      try {
        const lastStuRaw = localStorage.getItem('d2d_last_created_student');
        if (lastStuRaw) {
          const s = JSON.parse(lastStuRaw);
          textEl.textContent = `⭐ Newly Enrolled: ${s.name} (${s.student_id} / ${s.class_code.toUpperCase()})`;
          banner.style.display = 'block';
          btnUse.onclick = () => {
            inputUser.value = s.student_id || s.name;
            inputPass.value = s.class_code || 'bio101';
          };
          return;
        }
      } catch (_) {}
    } else if (this.selectedRole === 'teacher') {
      try {
        const lastTchRaw = localStorage.getItem('d2d_last_created_teacher');
        if (lastTchRaw) {
          const t = JSON.parse(lastTchRaw);
          textEl.textContent = `⭐ Newly Created: ${t.name} (${t.teacher_id} / ${t.pin || 'teacher123'})`;
          banner.style.display = 'block';
          btnUse.onclick = () => {
            inputUser.value = t.teacher_id || t.name;
            inputPass.value = t.pin || 'teacher123';
          };
          return;
        }
      } catch (_) {}
    }
    banner.style.display = 'none';
  }

  async fetchTeacherDirectory(container) {
    const listEl = container.querySelector('#teacher-pills-list');
    if (!listEl) return;
    try {
      const res = await fetch('/api/auth/teachers');
      const data = await res.json();
      if (data.status === 'ok' && Array.isArray(data.teachers) && data.teachers.length > 0) {
        listEl.innerHTML = data.teachers.map((t) => {
          const tid = t.teacher_id || 'teacher_bio101';
          const name = t.name || tid;
          const classCode = (t.class_code || 'all').toUpperCase();
          const pass = t.pin || 'teacher123';
          return `
            <button type="button" class="t-pill" data-tid="${tid}" data-pass="${pass}" style="font-size: 11px; padding: 6px 10px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; text-align: left; font-weight: 600;">
              👨‍🏫 ${name} — [${classCode}]
            </button>
          `;
        }).join('');

        // Re-bind newly rendered pills
        listEl.querySelectorAll('.t-pill').forEach(pill => {
          pill.addEventListener('click', () => {
            const inputUser = container.querySelector('#login-user');
            const inputPass = container.querySelector('#login-pass');
            if (inputUser) inputUser.value = pill.dataset.tid;
            if (inputPass) inputPass.value = pill.dataset.pass || 'teacher123';
          });
        });
      }
    } catch (_) {}
  }

  bindEvents(container) {
    const roleBtns = container.querySelectorAll('.role-btn');
    const labelUser = container.querySelector('#label-user');
    const labelPass = container.querySelector('#label-pass');
    const hintUser = container.querySelector('#hint-user');
    const hintPass = container.querySelector('#hint-pass');
    const inputUser = container.querySelector('#login-user');
    const inputPass = container.querySelector('#login-pass');
    
    roleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        // Update UI styles
        roleBtns.forEach(b => {
          b.classList.remove('active');
          b.style.border = '1px solid #dfe6e9';
          b.style.background = '#fff';
          b.style.color = '#636e72';
        });
        
        btn.classList.add('active');
        btn.style.border = '2px solid #6c5ce7';
        btn.style.background = '#f0edff';
        btn.style.color = '#6c5ce7';
        
        this.selectedRole = btn.dataset.role;
        
        const studentPills = container.querySelector('#student-quick-select');
        const teacherPills = container.querySelector('#teacher-quick-select');
        const adminPills = container.querySelector('#admin-quick-select');

        // Update Labels & Hints
        if (this.selectedRole === 'student') {
          labelUser.textContent = "Student ID or Name";
          inputUser.placeholder = "Enter Student ID (e.g. STU-001) or Full Name";
          labelPass.textContent = "Class Code or Password";
          inputPass.placeholder = "Enter class code (e.g., cs301) or password";
          inputPass.value = "";
          if (hintUser) hintUser.textContent = "💡 Enter your Full Name (e.g. Alex River) or Student ID (e.g. STU-001).";
          if (hintPass) hintPass.textContent = "💡 Enter your Class Code (e.g. cs301, bio101) or default password student123.";
          if (studentPills) studentPills.style.display = 'block';
          if (teacherPills) teacherPills.style.display = 'none';
          if (adminPills) adminPills.style.display = 'none';
        } else if (this.selectedRole === 'teacher') {
          labelUser.textContent = "Teacher Account / Name / ID";
          inputUser.placeholder = "Enter Teacher Full Name or ID (e.g. teacher_bio101)";
          labelPass.textContent = "Teacher Password / PIN";
          inputPass.placeholder = "Enter teacher password or PIN (e.g. teacher123)";
          inputPass.value = "";
          if (hintUser) hintUser.textContent = "💡 Enter your Full Name, Teacher ID, or assigned Class Code.";
          if (hintPass) hintPass.textContent = "💡 Enter your teacher password or custom PIN (default: teacher123).";
          if (studentPills) studentPills.style.display = 'none';
          if (teacherPills) teacherPills.style.display = 'block';
          if (adminPills) adminPills.style.display = 'none';
        } else {
          labelUser.textContent = "Admin ID";
          inputUser.placeholder = "admin";
          labelPass.textContent = "Administrator Passcode";
          inputPass.placeholder = "Enter passcode (e.g. admin2026)";
          inputPass.value = "";
          if (hintUser) hintUser.textContent = "💡 Default administrator ID is admin.";
          if (hintPass) hintPass.textContent = "💡 Passcode is admin2026 or admin123.";
          if (studentPills) studentPills.style.display = 'none';
          if (teacherPills) teacherPills.style.display = 'none';
          if (adminPills) adminPills.style.display = 'block';
        }

        this.loadRecentAccounts(container);
      });
    });

    // Bind student class quick pills
    container.querySelectorAll('.stu-class-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        inputPass.value = pill.dataset.class;
        inputPass.focus();
      });
    });

    // Bind teacher quick-select pills
    container.querySelectorAll('.t-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        inputUser.value = pill.dataset.tid;
        inputPass.value = pill.dataset.pass || 'teacher123';
      });
    });

    // Bind admin quick-select pill
    container.querySelector('#btn-admin-pill')?.addEventListener('click', () => {
      inputUser.value = 'admin';
      inputPass.value = 'admin2026';
    });

    const btnProceed = container.querySelector('#btn-proceed');
    const errorEl = container.querySelector('#login-error');
    
    const handleEnter = (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        btnProceed.click();
      }
    };
    inputUser.addEventListener("keydown", handleEnter);
    inputPass.addEventListener("keydown", handleEnter);
    
    btnProceed.addEventListener('click', async () => {
      const user = inputUser.value.trim();
      const pass = inputPass.value.trim();
      
      if (!user) {
        errorEl.textContent = this.selectedRole === 'student' 
          ? "Please enter your Student ID or Full Name." 
          : (this.selectedRole === 'teacher' 
            ? "Please enter your Teacher Name, Account, or Class Code." 
            : "Please enter your Admin ID.");
        errorEl.style.display = "block";
        inputUser.focus();
        return;
      }

      if (!pass) {
        errorEl.textContent = this.selectedRole === 'student' 
          ? "Please enter your Class Code or password to proceed." 
          : (this.selectedRole === 'teacher' 
            ? "Please enter your teacher password to proceed." 
            : "Please enter the administrator passcode to proceed.");
        errorEl.style.display = "block";
        inputPass.focus();
        return;
      }
      
      btnProceed.disabled = true;
      const originalText = btnProceed.innerHTML;
      btnProceed.textContent = "Verifying...";

      try {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            role: this.selectedRole,
            pin: pass,
            user_id: user
          })
        });
        
        const data = await res.json();
        if (res.ok && data.status === "authenticated") {
          errorEl.style.display = "none";
          if (data.token) {
            localStorage.setItem("d2d_session_token", data.token);
          }
          // Save credentials for session restore after OAuth redirect / server restart
          localStorage.setItem("d2d_role", this.selectedRole);
          const effectiveUserId = data.user_id || user;
          localStorage.setItem("d2d_user_id", effectiveUserId);
          localStorage.setItem("d2d_pin", pass);
          if (data.class_code) {
            localStorage.setItem("d2d_class_code", data.class_code);
          }
          if (data.student_name || data.teacher_name) {
            localStorage.setItem("d2d_student_name", data.student_name || data.teacher_name);
          }
          // Instruct app to switch to the main interface for this role
          this.app.completeLogin(this.selectedRole, effectiveUserId, pass, data.class_code);
        } else {
          errorEl.textContent = data.message || "Invalid credentials.";
          errorEl.style.display = "block";
          inputPass.focus();
        }
      } catch (e) {
        console.error("Login exception:", e);
        errorEl.textContent = `Error: ${e.message}`;
        errorEl.style.display = "block";
      } finally {
        btnProceed.disabled = false;
        btnProceed.innerHTML = originalText;
      }
    });

    const btnInstall = container.querySelector('#btn-login-install');
    if (btnInstall) {
      btnInstall.addEventListener('click', () => {
        if (window.DataToDirt) {
          window.DataToDirt.promptInstall();
        }
      });
    }
  }
}
window.LoginView = LoginView;
