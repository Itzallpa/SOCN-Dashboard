import os
import re

print("Building dedicated ob_bl.html from ObBL.html.txt...")

base_dir = r"c:\Users\spxth71637\Desktop\OB Dashboard"
ob_bl_txt_path = os.path.join(base_dir, "OB Late", "ObBL.html.txt")

with open(ob_bl_txt_path, "r", encoding="utf-8") as f:
    source_content = f.read()

# Shared Navbar Builder
def get_navbar(active_page):
    def active_style(name):
        if active_page == name:
            return "color:#ffffff; text-decoration:none; padding:6px 14px; border-radius:6px; font-weight:700; font-size:0.88rem; background:#2563eb; transition:all 0.2s;"
        return "color:#cbd5e1; text-decoration:none; padding:6px 14px; border-radius:6px; font-weight:600; font-size:0.88rem; background:rgba(255,255,255,0.08); transition:all 0.2s;"

    return f"""
  <!-- Top Navigation Header -->
  <nav style="background:#0d1b2a; color:#ffffff; padding:12px 24px; display:flex; align-items:center; justify-content:space-between; box-shadow:0 4px 14px rgba(0,0,0,0.25); position:sticky; top:0; z-index:1020;">
    <a href="index.html" style="color:#ffffff; font-size:1.15rem; font-weight:800; text-decoration:none; display:flex; align-items:center; gap:8px;">
      <span style="font-size:1.4rem;">📦</span> SOC Operations Portal
    </a>
    <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
      <a href="index.html" style="{active_style('portal')}">🏠 Portal Hub</a>
      <a href="investigation.html" style="{active_style('investigation')}">🚀 Investigation</a>
      <a href="skip_process.html" style="{active_style('skip')}">📦 Skip Monitor</a>
      <a href="cutoff_master.html" style="{active_style('cutoff')}">⏰ Cutoff Master</a>
      <a href="lh_trip.html" style="{active_style('lh_trip')}">🚚 LH Trip & OB Late</a>
      <a href="ob_bl.html" style="{active_style('ob_bl')}">📊 OB Backlog (OB BL)</a>
    </div>
  </nav>
  <script src="auth_guard.js"></script>
"""

# Include SweetAlert2 CDN and Bootstrap JS in head
head_inject = """
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.3.2/papaparse.min.js"></script>
"""

source_content = source_content.replace("</head>", head_inject + "\n</head>")

# Replace Body Header
navbar_html = get_navbar("ob_bl")

custom_header = """
    <!-- Header Banner & Controls -->
    <header style="display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; background:linear-gradient(120deg, #ee4d2d, #ff7a45); border-radius:14px; padding:16px 22px; color:#fff; box-shadow:0 8px 20px -8px rgba(238,77,45,.35); margin-bottom:14px;">
      <div>
        <h1 style="font-size:21px; margin:0 0 2px; font-weight:800; color:#fff;">📊 OB Backlog (OB BL) Dashboard</h1>
        <div class="subtitle" id="subtitle">ระบบติดตามพัสดุค้าง OB Backlog และวิเคราะห์ตามทีม/ชั่วโมง</div>
      </div>
      <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
        <button onclick="openGoogleSheetModal()" style="background:#059669; color:#fff; font-weight:700; border:none; padding:8px 14px; border-radius:8px;"><i class="fa-solid fa-link"></i> Sync Google Sheet</button>
        <select id="fileSelectDropdown" onchange="onFileDropdownChange(this.value)" style="padding:7px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.4); background:rgba(255,255,255,0.9); color:#1e293b; font-weight:700; font-size:13px; max-width:240px;">
          <option value="">-- เลือกไฟล์รายงาน OB BL --</option>
        </select>
        <button id="deleteFileBtn" onclick="deleteSelectedObBlFile()" style="background:#dc2626; color:#fff; font-weight:700; border:none; padding:8px 12px; border-radius:8px; font-size:12px;"><i class="fa-solid fa-trash"></i> ลบไฟล์ที่เลือก</button>
        <button onclick="document.getElementById('csvFileInput').click()" style="background:#2563eb; color:#fff; font-weight:700; border:none; padding:8px 14px; border-radius:8px;"><i class="fa-solid fa-upload"></i> อัปโหลด CSV/Excel</button>
        <input type="file" id="csvFileInput" accept=".csv, .xlsx, .xls" style="display:none;" onchange="handleFileUpload(event)">
        <button id="refreshBtn" onclick="forceRefresh()" style="background:#ffffff; color:#ee4d2d; font-weight:700; border:none; padding:8px 14px; border-radius:8px;">↻ Refresh</button>
        <button id="exportBtn" class="export-btn" disabled style="background:linear-gradient(120deg, #1a1d29, #3a3f58); color:#fff; font-weight:700; border:none; padding:8px 14px; border-radius:8px;">⇩ Export Raw (CSV)</button>
      </div>
    </header>
"""

