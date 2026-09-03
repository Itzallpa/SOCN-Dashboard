/**
 * SOC Operations Control Center - Public View & Local Database Auth Guard
 * - Everyone can view index.html freely
 * - Unauthenticated users cannot click/open modules (triggers Login/Signup modal)
 * - Users database stored directly in browser localStorage
 * Author: Antigravity AI
 */

(function () {
  const IDLE_TIMEOUT_MS = 60 * 60 * 1000; // 1 Hour (3,600,000 ms)
  const WARNING_BEFORE_MS = 5 * 60 * 1000;

  let idleTimer = null;
  let warningTimer = null;
  let lastActiveTimestamp = Date.now();

  // Local database initialization
  function getUsersDatabase() {
    try {
      const db = localStorage.getItem('socn_user_db');
      if (db) return JSON.parse(db);
    } catch (e) {}
    
    // Default initial user database
    const initialDb = [
      { name: 'Admin SOC', email: 'admin@spxexpress.com', pass: '1234', role: 'Admin' },
      { name: 'Ground Operator', email: 'ground@spxexpress.com', pass: '1234', role: 'Ground' }
    ];
    localStorage.setItem('socn_user_db', JSON.stringify(initialDb));
    return initialDb;
  }

  function saveUsersDatabase(users) {
    localStorage.setItem('socn_user_db', JSON.stringify(users));
  }

  function getStoredUser() {
    try {
      const u = localStorage.getItem('socn_user') || sessionStorage.getItem('socn_user');
      return u ? JSON.parse(u) : null;
    } catch (e) { return null; }
  }

  function saveStoredUser(user) {
    localStorage.setItem('socn_user', JSON.stringify(user));
    localStorage.setItem('socn_last_active', String(Date.now()));
  }

  function clearStoredUser() {
    localStorage.removeItem('socn_user');
    sessionStorage.removeItem('socn_user');
    localStorage.removeItem('socn_last_active');
  }

  /* ─── Login & Sign Up Modal ─── */
  function showAuthModal(customTitle) {
    if (document.getElementById('socnAuthOverlay')) {
      document.getElementById('socnAuthOverlay').style.display = 'flex';
      return;
    }

    const overlay = document.createElement('div');
    overlay.id = 'socnAuthOverlay';
    overlay.innerHTML = `
      <style>
        #socnAuthOverlay {
          position:fixed; inset:0; z-index:99999999;
          background:rgba(13,27,42,0.85); backdrop-filter:blur(8px);
          display:flex; align-items:center; justify-content:center;
          font-family:'Segoe UI',system-ui,sans-serif; padding:16px;
        }
        #socnAuthCard {
          background:#fff; border-radius:22px; width:100%; max-width:440px;
          box-shadow:0 30px 60px rgba(0,0,0,0.5); overflow:hidden; position:relative;
        }
        #socnAuthCard .auth-header {
          background:#0d1b2a; color:#fff; padding:24px 24px; text-align:center; position:relative;
        }
        #socnAuthCard .auth-body { padding:24px; }
        .auth-nav-tabs { display:flex; border-bottom:2px solid #e2e8f0; margin-bottom:20px; }
        .auth-nav-tab {
          flex:1; text-align:center; padding:10px; font-weight:700; font-size:0.9rem;
          color:#64748b; cursor:pointer; border-bottom:3px solid transparent; margin-bottom:-2px;
        }
        .auth-nav-tab.active { color:#2563eb; border-bottom-color:#2563eb; }
        
        .field-group { margin-bottom:14px; }
        .field-group label { display:block; font-size:0.8rem; font-weight:700; color:#334155; margin-bottom:5px; }
        .field-group input, .field-group select {
          width:100%; padding:10px 14px; border:1.5px solid #cbd5e1; border-radius:10px;
          font-size:0.92rem; outline:none; box-sizing:border-box;
        }
        .field-group input:focus { border-color:#2563eb; }

        .auth-submit-btn {
          width:100%; background:#2563eb; color:#fff; border:none; padding:12px;
          border-radius:12px; font-weight:800; font-size:0.95rem; cursor:pointer;
          box-shadow:0 4px 14px rgba(37,99,235,0.35); transition:all .2s; margin-top:6px;
        }
        .auth-submit-btn:hover { background:#1d4ed8; }

        .close-modal-btn {
          position:absolute; top:16px; right:16px; background:transparent; border:none;
          color:#94a3b8; font-size:1.4rem; cursor:pointer; line-height:1;
        }
        .close-modal-btn:hover { color:#fff; }
      </style>

      <div id="socnAuthCard">
        <div class="auth-header">
          <button class="close-modal-btn" onclick="document.getElementById('socnAuthOverlay').style.display='none'">✕</button>
          <div style="font-size:2.2rem; margin-bottom:4px;">🔒</div>
          <h4 style="font-weight:800; margin:0; font-size:1.2rem;">${customTitle || 'SOC Operations Portal'}</h4>
          <p style="font-size:0.78rem; color:#94a3b8; margin:4px 0 0;">เข้าสู่ระบบหรือลงทะเบียนเพื่อใช้งานโมดูล</p>
        </div>

        <div class="auth-body">
          <div class="auth-nav-tabs">
            <div class="auth-nav-tab active" id="tabLoginBtn" onclick="window.AuthGuard.switchTab('login')">🔑 เข้าสู่ระบบ (Login)</div>
            <div class="auth-nav-tab" id="tabSignupBtn" onclick="window.AuthGuard.switchTab('signup')">📝 ลงทะเบียน (Sign Up)</div>
          </div>

          <!-- LOGIN FORM -->
          <form id="socnLoginForm" onsubmit="window.AuthGuard.handleLoginSubmit(event)">
            <div class="field-group">
              <label>ชื่อผู้ใช้งาน หรือ อีเมล (Username / Email):</label>
              <input type="text" id="loginUserField" placeholder="เช่น Admin SOC หรือ admin@spxexpress.com" required>
            </div>
            <div class="field-group">
              <label>รหัสผ่าน (Password / PIN):</label>
              <input type="password" id="loginPassField" placeholder="กรอกรหัสผ่าน" required>
            </div>
            <button type="submit" class="auth-submit-btn">เข้าสู่ระบบ (Login)</button>
          </form>

          <!-- SIGNUP FORM -->
          <form id="socnSignupForm" style="display:none;" onsubmit="window.AuthGuard.handleSignupSubmit(event)">
            <div class="field-group">
              <label>ตั้งชื่อผู้ใช้งาน (Username / Display Name):</label>
              <input type="text" id="signupNameField" placeholder="เช่น Natakorn / Operator A" required>
            </div>
            <div class="field-group">
              <label>อีเมล (Email):</label>
              <input type="email" id="signupEmailField" placeholder="your.name@spxexpress.com" required>
            </div>
            <div class="field-group">
              <label>สร้างรหัสผ่าน (Password / PIN):</label>
              <input type="password" id="signupPassField" placeholder="กำหนดรหัสผ่าน" required>
            </div>
            <div class="field-group">
              <label>ระดับสิทธิ์การใช้งาน (User Role):</label>
              <select id="signupRoleSelect">
                <option value="Ground">👤 Ground (เจ้าหน้าที่ปฏิบัติการ)</option>
                <option value="Admin">🛡️ Admin (ผู้ดูแลระบบ & Audit Logs)</option>
              </select>
            </div>
            <button type="submit" class="auth-submit-btn" style="background:#059669;">ลงทะเบียนใหม่ (Sign Up)</button>
          </form>

          <div style="font-size:0.72rem; color:#94a3b8; text-align:center; margin-top:16px;">
            💾 ฐานข้อมูลบันทึกใน LocalStorage ของเครื่องโดยตรง
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
  }

  function switchTab(tab) {
    const loginForm = document.getElementById('socnLoginForm');
    const signupForm = document.getElementById('socnSignupForm');
    const tabLogin = document.getElementById('tabLoginBtn');
    const tabSignup = document.getElementById('tabSignupBtn');

    if (tab === 'login') {
      loginForm.style.display = 'block';
      signupForm.style.display = 'none';
      tabLogin.classList.add('active');
      tabSignup.classList.remove('active');
    } else {
      loginForm.style.display = 'none';
      signupForm.style.display = 'block';
      tabLogin.classList.remove('active');
      tabSignup.classList.add('active');
    }
  }

  function handleLoginSubmit(evt) {
    if (evt) evt.preventDefault();

    const userInput = (document.getElementById('loginUserField').value || '').trim().toLowerCase();
    const passInput = (document.getElementById('loginPassField').value || '').trim();

    const db = getUsersDatabase();
    const foundUser = db.find(u => 
      (u.name.toLowerCase() === userInput || u.email.toLowerCase() === userInput) && u.pass === passInput
    );

    if (foundUser) {
      finalizeLogin({
        name: foundUser.name,
        email: foundUser.email,
        role: foundUser.role,
        picture: `https://ui-avatars.com/api/?name=${encodeURIComponent(foundUser.name)}&background=0d1b2a&color=fff`
      });
    } else {
      alert('❌ ไม่พบบัญชีผู้ใช้ หรือ รหัสผ่านไม่ถูกต้อง\nกรุณาลงทะเบียนใหม่ที่แท็บ "ลงทะเบียน"');
    }
  }

  function handleSignupSubmit(evt) {
    if (evt) evt.preventDefault();

    const name = (document.getElementById('signupNameField').value || '').trim();
    const email = (document.getElementById('signupEmailField').value || '').trim().toLowerCase();
    const pass = (document.getElementById('signupPassField').value || '').trim();
    const role = document.getElementById('signupRoleSelect').value;

    if (!name || !email || !pass) {
      alert('กรุณากรอกข้อมูลให้ครบถ้วน');
      return;
    }

    const db = getUsersDatabase();
    const existing = db.find(u => u.email.toLowerCase() === email);

    if (existing) {
      alert('⚠️ อีเมลนี้ถูกลงทะเบียนไว้แล้ว กรุณาใช้แท็บ "เข้าสู่ระบบ"');
      switchTab('login');
      return;
    }

    const newUser = { name, email, pass, role };
    db.push(newUser);
    saveUsersDatabase(db);

    alert(`✅ ลงทะเบียนสำเร็จ! ยินดีต้อนรับคุณ ${name} (${role})`);

    finalizeLogin({
      name: name,
      email: email,
      role: role,
      picture: `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=0d1b2a&color=fff`
    });
  }

  function finalizeLogin(user) {
    saveStoredUser(user);

    fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(user)
    }).catch(function () {});

    const ov = document.getElementById('socnAuthOverlay');
    if (ov) ov.style.display = 'none';

    unlockPageInteractions();
    renderProfileBadge();
    resetIdleTimer();
  }

  /* ─── Click Guard & Page Interaction Lock ─── */
  function lockPageInteractions() {
    const user = getStoredUser();

    // If on a module page directly (lh_trip.html, investigation.html, etc.) and not logged in
    const isModulePage = location.pathname.includes('.html') && !location.pathname.includes('index.html');
    if (!user && isModulePage) {
      showAuthModal('🔒 กรุณาล็อกอินเพื่อใช้งาน');
    }

    // Attach click interceptor to interactive module cards and links if not logged in
    document.querySelectorAll('.module-card, a.btn, button.btn-module').forEach(el => {
      el.addEventListener('click', function (e) {
        const u = getStoredUser();
        if (!u) {
          e.preventDefault();
          e.stopPropagation();
          showAuthModal('🔒 กรุณาเข้าสู่ระบบเพื่อใช้งานโมดูลนี้');
          return false;
        }
      }, true);
    });
  }

  function unlockPageInteractions() {
    // Refresh badge and page state
    renderProfileBadge();
  }

  /* ─── Idle Timeout ─── */
  function resetIdleTimer() {
    lastActiveTimestamp = Date.now();
    localStorage.setItem('socn_last_active', String(lastActiveTimestamp));
    if (idleTimer) clearTimeout(idleTimer);
    if (warningTimer) clearTimeout(warningTimer);

    warningTimer = setTimeout(showWarning, IDLE_TIMEOUT_MS - WARNING_BEFORE_MS);
    idleTimer = setTimeout(function () {
      doAutoLogout('ไม่มีการใช้งานเกิน 1 ชั่วโมง (Idle Timeout)');
    }, IDLE_TIMEOUT_MS);
  }

  function showWarning() {
    if (!getStoredUser()) return;
    let w = document.getElementById('socnIdleWarn');
    if (!w) {
      w = document.createElement('div');
      w.id = 'socnIdleWarn';
      w.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:99998;background:#b7791f;color:#fff;padding:14px 20px;border-radius:10px;box-shadow:0 10px 25px rgba(0,0,0,.3);font-family:sans-serif;font-size:13px;display:flex;align-items:center;gap:12px;';
      w.innerHTML = '<div><strong>⏰ เซสชันกำลังจะหมดอายุ</strong><div>ไม่มีการใช้งานนาน 55 นาที จะ Logout อัตโนมัติในอีก 5 นาที</div></div><button onclick="window.AuthGuard.extendSession()" style="background:#fff;color:#b7791f;border:none;padding:6px 12px;border-radius:6px;font-weight:bold;cursor:pointer;">ต่อเวลา</button>';
      document.body.appendChild(w);
    } else { w.style.display = 'flex'; }
  }

  function doAutoLogout(reason) {
    var u = getStoredUser();
    if (u) logActivity('IDLE_AUTO_LOGOUT', reason);
    clearStoredUser();
    fetch('/api/auth/logout', { method: 'POST' }).catch(function () {});
    document.querySelectorAll('.user-profile-badge').forEach(function (el) { el.remove(); });
    renderProfileBadge();
    showAuthModal('🔒 เซสชันหมดอายุ กรุณาล็อกอินใหม่');
  }

  function setupActivityListeners() {
    ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(function (evt) {
      window.addEventListener(evt, function () {
        if (Date.now() - lastActiveTimestamp > 10000) {
          resetIdleTimer();
          var w = document.getElementById('socnIdleWarn');
          if (w) w.style.display = 'none';
        }
      }, { passive: true });
    });
    resetIdleTimer();
  }

  function logActivity(action, details) {
    var u = getStoredUser();
    fetch('/api/log-client-activity', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: action, details: details, user_email: u ? u.email : 'guest', user_name: u ? u.name : 'Guest' })
    }).catch(function () {});
  }

  /* ─── Profile Badge on Navbar ─── */
  function renderProfileBadge() {
    var user = getStoredUser();
    document.querySelectorAll('.top-nav, nav').forEach(function (nav) {
      var badge = nav.querySelector('.user-profile-badge');
      if (!badge) {
        badge = document.createElement('div');
        badge.className = 'user-profile-badge';
        badge.style.cssText = 'display:flex;align-items:center;gap:10px;font-size:.85rem;margin-left:auto;';
        nav.appendChild(badge);
      }

      if (user) {
        var roleBg = user.role === 'Admin' ? '#d0311d' : '#2563eb';
        var audit = user.role === 'Admin' ? '<a href="audit_logs.html" style="color:#fde047;text-decoration:none;font-weight:700;background:rgba(253,224,71,.15);padding:4px 10px;border-radius:6px;margin-right:4px;"><i class="fa-solid fa-shield-halved me-1"></i> Audit Logs</a>' : '';
        badge.innerHTML = audit +
          '<div style="display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.08);padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,.15);">' +
            '<img src="' + user.picture + '" style="width:24px;height:24px;border-radius:50%;object-fit:cover;">' +
            '<span style="font-weight:700;color:#fff;">' + esc(user.name) + '</span>' +
            '<span style="background:' + roleBg + ';color:#fff;font-size:10px;font-weight:800;padding:2px 8px;border-radius:12px;text-transform:uppercase;">' + user.role + '</span>' +
          '</div>' +
          '<button onclick="window.AuthGuard.logout()" style="background:#dc2626;color:#fff;border:none;padding:5px 12px;border-radius:6px;font-weight:700;font-size:.8rem;cursor:pointer;"><i class="fa-solid fa-right-from-bracket me-1"></i> Logout</button>';
      } else {
        badge.innerHTML = `
          <button onclick="window.AuthGuard.showModal('🔑 เข้าสู่ระบบ / ลงทะเบียน')" style="background:#2563eb; color:#fff; border:none; padding:6px 14px; border-radius:8px; font-weight:700; font-size:0.82rem; cursor:pointer; box-shadow:0 2px 6px rgba(37,99,235,0.4);"><i class="fa-solid fa-key me-1"></i> 🔑 เข้าสู่ระบบ / ลงทะเบียน</button>
        `;
      }
    });
  }

  function esc(s) { return s ? String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') : ''; }

  /* ─── Init ─── */
  function initAuthSystem() {
    getUsersDatabase(); // Initialize local database
    var user = getStoredUser();

    // Role guard: audit_logs.html is Admin-only
    if (user && user.role !== 'Admin' && (location.pathname.indexOf('audit_logs') !== -1)) {
      alert('⚠️ Access Denied: Audit Logs สงวนสิทธิ์เฉพาะ Admin เท่านั้น');
      location.href = 'index.html';
      return;
    }

    renderProfileBadge();
    lockPageInteractions();
    setupActivityListeners();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuthSystem);
  } else {
    initAuthSystem();
  }

  /* ─── Public API ─── */
  window.AuthGuard = {
    getUser: getStoredUser,
    saveUser: saveStoredUser,
    logout: function () { doAutoLogout('ผู้ใช้งานกด Logout'); },
    showModal: showAuthModal,
    switchTab: switchTab,
    handleLoginSubmit: handleLoginSubmit,
    handleSignupSubmit: handleSignupSubmit,
    extendSession: function () {
      resetIdleTimer();
      var w = document.getElementById('socnIdleWarn');
      if (w) w.style.display = 'none';
    },
    logActivity: logActivity
  };
})();
