/**
 * SOC Operations Control Center - Local Database & Admin Approval Auth System
 * - Everyone can view index.html freely
 * - Sign-up requests require Admin Approval & Role Assignment before login
 * - Users database stored directly in browser localStorage
 * Author: Antigravity AI
 */

(function () {
  const IDLE_TIMEOUT_MS = 60 * 60 * 1000; // 1 Hour (3,600,000 ms)
  const WARNING_BEFORE_MS = 5 * 60 * 1000;

  let idleTimer = null;
  let warningTimer = null;
  let lastActiveTimestamp = Date.now();

  /* ─── Client-side Security Suite (Passive) ─── */
  function initSecurityProtections() {
    // Keep passive console protection if needed
  }

  // Execute security protections immediately
  initSecurityProtections();

  // Local database initialization
  function getUsersDatabase() {
    try {
      const db = localStorage.getItem('socn_user_db');
      if (db) return JSON.parse(db);
    } catch (e) {}
    return [];
  }

  function saveUsersDatabase(users) {
    if (!Array.isArray(users)) return;
    const sanitized = users.map(u => {
      const copy = Object.assign({}, u);
      delete copy.pass;
      delete copy.password;
      return copy;
    });
    localStorage.setItem('socn_user_db', JSON.stringify(sanitized));
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
  function showAuthModal(customTitle, isMandatory = false) {
    const isAdminPage = location.pathname.includes('admin.html') || location.pathname.includes('audit_logs.html');
    const mandatory = isMandatory || isAdminPage;

    let overlay = document.getElementById('socnAuthOverlay');
    if (overlay) {
      overlay.style.display = 'flex';
      return;
    }

    overlay = document.createElement('div');
    overlay.id = 'socnAuthOverlay';
    overlay.onclick = function(e) {
      if (e.target === overlay) {
        window.AuthGuard.closeModal();
      }
    };
    overlay.innerHTML = `
      <style>
        #socnAuthOverlay {
          position:fixed; inset:0; z-index:99900;
          background:rgba(13,27,42,0.88); backdrop-filter:blur(10px);
          display:flex; align-items:center; justify-content:center;
          font-family:'Segoe UI',system-ui,sans-serif; padding:16px;
        }
        .swal2-container {
          z-index: 99999999 !important;
        }
        #socnAuthCard {
          background:#fff; border-radius:22px; width:100%; max-width:450px;
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
          <button class="close-modal-btn" onclick="window.AuthGuard.closeModal()" title="${mandatory ? 'กลับหน้าหลัก Portal Hub' : 'ปิดหน้าต่าง'}">✕</button>
          <div style="font-size:2.2rem; margin-bottom:4px;">🔒</div>
          <h4 style="font-weight:800; margin:0; font-size:1.2rem;">${customTitle || 'SOC Operations Portal'}</h4>
          <p style="font-size:0.78rem; color:#94a3b8; margin:4px 0 0;">เข้าสู่ระบบหรือสร้างบัญชีใหม่เพื่อรอ Admin อนุมัติ</p>
        </div>

        <div class="auth-body">
          <div class="auth-nav-tabs">
            <div class="auth-nav-tab active" id="tabLoginBtn" onclick="window.AuthGuard.switchTab('login')">🔑 เข้าสู่ระบบ (Login)</div>
            <div class="auth-nav-tab" id="tabSignupBtn" onclick="window.AuthGuard.switchTab('signup')">📝 ลงทะเบียนใหม่ (Sign Up)</div>
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
              <label>อีเมล (Google / Gmail):</label>
              <input type="email" id="signupEmailField" placeholder="your.name@spxexpress.com" required>
            </div>
            <div class="field-group">
              <label>กำหนดรหัสผ่าน (Password / PIN):</label>
              <input type="password" id="signupPassField" placeholder="กำหนดรหัสผ่านเพื่อใช้เข้าระบบ" required>
            </div>
            <div style="background:#fef3c7; border:1px solid #f59e0b; border-radius:10px; padding:10px 12px; font-size:0.78rem; color:#92400e; margin-bottom:14px;">
              <i class="fa-solid fa-clock-rotate-left me-1"></i> <b>ขั้นตอนการพิจารณา:</b> หลังจากลงทะเบียน Admin จะเป็นผู้ตรวจสอบ เลือกสิทธิ์ (Role: Ground/Admin) และกดอนุมัติสิทธิ์ให้คุณเข้าใช้งานครับ
            </div>
            <button type="submit" class="auth-submit-btn" style="background:#059669;">ส่งคำขอลงทะเบียน (Submit Sign-Up)</button>
          </form>

          ${mandatory ? `
            <div class="text-center mt-3 pt-2 border-top">
              <a href="index.html" class="text-secondary text-decoration-none fw-bold" style="font-size:0.8rem;">
                <i class="fa-solid fa-arrow-left me-1"></i> กลับสู่หน้าหลัก Portal Hub (index.html)
              </a>
            </div>
          ` : ''}

          <div style="font-size:0.72rem; color:#94a3b8; text-align:center; margin-top:16px;">
            💾 ฐานข้อมูลบันทึกปลอดภัยใน LocalStorage
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

  // Inject SweetAlert2 CDN dynamically if not present
  if (typeof Swal === 'undefined' && !document.getElementById('sweetalert2CDN')) {
    const swalScript = document.createElement('script');
    swalScript.id = 'sweetalert2CDN';
    swalScript.src = 'https://cdn.jsdelivr.net/npm/sweetalert2@11';
    document.head.appendChild(swalScript);
  }

  function showSweetAlert(title, text, icon = 'info', confirmText = 'ตกลง', showCancel = false, cancelText = 'ยกเลิก', callback = null) {
    if (!document.getElementById('swalTopZIndexStyle')) {
      const st = document.createElement('style');
      st.id = 'swalTopZIndexStyle';
      st.innerHTML = '.swal2-container { z-index: 99999999 !important; }';
      document.head.appendChild(st);
    }
    const runSwal = () => {
      if (typeof Swal !== 'undefined') {
        Swal.fire({
          title: title,
          html: text,
          icon: icon,
          showCancelButton: showCancel,
          confirmButtonColor: icon === 'error' || icon === 'warning' ? '#dc2626' : (icon === 'success' ? '#10b981' : '#2563eb'),
          cancelButtonColor: '#64748b',
          confirmButtonText: confirmText,
          cancelButtonText: cancelText,
          background: '#0d1b2a',
          color: '#ffffff',
          customClass: { popup: 'rounded-4 shadow-lg border border-secondary' }
        }).then((result) => {
          if (callback) callback(result.isConfirmed);
        });
      } else {
        if (showCancel) {
          const ok = confirm(`${title}\n\n${text}`);
          if (callback) callback(ok);
        } else {
          alert(`${title}\n\n${text}`);
          if (callback) callback(true);
        }
      }
    };
    if (typeof Swal === 'undefined') {
      setTimeout(runSwal, 300);
    } else {
      runSwal();
    }
  }

  function handleLoginSubmit(evt) {
    if (evt) evt.preventDefault();

    const userInput = (document.getElementById('loginUserField').value || '').trim().toLowerCase();
    const passInput = (document.getElementById('loginPassField').value || '').trim();

    fetch('/api/users/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: userInput, pass: passInput })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success && data.user) {
        finalizeLogin({
          name: data.user.name,
          email: data.user.email,
          role: data.user.role,
          picture: `https://ui-avatars.com/api/?name=${encodeURIComponent(data.user.name)}&background=0d1b2a&color=fff`
        });
      } else {
        showSweetAlert('เข้าสู่ระบบไม่สำเร็จ', data.error || 'ไม่สามารถเข้าสู่ระบบได้', 'error');
      }
    })
    .catch(() => {
      // Fallback to local DB if backend offline
      const db = getUsersDatabase();
      const foundUser = db.find(u => 
        (u.name.toLowerCase() === userInput || u.email.toLowerCase() === userInput) && u.pass === passInput
      );
      if (!foundUser) {
        showSweetAlert('เข้าสู่ระบบไม่สำเร็จ', 'ไม่พบบัญชีผู้ใช้ หรือ รหัสผ่านไม่ถูกต้อง', 'error');
        return;
      }
      if (foundUser.status === 'pending_approval') {
        showSweetAlert('รอการอนุมัติสิทธิ์', 'บัญชีของคุณกำลังอยู่ระหว่างรอ Admin อนุมัติสิทธิ์ (Pending Approval)', 'warning');
        return;
      }
      finalizeLogin({
        name: foundUser.name,
        email: foundUser.email,
        role: foundUser.role,
        picture: `https://ui-avatars.com/api/?name=${encodeURIComponent(foundUser.name)}&background=0d1b2a&color=fff`
      });
    });
  }

  function handleSignupSubmit(evt) {
    if (evt) evt.preventDefault();

    const name = (document.getElementById('signupNameField').value || '').trim();
    const email = (document.getElementById('signupEmailField').value || '').trim().toLowerCase();
    const pass = (document.getElementById('signupPassField').value || '').trim();

    if (!name || !email || !pass) {
      showSweetAlert('กรอกข้อมูลไม่ครบถ้วน', 'กรุณากรอกข้อมูลให้ครบถ้วนก่อนส่งคำขอลงทะเบียน', 'warning');
      return;
    }

    fetch('/api/users/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, email: email, pass: pass })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        if (data.users) saveUsersDatabase(data.users);
        showSweetAlert('ส่งคำขอลงทะเบียนสำเร็จ!', 'คำขอของคุณถูกบันทึกปลอดภัยในเซิร์ฟเวอร์เรียบร้อยแล้ว<br><span style="color:#f59e0b; font-size:0.85rem; margin-top:6px; display:inline-block;">กรุณาแจ้ง Admin เพื่อเลือกสิทธิ์และอนุมัติบัญชีของคุณก่อนเข้าใช้งานครับ</span>', 'success');
        switchTab('login');
        renderProfileBadge();
      } else {
        showSweetAlert('ลงทะเบียนไม่สำเร็จ', data.error || 'เกิดข้อผิดพลาดในการลงทะเบียน', 'error');
      }
    })
    .catch(() => {
      const db = getUsersDatabase();
      const existing = db.find(u => u.email.toLowerCase() === email || u.name.toLowerCase() === name.toLowerCase());
      if (existing) {
        showSweetAlert('พบข้อมูลซ้ำ', 'ชื่อผู้ใช้หรืออีเมลนี้ถูกลงทะเบียนไว้แล้วในระบบ', 'warning');
        switchTab('login');
        return;
      }
      const nowStr = new Date().toLocaleString('th-TH');
      const newUser = { id: 'u_' + Date.now(), name: name, email: email, pass: pass, role: 'Pending', status: 'pending_approval', createdAt: nowStr };
      db.push(newUser);
      saveUsersDatabase(db);
      showSweetAlert('ส่งคำขอลงทะเบียนสำเร็จ!', 'คำขอของคุณถูกบันทึกเรียบร้อยแล้ว รอ Admin อนุมัติสิทธิ์', 'success');
      switchTab('login');
      renderProfileBadge();
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

    unlockPageDisplay();
    renderProfileBadge();
    updateModuleButtonsUI();
    resetIdleTimer();

    const currentPath = location.pathname.toLowerCase();
    const pageName = currentPath.split('/').pop() || 'index.html';
    const isAdminPage = pageName.includes('admin.html') || pageName.includes('audit_logs.html');

    if (isAdminPage) {
      if (user.role === 'Admin') {
        location.reload();
      } else {
        showSweetAlert('🔒 Access Denied', 'หน้านี้สงวนสิทธิ์เฉพาะผู้ดูแลระบบ (Admin) เท่านั้น บัญชีของคุณไม่ใช่ Admin', 'warning');
        setTimeout(function () { location.href = 'index.html'; }, 1500);
      }
    }
  }

  /* ─── Admin Approval Modal ─── */
  function openAdminApprovalModal() {
    const user = getStoredUser();
    if (!user || user.role !== 'Admin') {
      showSweetAlert('🔒 สงวนสิทธิ์ Admin', 'สงวนสิทธิ์สำหรับผู้ใช้งานระดับ Admin เท่านั้น', 'warning');
      return;
    }

    let overlay = document.getElementById('socnAdminApprovalOverlay');
    if (overlay) {
      renderAdminApprovalTable();
      overlay.style.display = 'flex';
      return;
    }

    overlay = document.createElement('div');
    overlay.id = 'socnAdminApprovalOverlay';
    overlay.innerHTML = `
      <style>
        #socnAdminApprovalOverlay {
          position:fixed; inset:0; z-index:99999999;
          background:rgba(13,27,42,0.85); backdrop-filter:blur(8px);
          display:flex; align-items:center; justify-content:center;
          font-family:'Segoe UI',system-ui,sans-serif; padding:16px;
        }
        #socnApprovalCard {
          background:#fff; border-radius:22px; width:100%; max-width:780px;
          box-shadow:0 30px 60px rgba(0,0,0,0.5); overflow:hidden; position:relative; max-height:85vh; display:flex; flex-direction:column;
        }
        #socnApprovalCard .auth-header {
          background:#0d1b2a; color:#fff; padding:20px 24px; display:flex; justify-content:space-between; align-items:center;
        }
        #socnApprovalCard .auth-body { padding:20px; overflow-y:auto; flex:1; }
        .table-approval { width:100%; font-size:0.85rem; border-collapse:collapse; }
        .table-approval th { background:#0f172a; color:#fff; padding:10px 12px; text-align:left; }
        .table-approval td { padding:10px 12px; border-bottom:1px solid #e2e8f0; vertical-align:middle; }
        .status-badge-pending { background:#fef3c7; color:#92400e; padding:3px 8px; border-radius:12px; font-weight:700; font-size:11px; }
        .status-badge-approved { background:#dcfce7; color:#166534; padding:3px 8px; border-radius:12px; font-weight:700; font-size:11px; }
      </style>

      <div id="socnApprovalCard">
        <div class="auth-header">
          <div>
            <h5 style="font-weight:800; margin:0; font-size:1.15rem;"><i class="fa-solid fa-user-check me-2 text-warning"></i> ระบบอนุมัติสมาชิก & กำหนด Role (Admin Panel)</h5>
            <div style="font-size:0.78rem; color:#94a3b8; margin-top:2px;">ตรวจสอบคำขอลงทะเบียน เลือก Role และกดอนุมัติสิทธิ์ใช้งาน</div>
          </div>
          <button style="background:transparent; border:none; color:#94a3b8; font-size:1.4rem; cursor:pointer;" onclick="document.getElementById('socnAdminApprovalOverlay').style.display='none'">✕</button>
        </div>

        <div class="auth-body">
          <div style="margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
            <strong style="font-size:0.9rem; color:#0f172a;">รายชื่อสมาชิกที่ลงทะเบียนในระบบ:</strong>
            <button onclick="window.AuthGuard.renderAdminApprovalTable()" style="background:#2563eb; color:#fff; border:none; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:700; cursor:pointer;"><i class="fa-solid fa-rotate me-1"></i> รีเฟรชข้อมูล</button>
          </div>

          <div style="overflow-x:auto;">
            <table class="table-approval" id="adminApprovalTable">
              <thead>
                <tr>
                  <th>ชื่อผู้ใช้ (Username)</th>
                  <th>อีเมล (Email)</th>
                  <th>สถานะ (Status)</th>
                  <th>เลือก Role</th>
                  <th>จัดการ (Actions)</th>
                </tr>
              </thead>
              <tbody id="approvalTableBody">
                <!-- Rendered dynamically -->
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    renderAdminApprovalTable();
  }

  function renderAdminApprovalTable() {
    const tbody = document.getElementById('approvalTableBody');
    if (!tbody) return;

    const db = getUsersDatabase();
    if (!db || db.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:#94a3b8;">ไม่พบรายชื่อผู้ใช้งานในระบบ</td></tr>';
      return;
    }

    tbody.innerHTML = db.map(u => {
      const isPending = u.status === 'pending_approval';
      const statusBadge = isPending ? 
        '<span class="status-badge-pending">⏳ รออนุมัติ (Pending)</span>' : 
        `<span class="status-badge-approved">✅ อนุมัติแล้ว (${u.role})</span>`;

      const roleSelect = isPending ? `
        <select id="roleSelect_${u.id}" style="padding:4px 8px; border-radius:6px; border:1px solid #cbd5e1; font-size:0.8rem; font-weight:700;">
          <option value="Ground">👤 Ground</option>
          <option value="Admin">🛡️ Admin</option>
        </select>
      ` : `<span style="font-weight:700; color:#334155;">${u.role}</span>`;

      const actionBtn = isPending ? `
        <button onclick="window.AuthGuard.approveUser('${u.id}')" style="background:#059669; color:#fff; border:none; padding:5px 10px; border-radius:6px; font-size:0.78rem; font-weight:700; cursor:pointer; margin-right:4px;">
          <i class="fa-solid fa-check me-1"></i> อนุมัติ
        </button>
        <button onclick="window.AuthGuard.rejectUser('${u.id}')" style="background:#dc2626; color:#fff; border:none; padding:5px 8px; border-radius:6px; font-size:0.78rem; font-weight:700; cursor:pointer;">
          <i class="fa-solid fa-xmark"></i>
        </button>
      ` : `
        <button onclick="window.AuthGuard.rejectUser('${u.id}')" style="background:#94a3b8; color:#fff; border:none; padding:4px 8px; border-radius:6px; font-size:0.75rem; cursor:pointer;">
          ลบสมาชิก
        </button>
      `;

      return `
        <tr>
          <td style="font-weight:700; color:#0f172a;">${esc(u.name)}</td>
          <td style="color:#475569;">${esc(u.email)}</td>
          <td>${statusBadge}</td>
          <td>${roleSelect}</td>
          <td>${actionBtn}</td>
        </tr>
      `;
    }).join('');
  }

  function approveUser(userId) {
    const db = getUsersDatabase();
    const target = db.find(u => u.id === userId);
    if (!target) return;

    const roleSelect = document.getElementById(`roleSelect_${userId}`);
    const chosenRole = roleSelect ? roleSelect.value : 'Ground';

    target.status = 'approved';
    target.role = chosenRole;

    saveUsersDatabase(db);
    showSweetAlert('อนุมัติสมาชิกสำเร็จ!', `อนุมัติสมาชิก <b>"${target.name}"</b> เป็นสิทธิ์ <b>${chosenRole}</b> เรียบร้อยแล้ว`, 'success');

    renderAdminApprovalTable();
    renderProfileBadge();
  }

  function rejectUser(userId) {
    const db = getUsersDatabase();
    const targetIndex = db.findIndex(u => u.id === userId);
    if (targetIndex === -1) return;

    showSweetAlert(
      '⚠️ ยืนยันการลบสมาชิก?',
      `คุณต้องการลบคำขอ/สมาชิก <b>"${db[targetIndex].name}"</b> ออกจากระบบใช่หรือไม่?`,
      'warning',
      '<i class="fa-solid fa-trash me-1"></i> ใช่, ลบสมาชิก',
      true,
      'ยกเลิก',
      function (confirmed) {
        if (confirmed) {
          db.splice(targetIndex, 1);
          saveUsersDatabase(db);
          renderAdminApprovalTable();
          renderProfileBadge();
        }
      }
    );
  }

  /* ─── Page Display Lock & Unlock ─── */
  function lockPageDisplay() {
    let style = document.getElementById('socnLockPageStyle');
    if (!style) {
      style = document.createElement('style');
      style.id = 'socnLockPageStyle';
      style.innerHTML = `
        body > *:not(#socnAuthOverlay):not(#socnAdminApprovalOverlay):not(.swal2-container):not(nav):not(.top-nav):not(.modal):not(.modal-backdrop) {
          filter: blur(12px) grayscale(60%) !important;
          pointer-events: none !important;
          user-select: none !important;
          opacity: 0.25 !important;
          transition: all 0.3s ease !important;
        }
      `;
      document.head.appendChild(style);
    }
  }

  function unlockPageDisplay() {
    const style = document.getElementById('socnLockPageStyle');
    if (style) style.remove();
  }

  /* ─── Page Access Guard (Enforced on All Dashboard Modules) ─── */
  function checkPagePermissions() {
    const user = getStoredUser();
    const currentPath = location.pathname.toLowerCase();
    const pageName = currentPath.split('/').pop() || 'index.html';
    const isPublicPage = pageName === '' || pageName === 'index.html' || pageName === 'login.html';
    const isAdminOnlyPage = pageName.includes('admin.html') || pageName.includes('audit_logs.html');

    // Portal Hub (index.html) is public
    if (isPublicPage) {
      unlockPageDisplay();
      return true;
    }

    // All dashboard modules require authentication
    if (!user) {
      lockPageDisplay();
      showAuthModal('🔒 กรุณาเข้าสู่ระบบเพื่อเข้าใช้งานระบบนี้', true);
      return false;
    }

    // Admin pages require Admin role
    if (isAdminOnlyPage) {
      if (user.role !== 'Admin') {
        lockPageDisplay();
        showSweetAlert('🔒 Access Denied', 'หน้านี้สงวนสิทธิ์เฉพาะผู้ดูแลระบบ (Admin) เท่านั้น', 'warning');
        setTimeout(function () { location.href = 'index.html'; }, 1500);
        return false;
      }
    }

    unlockPageDisplay();
    return true;
  }

  function updateModuleButtonsUI() {
    const u = getStoredUser();
    const isAdmin = u && u.role === 'Admin';

    // Dynamic Admin Portal Card Visibility: Hide completely for non-admin users
    const adminCardCol = document.getElementById('adminPortalCardCol');
    if (adminCardCol) {
      adminCardCol.style.display = isAdmin ? 'block' : 'none';
    }
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
    setupExportAndUploadTrackers();
  }

  function setupExportAndUploadTrackers() {
    document.addEventListener('click', function (e) {
      var target = e.target.closest('button, a');
      if (!target) return;
      
      var text = (target.innerText || target.textContent || '').trim();
      var onclickAttr = target.getAttribute('onclick') || '';
      var hrefAttr = target.getAttribute('href') || '';

      if (text.includes('Export') || text.includes('Download') || text.includes('ส่งออก') || text.includes('ดาวน์โหลด') || onclickAttr.toLowerCase().includes('export') || onclickAttr.toLowerCase().includes('download') || hrefAttr.includes('export') || hrefAttr.includes('download')) {
        var pageName = location.pathname.split('/').pop() || 'index.html';
        logExport(text || 'Data Export', null, `ดาวน์โหลด/ส่งออกข้อมูลจากหน้า ${pageName}`);
      }
    }, true);

    document.addEventListener('change', function (e) {
      var target = e.target;
      if (target && target.type === 'file' && target.files && target.files.length > 0) {
        var file = target.files[0];
        var pageName = location.pathname.split('/').pop() || 'index.html';
        logUpload(file.name, null, `อัปโหลดไฟล์ขนาด ${Math.round(file.size / 1024)} KB ในหน้า ${pageName}`);
      }
    }, true);
  }

  function logActivity(action, details) {
    var u = getStoredUser();
    fetch('/api/log-client-activity', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: action,
        details: details,
        user_email: u ? u.email : 'guest',
        user_name: u ? u.name : 'Guest',
        user_role: u ? u.role : 'Ground'
      })
    }).catch(function () {});
  }

  function logUpload(filename, rowCount, details) {
    var u = getStoredUser();
    logActivity('FILE_UPLOAD', `📥 อัปโหลดไฟล์: ${filename} (${rowCount || 0} รายการ) ${details ? '- ' + details : ''}`);
  }

  function logExport(exportName, rowCount, details) {
    var u = getStoredUser();
    logActivity('DATA_EXPORT', `📤 ดาวน์โหลด/ส่งออกข้อมูล: ${exportName} (${rowCount || 0} รายการ) ${details ? '- ' + details : ''}`);
  }

  /* ─── Edit Profile & Change Password Modal ─── */
  function openProfileModal() {
    var user = getStoredUser();
    if (!user) {
      showAuthModal('กรุณาเข้าสู่ระบบก่อนแก้ไขข้อมูล');
      return;
    }

    var overlay = document.getElementById('socnProfileOverlay');
    if (overlay) {
      document.getElementById('cpNameField').value = user.name || '';
      document.getElementById('cpCurrentPass').value = '';
      document.getElementById('cpNewPass').value = '';
      document.getElementById('cpConfirmPass').value = '';
      overlay.style.display = 'flex';
      return;
    }

    overlay = document.createElement('div');
    overlay.id = 'socnProfileOverlay';
    overlay.onclick = function(e) {
      if (e.target === overlay) {
        overlay.style.display = 'none';
      }
    };
    overlay.innerHTML = `
      <style>
        #socnProfileOverlay {
          position:fixed; inset:0; z-index:99999999;
          background:rgba(13,27,42,0.85); backdrop-filter:blur(8px);
          display:flex; align-items:center; justify-content:center;
          font-family:'Segoe UI',system-ui,sans-serif; padding:16px;
        }
        #socnProfileCard {
          background:#fff; border-radius:20px; width:100%; max-width:460px;
          box-shadow:0 30px 60px rgba(0,0,0,0.5); overflow:hidden; position:relative;
        }
        #socnProfileCard .cp-header {
          background:#0f172a; color:#fff; padding:20px 24px; position:relative; text-align:center;
        }
        #socnProfileCard .cp-body { padding:24px; max-height:80vh; overflow-y:auto; }
      </style>
      <div id="socnProfileCard">
        <div class="cp-header">
          <button style="position:absolute; top:16px; right:16px; background:transparent; border:none; color:#94a3b8; font-size:1.4rem; cursor:pointer;" onclick="document.getElementById('socnProfileOverlay').style.display='none'">✕</button>
          <div style="font-size:2rem; margin-bottom:4px;">👤</div>
          <h5 style="font-weight:800; margin:0; font-size:1.15rem;">แก้ไขข้อมูลส่วนตัว & รหัสผ่าน (Edit Profile)</h5>
          <div style="font-size:0.78rem; color:#94a3b8; margin-top:3px;">สำหรับบัญชี: <strong style="color:#60a5fa;">${esc(user.email)}</strong> (${esc(user.role)})</div>
        </div>
        <div class="cp-body">
          <form id="socnProfileForm" onsubmit="window.AuthGuard.handleProfileSubmit(event)">
            
            <div class="field-group mb-3">
              <label style="display:block; font-size:0.82rem; font-weight:700; color:#1e293b; margin-bottom:5px;">
                <i class="fa-solid fa-user me-1 text-primary"></i> ชื่อผู้ใช้งาน (Username / Display Name):
              </label>
              <input type="text" id="cpNameField" value="${esc(user.name)}" placeholder="ระบุชื่อผู้ใช้งานใหม่" style="width:100%; padding:10px 14px; border:1.5px solid #cbd5e1; border-radius:10px; font-size:0.92rem; outline:none; box-sizing:border-box; font-weight:700; color:#0f172a;" required>
              <div style="font-size:0.74rem; color:#64748b; margin-top:3px;">ชื่อนี้จะแสดงบนมุมขวาบนของระบบ และในบันทึก Activity Logs</div>
            </div>

            <div style="margin:16px 0 12px; border-top:1px dashed #cbd5e1; padding-top:12px;">
              <span style="font-size:0.8rem; font-weight:700; color:#64748b;"><i class="fa-solid fa-key me-1 text-warning"></i> เปลี่ยนรหัสผ่าน (หากไม่ต้องการเปลี่ยน ให้เว้นว่างไว้):</span>
            </div>

            <div class="field-group mb-2">
              <label style="display:block; font-size:0.78rem; font-weight:600; color:#475569; margin-bottom:4px;">รหัสผ่านปัจจุบัน (Current Password):</label>
              <input type="password" id="cpCurrentPass" placeholder="กรอกรหัสเดิม (จำเป็นเมื่อต้องการเปลี่ยนรหัส)" style="width:100%; padding:9px 12px; border:1.5px solid #cbd5e1; border-radius:8px; font-size:0.88rem; outline:none; box-sizing:border-box;">
            </div>

            <div class="field-group mb-2">
              <label style="display:block; font-size:0.78rem; font-weight:600; color:#475569; margin-bottom:4px;">รหัสผ่านใหม่ (New Password):</label>
              <input type="password" id="cpNewPass" placeholder="รหัสผ่านใหม่ (เว้นว่างไว้ถ้าไม่เปลี่ยน)" minlength="4" style="width:100%; padding:9px 12px; border:1.5px solid #cbd5e1; border-radius:8px; font-size:0.88rem; outline:none; box-sizing:border-box;">
            </div>

            <div class="field-group mb-4">
              <label style="display:block; font-size:0.78rem; font-weight:600; color:#475569; margin-bottom:4px;">ยืนยันรหัสผ่านใหม่ (Confirm New Password):</label>
              <input type="password" id="cpConfirmPass" placeholder="กรอกรหัสผ่านใหม่อีกครั้ง" minlength="4" style="width:100%; padding:9px 12px; border:1.5px solid #cbd5e1; border-radius:8px; font-size:0.88rem; outline:none; box-sizing:border-box;">
            </div>

            <div style="display:flex; gap:10px;">
              <button type="button" onclick="document.getElementById('socnProfileOverlay').style.display='none'" style="flex:1; background:#f1f5f9; color:#475569; border:none; padding:12px; border-radius:10px; font-weight:700; cursor:pointer;">ยกเลิก</button>
              <button type="submit" id="btnSubmitProfile" style="flex:2; background:#0284c7; color:#fff; border:none; padding:12px; border-radius:10px; font-weight:800; cursor:pointer; box-shadow:0 4px 12px rgba(2,132,199,0.35);"><i class="fa-solid fa-save me-1"></i> บันทึกข้อมูล</button>
            </div>
          </form>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
  }

  function handleProfileSubmit(evt) {
    if (evt) evt.preventDefault();
    var user = getStoredUser();
    if (!user) return;

    var newName = (document.getElementById('cpNameField').value || '').trim();
    var currentPass = (document.getElementById('cpCurrentPass').value || '').trim();
    var newPass = (document.getElementById('cpNewPass').value || '').trim();
    var confirmPass = (document.getElementById('cpConfirmPass').value || '').trim();

    if (!newName) {
      showSweetAlert('กรอกข้อมูลไม่ครบ', 'กรุณาระบุชื่อผู้ใช้งาน (Username)', 'warning');
      return;
    }

    if (newPass || currentPass) {
      if (!currentPass) {
        showSweetAlert('ต้องการรหัสผ่านเดิม', 'กรุณากรอกรหัสผ่านปัจจุบันเพื่อยืนยันการตั้งรหัสผ่านใหม่', 'warning');
        return;
      }
      if (newPass !== confirmPass) {
        showSweetAlert('รหัสผ่านไม่ตรงกัน', 'รหัสผ่านใหม่และการยืนยันรหัสผ่านใหม่ไม่ตรงกัน', 'error');
        return;
      }
      if (newPass.length < 4) {
        showSweetAlert('รหัสผ่านสั้นเกินไป', 'รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 4 ตัวอักษร', 'warning');
        return;
      }
    }

    var btn = document.getElementById('btnSubmitProfile');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> กำลังบันทึก...';
    }

    fetch('/api/users/update-profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: user.email,
        name: newName,
        currentPass: currentPass,
        newPass: newPass,
        confirmPass: confirmPass
      })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-save me-1"></i> บันทึกข้อมูล';
      }
      if (data.success) {
        user.name = newName;
        user.picture = `https://ui-avatars.com/api/?name=${encodeURIComponent(newName)}&background=0d1b2a&color=fff`;
        saveStoredUser(user);

        var ov = document.getElementById('socnProfileOverlay');
        if (ov) ov.style.display = 'none';

        renderProfileBadge();
        showSweetAlert('อัปเดตข้อมูลสำเร็จ!', `บันทึกข้อมูลส่วนตัวเรียบร้อยแล้ว<br>ชื่อผู้ใช้ใหม่: <b>"${esc(newName)}"</b>`, 'success');
      } else {
        showSweetAlert('อัปเดตข้อมูลไม่สำเร็จ', data.error || 'เกิดข้อผิดพลาดในการบันทึกข้อมูล', 'error');
      }
    })
    .catch(function(err) {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-save me-1"></i> บันทึกข้อมูล';
      }
      showSweetAlert('เกิดข้อผิดพลาด', 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้: ' + err.message, 'error');
    });
  }

  // Backward compatibility aliases
  function openChangePasswordModal() { openProfileModal(); }
  function handleChangePasswordSubmit(evt) { handleProfileSubmit(evt); }

  /* ─── Profile Badge on Navbar ─── */
  function renderProfileBadge() {
    var user = getStoredUser();
    var db = getUsersDatabase();
    var pendingCount = db.filter(u => u.status === 'pending_approval').length;

    var adminTile = document.getElementById('adminPortalCardCol');
    if (adminTile) {
      if (!user || user.role === 'Admin') {
        adminTile.style.display = 'flex';
      } else {
        adminTile.style.display = 'none';
      }
    }

    document.querySelectorAll('.top-nav, nav, .portal-status-bar').forEach(function (nav) {
      var badge = nav.querySelector('.user-profile-badge');
      if (!badge) {
        badge = document.createElement('div');
        badge.className = 'user-profile-badge';
        badge.style.cssText = 'display:flex;align-items:center;gap:8px;font-size:.85rem;margin-left:auto;';
        nav.appendChild(badge);
      }

      if (user) {
        var roleBg = user.role === 'Admin' ? '#d0311d' : '#2563eb';
        var adminPanelBtn = user.role === 'Admin' ? '<a href="admin.html" style="color:#ffffff;text-decoration:none;font-weight:700;background:#d0311d;padding:5px 12px;border-radius:8px;box-shadow:0 2px 8px rgba(208,49,29,0.4);font-size:0.82rem;"><i class="fa-solid fa-user-shield me-1"></i> 🛡️ Admin Dashboard</a>' : '';
        
        var pendingBadgeBtn = user.role === 'Admin' ? `
          <button onclick="window.AuthGuard.openAdminApprovalModal()" style="background:#f59e0b; color:#fff; border:none; padding:5px 12px; border-radius:8px; font-weight:700; font-size:0.8rem; cursor:pointer; position:relative; box-shadow:0 2px 8px rgba(245,158,11,0.3);">
            <i class="fa-solid fa-user-clock me-1"></i> อนุมัติสมาชิก
            ${pendingCount > 0 ? `<span style="position:absolute; top:-6px; right:-6px; background:#dc2626; color:#fff; font-size:10px; font-weight:800; border-radius:50%; width:18px; height:18px; display:flex; align-items:center; justify-content:center; border:2px solid #fff;">${pendingCount}</span>` : ''}
          </button>
        ` : '';

        var changePassBtn = `
          <button onclick="window.AuthGuard.openProfileModal()" style="background:#0284c7; color:#fff; border:none; padding:5px 10px; border-radius:6px; font-weight:700; font-size:0.8rem; cursor:pointer; box-shadow:0 2px 6px rgba(2,132,199,0.3);" title="แก้ไขชื่อผู้ใช้งาน (Username) หรือเปลี่ยนรหัสผ่าน">
            <i class="fa-solid fa-user-pen me-1"></i> แก้ไขโปรไฟล์
          </button>
        `;

        badge.innerHTML = adminPanelBtn + pendingBadgeBtn +
          '<div style="display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.08);padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,.15);">' +
            '<img src="' + user.picture + '" style="width:24px;height:24px;border-radius:50%;object-fit:cover;">' +
            '<span style="font-weight:700;color:#fff;">' + esc(user.name) + '</span>' +
            '<span style="background:' + roleBg + ';color:#fff;font-size:10px;font-weight:800;padding:2px 8px;border-radius:12px;text-transform:uppercase;">' + user.role + '</span>' +
          '</div>' +
          changePassBtn +
          '<button onclick="window.AuthGuard.logout()" style="background:#dc2626;color:#fff;border:none;padding:5px 12px;border-radius:6px;font-weight:700;font-size:.8rem;cursor:pointer;"><i class="fa-solid fa-right-from-bracket me-1"></i> Logout</button>';
      } else {
        badge.innerHTML = `
          <button onclick="window.AuthGuard.showModal('🔑 เข้าสู่ระบบ / ลงทะเบียน')" style="background:#2563eb; color:#fff; border:none; padding:6px 14px; border-radius:8px; font-weight:700; font-size:0.82rem; cursor:pointer; box-shadow:0 2px 6px rgba(37,99,235,0.4);"><i class="fa-solid fa-key me-1"></i> 🔑 เข้าสู่ระบบ / ลงทะเบียน</button>
        `;
      }
    });
  }

  function esc(s) { return s ? String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') : ''; }

  function injectResponsiveMobileStyles() {
    if (document.getElementById('socnMobileResponsiveStyles')) return;
    var style = document.createElement('style');
    style.id = 'socnMobileResponsiveStyles';
    style.innerHTML = `
      html, body {
        max-width: 100vw !important;
        overflow-x: hidden !important;
        box-sizing: border-box !important;
        margin: 0 !important;
        padding: 0 !important;
      }

      /* Mobile Navigation Bar Auto Wrapping & Overflow Fix */
      @media (max-width: 992px) {
        .top-nav, nav {
          padding: 10px 14px !important;
          flex-direction: column !important;
          align-items: flex-start !important;
          gap: 8px !important;
        }
        .top-nav a.brand-title, nav a {
          font-size: 0.92rem !important;
          max-width: 100% !important;
          word-break: break-word !important;
        }
        .user-profile-badge {
          width: 100% !important;
          margin-left: 0 !important;
          justify-content: flex-start !important;
          flex-wrap: wrap !important;
          gap: 6px !important;
          padding-top: 8px !important;
          border-top: 1px solid rgba(255,255,255,0.12) !important;
        }
        .container-fluid {
          padding-left: 12px !important;
          padding-right: 12px !important;
          max-width: 100% !important;
        }
      }

      @media (max-width: 576px) {
        .user-profile-badge button, .user-profile-badge a {
          font-size: 0.75rem !important;
          padding: 4px 8px !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  /* ─── Init ─── */
  function initAuthSystem() {
    injectResponsiveMobileStyles();
    getUsersDatabase(); // Initialize local database
    checkPagePermissions();
    renderProfileBadge();
    updateModuleButtonsUI();
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
    closeModal: function () {
      const user = getStoredUser();
      const currentPath = location.pathname.toLowerCase();
      const pageName = currentPath.split('/').pop() || 'index.html';
      const isPublicPage = pageName === '' || pageName === 'index.html' || pageName === 'login.html';
      const isAdminPage = pageName.includes('admin.html') || pageName.includes('audit_logs.html');

      if (!isPublicPage && !user) {
        location.href = 'index.html';
        return;
      }

      if (isAdminPage && (!user || user.role !== 'Admin')) {
        location.href = 'index.html';
        return;
      }

      const overlay = document.getElementById('socnAuthOverlay');
      if (overlay) overlay.style.display = 'none';
    },
    switchTab: switchTab,
    handleLoginSubmit: handleLoginSubmit,
    handleSignupSubmit: handleSignupSubmit,
    openProfileModal: openProfileModal,
    handleProfileSubmit: handleProfileSubmit,
    openChangePasswordModal: openChangePasswordModal,
    handleChangePasswordSubmit: handleChangePasswordSubmit,
    openAdminApprovalModal: openAdminApprovalModal,
    renderAdminApprovalTable: renderAdminApprovalTable,
    approveUser: approveUser,
    rejectUser: rejectUser,
    extendSession: function () {
      resetIdleTimer();
      var w = document.getElementById('socnIdleWarn');
      if (w) w.style.display = 'none';
    },
    logActivity: logActivity,
    logUpload: logUpload,
    logExport: logExport
  };
})();
