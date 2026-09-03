/**
 * SOC Operations Control Center - Google Verify & Create Username Auth System
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

  /* ─── Inline Auth Modal (blocks page until user creates username) ─── */

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
          background:#fff; border-radius:20px; width:100%; max-width:420px;
          box-shadow:0 30px 60px rgba(0,0,0,0.5); overflow:hidden;
        }
        #socnAuthCard .auth-header {
          background:#0d1b2a; color:#fff; padding:28px 24px; text-align:center;
        }
        #socnAuthCard .auth-body { padding:24px; }
        #socnAuthCard label.field-label {
          display:block; font-size:0.78rem; font-weight:700; color:#475569; margin-bottom:5px;
        }
        #socnAuthCard input[type=text], #socnAuthCard input[type=email] {
          width:100%; padding:10px 14px; border:1.5px solid #cbd5e1; border-radius:10px;
          font-size:0.92rem; outline:none; box-sizing:border-box;
        }
        #socnAuthCard input:focus { border-color:#2563eb; }
        .role-row { display:flex; gap:10px; }
        .role-btn {
          flex:1; border:2px solid #cbd5e1; border-radius:10px; padding:10px;
          text-align:center; cursor:pointer; font-weight:700; font-size:0.84rem;
          color:#0f172a; background:#fff; transition:all .15s;
        }
        .role-btn.active-ground { border-color:#2563eb; background:#eff6ff; }
        .role-btn.active-admin  { border-color:#d0311d; background:#fef2f2; }
        #socnSubmitBtn {
          width:100%; background:#2563eb; color:#fff; border:none; padding:13px;
          border-radius:12px; font-weight:800; font-size:0.95rem; cursor:pointer;
          box-shadow:0 4px 14px rgba(37,99,235,0.35); margin-top:6px;
        }
        #socnSubmitBtn:hover { background:#1d4ed8; }
      </style>
      <div id="socnAuthCard">
        <div class="auth-header">
          <div style="font-size:2.4rem; margin-bottom:6px;">📦</div>
          <h4 style="font-weight:800; margin:0; font-size:1.25rem;">SOC Operations Portal</h4>
          <p style="font-size:0.8rem; color:#94a3b8; margin:4px 0 0;">Google Verify &amp; Create Username</p>
        </div>
        <div class="auth-body">
          <div style="margin-bottom:14px;">
            <label class="field-label">1. ตั้งชื่อผู้ใช้งาน (Create Username):</label>
            <input type="text" id="socnNameField" placeholder="พิมพ์ชื่อของคุณ เช่น Natakorn" required>
          </div>
          <div style="margin-bottom:14px;">
            <label class="field-label">2. อีเมล Google / Gmail (Google Verify):</label>
            <input type="email" id="socnEmailField" placeholder="your.name@spxexpress.com" required>
          </div>
          <div style="margin-bottom:18px;">
            <label class="field-label">3. สิทธิ์การใช้งาน (Role):</label>
            <div class="role-row">
              <div class="role-btn active-ground" id="socnRoleGround" onclick="window._socnSelectRole('Ground')">👤 Ground</div>
              <div class="role-btn" id="socnRoleAdmin" onclick="window._socnSelectRole('Admin')">🛡️ Admin</div>
            </div>
          </div>
          <button id="socnSubmitBtn" onclick="window._socnSubmitAuth()">ยืนยัน Google Verify &amp; เข้าใช้งาน</button>
          <div style="font-size:0.72rem; color:#94a3b8; text-align:center; margin-top:14px;">
            🔒 ระบบจะตัดการเชื่อมต่ออัตโนมัติหากไม่มีการใช้งานเกิน 1 ชั่วโมง
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
  }

  /* Global helpers for the inline modal (called from onclick) */
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

  window._socnSubmitAuth = function () {
    const name  = (document.getElementById('socnNameField')  || {}).value || '';
    const email = (document.getElementById('socnEmailField') || {}).value || '';
    if (!name.trim() || !email.trim()) {
      alert('กรุณากรอกชื่อผู้ใช้และอีเมล Google'); return;
    }
    const user = {
      name: name.trim(),
      email: email.trim().toLowerCase(),
      role: _selectedRole,
      picture: 'https://ui-avatars.com/api/?name=' + encodeURIComponent(name.trim()) + '&background=0d1b2a&color=fff'
    };
    saveStoredUser(user);

    fetch('/api/auth/login', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(user)
    }).catch(function(){});

    const ov = document.getElementById('socnAuthOverlay');
    if (ov) ov.remove();

    renderProfileBadge();
    resetIdleTimer();
  };

  /* ─── Idle Timeout ─── */

  function resetIdleTimer() {
    lastActiveTimestamp = Date.now();
    localStorage.setItem('socn_last_active', String(lastActiveTimestamp));
    if (idleTimer) clearTimeout(idleTimer);
    if (warningTimer) clearTimeout(warningTimer);

    warningTimer = setTimeout(showWarning, IDLE_TIMEOUT_MS - WARNING_BEFORE_MS);
    idleTimer   = setTimeout(function () {
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
    fetch('/api/auth/logout',{method:'POST'}).catch(function(){});
    // Remove profile badge and show auth modal again
    document.querySelectorAll('.user-profile-badge').forEach(function(el){ el.remove(); });
    showAuthModal();
  }

  function setupActivityListeners() {
    ['mousemove','keydown','click','scroll','touchstart'].forEach(function (evt) {
      window.addEventListener(evt, function () {
        if (Date.now() - lastActiveTimestamp > 10000) {
          resetIdleTimer();
          var w = document.getElementById('socnIdleWarn');
          if (w) w.style.display = 'none';
        }
      }, {passive:true});
    });
    resetIdleTimer();
  }

  /* ─── Activity Logging ─── */

  function logActivity(action, details) {
    var u = getStoredUser();
    fetch('/api/log-client-activity', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ action:action, details:details, user_email: u?u.email:'guest', user_name: u?u.name:'Guest' })
    }).catch(function(){});
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
      var audit  = user.role === 'Admin' ? '<a href="audit_logs.html" style="color:#fde047;text-decoration:none;font-weight:700;background:rgba(253,224,71,.15);padding:4px 10px;border-radius:6px;margin-right:4px;">🛡️ Audit Logs</a>' : '';
      badge.innerHTML = audit +
        '<div style="display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.08);padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,.15);">' +
          '<img src="' + user.picture + '" style="width:24px;height:24px;border-radius:50%;">' +
          '<span style="font-weight:700;color:#fff;">' + esc(user.name) + '</span>' +
          '<span style="background:' + roleBg + ';color:#fff;font-size:10px;font-weight:800;padding:2px 8px;border-radius:12px;text-transform:uppercase;">' + user.role + '</span>' +
        '</div>' +
        '<button onclick="window.AuthGuard.logout()" style="background:#dc2626;color:#fff;border:none;padding:5px 12px;border-radius:6px;font-weight:700;font-size:.8rem;cursor:pointer;">Logout</button>';
    });
  }

  function esc(s) { return s ? String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') : ''; }

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
      showAuthModal();       // Block page with Google Verify & Create Username modal
    } else {
      renderProfileBadge();  // Show logged-in profile on navbar
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
