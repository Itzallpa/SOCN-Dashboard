/**
 * SOC Operations Control Center - Universal Inline Auth Guard & 1-Hour Idle Timeout System
 * Author: Antigravity AI
 */

(function () {
  const IDLE_TIMEOUT_MS = 60 * 60 * 1000; // 1 Hour (3,600,000 ms)
  const WARNING_BEFORE_MS = 5 * 60 * 1000; // 5 Minutes warning before auto logout

  let idleTimer = null;
  let warningTimer = null;
  let lastActiveTimestamp = Date.now();

  function getStoredUser() {
    try {
      const u = sessionStorage.getItem('socn_user') || localStorage.getItem('socn_user');
      return u ? JSON.parse(u) : null;
    } catch (e) {
      return null;
    }
  }

  function saveStoredUser(user, remember = true) {
    if (remember) {
      localStorage.setItem('socn_user', JSON.stringify(user));
    } else {
      sessionStorage.setItem('socn_user', JSON.stringify(user));
    }
    localStorage.setItem('socn_last_active', String(Date.now()));
  }

  function clearStoredUser() {
    sessionStorage.removeItem('socn_user');
    localStorage.removeItem('socn_user');
    localStorage.removeItem('socn_last_active');
  }

  function checkAuthGuard() {
    const user = getStoredUser();

    if (!user) {
      // Show Inline Login Modal directly on page (No separate /login redirect required!)
      showInlineLoginModal();
    } else {
      // Hide modal if open
      const modalEl = document.getElementById('inlineAuthModalOverlay');
      if (modalEl) modalEl.style.display = 'none';

      // Role Guard for audit_logs.html (Admin only)
      if (user.role !== 'Admin' && (window.location.pathname.endsWith('audit_logs.html') || window.location.pathname.endsWith('/audit-logs'))) {
        alert("⚠️ Access Denied: Audit Logs are reserved for Admin users only.");
        window.location.href = "index.html";
        return;
      }
    }
  }

  function showInlineLoginModal() {
    let overlay = document.getElementById('inlineAuthModalOverlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'inlineAuthModalOverlay';
      overlay.style.cssText = 'position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(13,27,42,0.85); backdrop-filter:blur(6px); z-index:99999; display:flex; align-items:center; justify-content:center; padding:20px; font-family:"Segoe UI", sans-serif;';
      overlay.innerHTML = `
        <div style="background:#ffffff; border-radius:18px; box-shadow:0 25px 50px rgba(0,0,0,0.5); width:100%; max-width:440px; overflow:hidden; animation:fadeIn 0.3s ease;">
          <div style="background:#0d1b2a; color:#ffffff; padding:24px 24px; text-align:center;">
            <div style="font-size:2.4rem; margin-bottom:6px;">📦</div>
            <h4 style="font-weight:800; margin:0; font-size:1.3rem;">SOC Operations Control Center</h4>
            <p style="font-size:0.8rem; color:#94a3b8; margin-top:4px; margin-bottom:0;">กรอกชื่อหรือบัญชี Google เพื่อเริ่มใช้งานแดชบอร์ด</p>
          </div>
          <div style="padding:24px 24px;">
            <form onsubmit="window.AuthGuard.submitInlineLogin(event)">
              <div style="margin-bottom:16px;">
                <label style="font-size:0.8rem; font-weight:700; color:#475569; display:block; margin-bottom:6px;">1. ระบุชื่อผู้ใช้งาน (Enter Display Name / Username):</label>
                <input type="text" id="inlineUsernameInput" placeholder="พิมพ์ชื่อผู้ใช้ เช่น Natakorn / SPX Operator" required style="width:100%; padding:10px 14px; border:1.5px solid #cbd5e1; border-radius:8px; font-size:0.92rem; outline:none;" value="${getSuggestedName()}">
              </div>

              <div style="margin-bottom:20px;">
                <label style="font-size:0.8rem; font-weight:700; color:#475569; display:block; margin-bottom:6px;">2. เลือกสิทธิ์การใช้งาน (Select Role):</label>
                <div style="display:flex; gap:10px;">
                  <label id="roleInlineGroundLbl" style="flex:1; border:2px solid #2563eb; background:#eff6ff; border-radius:10px; padding:10px; text-align:center; cursor:pointer; font-weight:700; font-size:0.85rem; color:#0f172a;">
                    <input type="radio" name="inlineRoleRadio" value="Ground" checked onclick="window.AuthGuard.selectInlineRole('Ground')" style="display:none;">
                    👤 Ground (เจ้าหน้าที่)
                  </label>
                  <label id="roleInlineAdminLbl" style="flex:1; border:2px solid #cbd5e1; background:#ffffff; border-radius:10px; padding:10px; text-align:center; cursor:pointer; font-weight:700; font-size:0.85rem; color:#0f172a;">
                    <input type="radio" name="inlineRoleRadio" value="Admin" onclick="window.AuthGuard.selectInlineRole('Admin')" style="display:none;">
                    🛡️ Admin (ผู้ดูแลระบบ)
                  </label>
                </div>
              </div>

              <button type="submit" style="width:100%; background:#2563eb; color:#ffffff; border:none; padding:12px; border-radius:10px; font-weight:800; font-size:0.95rem; cursor:pointer; transition:all 0.2s;">
                <i class="fa-solid fa-right-to-bracket me-2"></i> เข้าใช้งานแดชบอร์ด (Enter Portal)
              </button>
            </form>
            <div style="font-size:0.75rem; color:#94a3b8; text-align:center; margin-top:16px;">
              🔒 ปลอดภัยด้วย Google Verify & 1-Hour Idle Session Guard
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);
    } else {
      overlay.style.display = 'flex';
    }
  }

  function getSuggestedName() {
    return 'SPX Operator';
  }

  let currentInlineRole = 'Ground';
  function selectInlineRole(role) {
    currentInlineRole = role;
    const groundLbl = document.getElementById('roleInlineGroundLbl');
    const adminLbl = document.getElementById('roleInlineAdminLbl');
    if (role === 'Ground') {
      if (groundLbl) { groundLbl.style.borderColor = '#2563eb'; groundLbl.style.background = '#eff6ff'; }
      if (adminLbl) { adminLbl.style.borderColor = '#cbd5e1'; adminLbl.style.background = '#ffffff'; }
    } else {
      if (groundLbl) { groundLbl.style.borderColor = '#cbd5e1'; groundLbl.style.background = '#ffffff'; }
      if (adminLbl) { adminLbl.style.borderColor = '#d0311d'; adminLbl.style.background = '#fef2f2'; }
    }
  }

  function submitInlineLogin(evt) {
    if (evt) evt.preventDefault();
    const nameInput = document.getElementById('inlineUsernameInput');
    const username = nameInput ? nameInput.value.trim() : 'SPX Operator';

    if (!username) return;

    const email = username.toLowerCase().replace(/\s+/g, '.') + '@spxexpress.com';
    const userObj = {
      name: username,
      email: email,
      role: currentInlineRole,
      picture: `https://ui-avatars.com/api/?name=${encodeURIComponent(username)}&background=0d1b2a&color=fff`
    };

    saveStoredUser(userObj, true);

    // Call server to store session and activity log
    fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userObj)
    }).catch(() => {});

    const overlay = document.getElementById('inlineAuthModalOverlay');
    if (overlay) overlay.style.display = 'none';

    renderUserProfileBadge();
    resetIdleTimer();
  }

  function resetIdleTimer() {
    lastActiveTimestamp = Date.now();
    localStorage.setItem('socn_last_active', String(lastActiveTimestamp));

    if (idleTimer) clearTimeout(idleTimer);
    if (warningTimer) clearTimeout(warningTimer);

    // Set 55-minute warning timer
    warningTimer = setTimeout(() => {
      showSessionWarningToast();
    }, IDLE_TIMEOUT_MS - WARNING_BEFORE_MS);

    // Set 60-minute logout timer
    idleTimer = setTimeout(() => {
      performAutoLogout("ไม่มีการใช้งานเกิน 1 ชั่วโมง (Idle Timeout for 1 hour)");
    }, IDLE_TIMEOUT_MS);
  }

  function showSessionWarningToast() {
    const user = getStoredUser();
    if (!user) return;

    let warningEl = document.getElementById('sessionWarningToast');
    if (!warningEl) {
      warningEl = document.createElement('div');
      warningEl.id = 'sessionWarningToast';
      warningEl.style.cssText = 'position:fixed; bottom:20px; right:20px; z-index:9999; background:#b7791f; color:#fff; padding:14px 20px; border-radius:10px; box-shadow:0 10px 25px rgba(0,0,0,0.3); font-family:sans-serif; font-size:13px; display:flex; align-items:center; gap:12px;';
      warningEl.innerHTML = `
        <div>
          <strong>⏰ แจ้งเตือนเซสชันกำลังจะหมดอายุ:</strong>
          <div>ไม่มีการใช้งานนาน 55 นาที ระบบจะ Logout ออกอัตโนมัติในอีก 5 นาที</div>
        </div>
        <button onclick="window.AuthGuard.extendSession()" style="background:#fff; color:#b7791f; border:none; padding:6px 12px; border-radius:6px; font-weight:bold; cursor:pointer;">ต่อเวลาใช้งาน</button>
      `;
      document.body.appendChild(warningEl);
    } else {
      warningEl.style.display = 'flex';
    }
  }

  function performAutoLogout(reason) {
    const user = getStoredUser();
    if (user) {
      logClientActivity('IDLE_AUTO_LOGOUT', `Automatic logout due to: ${reason}`);
    }

    clearStoredUser();

    fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});

    showInlineLoginModal();
  }

  function setupActivityListeners() {
    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
    events.forEach(evt => {
      window.addEventListener(evt, () => {
        const now = Date.now();
        if (now - lastActiveTimestamp > 10000) {
          resetIdleTimer();
          const warningEl = document.getElementById('sessionWarningToast');
          if (warningEl) warningEl.style.display = 'none';
        }
      }, { passive: true });
    });

    resetIdleTimer();
  }

  function logClientActivity(action, details) {
    const user = getStoredUser();
    const payload = {
      action: action,
      details: details,
      user_email: user ? user.email : 'guest',
      user_name: user ? user.name : 'Guest'
    };

    fetch('/api/log-client-activity', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).catch(() => {});
  }

  function renderUserProfileBadge() {
    const user = getStoredUser();
    if (!user) return;

    const navContainers = document.querySelectorAll('.top-nav, nav');
    if (!navContainers.length) return;

    navContainers.forEach(nav => {
      let badgeEl = nav.querySelector('.user-profile-badge');
      if (!badgeEl) {
        badgeEl = document.createElement('div');
        badgeEl.className = 'user-profile-badge';
        badgeEl.style.cssText = 'display:flex; align-items:center; gap:10px; font-size:0.85rem; margin-left:auto;';

        const roleBadgeBg = user.role === 'Admin' ? '#d0311d' : '#2563eb';
        const auditLink = user.role === 'Admin' ? `<a href="audit_logs.html" style="color:#fde047; text-decoration:none; font-weight:700; background:rgba(253,224,71,0.15); padding:4px 10px; border-radius:6px; margin-right:4px;"><i class="fa-solid fa-shield-halved me-1"></i> Audit Logs</a>` : '';

        badgeEl.innerHTML = `
          ${auditLink}
          <div style="display:flex; align-items:center; gap:8px; background:rgba(255,255,255,0.08); padding:4px 12px; border-radius:20px; border:1px solid rgba(255,255,255,0.15);">
            <img src="${user.picture || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(user.name)}" style="width:24px; height:24px; border-radius:50%; object-fit:cover;">
            <span style="font-weight:700; color:#ffffff;">${escapeHtml(user.name)}</span>
            <span style="background:${roleBadgeBg}; color:#fff; font-size:10px; font-weight:800; padding:2px 8px; border-radius:12px; text-transform:uppercase;">${user.role}</span>
          </div>
          <button onclick="window.AuthGuard.openChangeNameModal()" style="background:rgba(255,255,255,0.15); color:#fff; border:none; padding:5px 12px; border-radius:6px; font-weight:700; font-size:0.8rem; cursor:pointer;" title="เปลี่ยนชื่อผู้ใช้"><i class="fa-solid fa-user-pen me-1"></i> เปลี่ยนชื่อ</button>
        `;

        nav.appendChild(badgeEl);
      }
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // Initialize Auth Guard
  document.addEventListener('DOMContentLoaded', () => {
    checkAuthGuard();
    setupActivityListeners();
    renderUserProfileBadge();
  });

  // Global AuthGuard Interface
  window.AuthGuard = {
    getUser: getStoredUser,
    saveUser: saveStoredUser,
    logout: function () {
      performAutoLogout("ผู้ใช้งานกดสลับผู้ใช้");
    },
    openChangeNameModal: function () {
      showInlineLoginModal();
    },
    selectInlineRole: selectInlineRole,
    submitInlineLogin: submitInlineLogin,
    extendSession: function () {
      resetIdleTimer();
      const warningEl = document.getElementById('sessionWarningToast');
      if (warningEl) warningEl.style.display = 'none';
    },
    logActivity: logClientActivity
  };
})();
