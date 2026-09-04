import os
import re

print("Building dedicated ob_bl.html from ObBL.html.txt with Skip Monitor Logic & Restored lookupTeam...")

base_dir = r"c:\Users\spxth71637\Desktop\OB Dashboard"
ob_bl_txt_path = os.path.join(base_dir, "OB Late", "ObBL.html.txt")

with open(ob_bl_txt_path, "r", encoding="utf-8") as f:
    source_content = f.read()

# 1. Replace Orange CSS Variables with SOC Blue/Dark Theme
source_content = source_content.replace("--accent: #ee4d2d;", "--accent: #2563eb;")
source_content = source_content.replace("--accent2: #ff7a45;", "--accent2: #3b82f6;")
source_content = source_content.replace("--accent-soft: #fff1eb;", "--accent-soft: #eff6ff;")
source_content = source_content.replace("--bg: #fff9f6;", "--bg: #f8fafc;")
source_content = source_content.replace("--line: #f6ddd2;", "--line: #e2e8f0;")
source_content = source_content.replace("#EE4D2D", "#2563eb")
source_content = source_content.replace("#FF7A45", "#3b82f6")
source_content = source_content.replace("#FFE7DB", "#dbeafe")

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

head_inject = """
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.3.2/papaparse.min.js"></script>
"""

source_content = source_content.replace("</head>", head_inject + "\n</head>")

navbar_html = get_navbar("ob_bl")

custom_header = """
    <!-- Header Banner & Controls (SOC Blue Theme) -->
    <header style="display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; background:linear-gradient(120deg, #0d1b2a, #1e293b); border-radius:14px; padding:16px 22px; color:#fff; box-shadow:0 8px 20px -8px rgba(13,27,42,.4); margin-bottom:14px;">
      <div>
        <h1 style="font-size:21px; margin:0 0 2px; font-weight:800; color:#fff;">📊 OB Backlog (OB BL) Dashboard</h1>
        <div class="subtitle" id="subtitle" style="color:#94a3b8;">ระบบติดตามพัสดุค้าง OB Backlog และวิเคราะห์ตามทีม/ชั่วโมง</div>
      </div>
      <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
        <button onclick="openGoogleSheetModal()" style="background:#10b981; color:#fff; font-weight:700; border:none; padding:8px 14px; border-radius:8px;"><i class="fa-solid fa-link"></i> Sync Google Sheet</button>
        <select id="fileSelectDropdown" onchange="onFileDropdownChange(this.value)" style="padding:7px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.2); background:#1e293b; color:#ffffff; font-weight:700; font-size:13px; max-width:240px;">
          <option value="">-- เลือกไฟล์รายงาน OB BL --</option>
        </select>
        <button id="deleteFileBtn" onclick="deleteSelectedObBlFile()" style="background:#dc2626; color:#fff; font-weight:700; border:none; padding:8px 14px; border-radius:8px; font-size:12px;"><i class="fa-solid fa-trash"></i> ลบไฟล์ที่เลือก</button>
        <button onclick="document.getElementById('csvFileInput').click()" style="background:#2563eb; color:#fff; font-weight:700; border:none; padding:8px 14px; border-radius:8px;"><i class="fa-solid fa-upload"></i> อัปโหลด CSV/Excel</button>
        <input type="file" id="csvFileInput" accept=".csv, .xlsx, .xls" style="display:none;" onchange="handleFileUpload(event)">
        <button id="refreshBtn" onclick="forceRefresh()" style="background:rgba(255,255,255,0.12); color:#ffffff; font-weight:700; border:none; padding:8px 14px; border-radius:8px;">↻ Refresh</button>
        <button id="exportBtn" class="export-btn" disabled style="background:#334155; color:#fff; font-weight:700; border:none; padding:8px 14px; border-radius:8px;">⇩ Export Raw (CSV)</button>
      </div>
    </header>
"""

source_content = source_content.replace("<body>\n  <div class=\"app\">", f"<body>\n{navbar_html}\n  <div class=\"app\">")
source_content = re.sub(r'<header>.*?</header>', custom_header, source_content, flags=re.DOTALL)

