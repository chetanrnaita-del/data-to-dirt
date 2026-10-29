class LoginView {
  constructor(app) {
    this.app = app;
    this.selectedRole = 'student';
    this._lockoutInterval = null;
    try {
      localStorage.removeItem("d2d_last_created_student");
    } catch (_) {}
  }

  async render(container) {
    container.innerHTML = `
      <div style="display: flex; height: 100%; background-color: #f5efe6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        
        <!-- Left Pane (Botanical Forest Environment) -->
        <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; background: linear-gradient(165deg, #132a17 0%, #1c3d22 55%, #0f1d11 100%); position: relative; overflow: hidden; padding: 30px;">
          <div style="z-index: 10; text-align: center; max-width: 420px;">
            <div style="width: 120px; height: 120px; background: #fdfbf7; border-radius: 20px; margin: 0 auto 20px auto; display: flex; align-items: center; justify-content: center; border: 3px solid #b07542; box-shadow: 0 10px 25px rgba(0,0,0,0.35); overflow: hidden;">
              <img src="/logo.png" alt="Data-to-Dirt Logo" style="width: 100%; height: 100%; object-fit: cover;" />
            </div>
            <h1 style="color: #f7eedb; font-size: 28px; margin: 0; font-weight: 800; letter-spacing: 2px; text-shadow: 0 2px 4px rgba(0,0,0,0.4);">DATA-TO-DIRT</h1>
            <p style="color: #9be05c; font-size: 14px; margin-top: 8px; font-weight: 600;">🌱 Transforming Digital Waste into Living Forests</p>
            <div style="margin-top: 18px; display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; background: rgba(255,255,255,0.08); border: 1px solid rgba(155, 224, 92, 0.3); border-radius: 20px; color: #d6f2c4; font-size: 12px; font-weight: 500;">
              <span>🌲</span> Authentic Carbon Reduction Platform
            </div>
          </div>
          
          <!-- Earthen Topography Accent Contours (Organic Nature Shapes) -->
          <div style="position: absolute; bottom: -60px; left: -10%; right: -10%; height: 220px; background: radial-gradient(ellipse at center, rgba(82, 148, 92, 0.28) 0%, rgba(45, 106, 54, 0.05) 70%, transparent 100%); border-radius: 50%; z-index: 1;"></div>
          <div style="position: absolute; bottom: -90px; left: 15%; right: -25%; height: 220px; background: radial-gradient(ellipse at center, rgba(176, 117, 66, 0.22) 0%, rgba(120, 72, 36, 0.05) 70%, transparent 100%); border-radius: 50%; z-index: 2;"></div>
        </div>

        <!-- Right Pane (Warm Earthen Paper Login Form) -->
        <div style="width: 480px; background: #fdfbf7; border-left: 1.5px solid #e2d7c5; border-radius: 24px 0 0 24px; box-shadow: -10px 0 30px rgba(44, 30, 17, 0.06); display: flex; flex-direction: column; justify-content: center; padding: 40px; z-index: 10; box-sizing: border-box; overflow-y: auto;">
          <h2 style="color: #2b1f14; font-size: 20px; font-weight: 700; margin-bottom: 6px;">Sign In to Account</h2>
          <div style="color: #6d5b4a; font-size: 13px; margin-bottom: 22px;">Choose your role to access your eco dashboard</div>
          
          <div style="display: flex; gap: 8px; margin-bottom: 24px; flex-wrap: wrap;">
            <button class="role-btn active" data-role="student" style="flex: 1; min-width: 100px; padding: 12px 6px; border: 2px solid #2d6a36; border-radius: 10px; background: #eef6ef; color: #1e4a23; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; transition: all 0.2s;">
              <span style="font-size: 18px;">🧑‍🎓</span> Student
            </button>
            <button class="role-btn" data-role="teacher" style="flex: 1; min-width: 100px; padding: 12px 6px; border: 1.5px solid #ded4c5; border-radius: 10px; background: #ffffff; color: #6d5b4a; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; transition: all 0.2s;">
              <span style="font-size: 18px;">👨‍🏫</span> Staff
            </button>
            <button class="role-btn" data-role="admin" style="flex: 1; min-width: 90px; padding: 12px 6px; border: 1.5px solid #ded4c5; border-radius: 10px; background: #ffffff; color: #6d5b4a; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; transition: all 0.2s;">
              <span style="font-size: 18px;">⚙️</span> Admin
            </button>
          </div>

          <!-- Security System: Progressive Safety Lock Alert -->
          <div id="safety-lock-banner" style="display: none; margin-bottom: 16px; padding: 12px 14px; border-radius: 10px; background: rgba(192, 57, 43, 0.10); border: 1.5px solid #c0392b; font-size: 12.5px; color: #962d22; line-height: 1.45;">
            <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; margin-bottom: 4px; font-size: 13.5px; color: #c0392b;">
              <span style="font-size: 18px;">🔒</span> Security System: Safety Lock Active
            </div>
            <div id="safety-lock-desc">
              Too many incorrect password attempts. Login is temporarily locked for <strong id="safety-lock-timer" style="font-size: 14px; color: #c0392b;">10s</strong>.
            </div>
            <div style="font-size: 11px; opacity: 0.85; margin-top: 4px;">
              ⏱️ Safety lock duration increases with each single wrong password.
            </div>
          </div>

          <div style="margin-bottom: 18px;">
            <label style="display: block; font-size: 13px; font-weight: 700; color: #2b1f14; margin-bottom: 6px;">
              <span id="label-user">Student ID / Name</span> <span style="color: #c0392b;">*</span>
            </label>
            <input type="text" id="login-user" placeholder="Enter Student ID or Full Name" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" data-lpignore="true" data-1p-ignore="true" style="width: 100%; padding: 13px 15px; border: 1.5px solid #d4c8b8; border-radius: 8px; font-size: 14px; background: #ffffff; color: #2b1f14; outline: none; transition: border-color 0.2s; box-sizing: border-box;" />
            <div id="hint-user" style="font-size: 11px; color: #6d5b4a; margin-top: 4px;">
              💡 Enter your registered Student Full Name or Student ID.
            </div>
          </div>

          <div style="margin-bottom: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <label style="font-size: 13px; font-weight: 700; color: #2b1f14;">
                <span id="label-pass">Grade or Password</span> <span style="color: #c0392b;">*</span>
              </label>
            </div>
            <input type="password" id="login-pass" placeholder="Enter grade (e.g., grade5, grade6) or password" autocomplete="new-password" autocorrect="off" autocapitalize="off" spellcheck="false" data-lpignore="true" data-1p-ignore="true" style="width: 100%; padding: 13px 15px; border: 1.5px solid #d4c8b8; border-radius: 8px; font-size: 14px; background: #ffffff; color: #2b1f14; outline: none; transition: border-color 0.2s; box-sizing: border-box;" />
            <div id="hint-pass" style="font-size: 11px; color: #6d5b4a; margin-top: 4px;">
              💡 Select your Grade below or enter your password.
            </div>
          </div>

          <!-- Quick Select Shortcuts for Students -->
          <div id="student-quick-select" style="display: block; margin-bottom: 18px;">
            <div style="font-size: 11px; font-weight: bold; color: #5c4e3f; margin-bottom: 6px;">Select Your Grade:</div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
              <button type="button" class="stu-class-pill" data-class="grade5" style="font-size: 11px; padding: 5px 9px; border: 1.5px solid #d4c8b8; border-radius: 6px; background: #f5efe6; color: #3b2f23; cursor: pointer; font-weight: 600;">🎒 Grade 5</button>
              <button type="button" class="stu-class-pill" data-class="grade6" style="font-size: 11px; padding: 5px 9px; border: 1.5px solid #d4c8b8; border-radius: 6px; background: #f5efe6; color: #3b2f23; cursor: pointer; font-weight: 600;">🎒 Grade 6</button>
              <button type="button" class="stu-class-pill" data-class="grade7" style="font-size: 11px; padding: 5px 9px; border: 1.5px solid #d4c8b8; border-radius: 6px; background: #f5efe6; color: #3b2f23; cursor: pointer; font-weight: 600;">🎒 Grade 7</button>
              <button type="button" class="stu-class-pill" data-class="grade8" style="font-size: 11px; padding: 5px 9px; border: 1.5px solid #d4c8b8; border-radius: 6px; background: #f5efe6; color: #3b2f23; cursor: pointer; font-weight: 600;">🎒 Grade 8</button>
              <button type="button" class="stu-class-pill" data-class="grade9" style="font-size: 11px; padding: 5px 9px; border: 1.5px solid #d4c8b8; border-radius: 6px; background: #f5efe6; color: #3b2f23; cursor: pointer; font-weight: 600;">🎓 Grade 9</button>
              <button type="button" class="stu-class-pill" data-class="grade10" style="font-size: 11px; padding: 5px 9px; border: 1.5px solid #d4c8b8; border-radius: 6px; background: #f5efe6; color: #3b2f23; cursor: pointer; font-weight: 600;">🎓 Grade 10</button>
              <button type="button" class="stu-class-pill" data-class="grade11" style="font-size: 11px; padding: 5px 9px; border: 1.5px solid #d4c8b8; border-radius: 6px; background: #f5efe6; color: #3b2f23; cursor: pointer; font-weight: 600;">🎓 Grade 11</button>
              <button type="button" class="stu-class-pill" data-class="grade12" style="font-size: 11px; padding: 5px 9px; border: 1.5px solid #d4c8b8; border-radius: 6px; background: #f5efe6; color: #3b2f23; cursor: pointer; font-weight: 600;">🎓 Grade 12</button>
            </div>
          </div>
          
          <div id="login-error" style="color: #c0392b; font-size: 13px; margin-bottom: 15px; display: none; font-weight: 600; line-height: 1.4;"></div>

          <button id="btn-proceed" style="width: 100%; padding: 14px; background: #2d6a36; color: #ffffff; border: none; border-radius: 10px; font-size: 15px; font-weight: 700; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 8px; transition: background 0.2s, transform 0.1s; box-shadow: 0 4px 12px rgba(45, 106, 54, 0.28);">
            Proceed →
          </button>

          <!-- Outside & Personal Google Account Connection Section -->
          <div style="display: flex; align-items: center; margin: 20px 0 14px 0; gap: 10px;">
            <div style="flex: 1; height: 1px; background: #e2d7c5;"></div>
            <span style="font-size: 11px; font-weight: bold; color: #8c7b6c; text-transform: uppercase; letter-spacing: 0.5px;">Or Sign In With Google</span>
            <div style="flex: 1; height: 1px; background: #e2d7c5;"></div>
          </div>

          <div style="display: flex; flex-direction: column; gap: 9px;">
            <a href="/auth/google/login?provider=school" class="retro-btn" id="btn-login-google-school" style="text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 10px; padding: 12px 14px; background: #eef6ef; border: 2px solid #2d6a36; border-radius: 10px; color: #1e4a23; font-weight: 700; font-size: 13.5px; box-shadow: 0 2px 8px rgba(45, 106, 54, 0.2); cursor: pointer; transition: all 0.2s;">
              <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg>
              <span>🏫 <strong>Sign In with Lighthouse Email</strong></span>
            </a>

            <a href="/auth/google/login?provider=personal" class="retro-btn" id="btn-login-google-personal" style="text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 10px; padding: 12px 14px; background: #ffffff; border: 2px solid #b07542; border-radius: 10px; color: #784824; font-weight: 700; font-size: 13.5px; box-shadow: 0 2px 8px rgba(176, 117, 66, 0.15); cursor: pointer; transition: all 0.2s;">
              <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg>
              <span>📧 <strong>Sign In with Personal Email</strong> (@gmail.com)</span>
            </a>
          </div>

          <!-- PWA Install Option on Login -->
          <div style="margin-top: 16px; text-align: center; display: flex; justify-content: center; gap: 10px; flex-wrap: wrap;">
            <button id="btn-login-install" type="button" style="background: #f7f3ec; border: 1.5px solid #cfc2af; border-radius: 8px; padding: 8px 14px; font-size: 12px; font-weight: 600; color: #3d3328; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s;">
              <span>📲</span> Install App
            </button>
          </div>

        </div>
      </div>
    `;

    this.bindEvents(container);
    this.checkExistingSafetyLock(container);
  }

  checkExistingSafetyLock(container) {
    const rawUntil = sessionStorage.getItem('d2d_safety_lock_until');
    if (rawUntil) {
      const until = parseInt(rawUntil, 10);
      const now = Date.now();
      if (until > now) {
        const remaining = Math.ceil((until - now) / 1000);
        const attempts = parseInt(sessionStorage.getItem('d2d_safety_lock_attempts') || '3', 10);
        this.startSafetyLock(remaining, attempts, container);
        return true;
      } else {
        sessionStorage.removeItem('d2d_safety_lock_until');
      }
    }
    return false;
  }

  startSafetyLock(seconds, failedCount, container) {
    const lockBanner = container.querySelector('#safety-lock-banner');
    const lockTimerEl = container.querySelector('#safety-lock-timer');
    const lockDescEl = container.querySelector('#safety-lock-desc');
    const inputUser = container.querySelector('#login-user');
    const inputPass = container.querySelector('#login-pass');
    const btnProceed = container.querySelector('#btn-proceed');
    const errorEl = container.querySelector('#login-error');

    if (!lockBanner || !lockTimerEl || !btnProceed) return;

    if (this._lockoutInterval) {
      clearInterval(this._lockoutInterval);
      this._lockoutInterval = null;
    }

    const lockoutUntil = Date.now() + (seconds * 1000);
    sessionStorage.setItem('d2d_safety_lock_until', String(lockoutUntil));
    sessionStorage.setItem('d2d_safety_lock_attempts', String(failedCount));

    if (inputUser) inputUser.disabled = true;
    if (inputPass) inputPass.disabled = true;
    btnProceed.disabled = true;
    btnProceed.style.opacity = '0.6';
    btnProceed.style.cursor = 'not-allowed';

    if (errorEl) errorEl.style.display = 'none';

    lockBanner.style.display = 'block';
    if (lockDescEl) {
      lockDescEl.innerHTML = `Too many incorrect attempts (${failedCount}). Security lockout active for <strong id="safety-lock-timer" style="font-size: 14px; color: #c0392b;">${seconds}s</strong>.`;
    }

    let remaining = seconds;
    btnProceed.textContent = `🔒 Locked (${remaining}s)`;

    this._lockoutInterval = setInterval(() => {
      remaining -= 1;
      const currentTimer = container.querySelector('#safety-lock-timer');
      if (currentTimer) currentTimer.textContent = `${remaining}s`;
      btnProceed.textContent = `🔒 Locked (${remaining}s)`;

      if (remaining <= 0) {
        clearInterval(this._lockoutInterval);
        this._lockoutInterval = null;
        sessionStorage.removeItem('d2d_safety_lock_until');

        lockBanner.style.display = 'none';
        if (inputUser) inputUser.disabled = false;
        if (inputPass) {
          inputPass.disabled = false;
          inputPass.value = '';
          inputPass.focus();
        }
        btnProceed.disabled = false;
        btnProceed.style.opacity = '';
        btnProceed.style.cursor = 'pointer';
        btnProceed.textContent = 'Proceed →';

        if (errorEl) {
          errorEl.style.display = 'block';
          errorEl.style.color = '#2d6a36';
          errorEl.textContent = '🔓 Safety lock released. You may now enter your password.';
        }
      }
    }, 1000);
  }

  bindEvents(container) {
    const roleBtns = container.querySelectorAll('.role-btn');
    const labelUser = container.querySelector('#label-user');
    const labelPass = container.querySelector('#label-pass');
    const hintUser = container.querySelector('#hint-user');
    const hintPass = container.querySelector('#hint-pass');
    const inputUser = container.querySelector('#login-user');
    const inputPass = container.querySelector('#login-pass');
    const errorEl = container.querySelector('#login-error');
    
    roleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        // Update UI styles
        roleBtns.forEach(b => {
          b.classList.remove('active');
          b.style.border = '1.5px solid #ded4c5';
          b.style.background = '#ffffff';
          b.style.color = '#6d5b4a';
          b.style.fontWeight = '600';
        });
        
        btn.classList.add('active');
        btn.style.border = '2px solid #2d6a36';
        btn.style.background = '#eef6ef';
        btn.style.color = '#1e4a23';
        btn.style.fontWeight = '700';
        
        this.selectedRole = btn.dataset.role;
        
        const studentPills = container.querySelector('#student-quick-select');

        // Update Labels & Hints
        if (this.selectedRole === 'student') {
          labelUser.textContent = "Student ID or Name";
          inputUser.placeholder = "Enter Student ID or Full Name";
          labelPass.textContent = "Grade Code or Password";
          inputPass.placeholder = "Enter grade (e.g., grade5, grade6) or password";
          inputPass.value = "";
          if (hintUser) hintUser.textContent = "💡 Enter your registered Student Full Name or Student ID.";
          if (hintPass) hintPass.textContent = "💡 Select your Grade above (e.g. Grade 5, Grade 6) or enter password.";
          if (studentPills) studentPills.style.display = 'block';
        } else if (this.selectedRole === 'teacher') {
          labelUser.textContent = "Teacher Account / Name / ID";
          inputUser.placeholder = "Enter Teacher Full Name or ID";
          labelPass.textContent = "Teacher Password / PIN";
          inputPass.placeholder = "Enter teacher password or PIN";
          inputPass.value = "";
          if (hintUser) hintUser.textContent = "💡 Enter your Full Name, Teacher ID, or assigned Grade (e.g. grade5).";
          if (hintPass) hintPass.textContent = "💡 Enter your teacher password or custom PIN.";
          if (studentPills) studentPills.style.display = 'none';
        } else {
          labelUser.textContent = "Admin ID";
          inputUser.placeholder = "Enter Admin ID";
          labelPass.textContent = "Administrator Passcode";
          inputPass.placeholder = "Enter passcode";
          inputPass.value = "";
          if (hintUser) hintUser.textContent = "💡 Enter administrator username.";
          if (hintPass) hintPass.textContent = "💡 Enter administrator passcode.";
          if (studentPills) studentPills.style.display = 'none';
        }

        if (errorEl && errorEl.style.display !== 'none' && !this._lockoutInterval) {
          errorEl.style.display = 'none';
        }
      });
    });

    // Helper to update Google buttons links with selected grade and student hint
    const updateGoogleSchoolBtnHref = () => {
      const schoolBtn = container.querySelector('#btn-login-google-school');
      const personalBtn = container.querySelector('#btn-login-google-personal');
      const selectedGrade = inputPass.value.trim() || localStorage.getItem("d2d_class_code") || "grade5";
      const userHint = inputUser.value.trim() || localStorage.getItem("d2d_student_name") || localStorage.getItem("d2d_user_id") || "";
      
      if (schoolBtn) {
        let href = `/auth/google/login?provider=school&grade=${encodeURIComponent(selectedGrade)}`;
        if (userHint && !userHint.toLowerCase().startsWith("guest") && !userHint.toLowerCase().startsWith("personal")) {
          href += `&student_hint=${encodeURIComponent(userHint)}`;
        }
        schoolBtn.href = href;
      }

      if (personalBtn) {
        let href = `/auth/google/login?provider=personal&grade=${encodeURIComponent(selectedGrade)}`;
        if (userHint && !userHint.toLowerCase().startsWith("guest") && !userHint.toLowerCase().startsWith("personal")) {
          href += `&student_hint=${encodeURIComponent(userHint)}`;
        }
        personalBtn.href = href;
      }
    };

    // Bind student class quick pills
    container.querySelectorAll('.stu-class-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        if (inputPass.disabled) return;
        const selectedGrade = pill.dataset.class;
        inputPass.value = selectedGrade;
        localStorage.setItem("d2d_class_code", selectedGrade);
        updateGoogleSchoolBtnHref();
        container.querySelectorAll('.stu-class-pill').forEach(p => {
          p.style.background = "#f5efe6";
          p.style.borderColor = "#d4c8b8";
        });
        pill.style.background = "#dbeee0";
        pill.style.borderColor = "#2d6a36";
        inputPass.focus();
      });
    });

    inputUser.addEventListener('input', updateGoogleSchoolBtnHref);
    inputPass.addEventListener('input', updateGoogleSchoolBtnHref);
    updateGoogleSchoolBtnHref();

    container.querySelector('#btn-login-google-school')?.addEventListener('click', () => {
      localStorage.setItem("d2d_google_provider", "school");
      updateGoogleSchoolBtnHref();
    });

    container.querySelector('#btn-login-google-personal')?.addEventListener('click', () => {
      localStorage.setItem("d2d_google_provider", "personal");
      localStorage.setItem("d2d_role", "student");
      updateGoogleSchoolBtnHref();
    });

    const btnProceed = container.querySelector('#btn-proceed');
    
    const handleEnter = (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (!btnProceed.disabled) {
          btnProceed.click();
        }
      }
    };
    inputUser.addEventListener("keydown", handleEnter);
    inputPass.addEventListener("keydown", handleEnter);
    
    btnProceed.addEventListener('click', async () => {
      if (this._lockoutInterval) return;

      const isPersonal = this.selectedRole === 'personal';
      const user = inputUser.value.trim() || (isPersonal ? "Personal User" : "");
      const pass = inputPass.value.trim() || (isPersonal ? "student123" : "");
      
      if (!user && !isPersonal) {
        errorEl.textContent = this.selectedRole === 'student' 
          ? "Please enter your Student ID or Full Name." 
          : (this.selectedRole === 'teacher' 
            ? "Please enter your Teacher Name, Account, or Class Code." 
            : "Please enter your Admin ID.");
        errorEl.style.color = "#c0392b";
        errorEl.style.display = "block";
        inputUser.focus();
        return;
      }

      if (!pass && !isPersonal) {
        errorEl.textContent = this.selectedRole === 'student' 
          ? "Please enter your Class Code or password to proceed." 
          : (this.selectedRole === 'teacher' 
            ? "Please enter your teacher password to proceed." 
            : "Please enter the administrator passcode to proceed.");
        errorEl.style.color = "#c0392b";
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
          sessionStorage.removeItem('d2d_safety_lock_until');
          sessionStorage.removeItem('d2d_safety_lock_attempts');
          if (this._lockoutInterval) {
            clearInterval(this._lockoutInterval);
            this._lockoutInterval = null;
          }

          if (data.token) {
            localStorage.setItem("d2d_session_token", data.token);
          }
          // Save credentials for session restore after OAuth redirect / server restart
          const targetRole = this.selectedRole === 'personal' ? 'student' : this.selectedRole;
          localStorage.setItem("d2d_role", targetRole);
          if (this.selectedRole === 'personal') {
            localStorage.setItem("d2d_google_provider", "personal");
          }
          const effectiveUserId = data.user_id || user;
          localStorage.setItem("d2d_user_id", effectiveUserId);
          localStorage.setItem("d2d_pin", pass);
          if (data.class_code) {
            localStorage.setItem("d2d_class_code", data.class_code);
          }
          const effectiveDisplayName = data.student_name || data.teacher_name || data.name || user;
          if (effectiveDisplayName) {
            localStorage.setItem("d2d_student_name", effectiveDisplayName);
          }
          // Instruct app to switch to the main interface for this role
          this.app.completeLogin(targetRole, effectiveUserId, pass, data.class_code || "all", effectiveDisplayName);
        } else {
          // Check if safety lock triggered or active
          if (data.error_code === "safety_lock" || (data.lockout_seconds && data.lockout_seconds > 0)) {
            const sec = data.remaining_seconds || data.lockout_seconds || 10;
            const attempts = data.failed_attempts || 3;
            this.startSafetyLock(sec, attempts, container);
          } else {
            errorEl.textContent = data.message || "Invalid credentials.";
            errorEl.style.color = "#c0392b";
            errorEl.style.display = "block";
            inputPass.focus();
          }
        }
      } catch (e) {
        console.error("Login exception:", e);
        errorEl.textContent = `Error: ${e.message}`;
        errorEl.style.color = "#c0392b";
        errorEl.style.display = "block";
      } finally {
        if (!this._lockoutInterval) {
          btnProceed.disabled = false;
          btnProceed.innerHTML = originalText;
        }
      }
    });

    const btnGooglePersonal = container.querySelector('#btn-login-google-personal');
    if (btnGooglePersonal) {
      btnGooglePersonal.addEventListener('click', () => {
        localStorage.setItem("d2d_google_provider", "personal");
        localStorage.setItem("d2d_role", "student");
      });
    }

    const btnGoogleSchool = container.querySelector('#btn-login-google-school');
    if (btnGoogleSchool) {
      btnGoogleSchool.addEventListener('click', () => {
        localStorage.setItem("d2d_google_provider", "school");
      });
    }

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
