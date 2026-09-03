/**
 * SOC Operations Control Center - Google Verify & Create Username Auth System
 * Uses Official Google Identity Services (GIS) Sign-In Button.
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

  /* Load Google GIS Script */
  function loadGoogleSDK(callback) {
    if (window.google && window.google.accounts) {
      if (callback) callback();
      return;
    }
    const existing = document.getElementById('gsi-client-script');
    if (existing) {
      existing.addEventListener('load', callback);
      return;
    }
    const s = document.createElement('script');
    s.id = 'gsi-client-script';
    s.src = 'https://accounts.google.com/gsi/client';
    s.async = true;
    s.defer = true;
    s.onload = callback;
    document.head.appendChild(s);
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
          background:#fff; border-radius:20px; width:100%; max-width:440px;
          box-shadow:0 30px 60px rgba(0,0,0,0.5); overflow:hidden;
        }
        #socnAuthCard .auth-header {
          background:#0d1b2a; color:#fff; padding:28px 24px; text-align:center;
        }
        #socnAuthCard .auth-body { padding:24px; }
        #socnAuthCard label.field-label {
          display:block; font-size:0.8rem; font-weight:700; color:#475569; margin-bottom:6px;
        }
        #socnAuthCard input[type=text] {
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
        
        .divider-box {
          display:flex; align-items:center; text-align:center; margin:16px 0; color:#94a3b8; font-size:0.75rem;
        }
        .divider-box::before, .divider-box::after {
          content:''; flex:1; border-bottom:1px solid #e2e8f0;
        }
        .divider-box span { padding:0 10px; }
        
        #googleBtnWrapper {
          display:flex; justify-content:center; margin-bottom:10px; min-height:44px;
        }
        
        #directVerifyBtn {
          width:100%; background:#2563eb; color:#fff; border:none; padding:12px;
          border-radius:10px; font-weight:800; font-size:0.92rem; cursor:pointer;
          box-shadow:0 4px 14px rgba(37,99,235,0.3); transition:all .2s;
        }
        #directVerifyBtn:hover { background:#1d4ed8; }
      </style>
      <div id="socnAuthCard">
        <div class="auth-header">
          <div style="font-size:2.4rem; margin-bottom:6px;">📦</div>
          <h4 style="font-weight:800; margin:0; font-size:1.25rem;">SOC Operations Portal</h4>
          <p style="font-size:0.8rem; color:#94a3b8; margin:4px 0 0;">Sign in with Google / Gmail Verification</p>
        </div>
        <div class="auth-body">
          <!-- STEP 1: Create Username -->
          <div style="margin-bottom:16px;">
            <label class="field-label">1. ตั้งชื่อเรียกผู้ใช้งาน (Display Username):</label>
            <input type="text" id="socnNameField" placeholder="พิมพ์ชื่อเล่น/ชื่อของคุณ เช่น Natakorn, Operator 01" value="${getStoredUser() ? getStoredUser().name : ''}">
          </div>

          <!-- STEP 2: Select Role -->
          <div style="margin-bottom:16px;">
            <label class="field-label">2. สิทธิ์การใช้งาน (Role):</label>
            <div class="role-row">
              <div class="role-btn active-ground" id="socnRoleGround" onclick="window._socnSelectRole('Ground')">👤 Ground (เจ้าหน้าที่)</div>
              <div class="role-btn" id="socnRoleAdmin" onclick="window._socnSelectRole('Admin')">🛡️ Admin (ผู้ดูแลระบบ)</div>
            </div>
          </div>

          <!-- STEP 3: Google Login Button -->
          <div style="margin-bottom:10px;">
            <label class="field-label" style="text-align:center; margin-bottom:10px;">3. ยืนยันตัวตนด้วยบัญชี Google / Gmail:</label>
            <div id="googleBtnWrapper">
              <div style="color:#94a3b8; font-size:0.8rem; padding:10px;">กำลังโหลด Google Sign-In...</div>
            </div>
          </div>

          <div class="divider-box"><span>หรือเข้าสู่ระบบโดยตรง</span></div>

          <button id="directVerifyBtn" onclick="window._socnDirectLogin()">
            <i class="fa-solid fa-arrow-right-to-bracket me-1"></i> เข้าสู่ระบบด้วยชื่อที่ตั้งไว้
          </button>

          <div style="font-size:0.72rem; color:#94a3b8; text-align:center; margin-top:16px;">
            🔒 ระบบจะตัดการเชื่อมต่ออัตโนมัติหากไม่มีการใช้งานเกิน 1 ชั่วโมง
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    loadGoogleSDK(renderGoogleButton);
  }

  function renderGoogleButton() {
    const container = document.getElementById('googleBtnWrapper');
    if (!container || !window.google || !window.google.accounts) return;

    container.innerHTML = '';

    window.google.accounts.id.initialize({
      client_id: "1084209184512-mockclientid.apps.googleusercontent.com",
      callback: handleGoogleCredentialResponse,
      auto_select: false
    });

    window.google.accounts.id.renderButton(
      container,
      {
        theme: "filled_blue",
        size: "large",
        text: "signin_with",
        shape: "rectangular",
        width: 340,
        logo_alignment: "left"
      }
    );
  }

  function handleGoogleCredentialResponse(response) {
    if (!response || !response.credential) return;

    try {
      const base64Url = response.credential.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join(''));
      const payload = JSON.parse(jsonPayload);

      const customName = (document.getElementById('socnNameField') || {}).value || '';
      const finalName = customName.trim() || payload.name || payload.email.split('@')[0];

      finalizeLogin({
        name: finalName,
        email: payload.email,
        role: _selectedRole,
        picture: payload.picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(finalName)}&background=0d1b2a&color=fff`
      });
    } catch (e) {
      console.error("JWT Decode error:", e);
      window._socnDirectLogin();
    }
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

  window._socnDirectLogin = function () {
    const nameField = document.getElementById('socnNameField');
    const name = nameField ? nameField.value.trim() : '';
    if (!name) {
      alert('กรุณาพิมพ์ชื่อผู้ใช้งานของคุณก่อนครับ');
      if (nameField) nameField.focus();
      return;
    }

    const email = name.toLowerCase().replace(/\s+/g, '.') + '@spxexpress.com';
    finalizeLogin({
      name: name,
      email: email,
      role: _selectedRole,
      picture: `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=0d1b2a&color=fff`
    });
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