# Replace Column Index Building with Fuzzy Alias Matcher
fuzzy_column_matcher = """
    // Fuzzy Alias Matcher for columns so it NEVER fails on missing or renamed headers!
    const FIELD_ALIASES = {
      'shipment_id': ['shipment_id', 'tracking_id', 'tracking_no', 'waybill', 'shipment', 'parcel_id'],
      'route_type': ['route_type', 'route', 'route_name', 'type'],
      'latest_status_timestamp': ['latest_status_timestamp', 'status_timestamp', 'timestamp', 'snap_time', 'time', 'date'],
      'latest_operator_name': ['latest_operator_name', 'operator_name', 'operator', 'email', 'user', 'updated_by', 'recieve_team', 'team'],
      'action_flag': ['action_flag', 'action', 'flag', 'status', 'late_type', 'reason', 'soc_outbound_late_type_2nd_cutoff'],
      'day_in_soc': ['day_in_soc', 'days_in_soc', 'day', 'days'],
      'intentional_backlog_type': ['intentional_backlog_type', 'backlog_type', 'backlog', 'type'],
      'latest_awb_station_name': ['latest_awb_station_name', 'dest_station_name', 'dest_station', 'station_name', 'station', 'hub', 'destination']
    };

    function buildColumnIndex(rawHeaders) {
      const norm = rawHeaders.map(h => (h || '').toString().trim().toLowerCase());
      const idx = {};
      NEEDED_FIELDS.forEach(f => {
        let found = -1;
        const cands = FIELD_ALIASES[f] || [f];
        for (const cand of cands) {
          const i = norm.indexOf(cand.toLowerCase());
          if (i !== -1) { found = i; break; }
        }
        if (found === -1) {
          for (const cand of cands) {
            const i = norm.findIndex(n => n.includes(cand.toLowerCase()));
            if (i !== -1) { found = i; break; }
          }
        }
        idx[f] = found;
      });
      return idx;
    }
"""

source_content = re.sub(r'function buildColumnIndex\(rawHeaders\)\s*\{.*?return idx;\s*\}', fuzzy_column_matcher, source_content, flags=re.DOTALL)

# Replace strict header check in onData
source_content = source_content.replace(
    "if (missing.length > 0) {\n        onError({\n          message: 'ไม่พบคอลัมน์ที่ต้องใช้ในชีต OB BL แถว header: ' + missing.join(', ') +\n            '\\nHeader ที่อ่านได้: ' + rawHeaders.join(' | ')\n        });\n        return;\n      }",
    "// Resilient mode: proceed even if some optional columns are missing"
)

# Resilient lookupTeam and isOBBL replacements while preserving OPERATOR_TEAM_MAP (15,250 operator mappings)
resilient_lookup_team = """
    function lookupTeam(v) {
      if (!v) return '(blank)';
      const norm = normalizeOperator(v);
      if (typeof OPERATOR_TEAM_MAP !== 'undefined' && Object.prototype.hasOwnProperty.call(OPERATOR_TEAM_MAP, norm)) {
        return OPERATOR_TEAM_MAP[norm];
      }
      const upper = String(v).trim().toUpperCase();
      if (upper.includes('INTER')) return 'INTERSOC';
      if (upper.includes('RET')) return 'RETURN';
      if (upper.includes('A')) return 'Zone A';
      if (upper.includes('B')) return 'Zone B';
      if (upper.includes('C')) return 'Zone C';
      return String(v).trim() || 'Unknown';
    }
"""

