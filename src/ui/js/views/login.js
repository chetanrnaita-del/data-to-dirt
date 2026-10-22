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
        <div style="width: 450px; background: #fff; border-radius: 30px 0 0 30px; box-shadow: -10px 0 30px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: center; padding: 50px; z-index: 10;">
          <h2 style="color: #34495e; font-size: 18px; font-weight: 600; margin-bottom: 20px;">Please select your role</h2>
          
          <div style="display: flex; gap: 10px; margin-bottom: 30px;">
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

          <div style="margin-bottom: 20px;">
            <label style="display: block; font-size: 13px; font-weight: 700; color: #2d3436; margin-bottom: 8px;">
              <span id="label-user">Student ID / Name</span> <span style="color: #e74c3c;">*</span>
            </label>
            <input type="text" id="login-user" placeholder="Enter Student ID (e.g. STU-001) or Name" style="width: 100%; padding: 14px 16px; border: 1px solid #dfe6e9; border-radius: 10px; font-size: 14px; outline: none; transition: border 0.2s; box-sizing: border-box;" />
          </div>

          <div style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <label style="font-size: 13px; font-weight: 700; color: #2d3436;">
                <span id="label-pass">Class Code</span> <span style="color: #e74c3c;">*</span>
              </label>
            </div>
            <input type="password" id="login-pass" placeholder="Enter class code (e.g., class-a)" style="width: 100%; padding: 14px 16px; border: 1px solid #dfe6e9; border-radius: 10px; font-size: 14px; outline: none; transition: border 0.2s; box-sizing: border-box;" />
          </div>

          <!-- Quick Select Shortcuts for Demo/Evaluation -->
          <div id="teacher-quick-select" style="display: none; margin-bottom: 20px;">
            <div style="font-size: 11px; font-weight: bold; color: #636e72; margin-bottom: 6px;">Select Teacher Account:</div>
            <div style="display: flex; flex-direction: column; gap: 5px;">
              <button type="button" class="t-pill" data-tid="teacher_bio101" data-pass="teacher123" style="font-size: 11px; padding: 6px 10px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; text-align: left; font-weight: 600;">🌿 Dr. Evelyn Reed — Bio 101 (10 students)</button>
              <button type="button" class="t-pill" data-tid="teacher_env201" data-pass="teacher123" style="font-size: 11px; padding: 6px 10px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; text-align: left; font-weight: 600;">🌍 Prof. Marcus Green — Env 201 (10 students)</button>
              <button type="button" class="t-pill" data-tid="teacher_cs301" data-pass="teacher123" style="font-size: 11px; padding: 6px 10px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; text-align: left; font-weight: 600;">💻 Ms. Clara Patel — CS 301 (10 students)</button>
              <button type="button" class="t-pill" data-tid="teacher_chem102" data-pass="teacher123" style="font-size: 11px; padding: 6px 10px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; text-align: left; font-weight: 600;">🧪 Dr. Arthur Thorne — Chem 102 (10 students)</button>
              <button type="button" class="t-pill" data-tid="teacher_earth204" data-pass="teacher123" style="font-size: 11px; padding: 6px 10px; border: 1px solid #c8d6e5; border-radius: 6px; background: #f8f9fa; cursor: pointer; text-align: left; font-weight: 600;">⛰️ Mr. Samuel Woods — Earth 204 (10 students)</button>
            </div>
          </div>
          
          <div id="login-error" style="color: #e74c3c; font-size: 13px; margin-bottom: 15px; display: none; font-weight: 600;"></div>

          <button id="btn-proceed" style="width: 100%; padding: 16px; background: #5f27cd; color: #fff; border: none; border-radius: 12px; font-size: 16px; font-weight: 700; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 10px; transition: background 0.2s; box-shadow: 0 4px 15px rgba(95, 39, 205, 0.3);">
            Proceed →
          </button>

          <!-- PWA Install Button on Login -->
          <div style="margin-top: 18px; text-align: center;">
            <button id="btn-login-install" type="button" style="background: #f8f9fa; border: 1.5px solid #dcdde1; border-radius: 10px; padding: 10px 16px; font-size: 13px; font-weight: 600; color: #2f3640; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; transition: all 0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.04);">
              <span>📲</span> Download / Install App
            </button>
          </div>

        </div>
      </div>
    `;

    this.bindEvents(container);
  }

  bindEvents(container) {
    const roleBtns = container.querySelectorAll('.role-btn');
    const labelUser = container.querySelector('#label-user');
    const labelPass = container.querySelector('#label-pass');
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
        
        const teacherPills = container.querySelector('#teacher-quick-select');

        // Update Labels
        if (this.selectedRole === 'student') {
          labelUser.textContent = "Student ID / Name";
          inputUser.placeholder = "Enter Student ID (e.g. STU-BIO-001) or Name";
          labelPass.textContent = "Class Code";
          inputPass.placeholder = "Enter class code (e.g., bio101)";
          if (teacherPills) teacherPills.style.display = 'none';
        } else if (this.selectedRole === 'teacher') {
          labelUser.textContent = "Teacher Account / Class Code";
          inputUser.placeholder = "e.g. teacher_bio101 or bio101";
          labelPass.textContent = "Password";
          inputPass.placeholder = "teacher123";
          if (teacherPills) teacherPills.style.display = 'block';
        } else {
          labelUser.textContent = "Admin ID";
          inputUser.placeholder = "Please enter admin ID";
          labelPass.textContent = "Password";
          inputPass.placeholder = "Please enter admin password";
          if (teacherPills) teacherPills.style.display = 'none';
        }
      });
    });

    // Bind teacher quick-select pills
    container.querySelectorAll('.t-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        inputUser.value = pill.dataset.tid;
        inputPass.value = pill.dataset.pass || 'teacher123';
      });
    });

    const btnProceed = container.querySelector('#btn-proceed');
    const errorEl = container.querySelector('#login-error');
    
    btnProceed.addEventListener('click', async () => {
      const user = inputUser.value.trim();
      const pass = inputPass.value.trim();
      
      if (!user) {
        errorEl.textContent = "Please enter your ID/Name.";
        errorEl.style.display = "block";
        return;
      }
      
      try {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            role: this.selectedRole,
            pin: pass,
            user_id: user // Send the user ID to group students by teacher
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
          localStorage.setItem("d2d_user_id", user);
          localStorage.setItem("d2d_pin", pass);
          if (data.class_code) {
            localStorage.setItem("d2d_class_code", data.class_code);
          }
          // Instruct app to switch to the main interface for this role
          this.app.completeLogin(this.selectedRole, user, pass, data.class_code);
        } else {
          errorEl.textContent = data.message || "Invalid credentials.";
          errorEl.style.display = "block";
        }
      } catch (e) {
        console.error("Login exception:", e);
        errorEl.textContent = `Error: ${e.message}`;
        errorEl.style.display = "block";
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
