import os

print("Generating modular application HTML files...")

def get_navbar(active_page):
    def active_style(name):
        if active_page == name:
            return "color:#ffffff; text-decoration:none; padding:6px 14px; border-radius:6px; font-weight:700; font-size:0.88rem; background:#2563eb; transition:all 0.2s;"
        return "color:#cbd5e1; text-decoration:none; padding:6px 14px; border-radius:6px; font-weight:600; font-size:0.88rem; background:rgba(255,255,255,0.08); transition:all 0.2s;"

    return f"""
  <!-- Top Navigation Header -->
  <nav style="background:#0d1b2a; color:#ffffff; padding:12px 24px; display:flex; align-items:center; justify-content:space-between; box-shadow:0 4px 14px rgba(0,0,0,0.25); position:sticky; top:0; z-index:9999;">
    <a href="index.html" style="color:#ffffff; font-size:1.15rem; font-weight:800; text-decoration:none; display:flex; align-items:center; gap:8px;">
      <span style="font-size:1.4rem;">📦</span> SOC Operations Portal
    </a>
    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <a href="index.html" style="{active_style('portal')}">🏠 Portal Hub</a>
      <a href="investigation.html" style="{active_style('investigation')}">🚀 Investigation</a>
      <a href="skip_process.html" style="{active_style('skip')}">📦 Skip Monitor</a>
      <a href="cutoff_master.html" style="{active_style('cutoff')}">⏰ Cutoff & TTB Master</a>
    </div>
  </nav>
"""

# READ ORIGINAL SINGLE PAGE CODE FROM Index.txt
with open('Index.txt', 'r', encoding='utf-8') as f:
    full_code = f.read()

# INVESTIGATION PAGE (investigation.html)
# Insert navbar after <body> tag in full_code
investigation_code = full_code.replace('<body>', '<body>\n' + get_navbar('investigation'))
investigation_code = investigation_code.replace('<title>SOC Investigation & Skip Process Dashboard</title>', '<title>Outbound 2nd Cutoff Investigation Dashboard</title>')
investigation_code = investigation_code.replace('id="mainTab"', 'id="mainTab" style="display:none;"')

# Add Cutoff Target Column to Table Header in investigation.html
investigation_code = investigation_code.replace(
    '<th>Peak Time Outbound</th>',
    '<th>Peak Time Outbound</th>\n                  <th>Target Cutoff & TTB</th>'
)

# Add Cutoff Target Cell & Modal Button to Table Body in investigation.html
target_cell_replacement = """<td style="text-align: right; font-weight: 600; color: #1e293b;">${item.peakTime}</td>
                            <td style="text-align: center;">
                                <div style="font-size:12px; font-weight:600; color:#2563eb;">${item.cutoffTarget || '-'}</div>
                                <button type="button" class="btn btn-sm btn-outline-warning" style="font-size:10px; padding:2px 6px; margin-top:2px;" onclick="event.stopPropagation(); showCutoffStationModal('${stTitle}')">⏰ รอบ Cutoff</button>
                            </td>"""

investigation_code = investigation_code.replace(
    '<td style="text-align: right; font-weight: 600; color: #1e293b;">${item.peakTime}</td>',
    target_cell_replacement
)