resilient_is_obbl_fn = """
    function isOBBL(rec) {
      const af = normalizeActionFlag(rec.action_flag);
      if (af && OB_ACTIONS.indexOf(af) === -1) {
        const afLower = af.toLowerCase();
        const matchesOb = OB_ACTIONS.some(a => a.toLowerCase().includes(afLower) || afLower.includes(a.toLowerCase())) ||
                          afLower.includes('packed') || afLower.includes('linehual') || afLower.includes('linehaul') || afLower.includes('rework') || afLower.includes('pending') || afLower.includes('skip');
        if (!matchesOb) return false;
      }

      // Check route_type (If empty, DO NOT REJECT!)
      const rt = (rec.route_type === null || rec.route_type === undefined ? '' : String(rec.route_type)).trim().toUpperCase();
      if (rt && rt !== 'FWD' && rt !== 'FORWARD' && rt !== 'MAIN') {
        if (rt === 'RTS' || rt === 'RET' || rt === 'RETURN') return false;
      }

      // Check intentional_backlog_type (If empty, DO NOT REJECT!)
      const ibt = (rec.intentional_backlog_type === null || rec.intentional_backlog_type === undefined ? '' : String(rec.intentional_backlog_type)).trim().toLowerCase();
      if (ibt && ibt !== 'backlog' && ibt !== 'ob_bl' && ibt !== 'ob backlog') {
        if (ibt.includes('normal') || ibt.includes('regular')) return false;
      }

      // Check day_in_soc (If empty, DO NOT REJECT!)
      if (rec.day_in_soc !== undefined && rec.day_in_soc !== null && String(rec.day_in_soc).trim() !== '') {
        const str = String(rec.day_in_soc).trim().toLowerCase();
        if (str.includes('< 1') || str.includes('under 1') || str.includes('<1')) {
          // Pass under 1 day
        } else {
          const val = parseFloat(str);
          if (!isNaN(val) && val >= 1) return false;
          if (str.includes('2 day') || str.includes('3 day') || str.includes('4 day')) return false;
        }
      }

      return true;
    }
"""

source_content = re.sub(
    r'function lookupTeam\(v\)\s*\{.*?return \'Unknown\';\s*\}',
    resilient_lookup_team,
    source_content,
    flags=re.DOTALL
)

source_content = re.sub(
    r'function isOBBL\(rec\)\s*\{.*?return true;\s*\}',
    resilient_is_obbl_fn,
    source_content,
    flags=re.DOTALL
)

