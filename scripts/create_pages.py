import os

print("Generating modular HTML pages...")

nav_header_html = """
  <!-- Top Navigation Header -->
  <nav style="background:#0d1b2a; color:#ffffff; padding:14px 28px; display:flex; align-items:center; justify-content:space-between; box-shadow:0 4px 14px rgba(0,0,0,0.25); position:sticky; top:0; z-index:9999;">
    <a href="index.html" style="color:#ffffff; font-size:1.2rem; font-weight:800; text-decoration:none; display:flex; align-items:center; gap:10px;">
      <span style="font-size:1.5rem;">📦</span> SOC Operations Portal
    </a>
    <div style="display:flex; gap:10px; flex-wrap:wrap;">
      <a href="index.html" style="color:#cbd5e1; text-decoration:none; padding:7px 14px; border-radius:6px; font-weight:600; font-size:0.88rem; background:rgba(255,255,255,0.08); transition:all 0.2s;">🏠 Portal Hub</a>
      <a href="investigation.html" style="color:#cbd5e1; text-decoration:none; padding:7px 14px; border-radius:6px; font-weight:600; font-size:0.88rem; background:rgba(255,255,255,0.08); transition:all 0.2s;">🚀 Investigation</a>
      <a href="skip_process.html" style="color:#cbd5e1; text-decoration:none; padding:7px 14px; border-radius:6px; font-weight:600; font-size:0.88rem; background:rgba(255,255,255,0.08); transition:all 0.2s;">📦 Skip Monitor</a>
      <a href="cutoff_master.html" style="color:#cbd5e1; text-decoration:none; padding:7px 14px; border-radius:6px; font-weight:600; font-size:0.88rem; background:rgba(255,255,255,0.08); transition:all 0.2s;">⏰ Cutoff & TTB Master</a>
    </div>
  </nav>
"""