# Injected Cutoff Modal HTML & JS Script before </body>
cutoff_modal_script = """
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

  <script>
    function showCutoffStationModal(stationName) {
      const modalEl = new bootstrap.Modal(document.getElementById('cutoffDetailModal'));
      document.getElementById('cutoffModalTitle').innerHTML = `<i class="fa-solid fa-clock text-warning me-2"></i> ข้อมูลรอบ Cutoff: ${stationName}`;
      const bodyEl = document.getElementById('cutoffModalBody');
      bodyEl.innerHTML = '<div class="text-center py-3 text-muted">กำลังค้นหาข้อมูลรอบ Cutoff...</div>';
      modalEl.show();

      fetch('/api/cutoff-schedule')
        .then(res => res.json())
        .then(data => {
          if (data.success && data.data) {
            const stClean = stationName.split(' - ')[0].strip ? stationName.split(' - ')[0].strip().toLowerCase() : stationName.toLowerCase();
            const match = data.data.find(item => {
              const name = (item.station_name || '').toLowerCase();
              return name.includes(stClean) || stClean.includes(name.split('-')[0].trim());
            });

            if (match) {
              const fmtVal = (val) => val ? `<b>${val}</b>` : '-';
              bodyEl.innerHTML = `
                <div class="row g-3">
                  <div class="col-md-6">
                    <div class="p-3 bg-light rounded-3 border">
                      <div class="text-muted small">สายงาน (Area)</div>
                      <div class="fw-bold fs-6 text-primary">${match.area_group} (${match.area || '-'})</div>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <div class="p-3 bg-light rounded-3 border">
                      <div class="text-muted small">รหัสสถานี / ประเภท</div>
                      <div class="fw-bold fs-6 text-dark">${match.station_id || '-'} | ${match.op_type || match.route_type || '-'}</div>
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
                      <tr>
                        <td class="fw-bold">Cut 0</td>
                        <td>${fmtVal(match.cut0_ob)}</td>
                        <td>${fmtVal(match.cut0_arr)}</td>
                        <td>-</td>
                        <td>${fmtVal(match.cut0_travel)}</td>
                      </tr>
                      <tr>
                        <td class="fw-bold text-primary">Cut 1</td>
                        <td>${fmtVal(match.cut1_ob)}</td>
                        <td>${fmtVal(match.cut1_arr)}</td>
                        <td>${fmtVal(match.cut1_rec)}</td>
                        <td>${fmtVal(match.cut1_travel)}</td>
                      </tr>
                      <tr>
                        <td class="fw-bold text-success">Cut 2</td>
                        <td>${fmtVal(match.cut2_ob)}</td>
                        <td>${fmtVal(match.cut2_arr)}</td>
                        <td>${fmtVal(match.cut2_rec)}</td>
                        <td>${fmtVal(match.cut2_travel)}</td>
                      </tr>
                      <tr>
                        <td class="fw-bold text-warning">Cut 3</td>
                        <td>${fmtVal(match.cut3_ob)}</td>
                        <td>${fmtVal(match.cut3_arr)}</td>
                        <td>-</td>
                        <td>${fmtVal(match.cut3_travel)}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              `;
            } else {
              bodyEl.innerHTML = `<div class="alert alert-warning">ไม่พบรอบเวลา Cutoff ตรงตัวสำหรับสถานี <b>${stationName}</b><br><a href="cutoff_master.html" class="alert-link mt-2 d-inline-block">คลิกที่นี่เพื่อไปหน้า Cutoff Master</a></div>`;
            }
          }
        })
        .catch(() => {
          bodyEl.innerHTML = '<div class="alert alert-danger">เกิดข้อผิดพลาดในการโหลดข้อมูล Cutoff</div>';
        });
    }
  </script>
</body>
"""

investigation_code = investigation_code.replace('</body>', cutoff_modal_script)

with open('investigation.html', 'w', encoding='utf-8') as f:
    f.write(investigation_code)
print("Created investigation.html with Cutoff Target matching")


# SKIP PROCESS PAGE (skip_process.html)
skip_code = full_code.replace('<body>', '<body>\n' + get_navbar('skip'))

# Set Tab 2 (Skip Process Monitor) as active tab in skip_process.html
skip_code = skip_code.replace('id="skip-tab"', 'id="skip-tab"')
skip_code = skip_code.replace('id="outbound-tab" class="nav-link active"', 'id="outbound-tab" class="nav-link"')
skip_code = skip_code.replace('id="skip-tab" class="nav-link"', 'id="skip-tab" class="nav-link active"')
skip_code = skip_code.replace('id="outbound-pane" class="tab-pane fade show active"', 'id="outbound-pane" class="tab-pane fade"')
skip_code = skip_code.replace('id="skip-pane" class="tab-pane fade"', 'id="skip-pane" class="tab-pane fade show active"')