# Dual API & Google Sync System using SAME localStorage key as Skip Monitor
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

    const DEFAULT_OB_BL_SHEET_URL = 'https://script.google.com/a/spxexpress.com/macros/s/AKfycbyluFSbFvnJ_ZDJLZN-rFYVujOnQRIlxf1KQKlS9eYNrw/exec';

    function openGoogleSheetModal() {
      const savedUrl = localStorage.getItem('socn_google_sheet_url') || localStorage.getItem('socn_google_sheet_obbl_url') || DEFAULT_OB_BL_SHEET_URL;
      Swal.fire({
        title: '🔗 ดึงข้อมูลสดจาก Apps Script / Google Sheet',
        html: `
          <p class="text-start small text-muted mb-2">กรอก URL ของ Google Apps Script Web App หรือ Google Sheet URL ที่มีข้อมูล OB BL:</p>
          <input id="swal-gs-url" class="swal2-input" placeholder="https://script.google.com/macros/s/.../exec หรือ Google Sheet URL" value="${savedUrl}">
        `,
        showCancelButton: true,
        confirmButtonText: '⚡ ดึงข้อมูลสดทันที',
        cancelButtonText: 'ยกเลิก',
        confirmButtonColor: '#10b981',
        background: '#0d1b2a',
        color: '#ffffff',
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

    function convertToDirectCsvUrl(url) {
      if (!url) return '';
      let u = url.trim();
      const gidMatch = u.match(/gid=([0-9]+)/);
      const gidParam = gidMatch ? `&gid=${gidMatch[1]}` : '';

      if (u.includes('/pubhtml')) {
        let base = u.replace('/pubhtml', '/pub?output=csv');
        if (gidMatch && !base.includes('gid=')) {
          base += `&gid=${gidMatch[1]}`;
        }
        return base;
      }
      if (u.includes('docs.google.com/spreadsheets')) {
        if (u.includes('gviz/tq') || u.includes('output=csv') || u.includes('export?format=csv')) {
          return u;
        }
        const match = u.match(/\/d\/e\/([a-zA-Z0-9-_]+)/) || u.match(/\/d\/([a-zA-Z0-9-_]+)/);
        if (match) {
          return `https://docs.google.com/spreadsheets/d/${match[1]}/gviz/tq?tqx=out:csv${gidParam}`;
        }
      }
      return u;
    }

    function syncGoogleSheetUrl(url) {
      localStorage.setItem('socn_google_sheet_url', url);
      localStorage.setItem('socn_google_sheet_obbl_url', url);

      Swal.fire({
        title: 'กำลังเชื่อมต่อและดึงข้อมูลสด...',
        text: 'กรุณารอสักครู่ ระบบกำลังดึงข้อมูลสดเข้าสู่ระบบ',
        allowOutsideClick: false,
        background: '#0d1b2a',
        color: '#ffffff',
        didOpen: () => { Swal.showLoading(); }
      });

      if (url.includes('script.google.com') || url.includes('/exec') || url.includes('/dev')) {
        let fetchUrl = url;
        if (!fetchUrl.includes('page=obbl')) {
          fetchUrl += (fetchUrl.includes('?') ? '&' : '?') + 'page=obbl';
        }
        fetch(fetchUrl)
          .then(res => res.json())
          .then(data => {
            if (data && (data.rows || data.data || data.headers || data.success)) {
              Swal.fire({
                icon: 'success',
                title: 'ซิงค์ข้อมูลสดสำเร็จ!',
                text: `ดึงข้อมูลสดสำเร็จทั้งหมด ${(data.rows || data.data || []).length.toLocaleString()} แถว`,
                timer: 2000,
                showConfirmButton: false,
                background: '#0d1b2a',
                color: '#ffffff'
              });
              onData(data);
              fetchFileList();
            } else {
              fallbackToServerSync(url);
            }
          })
          .catch(() => fallbackToServerSync(url));
        return;
      }

      const directCsvUrl = convertToDirectCsvUrl(url);

      Papa.parse(directCsvUrl, {
        download: true,
        skipEmptyLines: true,
        complete: function(results) {
          if (results && results.data && results.data.length > 0) {
            const rows = results.data;
            const headers = rows[0];
            const dataRows = rows.slice(1);

            const firstCell = String(headers[0] || '');
            if (firstCell.includes('<!DOCTYPE') || firstCell.includes('<html') || firstCell.includes('Sign in')) {
              fallbackToServerSync(url);
              return;
            }

            const dataObj = {
              success: true,
              headers: headers,
              rows: dataRows,
              generatedAt: new Date().toLocaleString()
            };

            Swal.fire({
              icon: 'success',
              title: 'ซิงค์ข้อมูลสำเร็จ!',
              text: `ดึงข้อมูลสดผ่านสิทธิ์ Shopee Mobile สำเร็จทั้งหมด ${dataRows.length.toLocaleString()} แถว`,
              timer: 2000,
              showConfirmButton: false
            });

            onData(dataObj);
            fetchFileList();

            fetch('/api/sync-google-sheet', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ url: url })
            }).catch(() => {});
          } else {
            fallbackToServerSync(url);
          }
        },
        error: function() {
          fallbackToServerSync(url);
        }
      });
    }

    function fallbackToServerSync(url) {
      fetch('/api/sync-google-sheet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          Swal.fire({ icon: 'success', title: 'เชื่อมต่อข้อมูลสำเร็จ!', timer: 2000, showConfirmButton: false });
          fetchObBlData();
          fetchFileList();
        } else {
          Swal.fire({
            icon: 'error',
            title: 'ซิงค์ข้อมูลไม่สำเร็จ',
            text: data.error || 'ไม่สามารถดึงข้อมูลจาก URL ที่ระบุได้'
          });
        }
      })
      .catch(err => Swal.fire({ icon: 'error', title: 'เกิดข้อผิดพลาด', text: err.message }));
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

orig_load_pattern = r'function load\(\)\s*\{.*?function forceRefresh\(\)\s*\{.*?\}'
source_content = re.sub(orig_load_pattern, js_api_helpers, source_content, flags=re.DOTALL)

onload_script = """
    window.addEventListener('DOMContentLoaded', () => {
      fetchFileList();
      const savedGsUrl = localStorage.getItem('socn_google_sheet_url') || localStorage.getItem('socn_google_sheet_obbl_url') || DEFAULT_OB_BL_SHEET_URL;
      if (savedGsUrl) {
        syncGoogleSheetUrl(savedGsUrl);
      } else {
        load();
      }
    });
"""
source_content = source_content.replace("</script>", onload_script + "\n  </script>")

output_file = os.path.join(base_dir, "ob_bl.html")
with open(output_file, "w", encoding="utf-8") as f:
    f.write(source_content)

print(f"Updated ob_bl.html with restored lookupTeam and Skip Monitor logic successfully at {output_file}!")
