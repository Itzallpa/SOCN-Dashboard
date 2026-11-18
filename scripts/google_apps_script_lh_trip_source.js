/**
 * =========================================================================================
 * 🚚 LH Trip source relay — read the company Google Sheet ("Table" tab) for the OB Dashboard
 * =========================================================================================
 * The company sheet is not public, so the dashboard server cannot read it directly (HTTP 401).
 * This script runs as YOUR COMPANY ACCOUNT. Workspace only allows "Anyone within Shopee Mobile",
 * so the LH Trip page calls it from the browser (JSONP, company login) and forwards the rows
 * to the dashboard server.
 *
 * Deploy (once, logged in with the company email):
 *   1. https://script.google.com -> New project -> paste this file
 *   2. Run "testReadLhTrip" once -> Allow permissions -> check the log (headers + row count)
 *   3. Deploy -> New deployment -> type "Web app"
 *        Execute as: Me (company email)   |   Who has access: Anyone within Shopee Mobile
 *      (after editing the code: Manage deployments -> Edit -> Version "New version" -> Deploy;
 *       the URL stays the same)
 *   4. Copy the Web app URL (.../exec) -> LH Trip page -> "ตั้งค่าแหล่งข้อมูล"
 *      -> paste it in "Apps Script URL (เมลบริษัท)"
 *
 * Requests must carry the dashboard API key (same as GAS_API_KEY in app.py).
 * Response: { success, page: "lhtrip", headers: [...], rows: [[...], ...] }  (display values,
 * same as the old "Publish to web" CSV so the dashboard parser does not change)
 * =========================================================================================
 */

const LH_TRIP_SOURCE_CONFIG = {
  API_SECRET_KEY: "SOCN_OBBL_2026_SECRET_KEY_XK9M3",
  DEFAULT_SPREADSHEET_ID: "1gH3gDAuf0CWKYthnua50qLWC3gUWYovMVMN1hUKyFJo",
  DEFAULT_SHEET_NAME: "Table",
  DEFAULT_GID: "206460461",
  HEADER_ROW: 1
};

function doPost(e) {
  let params = {};
  try {
    params = e && e.postData && e.postData.contents ? JSON.parse(e.postData.contents) : {};
  } catch (err) {
    return jsonOut_({ success: false, error: "Invalid JSON body" });
  }
  return jsonOut_(safeHandle_(params));
}