with open('skip_process.html', 'w', encoding='utf-8') as f:
    f.write(skip_code)
print("Created skip_process.html")

# 4. CUTOFF & TTB MASTER PAGE (cutoff_master.html)
cutoff_master_html = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SOC Cutoff Schedule & TTB Master</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <style>
    body {{
      background-color: #f4f6f9;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      color: #1e293b;
      padding-bottom: 50px;
    }}
    .card-custom {{
      background: #ffffff;
      border-radius: 12px;
      border: none;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
      margin-bottom: 24px;
    }}
    .nav-tabs .nav-link {{
      font-weight: 600;
      color: #64748b;
      border: none;
      border-bottom: 3px solid transparent;
      padding: 12px 20px;
    }}
    .nav-tabs .nav-link.active {{
      color: #2563eb;
      border-bottom-color: #2563eb;
      background: transparent;
    }}
    .table-custom {{
      font-size: 0.88rem;
    }}
    .table-custom th {{
      background-color: #0f172a;
      color: #ffffff;
      font-weight: 600;
      vertical-align: middle;
    }}
    .badge-cutoff {{
      font-size: 0.78rem;
      padding: 4px 8px;
      border-radius: 6px;
    }}
  </style>
</head>
<body>

  {get_navbar('cutoff')}

  <div class="container-fluid px-4 py-3">

    <!-- Header Banner -->
    <div class="d-flex justify-content-between align-items-center mb-4 bg-white p-3 rounded-3 shadow-sm border">
      <div>
        <h4 class="fw-bold mb-1 text-slate-800"><i class="fa-solid fa-clock text-warning me-2"></i> SOC Cutoff Schedule & Truck Timetable (TTB) Master</h4>
        <p class="text-muted small mb-0">ค้นหารอบเวลา Cutoff มาตรฐาน (UPC Direct, Milkrun, GBKK) และตารางรถวิ่ง TTB รายวัน</p>
      </div>
      <div>
        <span class="badge bg-primary px-3 py-2 fs-6" id="totalMasterRecordsBadge"><i class="fa-solid fa-database me-1"></i> Loading Master Data...</span>
      </div>
    </div>

    <!-- Nav Tabs -->
    <ul class="nav nav-tabs mb-4" id="masterTabs" role="tablist">
      <li class="nav-item">
        <button class="nav-link active" id="cutoff-tab" data-bs-toggle="tab" data-bs-target="#cutoff-pane"><i class="fa-solid fa-list-check me-2"></i> 1. Cutoff Schedule (287 Stations)</button>
      </li>
      <li class="nav-item">
        <button class="nav-link" id="ttb-tab" data-bs-toggle="tab" data-bs-target="#ttb-pane"><i class="fa-solid fa-truck-moving me-2"></i> 2. Truck Timetable (TTB Master)</button>
      </li>
    </ul>

    <div class="tab-content" id="masterTabContent">
      
      <!-- TAB 1: CUTOFF SCHEDULE -->
      <div class="tab-pane fade show active" id="cutoff-pane">
        <div class="card-custom p-4">
          <div class="row g-3 mb-3">
            <div class="col-md-5">
              <label class="form-label fw-bold small text-muted">🔍 ค้นหาสถานี / รหัส / จังหวัด / ประเภท</label>
              <input type="text" class="form-control" id="cutoffSearchInput" placeholder="พิมพ์ชื่อสถานี เช่น 2AYT, NPM, หนองเสือ, ลพบุรี..." onkeyup="filterCutoffTable()">
            </div>
            <div class="col-md-3">
              <label class="form-label fw-bold small text-muted">📍 กรองสายงาน (Area Group)</label>
              <select class="form-select" id="cutoffAreaSelect" onchange="filterCutoffTable()">
                <option value="ALL">-- ทุกสายงาน (All Areas) --</option>
                <option value="UPC Direct">UPC Direct (187 สถานี)</option>
                <option value="UPC Milkrun">UPC Milkrun (48 สถานี)</option>
                <option value="GBKK">GBKK (56 สถานี)</option>
              </select>
            </div>
            <div class="col-md-4 d-flex align-items-end justify-content-end">
              <span class="text-muted small" id="cutoffCountText">แสดงผล 0 จาก 0 สถานี</span>
            </div>
          </div>

          <div class="table-responsive">
            <table class="table table-hover align-middle table-custom border" id="cutoffTable">
              <thead>
                <tr>
                  <th>#</th>
                  <th>สายงาน</th>
                  <th>รหัสสถานี</th>
                  <th>ชื่อสถานีปลายทาง</th>
                  <th>จังหวัด / อำเภอ</th>
                  <th>ประเภท</th>
                  <th>Cut 0 (OB / Arr / Trv)</th>
                  <th>Cut 1 (OB / Arr / Rec / Trv)</th>
                  <th>Cut 2 (OB / Arr / Rec / Trv)</th>
                  <th>Cut 3 (OB / Arr / Trv)</th>
                </tr>
              </thead>
              <tbody id="cutoffTableBody">
                <tr><td colspan="10" class="text-center py-4 text-muted">กำลังโหลดข้อมูล Cutoff Master...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 2: TTB SCHEDULE -->
      <div class="tab-pane fade" id="ttb-pane">
        <div class="card-custom p-4">
          
          <!-- Day Filter Buttons with Auto Detect Badge -->
          <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
            <div class="d-flex gap-2 flex-wrap" id="ttbDayButtons">
              <button class="btn btn-outline-primary" onclick="switchTTBDay('Mon TTB', this)"><i class="fa-solid fa-calendar-day me-1"></i> จันทร์ (Mon TTB)</button>
              <button class="btn btn-outline-primary" onclick="switchTTBDay('Tue TTB', this)"><i class="fa-solid fa-calendar-day me-1"></i> อังคาร (Tue TTB)</button>
              <button class="btn btn-outline-primary" onclick="switchTTBDay('Wed-Sat TTB', this)"><i class="fa-solid fa-calendar-day me-1"></i> พุธ - เสาร์ (Wed-Sat TTB)</button>
              <button class="btn btn-outline-primary" onclick="switchTTBDay('Sun TTB', this)"><i class="fa-solid fa-calendar-day me-1"></i> อาทิตย์ (Sun TTB)</button>
            </div>
            <span class="badge bg-success bg-opacity-15 text-success border border-success px-3 py-2" id="ttbAutoDetectBadge"><i class="fa-solid fa-robot me-1"></i> ตรวจจับวันประจำสัปดาห์อัตโนมัติ</span>
          </div>

          <div class="row g-3 mb-3">
            <div class="col-md-4">
              <label class="form-label fw-bold small text-muted">🔍 ค้นหาสายรถ / สถานี / หมายเหตุ</label>
              <input type="text" class="form-control" id="ttbSearchInput" placeholder="พิมพ์ชื่อสายรถ เช่น AAUTH, 4ล้อ, COT..." onkeyup="filterTTBTable()">
            </div>
            <div class="col-md-3">
              <label class="form-label fw-bold small text-muted">🚩 กรอง Zone</label>
              <select class="form-select" id="ttbZoneSelect" onchange="filterTTBTable()">
                <option value="ALL">-- ทุก Zone --</option>
                <option value="CE">CE</option>
                <option value="CW">CW</option>
                <option value="NE">NE</option>
                <option value="N">N</option>
                <option value="S">S</option>
              </select>
            </div>
            <div class="col-md-5 d-flex align-items-end justify-content-end">
              <span class="text-muted small" id="ttbCountText">แสดงผล 0 เที่ยวรถ</span>
            </div>
          </div>

          <div class="table-responsive">
            <table class="table table-hover align-middle table-custom border" id="ttbTable">
              <thead>
                <tr>
                  <th>#</th>
                  <th>สายรถ (Route)</th>
                  <th>สถานีปลายทาง</th>
                  <th>Standby</th>
                  <th>Loading</th>
                  <th>Depart</th>
                  <th>ประเภทรถ</th>
                  <th>Zone</th>
                  <th>Dock</th>
                  <th>Vendor</th>
                  <th>หมายเหตุ</th>
                </tr>
              </thead>
              <tbody id="ttbTableBody">
                <tr><td colspan="11" class="text-center py-4 text-muted">กำลังโหลดข้อมูล TTB Master...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

    </div>

  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    let globalCutoffData = [];
    let globalTTBData = {{}};
    let activeTTBDay = 'Wed-Sat TTB';

    document.addEventListener('DOMContentLoaded', () => {{
      fetchCutoffData();
      fetchTTBData();
    }});

    function fetchCutoffData() {{
      fetch('/api/cutoff-schedule')
        .then(res => res.json())
        .then(data => {{
          if (data.success && data.data) {{
            globalCutoffData = data.data;
            document.getElementById('totalMasterRecordsBadge').innerHTML = `<i class="fa-solid fa-check-double me-1"></i> ${{data.total}} Stations Loaded`;
            renderCutoffTable(globalCutoffData);
          }}
        }})
        .catch(err => console.error(err));
    }}

    function renderCutoffTable(list) {{
      const tbody = document.getElementById('cutoffTableBody');
      document.getElementById('cutoffCountText').innerText = `แสดงผล ${{list.length.toLocaleString()}} จาก ${{globalCutoffData.length.toLocaleString()}} สถานี`;
      
      if (list.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4 text-muted">ไม่พบข้อมูลที่ค้นหา</td></tr>';
        return;
      }}

      tbody.innerHTML = list.map((item, idx) => {{
        const fmtCut = (ob, arr, rec, trv) => {{
          if (!ob && !arr && !rec) return '<span class="text-muted">-</span>';
          let parts = [];
          if (ob) parts.push(`OB: <b>${{ob}}</b>`);
          if (arr) parts.push(`Arr: <b>${{arr}}</b>`);
          if (rec) parts.push(`Rec: <b>${{rec}}</b>`);
          return parts.join(' | ');
        }};

        const c0 = fmtCut(item.cut0_ob, item.cut0_arr, '', item.cut0_travel);
        const c1 = fmtCut(item.cut1_ob, item.cut1_arr, item.cut1_rec, item.cut1_travel);
        const c2 = fmtCut(item.cut2_ob, item.cut2_arr, item.cut2_rec, item.cut2_travel);
        const c3 = fmtCut(item.cut3_ob, item.cut3_arr, '', item.cut3_travel);

        const areaBadge = item.area_group === 'UPC Direct' ? 'bg-primary' : (item.area_group === 'UPC Milkrun' ? 'bg-purple' : 'bg-success');

        return `<tr>
          <td class="text-muted small">${{idx + 1}}</td>
          <td><span class="badge ${{areaBadge}}" style="font-size:0.75rem;">${{item.area_group}}</span></td>
          <td class="fw-bold text-primary">${{item.station_id || '-'}}</td>
          <td class="fw-bold text-dark">${{item.station_name}}</td>
          <td class="small">${{item.province || ''}} ${{item.district ? ' / ' + item.district : ''}}</td>
          <td><span class="badge bg-secondary" style="font-size:0.7rem;">${{item.op_type || item.route_type}}</span></td>
          <td class="small">${{c0}}</td>
          <td class="small">${{c1}}</td>
          <td class="small">${{c2}}</td>
          <td class="small">${{c3}}</td>
        </tr>`;
      }}).join('');
    }}

    function filterCutoffTable() {{
      const query = document.getElementById('cutoffSearchInput').value.toLowerCase().trim();
      const area = document.getElementById('cutoffAreaSelect').value;

      const filtered = globalCutoffData.filter(item => {{
        const matchArea = area === 'ALL' || item.area_group === area;
        const textStr = `${{item.station_name}} ${{item.station_id}} ${{item.province}} ${{item.district}} ${{item.op_type}}`.toLowerCase();
        const matchQuery = !query || textStr.includes(query);
        return matchArea && matchQuery;
      }});

      renderCutoffTable(filtered);
    }}

    function fetchTTBData() {{
      fetch('/api/ttb-schedule')
        .then(res => res.json())
        .then(data => {{
          if (data.success && data.sheets) {{
            globalTTBData = data.sheets;
            if (data.active_sheet) {{
              activeTTBDay = data.active_sheet;
              document.querySelectorAll('#ttbDayButtons .btn').forEach(btn => {{
                if (btn.getAttribute('onclick').includes(activeTTBDay)) {{
                  btn.classList.add('btn-primary', 'text-white', 'fw-bold');
                  btn.classList.remove('btn-outline-primary');
                }} else {{
                  btn.classList.remove('btn-primary', 'text-white', 'fw-bold');
                  btn.classList.add('btn-outline-primary');
                }}
              }});
              const autoBadge = document.getElementById('ttbAutoDetectBadge');
              if (autoBadge) autoBadge.innerHTML = `<i class="fa-solid fa-robot me-1"></i> ตรวจจับวันอัตโนมัติ -> เลือก <b>${{activeTTBDay}}</b> ให้อัตโนมัติ`;
            }}
            renderTTBTable();
          }}
        }})
        .catch(err => console.error(err));
    }}

    function switchTTBDay(daySheet, btn) {{
      activeTTBDay = daySheet;
      document.querySelectorAll('#ttbDayButtons .btn').forEach(b => {{
        b.classList.remove('btn-primary', 'text-white', 'fw-bold');
        b.classList.add('btn-outline-primary');
      }});
      btn.classList.add('btn-primary', 'text-white', 'fw-bold');
      btn.classList.remove('btn-outline-primary');
      renderTTBTable();
    }}

    function renderTTBTable() {{
      const list = globalTTBData[activeTTBDay] || [];
      const query = document.getElementById('ttbSearchInput').value.toLowerCase().trim();
      const zone = document.getElementById('ttbZoneSelect').value;

      const filtered = list.filter(item => {{
        const matchZone = zone === 'ALL' || item.zone === zone;
        const textStr = `${{item.route}} ${{item.station1}} ${{item.station2}} ${{item.vehicle_type}} ${{item.vendor}} ${{item.comment}}`.toLowerCase();
        const matchQuery = !query || textStr.includes(query);
        return matchZone && matchQuery;
      }});

      const tbody = document.getElementById('ttbTableBody');
      document.getElementById('ttbCountText').innerText = `แสดงผล ${{filtered.length.toLocaleString()}} เที่ยวรถ (${{activeTTBDay}})`;

      if (filtered.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="11" class="text-center py-4 text-muted">ไม่พบเที่ยวรถในวันและเงื่อนไขที่เลือก</td></tr>';
        return;
      }}

      tbody.innerHTML = filtered.map((item, idx) => {{
        const fmtTime = (t) => t ? `<span class="fw-bold text-dark">${{t}}</span>` : '-';
        return `<tr>
          <td class="text-muted small">${{idx + 1}}</td>
          <td class="fw-bold text-primary">${{item.route}}</td>
          <td>${{item.station1}} ${{item.station2 ? ' / ' + item.station2 : ''}}</td>
          <td>${{fmtTime(item.standby)}}</td>
          <td>${{fmtTime(item.loading)}}</td>
          <td>${{fmtTime(item.depart)}}</td>
          <td><span class="badge bg-info text-dark">${{item.vehicle_type}}</span></td>
          <td><span class="badge bg-dark">${{item.zone || '-'}}</span></td>
          <td>${{item.dock || '-'}}</td>
          <td class="small">${{item.vendor || '-'}}</td>
          <td class="small text-muted">${{item.comment || '-'}}</td>
        </tr>`;
      }}).join('');
    }}

    function filterTTBTable() {{
      renderTTBTable();
    }}
  </script>
</body>
</html>
"""

with open('cutoff_master.html', 'w', encoding='utf-8') as f:
    f.write(cutoff_master_html)

print("Created cutoff_master.html")