# Replace <body> ... <div class="app">
source_content = source_content.replace("<body>\n  <div class=\"app\">", f"<body>\n{navbar_html}\n  <div class=\"app\">")

# Replace original <header> ... </header> block
source_content = re.sub(r'<header>.*?</header>', custom_header, source_content, flags=re.DOTALL)

# Replace data loading script functions with Flask API + Google Apps Script support
js_api_helpers = """
    // =======================================================================
    // FLASK API & GOOGLE APPS SCRIPT DUAL LOAD SYSTEM
    // =======================================================================
    let currentFilename = '';

    function safeFetchJson(url, options) {
      return fetch(url, options).then(res => {
        return res.text().then(text => {
          let json = null;
          try {
            if (text && text.trim()) json = JSON.parse(text);
          } catch (e) {}

          if (!res.ok) {
            const errDetail = json && json.error ? json.error : `เซิร์ฟเวอร์ตอบกลับ Error Status ${res.status}`;
            throw new Error(errDetail);
          }
          if (!json) {
            throw new Error('ไม่สามารถอ่านข้อมูลจากเซิร์ฟเวอร์ได้');
          }
          return json;
        });
      });
    }

    function fetchFileList() {
      safeFetchJson('/api/list-files')
        .then(data => {
          const select = document.getElementById('fileSelectDropdown');
          if (!select) return;
          const current = select.value;
          select.innerHTML = '<option value="">-- เลือกไฟล์รายงาน OB BL --</option>';

          const files = data.files || [];
          files.forEach(f => {
            const fname = typeof f === 'string' ? f : f.name;
            if (!fname) return;
            const opt = document.createElement('option');
            opt.value = fname;
            opt.textContent = (fname.length > 35 ? fname.substring(0, 32) + '...' : fname);
            select.appendChild(opt);
          });

          if (current && files.some(f => (typeof f === 'string' ? f : f.name) === current)) {
            select.value = current;
          } else if (currentFilename) {
            select.value = currentFilename;
          }
        })
        .catch(err => console.log('Error listing files:', err));
    }

    function onFileDropdownChange(filename) {
      if (!filename) return;
      currentFilename = filename;
      fetchObBlData(filename);
    }

    function deleteSelectedObBlFile() {
      const select = document.getElementById('fileSelectDropdown');
      const filename = select ? select.value : '';
      if (!filename) {
        Swal.fire({ icon: 'warning', title: 'โปรดเลือกไฟล์ที่ต้องการลบ', text: 'กรุณาเลือกไฟล์ในรายการ Dropdown ก่อนครับ' });
        return;
      }

      Swal.fire({
        title: `ต้องการลบไฟล์ "${filename}" ใช่หรือไม่?`,
        text: 'เมื่อลบแล้วจะไม่สามารถกู้คืนได้!',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc2626',
        cancelButtonColor: '#64748b',
        confirmButtonText: 'ลบไฟล์ทันที',
        cancelButtonText: 'ยกเลิก'
      }).then(result => {
        if (result.isConfirmed) {
          fetch('/api/delete-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: filename })
          })
          .then(res => res.json())
          .then(data => {
            if (data.success) {
              Swal.fire({ icon: 'success', title: 'ลบไฟล์เรียบร้อย!', timer: 1500, showConfirmButton: false });
              fetchFileList();
              fetchObBlData();
            } else {
              Swal.fire({ icon: 'error', title: 'ไม่สามารถลบไฟล์ได้', text: data.error });
            }
          })
          .catch(err => Swal.fire({ icon: 'error', title: 'เกิดข้อผิดพลาด', text: err.message }));
        }
      });
    }

    function handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('file', file);

      Swal.fire({
        title: 'กำลังอัปโหลดไฟล์...',
        text: file.name,
        allowOutsideClick: false,
        didOpen: () => { Swal.showLoading(); }
      });

      fetch('/api/upload', {
        method: 'POST',
        body: formData
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          Swal.fire({ icon: 'success', title: 'อัปโหลดสำเร็จ!', timer: 1500, showConfirmButton: false });
          currentFilename = data.filename || file.name;
          fetchFileList();
          fetchObBlData(currentFilename);
        } else {
          Swal.fire({ icon: 'error', title: 'อัปโหลดไม่สำเร็จ', text: data.error });
        }
      })
      .catch(err => Swal.fire({ icon: 'error', title: 'เกิดข้อผิดพลาด', text: err.message }));
    }

    function openGoogleSheetModal() {
      const savedUrl = localStorage.getItem('socn_google_sheet_obbl_url') || localStorage.getItem('socn_google_sheet_url') || '';
      Swal.fire({
        title: '🔗 ดึงข้อมูลสดจาก Google Sheet / Apps Script',
        html: `
          <p class="text-start small text-muted mb-2">กรอก URL ของ Google Apps Script Web App หรือ Google Sheet CSV Link ที่มีข้อมูล OB BL:</p>
          <input id="swal-gs-url" class="swal2-input" placeholder="https://script.google.com/macros/s/.../exec หรือ Google Sheet URL" value="${savedUrl}">
        `,
        showCancelButton: true,
        confirmButtonText: '⚡ ดึงข้อมูลทันที',
        cancelButtonText: 'ยกเลิก',
        confirmButtonColor: '#059669',
        preConfirm: () => {
          const url = document.getElementById('swal-gs-url').value.trim();
          if (!url) {
            Swal.showValidationMessage('กรุณากรอก URL ให้ถูกต้อง');
            return false;
          }
          return url;
        }
      }).then((result) => {
        if (result.isConfirmed) {
          syncGoogleSheetUrl(result.value);
        }
      });
    }

    function syncGoogleSheetUrl(url) {
      localStorage.setItem('socn_google_sheet_obbl_url', url);
      Swal.fire({
        title: 'กำลังเชื่อมต่อและดึงข้อมูล...',
        text: 'กรุณารอสักครู่ ระบบกำลังดึงข้อมูลสดจาก Google Sheet',
        allowOutsideClick: false,
        didOpen: () => { Swal.showLoading(); }
      });

      fetch('/api/sync-ob-bl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          Swal.fire({
            icon: 'success',
            title: 'เชื่อมต่อข้อมูลสำเร็จ!',
            text: `โหลดข้อมูลสำเร็จทั้งหมด ${(data.rows || []).length.toLocaleString()} แถว`,
            timer: 2000,
            showConfirmButton: false
          });
          onData(data);
          fetchFileList();
        } else {
          Swal.fire({
            icon: 'error',
            title: 'ซิงค์ข้อมูลไม่สำเร็จ',
            text: data.error || 'ไม่สามารถดึงข้อมูลจาก URL ที่ระบุได้'
          });
        }
      })
      .catch(err => {
        Swal.fire({
          icon: 'error',
          title: 'เกิดข้อผิดพลาด',
          text: err.message
        });
      });
    }

    function fetchObBlData(filename, force) {
      hideError();
      document.getElementById('content').style.display = 'none';
      document.getElementById('stateMsg').style.display = 'block';
      document.getElementById('exportBtn').disabled = true;

      if (window.google && google.script && google.script.run) {
        if (force) {
          google.script.run.withSuccessHandler(onData).withFailureHandler(onError).forceRefreshObBlData();
        } else {
          google.script.run.withSuccessHandler(onData).withFailureHandler(onError).getObBlData();
        }
        return;
      }

      let apiUrl = '/api/load-ob-bl';
      if (filename) apiUrl += '?filename=' + encodeURIComponent(filename);
      else if (currentFilename) apiUrl += '?filename=' + encodeURIComponent(currentFilename);

      safeFetchJson(apiUrl)
        .then(data => {
          if (data.success) {
            onData(data);
          } else {
            onError({ message: data.error });
          }
        })
        .catch(err => {
          onError({ message: err.message });
        });
    }

    function load() {
      fetchFileList();
      fetchObBlData();
    }

    function forceRefresh() {
      fetchObBlData(null, true);
    }
"""

# Replace original load/forceRefresh JS block
orig_load_pattern = r'function load\(\)\s*\{.*?function forceRefresh\(\)\s*\{.*?\}'
source_content = re.sub(orig_load_pattern, js_api_helpers, source_content, flags=re.DOTALL)

onload_script = """
    window.addEventListener('DOMContentLoaded', () => {
      fetchFileList();
      load();
    });
"""
source_content = source_content.replace("</script>", onload_script + "\n  </script>")

output_file = os.path.join(base_dir, "ob_bl.html")
with open(output_file, "w", encoding="utf-8") as f:
    f.write(source_content)

print(f"Created dedicated ob_bl.html successfully at {output_file}!")