// GET + callback=... → JSONP. The LH Trip page uses this from a browser logged in with the
// company account, because access is "Anyone within Shopee Mobile" (the server cannot call it).
function doGet(e) {
  const params = (e && e.parameter) || {};
  if (params.mode === "popup") return popupPage_(params);
  const result = safeHandle_(params);
  const cb = String(params.callback || "");
  if (cb && /^[A-Za-z_$][\w$]{0,63}$/.test(cb)) {
    return ContentService.createTextOutput(cb + "(" + JSON.stringify(result) + ");")
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  return jsonOut_(result);
}

function safeHandle_(params) {
  try {
    return handleRequest_(params);
  } catch (err) {
    return { success: false, error: String(err && err.message || err) };
  }
}

function handleRequest_(params) {
  if (!params.key || params.key !== LH_TRIP_SOURCE_CONFIG.API_SECRET_KEY) {
    return { success: false, error: "Unauthorized: Invalid API Key" };
  }
  const page = String(params.page || "lhtrip").toLowerCase();
  if (page !== "lhtrip") {
    return { success: false, error: "Unknown page: " + page };
  }
  return readLhTrip_(params.spreadsheetId, params.gid, params.sheetName);
}

function readLhTrip_(spreadsheetId, gid, sheetName) {
  const cfg = LH_TRIP_SOURCE_CONFIG;
  const ss = SpreadsheetApp.openById(spreadsheetId || cfg.DEFAULT_SPREADSHEET_ID);

  let sh = null;
  const wantGid = String(gid || (spreadsheetId ? "" : cfg.DEFAULT_GID) || "");
  if (wantGid) sh = ss.getSheets().filter(s => String(s.getSheetId()) === wantGid)[0] || null;
  if (!sh) sh = ss.getSheetByName(sheetName || cfg.DEFAULT_SHEET_NAME);
  if (!sh) throw new Error(`ไม่พบแท็บ gid=${wantGid} / "${sheetName || cfg.DEFAULT_SHEET_NAME}"`);

  const lastRow = sh.getLastRow();
  const lastCol = sh.getLastColumn();
  if (lastRow < cfg.HEADER_ROW || lastCol < 1) {
    return { success: true, page: "lhtrip", sheet: sh.getName(), headers: [], rows: [] };
  }
  const values = sh.getRange(cfg.HEADER_ROW, 1, lastRow - cfg.HEADER_ROW + 1, lastCol).getDisplayValues();
  const headers = values[0];
  const rows = values.slice(1).filter(r => r.some(v => String(v).trim() !== ""));

  return {
    success: true,
    page: "lhtrip",
    spreadsheetName: ss.getName(),
    sheet: sh.getName(),
    gid: String(sh.getSheetId()),
    fetchedAt: Utilities.formatDate(new Date(), ss.getSpreadsheetTimeZone(), "yyyy-MM-dd HH:mm:ss"),
    totalRows: rows.length,
    headers: headers,
    rows: rows
  };
}

// ===== Popup mode: the LH Trip page opens .../exec?mode=popup&... in a small window.
// A popup is a normal (first-party) page visit, so Google asks for the company login right there
// and it works even when the browser blocks third-party cookies. The popup reads the sheet and
// sends it back to the dashboard (postMessage to the opener; if that is not possible, POST to the
// dashboard server), then repeats every 10 minutes while it stays open.
function getLhTripForPopup(key, spreadsheetId, gid) {
  return safeHandle_({ key: key, page: "lhtrip", spreadsheetId: spreadsheetId, gid: gid });
}

function popupPage_(params) {
  const origin = String(params.origin || "");
  if (!/^https?:\/\/[^\/\s"'<>]+$/.test(origin)) {
    return HtmlService.createHtmlOutput("<p>Invalid origin</p>");
  }
  const cfg = {
    key: String(params.key || ""),
    spreadsheetId: String(params.spreadsheetId || ""),
    gid: String(params.gid || ""),
    origin: origin
  };
  const cfgJson = JSON.stringify(cfg).replace(/</g, "\\u003c");
  const html = `<!doctype html><html><head><meta charset="utf-8"><base target="_top">
<style>body{font-family:Arial,sans-serif;padding:20px;color:#1e293b}.ok{color:#15803d}.err{color:#b91c1c}small{color:#64748b}</style>
</head><body>
<h3>🚚 SOCN LH Trip Sync</h3>
<div id="st">กำลังอ่านข้อมูลจาก Google Sheet...</div>
<p><small>หน้าต่างนี้ใช้บัญชีเมลบริษัทของคุณดึงข้อมูลส่งให้ Dashboard · เปิดทิ้งไว้ (ย่อได้) เพื่อ Sync อัตโนมัติทุก 10 นาที</small></p>
<script>
const CFG = ${cfgJson};
function st(html, cls) { const el = document.getElementById('st'); el.className = cls || ''; el.innerHTML = html; }
function getOpener() { try { return window.top.opener || null; } catch (e) { return null; } }
function deliver(res) {
  const op = getOpener();
  if (op) {
    op.postMessage({ type: 'socn-lhtrip', result: res }, CFG.origin);
    return Promise.resolve('Dashboard');
  }
  return fetch(CFG.origin + '/api/lh-trip/ingest-sheet', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ headers: res.headers, rows: res.rows, fetchedAt: res.fetchedAt, sheet: res.sheet, via: 'popup' })
  }).then(r => r.json()).then(d => { if (!d.success) throw new Error(d.error || 'server error'); return 'Server'; });
}
function run() {
  st('กำลังอ่านข้อมูลจาก Google Sheet...');
  google.script.run
    .withSuccessHandler(res => {
      if (!res || !res.success) { st('⚠️ ' + ((res && res.error) || 'อ่านข้อมูลไม่สำเร็จ'), 'err'); return; }
      deliver(res)
        .then(via => st('✅ ส่งข้อมูล ' + res.totalRows.toLocaleString() + ' แถว ให้ ' + via + ' แล้ว (' + new Date().toLocaleTimeString() + ')<br><small>จะ Sync ใหม่อัตโนมัติทุก 10 นาที</small>', 'ok'))
        .catch(err => st('⚠️ ส่งข้อมูลให้ Dashboard ไม่สำเร็จ: ' + err.message, 'err'));
    })
    .withFailureHandler(err => st('⚠️ ' + (err && err.message || err), 'err'))
    .getLhTripForPopup(CFG.key, CFG.spreadsheetId, CFG.gid);
}
run();
setInterval(run, 10 * 60 * 1000);
</script></body></html>`;
  return HtmlService.createHtmlOutput(html).setTitle("SOCN LH Trip Sync");
}

function jsonOut_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/** Run once in the editor to authorize and check the result in the log. */
function testReadLhTrip() {
  const r = readLhTrip_();
  Logger.log(`${r.spreadsheetName} / ${r.sheet}: ${r.totalRows} rows`);
  Logger.log(JSON.stringify(r.headers));
  Logger.log(JSON.stringify(r.rows.slice(0, 2)));
}
