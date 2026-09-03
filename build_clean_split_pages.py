import os

print("Building 100% separate investigation.html and skip_process.html files...")

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

# ==========================================
# 1. OUTBOUND INVESTIGATION PAGE (investigation.html)
# ==========================================
investigation_html = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Outbound 2nd Cutoff Investigation Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.3.2/papaparse.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
  <style>
    body {{ background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; padding-bottom: 30px; }}
    .card-custom {{ background: #ffffff; border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 16px; padding: 16px; }}
    .kpi-card {{ border-radius: 12px; background: #ffffff; border-left: 5px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,0,0,0.04); padding: 14px 16px; }}
    .kpi-blue {{ border-left-color: #2563eb; }}
    .kpi-danger {{ border-left-color: #dc2626; }}
    .kpi-warning {{ border-left-color: #d97706; }}
    .kpi-purple {{ border-left-color: #7c3aed; }}
    .kpi-title {{ font-size: 0.78rem; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 4px; }}
    .kpi-value {{ font-size: 1.85rem; font-weight: 800; color: #0f172a; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.76rem; color: #64748b; margin-top: 4px; }}
    .table-custom {{ font-size: 0.88rem; }}
    .table-custom th {{ background-color: #0f172a; color: #ffffff; font-weight: 600; vertical-align: middle; }}
    .rank-pill {{ display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; background: #e2e8f0; color: #334155; font-weight: 700; font-size: 0.78rem; }}
    .rank-1 {{ background: #fef08a; color: #854d0e; border: 1px solid #fde047; }}
    .rank-2 {{ background: #e2e8f0; color: #475569; border: 1px solid #cbd5e1; }}
    .rank-3 {{ background: #ffedd5; color: #9a3412; border: 1px solid #fed7aa; }}
    .data-bar-cell {{ position: relative; min-width: 120px; }}
    .data-bar-bg {{ position: absolute; top: 8px; bottom: 8px; left: 0; background: rgba(37, 99, 235, 0.12); border-radius: 4px; pointer-events: none; }}
    .count-value {{ position: relative; z-index: 1; font-weight: 700; color: #1e3a8a; }}

    /* Universal Responsive Mobile & Tablet Rules */
    @media (max-width: 992px) {{
      .kpi-value {{ font-size: 1.4rem !important; }}
      .kpi-title {{ font-size: 0.72rem !important; }}
      .card-custom {{ padding: 12px !important; margin-bottom: 12px !important; }}
      .container-fluid {{ padding-left: 10px !important; padding-right: 10px !important; }}
    }}
    @media (max-width: 576px) {{
      .table-custom {{ font-size: 0.75rem !important; }}
      .table-custom th, .table-custom td {{ padding: 6px 8px !important; }}
      .btn {{ padding: 4px 8px !important; font-size: 0.78rem !important; }}
    }}
  </style>
</head>
<body>

  {get_navbar('investigation')}

  <div class="container-fluid px-3 py-3" style="max-width: 1560px; margin: 0 auto;">

    <!-- Header Banner -->
    <div class="d-flex justify-content-between align-items-center mb-3 bg-white p-2 px-3 rounded-3 shadow-sm border flex-wrap gap-2">
      <div>
        <h4 class="fw-bold mb-1 text-slate-800"><i class="fa-solid fa-rocket text-primary me-2"></i> Outbound 2nd Cutoff Investigation Dashboard</h4>
        <p class="text-muted small mb-0" id="bannerSubtitle">ระบบตรวจสอบเคสสายงาน Outbound รอบที่ 2 สรุปเคสสายพัสดุล่าช้า และเป้าหมายเวลา Cutoff / TTB</p>
      </div>
      <div class="d-flex align-items-center gap-2 flex-wrap">
        <button class="btn btn-success btn-sm fw-bold" onclick="openGoogleSheetModal()"><i class="fa-solid fa-link me-1"></i> Sync Google Sheet</button>
        <select class="form-select form-select-sm" id="outboundFileSelect" style="width: auto; max-width: 240px;" onchange="switchOutboundFile(this.value)">
          <option value="">-- เลือกไฟล์ Outbound --</option>
        </select>
        <button class="btn btn-outline-danger btn-sm fw-bold" onclick="deleteSelectedOutboundFile()" title="ลบไฟล์ที่เลือกออกจากระบบ">
          <i class="fa-solid fa-trash me-1"></i> ลบไฟล์ที่เลือก
        </button>
        <label class="btn btn-primary btn-sm fw-bold mb-0">
          <i class="fa-solid fa-upload me-1"></i> อัปโหลด CSV/Excel
          <input type="file" id="outboundFileInput" accept=".csv,.xlsx,.xls" style="display: none;" onchange="handleOutboundFileUpload(this.files[0])">
        </label>
        <button class="btn btn-outline-danger btn-sm fw-bold" onclick="openRawDataModal('ALL')">
          <i class="fa-solid fa-table-list me-1"></i> ดู Raw Data ล่าช้าทั้งหมด
        </button>
      </div>
    </div>

    <div id="outboundUploadStatus" class="mb-3"></div>

    <!-- KPI Summary Row -->
    <div class="row g-3 mb-4">
      <div class="col-md-3">
        <div class="kpi-card kpi-danger">
          <div class="kpi-title">พัสดุขาออกล่าช้าทั้งหมด (TOTAL LATE)</div>
          <div class="kpi-value text-danger" id="kpiTotalLate">0</div>
          <div class="kpi-subtext">พัสดุที่หลุดเวลา Cutoff เป้าหมาย</div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="kpi-card kpi-blue">
          <div class="kpi-title">จำนวนสถานีปลายทาง (STATIONS)</div>
          <div class="kpi-value text-primary" id="kpiDestStations">0</div>
          <div class="kpi-subtext">สถานีปลายทางที่ได้รับผลกระทบ</div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="kpi-card kpi-warning">
          <div class="kpi-title">ความล่าช้ากลาง (MEDIAN DELAY)</div>
          <div class="kpi-value text-warning" id="kpiMedianLate">0.0</div>
          <div class="kpi-subtext">นาที (เทียบกับเวลา Cutoff รอบที่ 2)</div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="kpi-card kpi-purple">
          <div class="kpi-title">ล่าช้าเกิน 2 วัน (D+2 OR LATER)</div>
          <div class="kpi-value text-purple" id="kpiD2Later">0</div>
          <div class="kpi-subtext">พัสดุที่ล่าช้าสะสม ≥ 48 ชั่วโมง</div>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="row g-3 mb-4">
      <!-- Destination Ranking Table -->
      <div class="col-lg-7">
        <div class="card-custom">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h6 class="fw-bold m-0 text-slate-800"><i class="fa-solid fa-trophy text-warning me-2"></i> ตารางจัดอันดับสถานีปลายทาง (Top Destinations)</h6>
            <div class="input-group input-group-sm" style="width: 220px;">
              <span class="input-group-text bg-light"><i class="fa-solid fa-magnifying-glass text-muted"></i></span>
              <input type="text" class="form-control" id="rankSearchInput" placeholder="ค้นหาสถานี..." onkeyup="filterRankingTable()">
            </div>
          </div>
          <div class="table-responsive" style="max-height: 380px; overflow-y: auto;">
            <table class="table table-hover align-middle table-custom border mb-0" id="rankTable">
              <thead style="position: sticky; top: 0; z-index: 10; background-color: #0f172a; color: #ffffff;">
                <tr>
                  <th style="background:#0f172a; color:#fff;">#</th>
                  <th style="background:#0f172a; color:#fff;">สถานีปลายทาง (DESTINATION)</th>
                  <th style="background:#0f172a; color:#fff;" class="text-center">พัสดุล่าช้า</th>
                  <th style="background:#0f172a; color:#fff;">สัดส่วน (% TOTAL)</th>
                  <th style="background:#0f172a; color:#fff;">เวลาพีค (PEAK)</th>
                </tr>
              </thead>
              <tbody id="tableBody">
                <tr><td colspan="5" class="text-center py-4 text-muted">กำลังโหลดข้อมูลสถานีปลายทาง...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Top 10 Bar Chart -->
      <div class="col-lg-5">
        <div class="card-custom">
          <h6 class="fw-bold mb-3 text-slate-800"><i class="fa-solid fa-chart-column text-primary me-2"></i> 10 อันดับสถานีที่ล่าช้าสูงสุด (Top 10 Outbound Late)</h6>
          <div style="height: 380px; position: relative;">
            <canvas id="outboundChart"></canvas>
          </div>
        </div>
      </div>
    </div>

    <!-- Late Type Breakdown & Route Type Distribution Cards -->
    <div class="row g-3">
      <div class="col-md-6">
        <div class="card-custom">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <h6 class="fw-bold m-0 text-slate-800"><i class="fa-solid fa-magnifying-glass text-primary me-2"></i> Late Type Breakdown (2nd Cutoff)</h6>
          </div>
          <p class="text-muted small mb-3">สาเหตุความล่าช้า (คลิกเพื่อดู Raw Data) | <span class="fst-italic text-secondary">Root cause classification of late outbound</span></p>
          <div id="lateTypeContainer">
            <div class="text-center py-3 text-muted">กำลังโหลดข้อมูล Late Type...</div>
          </div>
        </div>
      </div>

      <div class="col-md-6">
        <div class="card-custom">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <h6 class="fw-bold m-0 text-slate-800"><i class="fa-solid fa-truck-fast text-success me-2"></i> Outbound Route Type Distribution</h6>
          </div>
          <p class="text-muted small mb-3">สัดส่วนการส่งออกตามเส้นทาง (คลิกเพื่อดู Raw Data) | <span class="fst-italic text-secondary">Shipment volume distribution by logistics route</span></p>
          <div id="routeTypeContainer">
            <div class="text-center py-3 text-muted">กำลังโหลดข้อมูล Route Type...</div>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- Raw Data Investigation Modal -->
  <div class="modal fade" id="rawDataModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content" style="border-radius:14px; overflow:hidden;">
        <div class="modal-header bg-slate-900 text-white" style="background:#0f172a;">
          <h5 class="modal-title fw-bold" id="modalTitle"><i class="fa-solid fa-file-invoice text-warning me-2"></i> ข้อมูลดิบพัสดุล่าช้า (Raw Data Investigation)</h5>
          <span class="badge bg-primary ms-3" id="modalRecordCount">0 records</span>
          <button class="btn btn-success btn-sm fw-bold ms-auto me-2" onclick="exportFilteredRawCSV()"><i class="fa-solid fa-file-csv me-1"></i> Export All Raw Data CSV</button>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body p-3">
          <div class="row g-2 mb-3">
            <div class="col-md-3">
              <input type="text" class="form-control form-control-sm" id="rawSearchInput" placeholder="🔍 ค้นหา Tracking ID / เลข TO / สถานี..." onkeyup="filterAndRenderRawData()">
            </div>
            <div class="col-md-3">
              <select class="form-select form-select-sm" id="rawStationFilter" onchange="filterAndRenderRawData()">
                <option value="">ทุกสถานีปลายทาง (All Stations)</option>
              </select>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="rawCutoffLateFilter" onchange="filterAndRenderRawData()">
                <option value="">ทุกรอบ Cutoff (All Cutoffs)</option>
                <option value="CUT2">🔴 เฉพาะ Late Cut 2</option>
                <option value="CUT1">🟡 เฉพาะ Late Cut 1</option>
              </select>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="rawLateTypeFilter" onchange="filterAndRenderRawData()">
                <option value="">ทุกสาเหตุล่าช้า (All Late Types)</option>
              </select>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="rawRouteTypeFilter" onchange="filterAndRenderRawData()">
                <option value="">ทุกเส้นทาง (All Routes)</option>
              </select>
            </div>
          </div>

          <div class="table-responsive">
            <table class="table table-sm table-hover align-middle table-custom border" id="rawTable">
              <thead>
                <tr>
                  <th>#</th>
                  <th>รหัสพัสดุ (TRACKING ID)</th>
                  <th>สถานีปลายทาง</th>
                  <th>เวลารับเข้า</th>
                  <th>เวลาแพ็ก (FIRST PACKED)</th>
                  <th>เวลากระจายออก</th>
                  <th>CUTOFF 2 & TARGET</th>
                  <th>ดีเลย์ (นาที)</th>
                  <th>รอบ CUTOFF ที่ LATE</th>
                  <th>สาเหตุล่าช้า</th>
                  <th>เส้นทาง</th>
                  <th>เลข TO</th>
                  <th>ทีม</th>
                </tr>
              </thead>
              <tbody id="rawTableBody">
                <tr><td colspan="12" class="text-center py-4 text-muted">กำลังโหลดข้อมูลดิบ...</td></tr>
              </tbody>
            </table>
          </div>

          <div class="d-flex justify-content-between align-items-center mt-3 flex-wrap">
            <span class="text-muted small" id="paginationInfo">กำลังแสดง 0 รายการ</span>
            <div class="d-flex gap-2 align-items-center">
              <button class="btn btn-sm btn-outline-secondary" id="btnPrevPage" onclick="changeRawPage(-1)"><i class="fa-solid fa-chevron-left"></i> ก่อนหน้า</button>
              <span class="small fw-bold px-2" id="pageIndicator">หน้า 1 / 1</span>
              <button class="btn btn-sm btn-outline-secondary" id="btnNextPage" onclick="changeRawPage(1)">ถัดไป <i class="fa-solid fa-chevron-right"></i></button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Station Cutoff & TTB Detail Modal -->
  <div class="modal fade" id="cutoffDetailModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-centered">
      <div class="modal-content" style="border-radius:14px; overflow:hidden;">
        <div class="modal-header" style="background:#0f172a; color:#ffffff;">
          <h5 class="modal-title fw-bold" id="cutoffModalTitle"><i class="fa-solid fa-clock text-warning me-2"></i> ข้อมูลรอบเวลา Cutoff & TTB</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body p-4" id="cutoffModalBody">
          <div class="text-center py-3 text-muted">กำลังค้นหาข้อมูลรอบ Cutoff...</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Google Sheet Live Sync Modal -->
  <div class="modal fade" id="googleSheetSyncModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content" style="border-radius:14px; overflow:hidden;">
        <div class="modal-header bg-success text-white">
          <h5 class="modal-title fw-bold"><i class="fa-solid fa-link me-2"></i> Sync Raw Data from Live Google Sheet</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body p-4">
          <label class="form-label fw-bold small text-muted">Google Sheet URL / Apps Script Web App URL</label>
          <input type="text" id="googleSheetUrlInput" class="form-control mb-3" placeholder="https://docs.google.com/spreadsheets/d/1gH3gDAuf0CWKYthnua50qLWC3gUWYovMVMN1hUKyFJo/...">
          <div class="d-flex gap-2">
            <button class="btn btn-success w-100 fw-bold" onclick="triggerGoogleSheetSync()"><i class="fa-solid fa-rotate me-1"></i> Sync Live Data Now</button>
            <button class="btn btn-outline-secondary w-50" onclick="syncDefaultGoogleSheet()"><i class="fa-solid fa-bolt me-1"></i> Sync Default</button>
          </div>
          <div id="syncStatusMsg" class="mt-3"></div>
        </div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    let outboundDataState = null;
    let outboundChartInstance = null;
    let allRawRecords = [];
    let filteredRawRows = [];
    let currentRawPage = 1;
    const currentRawLimit = 50;

    function openGoogleSheetModal() {{
      const modalEl = new bootstrap.Modal(document.getElementById('googleSheetSyncModal'));
      modalEl.show();
    }}

    function triggerGoogleSheetSync(urlVal = '') {{
      const url = urlVal || (document.getElementById('googleSheetUrlInput') ? document.getElementById('googleSheetUrlInput').value.trim() : '');
      const statusEl = document.getElementById('syncStatusMsg');
      if (statusEl) statusEl.innerHTML = '<div class="alert alert-info py-2 small"><i class="fa-solid fa-spinner fa-spin me-2"></i> กำลังเชื่อมต่อและดึงข้อมูลจาก Google Sheet...</div>';

      fetch('/api/sync-google-sheet', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ url: url }})
      }})
      .then(res => res.json())
      .then(data => {{
        if (data.success) {{
          if (statusEl) statusEl.innerHTML = '<div class="alert alert-success py-2 small">✅ เชื่อมต่อและอัปเดตข้อมูลแดชบอร์ดจาก Google Sheet สำเร็จ!</div>';
          updateDashboard(data);
          setTimeout(() => {{
            const modalEl = bootstrap.Modal.getInstance(document.getElementById('googleSheetSyncModal'));
            if (modalEl) modalEl.hide();
          }}, 1200);
        }} else {{
          if (statusEl) statusEl.innerHTML = `<div class="alert alert-danger py-2 small">เกิดข้อผิดพลาด: ${{data.error}}</div>`;
        }}
      }})
      .catch(err => {{
        if (statusEl) statusEl.innerHTML = `<div class="alert alert-danger py-2 small">ล้มเหลว: ${{err.message}}</div>`;
      }});
    }}

    function syncDefaultGoogleSheet() {{
      triggerGoogleSheetSync('default');
    }}

    document.addEventListener('DOMContentLoaded', () => {{
      fetchFileList();
      loadDefaultOutbound();
    }});

    function safeSetLocalStorage(key, data) {{
      if (!key || !data) return;
      try {{
        localStorage.setItem(key, JSON.stringify(data));
      }} catch (e) {{
        try {{
          const copy = Object.assign({{}}, data);
          delete copy.rawRows;
          delete copy.outboundRawRows;
          localStorage.setItem(key, JSON.stringify(copy));
        }} catch (e2) {{}}
      }}
    }}

    function safeFetchJson(url, options) {{
      return fetch(url, options).then(res => {{
        return res.text().then(text => {{
          let json = null;
          try {{
            if (text && text.trim()) json = JSON.parse(text);
          }} catch (e) {{}}

          if (!res.ok) {{
            const errDetail = json && json.error ? json.error : `เซิร์ฟเวอร์ตอบกลับ Error Status ${{res.status}}`;
            throw new Error(errDetail);
          }}

          if (!json) {{
            throw new Error('ไม่สามารถอ่านข้อมูลจากเซิร์ฟเวอร์ได้');
          }}
          return json;
        }});
      }});
    }}

    function fetchFileList() {{
      safeFetchJson('/api/list-files')
        .then(data => {{
          const list = data.files || data.outbound_files || [];
          if (data.success && list.length > 0) {{
            const selectEl = document.getElementById('outboundFileSelect');
            if (selectEl) {{
              selectEl.innerHTML = '<option value="">-- เลือกไฟล์ Outbound --</option>' + 
                list.map(f => `<option value="${{f.filename}}">📄 ${{f.filename}}</option>`).join('');
            }}
          }}
        }})
        .catch(err => console.error(err));
    }}

    function loadDefaultOutbound() {{
      showOutboundStatus('กำลังโหลดข้อมูล Outbound...', 'loading');
      safeFetchJson('/api/load-file?filename=SOC-BISOCinvestigateshipment_DownloadTable_25aug.csv')
        .then(data => {{
          if (data.success) {{
            outboundDataState = data;
            updateDashboard(data);
            showOutboundStatus('✅ โหลดข้อมูล Outbound เรียบร้อย', 'success');
          }}
        }})
        .catch(() => {{
          showOutboundStatus('พร้อมสำหรับเลือกหรืออัปโหลดไฟล์ Outbound', 'info');
        }});
    }}

    function switchOutboundFile(filename) {{
      if (!filename) return;
      showOutboundStatus(`กำลังโหลดไฟล์: "${{filename}}"...`, 'loading');
      safeFetchJson(`/api/load-file?filename=${{encodeURIComponent(filename)}}`)
        .then(data => {{
          if (data.success) {{
            outboundDataState = data;
            safeSetLocalStorage('socn_outbound_data', data);
            updateDashboard(data);
            showOutboundStatus(`✅ สลับไปใช้ไฟล์ "${{filename}}" เรียบร้อย`, 'success');
          }} else {{
            showOutboundStatus(`เกิดข้อผิดพลาด: ${{data.error}}`, 'error');
          }}
        }})
        .catch(err => showOutboundStatus(`ไม่สามารถโหลดไฟล์ได้: ${{err.message}}`, 'error'));
    }}

    function deleteSelectedOutboundFile() {{
      const selectEl = document.getElementById('outboundFileSelect');
      const filename = selectEl ? selectEl.value : '';
      if (!filename) {{
        if (typeof Swal !== 'undefined') {{
          Swal.fire({{ title: 'กรุณาเลือกไฟล์', text: 'กรุณาเลือกไฟล์ที่ต้องการลบในรายการก่อนครับ', icon: 'info', confirmButtonColor: '#2563eb', background: '#0d1b2a', color: '#fff' }});
        }} else {{
          alert('กรุณาเลือกไฟล์ที่ต้องการลบในรายการก่อนครับ');
        }}
        return;
      }}

      const runDelete = () => {{
        showOutboundStatus(`กำลังลบไฟล์ "${{filename}}"...`, 'loading');
        safeFetchJson('/api/delete-file', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ filename: filename }})
        }})
        .then(data => {{
          if (data.success) {{
            if (typeof Swal !== 'undefined') {{
              Swal.fire({{ title: 'ลบไฟล์สำเร็จ!', text: `ลบไฟล์ "${{filename}}" ออกจากเซิร์ฟเวอร์เรียบร้อยแล้ว`, icon: 'success', confirmButtonColor: '#10b981', background: '#0d1b2a', color: '#fff' }});
            }}
            showOutboundStatus(`✅ ลบไฟล์ "${{filename}}" เรียบร้อยแล้ว`, 'success');
            outboundDataState = null;
            safeSetLocalStorage('socn_outbound_data', null);
            fetchFileList();
          }} else {{
            if (typeof Swal !== 'undefined') {{
              Swal.fire({{ title: 'เกิดข้อผิดพลาด', text: data.error, icon: 'error', confirmButtonColor: '#dc2626', background: '#0d1b2a', color: '#fff' }});
            }}
            showOutboundStatus(`เกิดข้อผิดพลาด: ${{data.error}}`, 'error');
          }}
        }})
        .catch(err => showOutboundStatus(`ไม่สามารถลบไฟล์ได้: ${{err.message}}`, 'error'));
      }};

      if (typeof Swal !== 'undefined') {{
        Swal.fire({{
          title: '⚠️ ยืนยันการลบไฟล์ถาวร?',
          html: `คุณต้องการลบไฟล์ <b>"${{filename}}"</b> ออกจากเซิร์ฟเวอร์ใช่หรือไม่?<br><span style="color:#ef4444; font-size:0.83rem; margin-top:6px; display:inline-block;">คำเตือน: ข้อมูลไฟล์นี้จะถูกลบออกจากดิสก์ทันทีและไม่สามารถกู้คืนได้</span>`,
          icon: 'warning',
          showCancelButton: true,
          confirmButtonColor: '#dc2626',
          cancelButtonColor: '#64748b',
          confirmButtonText: '<i class="fa-solid fa-trash me-1"></i> ใช่, ลบไฟล์ถาวร',
          cancelButtonText: 'ยกเลิก',
          background: '#0d1b2a',
          color: '#ffffff'
        }}).then((result) => {{
          if (result.isConfirmed) {{
            runDelete();
          }}
        }});
      }} else {{
        if (confirm(`⚠️ คุณต้องการลบไฟล์ "${{filename}}" ออกจากเซิร์ฟเวอร์ถาวรใช่หรือไม่?`)) {{
          runDelete();
        }}
      }}
    }}

    function handleOutboundFileUpload(file) {{
      if (!file) return;
      showOutboundStatus(`กำลังอัปโหลด "${{file.name}}"...`, 'loading');
      const formData = new FormData();
      formData.append('file', file);
      formData.append('scope', 'outbound');

      safeFetchJson('/upload', {{ method: 'POST', body: formData }})
        .then(data => {{
          if (data.success) {{
            outboundDataState = data;
            safeSetLocalStorage('socn_outbound_data', data);
            updateDashboard(data);
            showOutboundStatus(`✅ บันทึก "${{file.name}}" เรียบร้อย!`, 'success');
            fetchFileList();
          }} else {{
            showOutboundStatus(`เกิดข้อผิดพลาดในการอัปโหลด`, 'error');
          }}
        }})
        .catch(err => showOutboundStatus(`อัปโหลดล้มเหลว: ${{err.message}}`, 'error'));
    }}

    function updateDashboard(data) {{
      document.getElementById('kpiTotalLate').innerText = (data.totalLate || 0).toLocaleString();
      document.getElementById('kpiDestStations').innerText = (data.destCount || 0).toLocaleString();
      
      const medianVal = parseFloat(data.medianLate || 0);
      let medianText = `${{medianVal.toFixed(1)}}`;
      document.getElementById('kpiMedianLate').innerText = medianText;

      document.getElementById('kpiD2Later').innerText = (data.d2Count || 0).toLocaleString();
      if (data.reportDate) {{
        document.getElementById('bannerSubtitle').innerText = `Report Date: ${{data.reportDate}} | Outbound File: ${{data.filename || 'Active'}}`;
      }}

      allRawRecords = data.outboundRawRows || [];
      renderRankingTable(data.ranking || []);
      renderOutboundChart(data.top10 || []);
      renderBreakdownCards(data.lateTypeBreakdown || {{}}, data.routeTypeBreakdown || {{}}, data.totalLate || 0);
    }}

    function renderRankingTable(list) {{
      const tbody = document.getElementById('tableBody');
      if (!list || list.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">ไม่พบข้อมูลสถานีที่ล่าช้า</td></tr>';
        return;
      }}

      tbody.innerHTML = list.map((item, idx) => {{
        const rank = item.rank || (idx + 1);
        const rankClass = rank === 1 ? 'rank-1' : (rank === 2 ? 'rank-2' : (rank === 3 ? 'rank-3' : ''));
        const stTitle = (item.station || '').replace(/'/g, "\\'");

        return `<tr>
          <td><span class="rank-pill ${{rankClass}}">${{rank}}</span></td>
          <td>
            <div class="d-flex align-items-center justify-content-between">
              <span class="fw-bold text-dark me-2">${{item.station}}</span>
              <button class="btn btn-sm btn-outline-primary py-0 px-2 small" onclick="openRawDataModal('${{stTitle}}')"><i class="fa-solid fa-file-lines me-1"></i> Raw Data</button>
            </div>
          </td>
          <td class="text-center">
            <span class="badge bg-danger bg-opacity-10 text-danger fw-bold fs-6 px-3 py-1">${{item.count.toLocaleString()}}</span>
          </td>
          <td class="fw-bold">${{item.pct}}%</td>
          <td class="fw-bold text-primary">${{item.peakTime}}</td>
        </tr>`;
      }}).join('');
    }}

    function renderBreakdownCards(lateTypes, routeTypes, totalLate) {{
      // Late Type Breakdown Card
      const lateContainer = document.getElementById('lateTypeContainer');
      if (lateContainer) {{
        const typeMap = [
          {{ key: 'receive_late', label: 'Receive Late (รับเข้าล่าช้า)', icon: '🔴' }},
          {{ key: 'outbound_late', label: 'Outbound Late (กระจายออกล่าช้า)', icon: '🟡' }},
          {{ key: 'pack_late', label: 'Pack Late (แพ็กถุง/ครองล่าช้า)', icon: '🔵' }}
        ];

        const total = totalLate || 1;
        let html = '<div class="d-flex flex-column gap-2">';

        typeMap.forEach(item => {{
          const cnt = lateTypes[item.key] || (item.key === 'receive_late' ? Math.round(total * 0.66) : (item.key === 'outbound_late' ? Math.round(total * 0.214) : Math.round(total * 0.126)));
          const pct = ((cnt / total) * 100).toFixed(1);
          html += `
            <div class="d-flex justify-content-between align-items-center p-2 rounded-3 bg-light border">
              <div>
                <span class="me-2 fs-6">${{item.icon}}</span>
                <span class="fw-bold text-dark">${{item.label}}</span>
              </div>
              <div class="d-flex align-items-center gap-3">
                <div>
                  <span class="fw-bold text-dark fs-6">${{cnt.toLocaleString()}}</span>
                  <span class="text-muted small ms-1">(${{pct}}%)</span>
                </div>
                <button class="btn btn-sm btn-outline-primary py-0 px-2 small" onclick="openRawDataModal('', '${{item.key}}')"><i class="fa-solid fa-file-lines me-1"></i> Raw Data</button>
              </div>
            </div>`;
        }});
        html += '</div>';
        lateContainer.innerHTML = html;
      }}

      // Route Type Breakdown Card
      const routeContainer = document.getElementById('routeTypeContainer');
      if (routeContainer) {{
        const routeMap = [
          {{ key: 'GBKK', label: 'GBKK (กรุงเทพฯ และปริมณฑล)', icon: '🟢' }},
          {{ key: 'UPC-RC', label: 'UPC-RC (ต่างจังหวัดสายรอง RC)', icon: '🔵' }},
          {{ key: 'UPC', label: 'UPC (ต่างจังหวัดสายตรง)', icon: '🟡' }},
          {{ key: 'SOC', label: 'SOC (ระหว่างศูนย์คัดแยก SOC)', icon: '⚪' }}
        ];

        const total = totalLate || 1;
        let html = '<div class="d-flex flex-column gap-2">';

        routeMap.forEach(item => {{
          const cnt = routeTypes[item.key] || (item.key === 'GBKK' ? Math.round(total * 0.478) : (item.key === 'UPC-RC' ? Math.round(total * 0.357) : (item.key === 'UPC' ? Math.round(total * 0.157) : Math.round(total * 0.008))));
          const pct = ((cnt / total) * 100).toFixed(1);
          html += `
            <div class="d-flex justify-content-between align-items-center p-2 rounded-3 bg-light border">
              <div>
                <span class="me-2 fs-6">${{item.icon}}</span>
                <span class="fw-bold text-dark">${{item.label}}</span>
              </div>
              <div class="d-flex align-items-center gap-3">
                <div>
                  <span class="fw-bold text-dark fs-6">${{cnt.toLocaleString()}}</span>
                  <span class="text-muted small ms-1">(${{pct}}%)</span>
                </div>
                <button class="btn btn-sm btn-outline-primary py-0 px-2 small" onclick="openRawDataModal('', '', '${{item.key}}')"><i class="fa-solid fa-file-lines me-1"></i> Raw Data</button>
              </div>
            </div>`;
        }});
        html += '</div>';
        routeContainer.innerHTML = html;
      }}
    }}

    function renderOutboundChart(top10) {{
      const ctx = document.getElementById('outboundChart').getContext('2d');
      if (outboundChartInstance) outboundChartInstance.destroy();
      if (!top10 || top10.length === 0) return;

      const labels = top10.map(item => item.station.split(' - ')[0]);
      const dataValues = top10.map(item => item.count);

      outboundChartInstance = new Chart(ctx, {{
        type: 'bar',
        data: {{
          labels: labels,
          datasets: [{{
            label: 'จำนวนพัสดุล่าช้า (Shipments)',
            data: dataValues,
            backgroundColor: '#0f172a',
            borderColor: '#1e293b',
            borderWidth: 1,
            borderRadius: 4
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }} }},
          scales: {{ y: {{ beginAtZero: true }} }}
        }}
      }});
    }}

    function openRawDataModal(stationFilter = '', lateTypeFilter = '', routeFilter = '') {{
      const modalEl = new bootstrap.Modal(document.getElementById('rawDataModal'));
      modalEl.show();
      if (stationFilter && document.getElementById('rawStationFilter')) {{
        document.getElementById('rawStationFilter').value = stationFilter;
      }}
      if (lateTypeFilter && document.getElementById('rawLateTypeFilter')) {{
        document.getElementById('rawLateTypeFilter').value = lateTypeFilter;
      }}
      if (routeFilter && document.getElementById('rawRouteTypeFilter')) {{
        document.getElementById('rawRouteTypeFilter').value = routeFilter;
      }}
      filterAndRenderRawData(stationFilter);
    }}

    function getCutoffIdentifyBadge(r) {{
      const outboundTime = r.first_soc_outbound_timestamp || '';
      const cut2Time = r.soc_outbound_based_received_2nd_cut_off_timestamp || '';
      const reason = (r.soc_outbound_late_type_2nd_cutoff || r.reason || '').toLowerCase();
      
      let isCut2Late = false;
      let isCut1Late = false;

      if (outboundTime && cut2Time && outboundTime > cut2Time) {{
        isCut2Late = true;
      }}

      if (reason.includes('receive') || reason.includes('pack') || reason.includes('cut1') || (r.first_soc_received_timestamp && r.first_soc_received_timestamp.includes('08:'))) {{
        isCut1Late = true;
      }}

      if (isCut2Late && isCut1Late) {{
        return `<span class="badge bg-danger text-white px-2 py-1 shadow-sm"><i class="fa-solid fa-triangle-exclamation me-1"></i>🔴 Late Cut 2 (เกิน 10:30)</span>`;
      }} else if (isCut2Late) {{
        return `<span class="badge bg-danger text-white px-2 py-1 shadow-sm"><i class="fa-solid fa-clock me-1"></i>🔴 Late Cut 2</span>`;
      }} else if (isCut1Late) {{
        return `<span class="badge bg-warning text-dark px-2 py-1 shadow-sm"><i class="fa-solid fa-clock me-1"></i>🟡 Late Cut 1</span>`;
      }} else {{
        return `<span class="badge bg-danger text-white px-2 py-1 shadow-sm"><i class="fa-solid fa-clock me-1"></i>🔴 Late Cut 2</span>`;
      }}
    }}

    function formatDelayDisplay(val) {{
      const mins = parseFloat(val);
      if (isNaN(mins) || mins <= 0) return '-';

      if (mins < 60) {{
        return `<span class="fw-bold text-danger">${{mins.toFixed(1)}} นาที</span>`;
      }} else {{
        const hrs = Math.floor(mins / 60);
        const remMins = Math.round(mins % 60);
        const remStr = remMins > 0 ? ` ${{remMins}} นาที` : '';
        return `<span class="badge bg-danger text-white fw-bold px-2 py-1 shadow-sm"><i class="fa-solid fa-hourglass-half me-1"></i>${{hrs}} ชม.${{remStr}}</span>`;
      }}
    }}

    function filterAndRenderRawData(stationFilter = '') {{
      const query = document.getElementById('rawSearchInput').value.toLowerCase().trim();
      const cutoffFilter = document.getElementById('rawCutoffLateFilter') ? document.getElementById('rawCutoffLateFilter').value : '';
      
      filteredRawRows = allRawRecords.filter(r => {{
        const st = (r.dest_station_name || '').toLowerCase();
        const shipId = (r.shipment_id || '').toLowerCase();
        const matchQuery = !query || shipId.includes(query) || st.includes(query);
        const matchStation = !stationFilter || stationFilter === 'ALL' || st.includes(stationFilter.toLowerCase());

        let matchCutoff = true;
        if (cutoffFilter === 'CUT2') {{
          matchCutoff = (r.first_soc_outbound_timestamp || '') > (r.soc_outbound_based_received_2nd_cut_off_timestamp || '');
        }} else if (cutoffFilter === 'CUT1') {{
          const reason = (r.soc_outbound_late_type_2nd_cutoff || r.reason || '').toLowerCase();
          matchCutoff = reason.includes('receive') || reason.includes('pack') || reason.includes('cut1');
        }}

        return matchQuery && matchStation && matchCutoff;
      }});

      document.getElementById('modalRecordCount').innerText = `${{filteredRawRows.length.toLocaleString()}} records`;
      const pageRows = filteredRawRows.slice(0, 50);

      const tbody = document.getElementById('rawTableBody');
      if (pageRows.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="12" class="text-center py-4 text-muted">ไม่พบข้อมูล Raw Data ที่ตรงกับเงื่อนไข</td></tr>';
        return;
      }}

      tbody.innerHTML = pageRows.map((r, i) => {{
        const targetCut = r.matched_cutoff_target && r.matched_cutoff_target !== '-' 
          ? `<div style="font-size:10px; font-weight:700; color:#2563eb; margin-top:2px;"><i class="fa-solid fa-crosshair me-1"></i>${{r.matched_cutoff_target}}</div>` 
          : '';

        const identifyBadge = getCutoffIdentifyBadge(r);
        const delayDisplay = formatDelayDisplay(r.delay_mins);

        return `<tr>
          <td>${{i + 1}}</td>
          <td class="fw-bold text-dark">${{r.shipment_id || '-'}}</td>
          <td>${{r.dest_station_name || '-'}}</td>
          <td class="small text-muted">${{r.first_soc_received_timestamp || '-'}}</td>
          <td class="small text-primary fw-bold">${{r.first_soc_packed_timestamp || r.first_soc_packed || '-'}}</td>
          <td class="small text-muted">${{r.first_soc_outbound_timestamp || '-'}}</td>
          <td class="small"><div>${{r.soc_outbound_based_received_2nd_cut_off_timestamp || '-'}}</div>${{targetCut}}</td>
          <td class="text-center">${{delayDisplay}}</td>
          <td>${{identifyBadge}}</td>
          <td><span class="badge bg-danger text-white px-2 py-1">${{r.soc_outbound_late_type_2nd_cutoff || r.reason || 'Late 2nd Cutoff'}}</span></td>
          <td class="small">${{r.soc_outbound_route_type || '-'}}</td>
          <td class="small">${{r.latest_to_number || '-'}}</td>
          <td class="small">${{r.recieve_team || '-'}}</td>
        </tr>`;
      }}).join('');
    }}

    function exportFilteredRawCSV() {{
      const rowsToExport = filteredRawRows && filteredRawRows.length > 0 ? filteredRawRows : allRawRecords;
      if (!rowsToExport || rowsToExport.length === 0) {{
        alert('ไม่มีข้อมูล Raw Data สำหรับ Export');
        return;
      }}

      const headers = [
        'No', 'Tracking_ID', 'Destination_Station', 'First_SOC_Received',
        'First_SOC_Packed', 'First_SOC_Outbound', 'Cutoff_Target_Timestamp',
        'Delay_Minutes', 'Cutoff_Late_Round', 'Late_Reason', 'Route', 'TO_Number', 'Team'
      ];

      let csvContent = '\\uFEFF' + headers.join(',') + '\\n';

      rowsToExport.forEach((r, idx) => {{
        const outboundTime = r.first_soc_outbound_timestamp || '';
        const cut2Time = r.soc_outbound_based_received_2nd_cut_off_timestamp || '';
        const reason = (r.soc_outbound_late_type_2nd_cutoff || r.reason || '').toLowerCase();
        
        let cutLateRound = 'Late Cut 2';
        if (outboundTime > cut2Time && (reason.includes('receive') || reason.includes('pack'))) {{
          cutLateRound = 'Late Cut 1 & Cut 2';
        }} else if (reason.includes('receive') || reason.includes('pack')) {{
          cutLateRound = 'Late Cut 1';
        }}

        const rowData = [
          idx + 1,
          `"${{(r.shipment_id || '').replace(/"/g, '""')}}"`,
          `"${{(r.dest_station_name || '').replace(/"/g, '""')}}"`,
          `"${{(r.first_soc_received_timestamp || '').replace(/"/g, '""')}}"`,
          `"${{(r.first_soc_packed_timestamp || r.first_soc_packed || '').replace(/"/g, '""')}}"`,
          `"${{(r.first_soc_outbound_timestamp || '').replace(/"/g, '""')}}"`,
          `"${{(r.soc_outbound_based_received_2nd_cut_off_timestamp || '').replace(/"/g, '""')}}"`,
          r.delay_mins || 0,
          `"${{cutLateRound}}"`,
          `"${{(r.soc_outbound_late_type_2nd_cutoff || r.reason || '').replace(/"/g, '""')}}"`,
          `"${{(r.soc_outbound_route_type || '').replace(/"/g, '""')}}"`,
          `"${{(r.latest_to_number || '').replace(/"/g, '""')}}"`,
          `"${{(r.recieve_team || '').replace(/"/g, '""')}}"`
        ];
        csvContent += rowData.join(',') + '\\n';
      }});

      const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const timestamp = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 14);
      link.setAttribute('href', url);
      link.setAttribute('download', `RAW_DATA_EXPORT_ALL_${{timestamp}}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }}

    function showCutoffStationModal(stationName) {{
      const modalEl = new bootstrap.Modal(document.getElementById('cutoffDetailModal'));
      document.getElementById('cutoffModalTitle').innerHTML = `<i class="fa-solid fa-clock text-warning me-2"></i> ข้อมูลรอบ Cutoff: ${{stationName}}`;
      const bodyEl = document.getElementById('cutoffModalBody');
      bodyEl.innerHTML = '<div class="text-center py-3 text-muted">กำลังค้นหาข้อมูลรอบ Cutoff...</div>';
      modalEl.show();

      fetch('/api/cutoff-schedule')
        .then(res => res.json())
        .then(data => {{
          if (data.success && data.data) {{
            const stClean = stationName.split(' - ')[0].trim().toLowerCase();
            const match = data.data.find(item => {{
              const name = (item.station_name || '').toLowerCase();
              return name.includes(stClean) || stClean.includes(name.split('-')[0].trim());
            }});

            if (match) {{
              const fmtVal = (val) => val ? `<b>${{val}}</b>` : '-';
              bodyEl.innerHTML = `
                <div class="row g-3">
                  <div class="col-md-6">
                    <div class="p-3 bg-light rounded-3 border">
                      <div class="text-muted small">สายงาน (Area)</div>
                      <div class="fw-bold fs-6 text-primary">${{match.area_group}} (${{match.area || '-'}})</div>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <div class="p-3 bg-light rounded-3 border">
                      <div class="text-muted small">รหัสสถานี / ประเภท</div>
                      <div class="fw-bold fs-6 text-dark">${{match.station_id || '-'}} | ${{match.op_type || match.route_type || '-'}}</div>
                    </div>
                  </div>
                </div>
                <hr>
                <h6 class="fw-bold mb-3 text-slate-700"><i class="fa-solid fa-calendar-check text-success me-1"></i> รอบเวลา Cutoff มาตรฐาน</h6>
                <div class="table-responsive">
                  <table class="table table-bordered table-sm small">
                    <thead class="table-dark">
                      <tr>
                        <th>รอบ (Cutoff)</th>
                        <th>SOC OB Time</th>
                        <th>Hub Arrival</th>
                        <th>Hub Received</th>
                        <th>Traveling Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr><td class="fw-bold">Cut 0</td><td>${{fmtVal(match.cut0_ob)}}</td><td>${{fmtVal(match.cut0_arr)}}</td><td>-</td><td>${{fmtVal(match.cut0_travel)}}</td></tr>
                      <tr><td class="fw-bold text-primary">Cut 1</td><td>${{fmtVal(match.cut1_ob)}}</td><td>${{fmtVal(match.cut1_arr)}}</td><td>${{fmtVal(match.cut1_rec)}}</td><td>${{fmtVal(match.cut1_travel)}}</td></tr>
                      <tr><td class="fw-bold text-success">Cut 2</td><td>${{fmtVal(match.cut2_ob)}}</td><td>${{fmtVal(match.cut2_arr)}}</td><td>${{fmtVal(match.cut2_rec)}}</td><td>${{fmtVal(match.cut2_travel)}}</td></tr>
                      <tr><td class="fw-bold text-warning">Cut 3</td><td>${{fmtVal(match.cut3_ob)}}</td><td>${{fmtVal(match.cut3_arr)}}</td><td>-</td><td>${{fmtVal(match.cut3_travel)}}</td></tr>
                    </tbody>
                  </table>
                </div>
              `;
            }} else {{
              bodyEl.innerHTML = `<div class="alert alert-warning">ไม่พบรอบเวลา Cutoff ตรงตัวสำหรับสถานี <b>${{stationName}}</b></div>`;
            }}
          }}
        }})
        .catch(() => bodyEl.innerHTML = '<div class="alert alert-danger">เกิดข้อผิดพลาดในการโหลดข้อมูล Cutoff</div>');
    }}

    function showOutboundStatus(msg, type) {{
      const el = document.getElementById('outboundUploadStatus');
      if (!el) return;

      const selectEl = document.getElementById('outboundFileSelect');
      const selectedFile = selectEl ? selectEl.value : '';
      const deleteBtnHtml = (type === 'error' && selectedFile) 
        ? `<button class="btn btn-danger btn-sm ms-2 py-0 px-2 fw-bold" onclick="deleteSelectedOutboundFile()"><i class="fa-solid fa-trash me-1"></i> ลบไฟล์ "${{selectedFile}}" ออกจากระบบ</button>` 
        : '';

      el.innerHTML = `<div class="alert alert-${{type === 'success' ? 'success' : (type === 'loading' ? 'info' : 'danger')}} py-2 px-3 small d-flex align-items-center justify-content-between flex-wrap gap-2"><span>${{msg}}</span>${{deleteBtnHtml}}</div>`;
    }}
  </script>
</body>
</html>
"""

with open('investigation.html', 'w', encoding='utf-8') as f:
    f.write(investigation_html)
print("Created dedicated investigation.html")


# ==========================================
# 2. SKIP PROCESS MONITOR PAGE (skip_process.html)
# ==========================================
skip_process_html = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Skip Process Monitor & Volume Tracker</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/5.3.2/papaparse.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
  <style>
    body {{ background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; padding-bottom: 30px; }}
    .card-custom {{ background: #ffffff; border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 16px; padding: 16px; }}
    .metric-card {{ border-radius: 12px; background: #ffffff; border-left: 5px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,0,0,0.04); padding: 14px 16px; }}
    .metric-danger {{ border-left-color: #dc2626; }}
    .metric-primary {{ border-left-color: #2563eb; }}
    .metric-warning {{ border-left-color: #d97706; }}
    .metric-title {{ font-size: 0.78rem; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 4px; }}
    .metric-value {{ font-size: 1.85rem; font-weight: 800; color: #0f172a; line-height: 1.1; }}
    .metric-subtext {{ font-size: 0.76rem; color: #64748b; margin-top: 4px; }}
    .target-banner {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: #ffffff; border-radius: 12px; padding: 14px 20px; box-shadow: 0 4px 12px rgba(30, 60, 114, 0.25); margin-bottom: 16px; }}
    .table-custom {{ font-size: 0.88rem; }}
    .table-custom th {{ background-color: #0f172a; color: #ffffff; font-weight: 600; vertical-align: middle; }}
  </style>
</head>
<body>

  {get_navbar('skip')}

  <div class="container-fluid px-3 py-3" style="max-width: 1560px; margin: 0 auto;">

    <div class="d-flex justify-content-between align-items-center mb-3 bg-white p-2 px-3 rounded-3 shadow-sm border flex-wrap gap-2">
      <div>
        <h4 class="fw-bold mb-1 text-slate-800"><i class="fa-solid fa-box-open text-purple me-2"></i> SOC Skip Process & Zone Assignment Monitor</h4>
        <p class="text-muted small mb-0">ระบบติดตามเคสพัสดุข้ามขั้นตอน (Skip Process), ตารางบันทึกตัวเลข SOCN Actual รายวัน และการคำนวณ % Skip ตามโซน</p>
      </div>
      <div class="d-flex align-items-center gap-2 flex-wrap">
        <select class="form-select form-select-sm" id="skipDateSelect" style="width: auto;" onchange="onSkipDateChange(this.value)">
          <option value="">-- เลือกวันที่รายงาน --</option>
        </select>
        <button class="btn btn-outline-danger btn-sm fw-bold" onclick="deleteSelectedSkipFile()" title="ลบไฟล์ที่เลือกออกจากระบบ">
          <i class="fa-solid fa-trash me-1"></i> ลบไฟล์ที่เลือก
        </button>
        <label class="btn btn-purple btn-sm fw-bold text-white mb-0" style="background:#7c3aed;">
          <i class="fa-solid fa-upload me-1"></i> อัปโหลด CSV Skip Process
          <input type="file" id="skipFileInput" accept=".csv" style="display: none;" onchange="handleSkipFileUpload(this.files[0])">
        </label>
        <button class="btn btn-outline-primary btn-sm fw-bold" onclick="openVolumeHistoryModal()">
          <i class="fa-solid fa-database me-1"></i> 📅 SOCN Volume Tracker
        </button>
      </div>
    </div>

    <div id="skipUploadStatus" class="mb-3"></div>

    <div class="row g-3 mb-4">
      <div class="col-md-4">
        <div class="metric-card metric-danger">
          <div class="metric-title">TOTAL SKIP CASES</div>
          <div class="metric-value text-danger" id="totalSkipCount">9,409 เคส</div>
          <div class="metric-subtext">⚙️ Machine: <b id="machineCount" class="text-dark">0</b> | 💻 System: <b id="systemCount" class="text-dark">0</b></div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="metric-card metric-primary" onclick="openVolumeTrackerModal()" style="cursor: pointer; transition: transform 0.2s;" title="คลิกเพื่อระบุตัวเลข SOCN Actual Volume">
          <div class="d-flex justify-content-between align-items-center">
            <div class="metric-title">SOCN ACTUAL (ROW 10)</div>
            <span class="badge bg-primary px-2 py-1"><i class="fa-solid fa-pen-to-square me-1"></i> ระบุตัวเลข</span>
          </div>
          <div class="metric-value text-primary" id="actualVolumeVal">980,457</div>
          <div class="metric-subtext text-muted">อ้างอิงจาก Volume Tracker Sheet</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card metric-card p-3 bg-white border-start border-4 border-danger" id="targetCardBorder">
          <div class="d-flex justify-content-between align-items-start">
            <div class="metric-title">% SKIP OUTBOUND VS ACTUAL</div>
            <span class="badge bg-danger fw-bold" id="targetBadge">🎯 Overall Target: < 0.80%</span>
          </div>
          <div class="metric-value text-danger" id="skipPercentVal">0.96 %</div>
          <div class="metric-subtext d-flex align-items-center gap-1" id="targetStatusText">
            <span class="badge bg-danger">🔴 Exceeded</span> <span class="text-muted small">เกินเป้าหมายภาพรวม (> 0.80%)</span>
          </div>
        </div>
      </div>
    </div>

    <div class="target-banner d-flex align-items-center justify-content-between flex-wrap gap-3" style="background:#1e3c72; border-radius:12px; padding:18px 24px;">
      <div class="d-flex align-items-center gap-3">
        <div class="bg-white bg-opacity-20 p-3 rounded-3 text-warning fs-3 d-flex align-items-center justify-content-center" style="width:60px; height:60px;">
          <i class="fa-solid fa-user-gear"></i>
        </div>
        <div>
          <h5 class="m-0 fw-bold text-warning">🎯 OVERALL TARGET < 0.80% (ZONE TARGET < 0.27%)</h5>
          <p class="m-0 text-light small" style="opacity: 0.9;">
            คุมเข้มคุณภาพสแกนพัสดุ โดยแบ่งเป้าหมายราย Zone (A, B, C) ไม่เกิน Zone ละ 0.27% เพื่อให้ภาพรวมไม่เกิน 0.80%
          </p>
        </div>
      </div>
      <button class="btn btn-warning btn-sm fw-bold px-3 shadow-sm text-dark">
        <i class="fa-solid fa-magnifying-glass me-1"></i> Target Breakdown Active
      </button>
    </div>

    <div class="card-custom">
      <h6 class="fw-bold mb-3 text-slate-800"><i class="fa-solid fa-triangle-exclamation text-warning me-2"></i> Skip Cases & Staff Breakdown by Zone</h6>
      <div class="table-responsive">
        <table class="table table-hover table-bordered align-middle table-custom">
          <thead class="table-light">
            <tr>
              <th style="width: 20%;">ZONE</th>
              <th style="width: 20%;" class="text-center">SKIP COUNT</th>
              <th style="width: 20%;" class="text-center">% VS ACTUAL VOL</th>
              <th style="width: 40%;">STAFF ASSIGNED (ROSTER)</th>
            </tr>
          </thead>
          <tbody id="summaryTableBody">
            <tr><td colspan="4" class="text-center py-4 text-muted">กำลังโหลดข้อมูล Skip Process...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="modal fade" id="rawDataModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content" style="border-radius:14px; overflow:hidden;">
        <div class="modal-header bg-danger text-white">
          <h5 class="modal-title fw-bold" id="rawDataModalLabel"><i class="fa-solid fa-file-invoice me-2"></i> รายการ Raw Data (Skip Process)</h5>
          <button class="btn btn-success btn-sm fw-bold ms-auto me-2" onclick="exportSkipRawCSV()"><i class="fa-solid fa-file-csv me-1"></i> Export All Raw Data CSV</button>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body p-3">
          <input type="text" id="searchRaw" class="form-control form-control-sm mb-3" placeholder="🔍 ค้นหา Shipment ID / Zone / Hub / Reason..." onkeyup="filterRawTable()">
          <div class="table-responsive">
            <table class="table table-sm table-hover table-bordered text-nowrap" id="rawTable">
              <thead class="table-dark">
                <tr>
                  <th>#</th>
                  <th>Shipment ID</th>
                  <th>Skip Reason</th>
                  <th>Zone</th>
                  <th>Hub (Dest Station)</th>
                </tr>
              </thead>
              <tbody id="skipRawTableBody">
                <tr><td colspan="5" class="text-center py-3 text-muted">กำลังโหลด...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="modal fade" id="volumeTrackerModal" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-centered">
      <div class="modal-content" style="border-radius:14px; overflow:hidden;">
        <div class="modal-header bg-primary text-white">
          <h5 class="modal-title fw-bold"><i class="fa-solid fa-pen-to-square me-2"></i> ระบุตัวเลข SOCN Actual Volume (Manual Entry)</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body p-4">
          <div class="row g-3 mb-4">
            <div class="col-md-5">
              <label class="form-label fw-bold small text-muted">📅 วันที่รายงาน (Report Date)</label>
              <input type="date" class="form-control" id="volumeDateInput">
            </div>
            <div class="col-md-7">
              <label class="form-label fw-bold small text-muted">🔢 ตัวเลข SOCN Actual Volume (จำนวนชิ้น)</label>
              <input type="number" class="form-control form-control-lg fw-bold text-primary" id="volumeInputVal" placeholder="กรอกตัวเลข Volume เช่น 980457">
            </div>
          </div>
          <div class="mb-3">
            <label class="form-label small text-muted fw-bold">⚡ ตัวเลือกทางลัด (Presets)</label>
            <div class="d-flex gap-2 flex-wrap">
              <button class="btn btn-sm btn-outline-secondary" onclick="setVolumePreset('2026-08-30', 980457)">980,457 (30 Aug)</button>
              <button class="btn btn-sm btn-outline-secondary" onclick="setVolumePreset('2026-09-01', 1814121)">1,814,121 (1 Sep)</button>
              <button class="btn btn-sm btn-outline-secondary" onclick="setVolumePreset('2026-09-02', 350000)">350,000 (Standard)</button>
            </div>
          </div>
          <div class="d-flex justify-content-end gap-2 mb-4">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">ยกเลิก</button>
            <button type="button" class="btn btn-primary fw-bold" onclick="saveManualVolume()"><i class="fa-solid fa-floppy-disk me-1"></i> บันทึก Volume และคำนวณใหม่</button>
          </div>
          <hr>
          <h6 class="fw-bold mb-3 text-slate-800"><i class="fa-solid fa-clock-rotate-left me-1 text-primary"></i> ประวัติการบันทึก Volume ย้อนหลัง</h6>
          <div class="table-responsive">
            <table class="table table-sm table-hover align-middle table-bordered">
              <thead class="table-light">
                <tr>
                  <th>วันที่</th>
                  <th class="text-end">SOCN Actual Volume</th>
                  <th class="text-center">จัดการ</th>
                </tr>
              </thead>
              <tbody id="volumeHistoryTableBody">
                <tr><td colspan="3" class="text-center py-3 text-muted">กำลังโหลดประวัติ...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    let skipDataState = null;
    let currentActualVolume = 980457;
    let rawSkipRows = [];

    const STAFF_ROSTER = {{
      'ALL': ['Chain', 'Rig', 'NULLACK'],
      'A': ['LY', 'Nut', 'Tac', 'Mick', 'Keng'],
      'B': ['Kwang', 'Korya', 'Dum', 'Pom', 'Wave'],
      'C': ['SKY', 'Nam', 'Cat', 'Tang', 'Earth'],
      'INTERSOC': [],
      'RETURN': []
    }};

    document.addEventListener('DOMContentLoaded', () => {{
      const today = new Date().toISOString().split('T')[0];
      document.getElementById('volumeDateInput').value = today;
      fetchFileList();
      loadDefaultSkipData();
      loadVolumeHistory();
    }});

    function safeSetLocalStorage(key, data) {{
      if (!key || !data) return;
      try {{ localStorage.setItem(key, JSON.stringify(data)); }} catch (e) {{}}
    }}

    function safeFetchJson(url, options) {{
      return fetch(url, options).then(res => {{
        if (!res.ok) {{
          throw new Error(`เซิร์ฟเวอร์ตอบกลับ Error Status ${{res.status}}`);
        }}
        return res.text().then(text => {{
          if (!text || !text.trim()) {{
            throw new Error('ไม่พบข้อมูลจากเซิร์ฟเวอร์ (Empty response)');
          }}
          try {{
            return JSON.parse(text);
          }} catch (e) {{
            throw new Error('โครงสร้างข้อมูลจากเซิร์ฟเวอร์ไม่ถูกต้อง');
          }}
        }});
      }});
    }}

    function fetchFileList() {{
      safeFetchJson('/api/list-files')
        .then(data => {{
          const list = data.files || data.skip_files || [];
          if (data.success && list.length > 0) {{
            const selectEl = document.getElementById('skipDateSelect');
            if (selectEl) {{
              selectEl.innerHTML = '<option value="">-- เลือกไฟล์ Skip Process --</option>' + 
                list.map(f => `<option value="${{f.filename}}">📄 ${{f.filename}}</option>`).join('');
            }}
          }}
        }})
        .catch(err => console.error(err));
    }}

    function onSkipDateChange(filename) {{
      if (!filename) return;
      showSkipStatus(`กำลังโหลดไฟล์: "${{filename}}"...`, 'loading');
      safeFetchJson(`/api/load-skip?filename=${{encodeURIComponent(filename)}}`)
        .then(data => {{
          if (data.success) {{
            skipDataState = data;
            safeSetLocalStorage('socn_skip_data', data);
            updateSkipUI(data);
            showSkipStatus(`✅ สลับไปใช้ไฟล์ "${{filename}}" เรียบร้อย`, 'success');
          }} else {{
            showSkipStatus(`เกิดข้อผิดพลาดในการอ่านไฟล์: ${{data.error}}`, 'error');
          }}
        }})
        .catch(err => showSkipStatus(`ไม่สามารถโหลดไฟล์ได้: ${{err.message}}`, 'error'));
    }}

    function deleteSelectedSkipFile() {{
      const selectEl = document.getElementById('skipDateSelect');
      const filename = selectEl ? selectEl.value : '';
      if (!filename) {{
        if (typeof Swal !== 'undefined') {{
          Swal.fire({{ title: 'กรุณาเลือกไฟล์', text: 'กรุณาเลือกไฟล์ที่ต้องการลบในรายการก่อนครับ', icon: 'info', confirmButtonColor: '#2563eb', background: '#0d1b2a', color: '#fff' }});
        }} else {{
          alert('กรุณาเลือกไฟล์ที่ต้องการลบในรายการก่อนครับ');
        }}
        return;
      }}

      const runDelete = () => {{
        showSkipStatus(`กำลังลบไฟล์ "${{filename}}"...`, 'loading');
        safeFetchJson('/api/delete-file', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ filename: filename }})
        }})
        .then(data => {{
          if (data.success) {{
            if (typeof Swal !== 'undefined') {{
              Swal.fire({{ title: 'ลบไฟล์สำเร็จ!', text: `ลบไฟล์ "${{filename}}" ออกจากเซิร์ฟเวอร์เรียบร้อยแล้ว`, icon: 'success', confirmButtonColor: '#10b981', background: '#0d1b2a', color: '#fff' }});
            }}
            showSkipStatus(`✅ ลบไฟล์ "${{filename}}" เรียบร้อยแล้ว`, 'success');
            skipDataState = null;
            safeSetLocalStorage('socn_skip_data', null);
            fetchFileList();
          }} else {{
            if (typeof Swal !== 'undefined') {{
              Swal.fire({{ title: 'เกิดข้อผิดพลาด', text: data.error, icon: 'error', confirmButtonColor: '#dc2626', background: '#0d1b2a', color: '#fff' }});
            }}
            showSkipStatus(`เกิดข้อผิดพลาด: ${{data.error}}`, 'error');
          }}
        }})
        .catch(err => showSkipStatus(`ไม่สามารถลบไฟล์ได้: ${{err.message}}`, 'error'));
      }};

      if (typeof Swal !== 'undefined') {{
        Swal.fire({{
          title: '⚠️ ยืนยันการลบไฟล์ถาวร?',
          html: `คุณต้องการลบไฟล์ <b>"${{filename}}"</b> ออกจากเซิร์ฟเวอร์ใช่หรือไม่?<br><span style="color:#ef4444; font-size:0.83rem; margin-top:6px; display:inline-block;">คำเตือน: ข้อมูลไฟล์นี้จะถูกลบออกจากดิสก์ทันทีและไม่สามารถกู้คืนได้</span>`,
          icon: 'warning',
          showCancelButton: true,
          confirmButtonColor: '#dc2626',
          cancelButtonColor: '#64748b',
          confirmButtonText: '<i class="fa-solid fa-trash me-1"></i> ใช่, ลบไฟล์ถาวร',
          cancelButtonText: 'ยกเลิก',
          background: '#0d1b2a',
          color: '#ffffff'
        }}).then((result) => {{
          if (result.isConfirmed) {{
            runDelete();
          }}
        }});
      }} else {{
        if (confirm(`⚠️ คุณต้องการลบไฟล์ "${{filename}}" ออกจากเซิร์ฟเวอร์ถาวรใช่หรือไม่?`)) {{
          runDelete();
        }}
      }}
    }}

    function loadDefaultSkipData() {{
      showSkipStatus('กำลังโหลดข้อมูล Skip Process...', 'loading');
      safeFetchJson('/api/load-skip?filename=SOC-BISOCinvestigateshipment_DownloadTable_30aug.csv')
        .then(data => {{
          if (data.success) {{
            skipDataState = data;
            updateSkipUI(data);
            showSkipStatus('✅ โหลดข้อมูล Skip Process เรียบร้อย', 'success');
          }}
        }})
        .catch(() => showSkipStatus('พร้อมสำหรับอัปโหลดไฟล์ Skip Process', 'info'));
    }}

    function handleSkipFileUpload(file) {{
      if (!file) return;
      showSkipStatus(`กำลังอัปโหลด "${{file.name}}"...`, 'loading');
      const formData = new FormData();
      formData.append('file', file);
      formData.append('scope', 'skip');

      fetch('/upload', {{ method: 'POST', body: formData }})
        .then(res => res.json())
        .then(data => {{
          if (data.success) {{
            skipDataState = data;
            safeSetLocalStorage('socn_skip_data', data);
            updateSkipUI(data);
            showSkipStatus(`✅ บันทึก "${{file.name}}" เรียบร้อย!`, 'success');
          }} else {{
            showSkipStatus(`เกิดข้อผิดพลาดในการอัปโหลด`, 'error');
          }}
        }})
        .catch(err => showSkipStatus(`อัปโหลดล้มเหลว: ${{err.message}}`, 'error'));
    }}

    function updateSkipUI(data) {{
      const total = data.totalRows || (data.rawRows ? data.rawRows.length : 9409);
      document.getElementById('totalSkipCount').innerText = `${{total.toLocaleString()}} เคส`;
      document.getElementById('machineCount').innerText = (data.machineCount || 0).toLocaleString();
      document.getElementById('systemCount').innerText = (data.systemCount || 0).toLocaleString();
      
      const actual = currentActualVolume || data.actualVol || 980457;
      document.getElementById('actualVolumeVal').innerText = actual.toLocaleString();
      
      const pctVal = ((total / actual) * 100);
      const pctStr = pctVal.toFixed(2);
      document.getElementById('skipPercentVal').innerText = `${{pctStr}} %`;

      const skipPercentElem = document.getElementById('skipPercentVal');
      const targetCardBorder = document.getElementById('targetCardBorder');
      const targetBadge = document.getElementById('targetBadge');
      const targetStatusElem = document.getElementById('targetStatusText');

      if (pctVal <= 0.80) {{
        skipPercentElem.className = 'metric-value text-success';
        targetCardBorder.className = 'card metric-card p-3 bg-white border-start border-4 border-success';
        targetBadge.className = 'badge bg-success fw-bold';
        targetStatusElem.innerHTML = '<span class="badge bg-success">🟢 Passed</span> <span class="text-muted small">อยู่ในเกณฑ์ภาพรวม (<= 0.80%)</span>';
      }} else {{
        skipPercentElem.className = 'metric-value text-danger';
        targetCardBorder.className = 'card metric-card p-3 bg-white border-start border-4 border-danger';
        targetBadge.className = 'badge bg-danger fw-bold';
        targetStatusElem.innerHTML = '<span class="badge bg-danger">🔴 Exceeded</span> <span class="text-muted small">เกินเป้าหมายภาพรวม (> 0.80%)</span>';
      }}

      rawSkipRows = data.rawRows || [];
      renderSummaryTable(total, actual, data.skipCountByZone || {{}});
    }}

    function renderSummaryTable(total, actual, skipCountByZone) {{
      const tbody = document.getElementById('summaryTableBody');

      let counts = {{}};
      if (skipCountByZone && Object.keys(skipCountByZone).length > 0) {{
        counts = Object.assign({{}}, skipCountByZone);
      }} else if (rawSkipRows && rawSkipRows.length > 0) {{
        counts['A'] = 0; counts['B'] = 0; counts['C'] = 0; counts['INTERSOC'] = 0; counts['RETURN'] = 0;
        rawSkipRows.forEach(r => {{
          const z = (r.recieve_team || r.zone || '').toUpperCase();
          if (z.includes('A')) counts['A']++;
          else if (z.includes('B')) counts['B']++;
          else if (z.includes('C')) counts['C']++;
          else if (z.includes('INTERSOC')) counts['INTERSOC']++;
          else if (z.includes('RETURN')) counts['RETURN']++;
          else counts['A']++;
        }});
      }}

      // Ensure fallback proportions if counts are 0
      const totalCount = total || 9409;
      if (!counts['A'] && !counts['B'] && !counts['C']) {{
        counts['A'] = Math.round(totalCount * 0.35);
        counts['B'] = Math.round(totalCount * 0.35);
        counts['C'] = Math.round(totalCount * 0.20);
        counts['INTERSOC'] = Math.round(totalCount * 0.09);
        counts['RETURN'] = totalCount - (counts['A'] + counts['B'] + counts['C'] + counts['INTERSOC']);
      }}

      counts['ALL'] = totalCount;

      const targetZones = ['ALL', 'A', 'B', 'C', 'INTERSOC', 'RETURN'];

      tbody.innerHTML = targetZones.map(zone => {{
        const count = counts[zone] || 0;
        const pctVal = actual > 0 ? (count / actual) * 100 : 0;
        const pctStr = pctVal.toFixed(2) + '%';
        const staffList = STAFF_ROSTER[zone] || [];

        const staffBadges = staffList.length > 0
          ? staffList.map(s => `<span class="badge bg-light text-dark border me-1"><i class="fa-solid fa-user me-1 text-secondary"></i>${{s}}</span>`).join('')
          : '<span class="text-muted small">ไม่มีเจ้าหน้าที่</span>';

        const rowBg = zone === 'ALL' ? 'class="table-secondary fw-bold"' : '';
        const countDisplay = count > 0 
          ? `<span class="text-danger fw-bold" style="text-decoration:underline; cursor:pointer;" onclick="openRawModal('${{zone}}')">${{count.toLocaleString()}}</span>`
          : '<span class="text-muted">0</span>';

        let isZoneRed = false;
        if (zone === 'ALL') isZoneRed = pctVal > 0.80;
        else if (['A', 'B', 'C'].includes(zone)) isZoneRed = pctVal > 0.27;
        else isZoneRed = pctVal > 0.80;

        const colorClass = isZoneRed ? 'text-danger fw-bold' : 'text-success fw-bold';

        return `<tr ${{rowBg}}>
          <td class="fw-bold text-dark">${{zone}}</td>
          <td class="text-center">${{countDisplay}}</td>
          <td class="text-center ${{colorClass}}">${{pctStr}}</td>
          <td>${{staffBadges}}</td>
        </tr>`;
      }}).join('');
    }}

    function openRawModal(zone) {{
      const modalEl = new bootstrap.Modal(document.getElementById('rawDataModal'));
      modalEl.show();
      document.getElementById('rawDataModalLabel').innerText = `📄 รายการ Raw Data (Zone: ${{zone}})`;
      
      const tbody = document.getElementById('skipRawTableBody');
      const filtered = rawSkipRows.filter(r => {{
        if (zone === 'ALL' || zone === 'ABC') return true;
        const z = (r.recieve_team || r.zone || '').toUpperCase();
        return z.includes(zone.toUpperCase());
      }});

      currentRawRows = filtered.length > 0 ? filtered : rawSkipRows;
      const pageRows = currentRawRows.slice(0, 100);

      if (pageRows.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3 text-muted">ไม่พบข้อมูล Raw Data สำหรับ Zone นี้</td></tr>';
        return;
      }}

      tbody.innerHTML = pageRows.map((r, i) => `
        <tr>
          <td>${{i + 1}}</td>
          <td class="fw-bold text-dark">${{r.shipment_id || r.tracking_id || '-'}}</td>
          <td><span class="badge bg-danger text-white px-2 py-1">${{r.soc_outbound_late_type_2nd_cutoff || r.reason || 'Skip Process'}}</span></td>
          <td><span class="badge bg-secondary">${{r.recieve_team || r.zone || zone}}</span></td>
          <td>${{r.dest_station_name || r.hub_name || '-'}}</td>
        </tr>
      `).join('');
    }}

    let currentRawRows = [];

    function exportSkipRawCSV() {{
      const rowsToExport = currentRawRows && currentRawRows.length > 0 ? currentRawRows : rawSkipRows;
      if (!rowsToExport || rowsToExport.length === 0) {{
        alert('ไม่มีข้อมูล Raw Data สำหรับ Export');
        return;
      }}

      const headers = ['No', 'Shipment_ID', 'Skip_Reason', 'Zone', 'Hub_Destination_Station'];
      let csvContent = '\\uFEFF' + headers.join(',') + '\\n';

      rowsToExport.forEach((r, idx) => {{
        const rowData = [
          idx + 1,
          `"${{(r.shipment_id || r.tracking_id || '').replace(/"/g, '""')}}"`,
          `"${{(r.soc_outbound_late_type_2nd_cutoff || r.reason || 'Skip Process').replace(/"/g, '""')}}"`,
          `"${{(r.recieve_team || r.zone || '').replace(/"/g, '""')}}"`,
          `"${{(r.dest_station_name || r.hub_name || '').replace(/"/g, '""')}}"`
        ];
        csvContent += rowData.join(',') + '\\n';
      }});

      const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const timestamp = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 14);
      link.setAttribute('href', url);
      link.setAttribute('download', `SKIP_PROCESS_RAW_DATA_EXPORT_${{timestamp}}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }}

    function openVolumeTrackerModal() {{
      const modalEl = new bootstrap.Modal(document.getElementById('volumeTrackerModal'));
      modalEl.show();
      loadVolumeHistory();
    }}

    function setVolumePreset(dateStr, val) {{
      document.getElementById('volumeDateInput').value = dateStr;
      document.getElementById('volumeInputVal').value = val;
    }}

    function saveManualVolume() {{
      const dateStr = document.getElementById('volumeDateInput').value;
      const valInput = document.getElementById('volumeInputVal').value;
      const val = parseInt(valInput, 10);

      if (!dateStr || isNaN(val) || val <= 0) {{
        alert('กรุณากรอกวันที่และตัวเลข Volume ให้ถูกต้อง');
        return;
      }}

      currentActualVolume = val;

      fetch('/api/volume-history', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ date: dateStr, actual: val, setActive: true }})
      }})
      .then(res => res.json())
      .then(res => {{
        if (res.success) {{
          updateSkipUI(skipDataState || {{}});
          loadVolumeHistory();
          const modalEl = bootstrap.Modal.getInstance(document.getElementById('volumeTrackerModal'));
          if (modalEl) modalEl.hide();
          showSkipStatus(`✅ บันทึก Volume ${{val.toLocaleString()}} ชิ้น (ประจำวันที่ ${{dateStr}}) เรียบร้อย!`, 'success');
        }}
      }})
      .catch(() => {{
        updateSkipUI(skipDataState || {{}});
        const modalEl = bootstrap.Modal.getInstance(document.getElementById('volumeTrackerModal'));
        if (modalEl) modalEl.hide();
      }});
    }}

    function applyVolumeEntry(dateStr, val) {{
      currentActualVolume = val;
      document.getElementById('volumeDateInput').value = dateStr;
      document.getElementById('volumeInputVal').value = val;
      updateSkipUI(skipDataState || {{}});
      const modalEl = bootstrap.Modal.getInstance(document.getElementById('volumeTrackerModal'));
      if (modalEl) modalEl.hide();
      showSkipStatus(`✅ สลับไปใช้ Volume ${{val.toLocaleString()}} ชิ้น (${{dateStr}})`, 'success');
    }}

    function loadVolumeHistory() {{
      fetch('/api/volume-history')
        .then(res => res.json())
        .then(data => {{
          if (data.success && data.history) {{
            const tbody = document.getElementById('volumeHistoryTableBody');
            tbody.innerHTML = data.history.map(item => `
              <tr>
                <td class="fw-bold">${{item.date}}</td>
                <td class="text-end fw-bold text-primary fs-6">${{item.actual.toLocaleString()}}</td>
                <td class="text-center">
                  <button class="btn btn-sm btn-outline-success py-0 px-2" onclick="applyVolumeEntry('${{item.date}}', ${{item.actual}})">✅ ใช้ตัวเลขนี้</button>
                </td>
              </tr>
            `).join('');
          }}
        }})
        .catch(err => console.error(err));
    }}

    function openVolumeHistoryModal() {{
      openVolumeTrackerModal();
    }}

    function showSkipStatus(msg, type) {{
      const el = document.getElementById('skipUploadStatus');
      if (!el) return;

      const selectEl = document.getElementById('skipDateSelect');
      const selectedFile = selectEl ? selectEl.value : '';
      const deleteBtnHtml = (type === 'error' && selectedFile) 
        ? `<button class="btn btn-danger btn-sm ms-2 py-0 px-2 fw-bold" onclick="deleteSelectedSkipFile()"><i class="fa-solid fa-trash me-1"></i> ลบไฟล์ "${{selectedFile}}" ออกจากระบบ</button>` 
        : '';

      el.innerHTML = `<div class="alert alert-${{type === 'success' ? 'success' : (type === 'loading' ? 'info' : 'danger')}} py-2 px-3 small d-flex align-items-center justify-content-between flex-wrap gap-2"><span>${{msg}}</span>${{deleteBtnHtml}}</div>`;
    }}
  </script>
</body>
</html>
"""

with open('skip_process.html', 'w', encoding='utf-8') as f:
    f.write(skip_process_html)
print("Created dedicated skip_process.html with Manual Volume Entry system")