# 1. LANDING PORTAL (index.html)
portal_html = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SOC Operations Portal - Control Center</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
  <style>
    body {{
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      color: #f8fafc;
      font-family: 'Segoe UI', Roboto, sans-serif;
      min-height: 100vh;
      padding-bottom: 50px;
    }}
    .hero-card {{
      background: linear-gradient(135deg, rgba(37, 99, 235, 0.25) 0%, rgba(124, 58, 237, 0.25) 100%);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 20px;
      padding: 40px;
      margin-top: 30px;
      margin-bottom: 40px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.4);
    }}
    .hero-title {{
      font-size: 2.5rem;
      font-weight: 800;
      background: linear-gradient(90deg, #60a5fa, #a78bfa);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .feature-card {{
      background: rgba(30, 41, 59, 0.75);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 18px;
      padding: 32px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .feature-card:hover {{
      transform: translateY(-8px);
      box-shadow: 0 20px 35px rgba(0, 0, 0, 0.45);
      border-color: rgba(96, 165, 250, 0.5);
    }}
    .icon-box {{
      width: 64px;
      height: 64px;
      border-radius: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.8rem;
      margin-bottom: 24px;
    }}
    .icon-blue {{ background: rgba(37, 99, 235, 0.25); color: #60a5fa; }}
    .icon-purple {{ background: rgba(124, 58, 237, 0.25); color: #c084fc; }}
    .icon-amber {{ background: rgba(217, 119, 6, 0.25); color: #fbbf24; }}

    .btn-action {{
      width: 100%;
      padding: 14px;
      border-radius: 12px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      text-decoration: none;
      transition: all 0.2s;
    }}
    .btn-blue {{ background: #2563eb; color: #ffffff; }}
    .btn-blue:hover {{ background: #1d4ed8; color: #ffffff; }}
    
    .btn-purple {{ background: #7c3aed; color: #ffffff; }}
    .btn-purple:hover {{ background: #6d28d9; color: #ffffff; }}
    
    .btn-amber {{ background: #d97706; color: #ffffff; }}
    .btn-amber:hover {{ background: #b45309; color: #ffffff; }}
  </style>
</head>
<body>

  {nav_header_html}

  <div class="container py-4">

    <!-- Hero Section -->
    <div class="hero-card">
      <div class="row align-items-center">
        <div class="col-lg-8">
          <div class="mb-3">
            <span class="badge bg-success bg-opacity-20 text-success border border-success px-3 py-2 rounded-pill fw-bold">
              <i class="fa-solid fa-circle-check me-1"></i> Operations Portal Active
            </span>
          </div>
          <h1 class="hero-title mb-2">SOC Operations Control Center</h1>
          <p class="text-slate-300 fs-5 mb-0">ศูนย์รวมระบบตรวจสอบ Outbound 2nd Cutoff, ติดตาม Skip Process & Volume Tracker และค้นหารอบเวลา Cutoff & TTB Master</p>
        </div>
        <div class="col-lg-4 text-lg-end mt-4 mt-lg-0">
          <div class="p-3 rounded-3" style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);">
            <div class="text-muted small">System Status</div>
            <div class="fw-bold fs-6 text-light mt-1"><i class="fa-solid fa-server text-success me-1"></i> Multi-Page Architecture Ready</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Portal Navigation Cards -->
    <div class="row g-4">
      
      <!-- Module 1 -->
      <div class="col-lg-4 col-md-6">
        <div class="feature-card">
          <div>
            <div class="icon-box icon-blue">
              <i class="fa-solid fa-magnifying-glass-chart"></i>
            </div>
            <h3 class="fw-bold text-white fs-4 mb-3">1. Outbound Investigation</h3>
            <p class="text-slate-400 lh-lg mb-4">ระบบตรวจสอบพัสดุสายงาน Outbound รอบที่ 2 สรุปเคสสายพัสดุล่าช้า, โซนที่ได้รับผลกระทบ, Workload รายทีมงาน FTE/Aug และการจำแนกสถานีปลายทาง</p>
          </div>
          <div>
            <div class="d-flex justify-content-between text-slate-400 small mb-3 border-top border-slate-700 pt-3">
              <span><i class="fa-solid fa-file-csv text-info me-1"></i> Outbound CSV</span>
              <span class="text-success">Live Analysis</span>
            </div>
            <a href="investigation.html" class="btn-action btn-blue">
              <span>เข้าสู่ระบบ Outbound Investigation</span>
              <i class="fa-solid fa-arrow-right"></i>
            </a>
          </div>
        </div>
      </div>

      <!-- Module 2 -->
      <div class="col-lg-4 col-md-6">
        <div class="feature-card">
          <div>
            <div class="icon-box icon-purple">
              <i class="fa-solid fa-box-archive"></i>
            </div>
            <h3 class="fw-bold text-white fs-4 mb-3">2. Skip Process Monitor</h3>
            <p class="text-slate-400 lh-lg mb-4">ระบบติดตามเคสพัสดุข้ามขั้นตอน (Skip Process), ตารางบันทึกตัวเลข SOCN Actual รายวันย้อนหลัง และการคำนวณ % อัตราส่วน Skip ตามโซน</p>
          </div>
          <div>
            <div class="d-flex justify-content-between text-slate-400 small mb-3 border-top border-slate-700 pt-3">
              <span><i class="fa-solid fa-database text-warning me-1"></i> Volume Tracker</span>
              <span class="text-success">Shared Sync</span>
            </div>
            <a href="skip_process.html" class="btn-action btn-purple">
              <span>เข้าสู่ระบบ Skip Process Monitor</span>
              <i class="fa-solid fa-arrow-right"></i>
            </a>
          </div>
        </div>
      </div>

      <!-- Module 3 -->
      <div class="col-lg-4 col-md-6">
        <div class="feature-card">
          <div>
            <div class="icon-box icon-amber">
              <i class="fa-solid fa-clock-rotate-left"></i>
            </div>
            <h3 class="fw-bold text-white fs-4 mb-3">3. Cutoff & TTB Master</h3>
            <p class="text-slate-400 lh-lg mb-4">ศูนย์ค้นหารอบเวลา Cutoff มาตรฐานแยกตามสถานี (UPC Direct, Milkrun, GBKK) และตารางเวลาเดินรถตู้/รถใหญ่ Truck Timetable (TTB) รายวัน</p>
          </div>
          <div>
            <div class="d-flex justify-content-between text-slate-400 small mb-3 border-top border-slate-700 pt-3">
              <span><i class="fa-solid fa-truck-fast text-danger me-1"></i> 287 Stations & TTB</span>
              <span class="text-success">Master Lookup</span>
            </div>
            <a href="cutoff_master.html" class="btn-action btn-amber">
              <span>เข้าสู่ระบบ Cutoff & TTB Master</span>
              <i class="fa-solid fa-arrow-right"></i>
            </a>
          </div>
        </div>
      </div>

    </div>

  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(portal_html)

print("Created index.html (Portal Hub)")

