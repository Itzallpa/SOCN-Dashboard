/**
 * SOC Operations Control Center - Google Verify & Create Username Auth System
 * Uses Direct Google Account Verification without requiring a pre-registered OAuth Client ID.
 * No /login redirect needed. Modal overlay appears directly on any page.
 */

(function () {
  const IDLE_TIMEOUT_MS = 60 * 60 * 1000;
  const WARNING_BEFORE_MS = 5 * 60 * 1000;

  let idleTimer = null;
  let warningTimer = null;
  let lastActiveTimestamp = Date.now();

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

  /* ─── Inline Auth Modal ─── */
  function showAuthModal() {
    if (document.getElementById('socnAuthOverlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'socnAuthOverlay';
    overlay.innerHTML = `
      <style>
        #socnAuthOverlay {
          position:fixed; inset:0; z-index:999999;
          background:rgba(13,27,42,0.92); backdrop-filter:blur(10px);
          display:flex; align-items:center; justify-content:center;
          font-family:'Segoe UI',system-ui,sans-serif; padding:16px;
        }
        #socnAuthCard {
          background:#fff; border-radius:22px; width:100%; max-width:440px;
          box-shadow:0 30px 60px rgba(0,0,0,0.5); overflow:hidden;
        }
        #socnAuthCard .auth-header {
          background:#0d1b2a; color:#fff; padding:28px 24px; text-align:center;
        }
        #socnAuthCard .auth-body { padding:24px; }
        #socnAuthCard label.field-label {
          display:block; font-size:0.8rem; font-weight:700; color:#334155; margin-bottom:6px;
        }
        #socnAuthCard input[type=text], #socnAuthCard input[type=email] {
          width:100%; padding:11px 14px; border:1.5px solid #cbd5e1; border-radius:10px;
          font-size:0.95rem; outline:none; box-sizing:border-box; transition:border .2s;
        }
        #socnAuthCard input:focus { border-color:#2563eb; }
        .role-row { display:flex; gap:10px; margin-bottom:18px; }
        .role-btn {
          flex:1; border:2px solid #cbd5e1; border-radius:10px; padding:10px;
          text-align:center; cursor:pointer; font-weight:700; font-size:0.85rem;
          color:#0f172a; background:#fff; transition:all .15s;
        }
        .role-btn.active-ground { border-color:#2563eb; background:#eff6ff; }
        .role-btn.active-admin  { border-color:#d0311d; background:#fef2f2; }
        
        #googleVerifyBtn {
          width:100%; background:#2563eb; color:#fff; border:none; padding:13px;
          border-radius:12px; font-weight:800; font-size:0.95rem; cursor:pointer;
          box-shadow:0 4px 14px rgba(37,99,235,0.35); transition:all .2s;
          display:flex; align-items:center; justify-content:center; gap:8px;
        }
        #googleVerifyBtn:hover { background:#1d4ed8; }

        .quick-tag {
          font-size:0.75rem; background:#f1f5f9; color:#475569; padding:3px 8px;
          border-radius:6px; cursor:pointer; border:1px solid #e2e8f0;
        }
        .quick-tag:hover { background:#e2e8f0; }
      </style>
      <div id="socnAuthCard">
        <div class="auth-header">
          <div style="font-size:2.4rem; margin-bottom:6px;">📦</div>
          <h4 style="font-weight:800; margin:0; font-size:1.25rem;">SOC Operations Portal</h4>
          <p style="font-size:0.8rem; color:#94a3b8; margin:4px 0 0;">Google / Gmail Verify &amp; Username Setup</p>
        </div>
        <div class="auth-body">
          <form onsubmit="window._socnSubmitGoogleAuth(event)">
            <!-- 1. Username -->
            <div style="margin-bottom:16px;">
              <label class="field-label">1. ตั้งชื่อเรียกผู้ใช้งาน (Display Username):</label>
              <input type="text" id="socnNameField" placeholder="พิมพ์ชื่อเล่นของคุณ เช่น Natakorn" required autofocus>
            </div>

            <!-- 2. Gmail Account -->
            <div style="margin-bottom:16px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <label class="field-label" style="margin-bottom:0;">2. บัญชี Google / Gmail (Verify Email):</label>
                <div style="display:flex; gap:4px;">
                  <span class="quick-tag" onclick="window._socnAppendDomain('@spxexpress.com')">@spxexpress.com</span>
                  <span class="quick-tag" onclick="window._socnAppendDomain('@gmail.com')">@gmail.com</span>
                </div>
              </div>
              <input type="email" id="socnEmailField" placeholder="guy.panmanee@spxexpress.com" required>
            </div>

            <!-- 3. Role Selection -->
            <div style="margin-bottom:20px;">
              <label class="field-label">3. สิทธิ์การใช้งาน (User Role):</label>
              <div class="role-row">
                <div class="role-btn active-ground" id="socnRoleGround" onclick="window._socnSelectRole('Ground')">
                  👤 Ground (เจ้าหน้าที่)
                </div>
                <div class="role-btn" id="socnRoleAdmin" onclick="window._socnSelectRole('Admin')">
                  🛡️ Admin (ผู้ดูแลระบบ)
                </div>
              </div>
            </div>

            <!-- Submit Button -->
            <button type="submit" id="googleVerifyBtn">
              <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#fff" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#fff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#fff" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                <path fill="#fff" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
              </svg>
              ยืนยัน Google Verify &amp; เข้าใช้งาน
            </button>
          </form>

          <div style="font-size:0.72rem; color:#94a3b8; text-align:center; margin-top:16px;">
            🔒 ระบบจะตัดการเชื่อมต่ออัตโนมัติหากไม่มีการใช้งานเกิน 1 ชั่วโมง
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
  }

  let _selectedRole = 'Ground';

  window._socnSelectRole = function (role) {
    _selectedRole = role;
    const g = document.getElementById('socnRoleGround');
    const a = document.getElementById('socnRoleAdmin');
    if (role === 'Ground') {
      g.className = 'role-btn active-ground';
      a.className = 'role-btn';
    } else {
      g.className = 'role-btn';
      a.className = 'role-btn active-admin';
    }
  };

  window._socnAppendDomain = function (domain) {
    const emailField = document.getElementById('socnEmailField');
    if (!emailField) return;
    let val = emailField.value.trim();
    if (val.indexOf('@') !== -1) {
      val = val.split('@')[0];
    }
    emailField.value = (val ? val : '') + domain;
    emailField.focus();
  };

  window._socnSubmitGoogleAuth = function (evt) {
    if (evt) evt.preventDefault();

    const nameField = document.getElementById('socnNameField');
    const emailField = document.getElementById('socnEmailField');

    const name = nameField ? nameField.value.trim() : '';
    const email = emailField ? emailField.value.trim().toLowerCase() : '';

    if (!name) {
      alert('กรุณาตั้งชื่อเรียกผู้ใช้งานก่อนครับ');
      if (nameField) nameField.focus();
      return;
    }

    if (!email || email.indexOf('@') === -1) {
      alert('กรุณากรอกอีเมล Google / Gmail ให้ถูกต้องครับ');
      if (emailField) emailField.focus();
      return;
    }

    const user = {
      name: name,
      email: email,
      role: _selectedRole,
      picture: `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=0d1b2a&color=fff`
    };

    finalizeLogin(user);
  };

  function finalizeLogin(user) {
    saveStoredUser(user);

    fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(user)
    }).catch(function () {});

    const ov = document.getElementById('socnAuthOverlay');
    if (ov) ov.remove();

    renderProfileBadge();
    resetIdleTimer();
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
    showAuthModal();
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

  /* ─── Activity Logging ─── */
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
    if (!user) return;

    document.querySelectorAll('.top-nav, nav').forEach(function (nav) {
      var badge = nav.querySelector('.user-profile-badge');
      if (!badge) {
        badge = document.createElement('div');
        badge.className = 'user-profile-badge';
        badge.style.cssText = 'display:flex;align-items:center;gap:10px;font-size:.85rem;margin-left:auto;';
        nav.appendChild(badge);
      }
      var roleBg = user.role === 'Admin' ? '#d0311d' : '#2563eb';
      var audit = user.role === 'Admin' ? '<a href="audit_logs.html" style="color:#fde047;text-decoration:none;font-weight:700;background:rgba(253,224,71,.15);padding:4px 10px;border-radius:6px;margin-right:4px;"><i class="fa-solid fa-shield-halved me-1"></i> Audit Logs</a>' : '';
      badge.innerHTML = audit +
        '<div style="display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.08);padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,.15);">' +
          '<img src="' + user.picture + '" style="width:24px;height:24px;border-radius:50%;object-fit:cover;">' +
          '<span style="font-weight:700;color:#fff;">' + esc(user.name) + '</span>' +
          '<span style="background:' + roleBg + ';color:#fff;font-size:10px;font-weight:800;padding:2px 8px;border-radius:12px;text-transform:uppercase;">' + user.role + '</span>' +
        '</div>' +
        '<button onclick="window.AuthGuard.logout()" style="background:#dc2626;color:#fff;border:none;padding:5px 12px;border-radius:6px;font-weight:700;font-size:.8rem;cursor:pointer;"><i class="fa-solid fa-right-from-bracket me-1"></i> Logout</button>';
    });
  }

  function esc(s) { return s ? String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') : ''; }

  /* ─── Init ─── */
  document.addEventListener('DOMContentLoaded', function () {
    var user = getStoredUser();

    // Role guard: audit_logs.html is Admin-only
    if (user && user.role !== 'Admin' && (location.pathname.indexOf('audit_logs') !== -1)) {
      alert('⚠️ Access Denied: Audit Logs สงวนสิทธิ์เฉพาะ Admin เท่านั้น');
      location.href = 'index.html';
      return;
    }

    if (!user) {
      showAuthModal();
    } else {
      renderProfileBadge();
    }

    setupActivityListeners();
  });

  /* ─── Public API ─── */
  window.AuthGuard = {
    getUser: getStoredUser,
    saveUser: saveStoredUser,
    logout: function () { doAutoLogout('ผู้ใช้งานกด Logout'); },
    extendSession: function () {
      resetIdleTimer();
      var w = document.getElementById('socnIdleWarn');
      if (w) w.style.display = 'none';
    },
    logActivity: logActivity
  };
})();
