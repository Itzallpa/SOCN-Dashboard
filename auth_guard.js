/**
 * SOC Operations Control Center - Universal Auth Guard & 1-Hour Idle Timeout System
 * Author: Antigravity AI
 */

(function () {
  const IDLE_TIMEOUT_MS = 60 * 60 * 1000; // 1 Hour (3,600,000 ms)
  const WARNING_BEFORE_MS = 5 * 60 * 1000; // 5 Minutes warning before auto logout

  let idleTimer = null;
  let warningTimer = null;
  let lastActiveTimestamp = Date.now();

  const isLoginPage = window.location.pathname.endsWith('login.html') || window.location.pathname.endsWith('/login');

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

    if (!user && !isLoginPage) {
      console.warn("Unauthenticated access detected. Redirecting to login.html...");
      window.location.href = "login.html";
      return;
    }

    // Role Guard for audit_logs.html (Admin only)
    if (user && user.role !== 'Admin' && (window.location.pathname.endsWith('audit_logs.html') || window.location.pathname.endsWith('/audit-logs'))) {
      alert("⚠️ Access Denied: Audit Logs are reserved for Admin users only.");
      window.location.href = "index.html";
      return;
    }
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
    if (!user || isLoginPage) return;

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

    alert(`🔒 ระบบได้ Logout ออกอัตโนมัติเนื่องจาก:\n${reason}`);
    window.location.href = "login.html";
  }

  function setupActivityListeners() {
    if (isLoginPage) return;

    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
    events.forEach(evt => {
      window.addEventListener(evt, () => {
        const now = Date.now();
        // Throttle idle timer reset to once every 10 seconds
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
    if (!user || isLoginPage) return;

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
          <button onclick="window.AuthGuard.logout()" style="background:#dc2626; color:#fff; border:none; padding:5px 12px; border-radius:6px; font-weight:700; font-size:0.8rem; cursor:pointer;"><i class="fa-solid fa-right-from-bracket me-1"></i> Logout</button>
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
      performAutoLogout("ผู้ใช้งานกด Log Out");
    },
    extendSession: function () {
      resetIdleTimer();
      const warningEl = document.getElementById('sessionWarningToast');
      if (warningEl) warningEl.style.display = 'none';
    },
    logActivity: logClientActivity
  };
})();
