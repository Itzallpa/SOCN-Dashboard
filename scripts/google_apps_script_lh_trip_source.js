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
 *
 * Daily raw data (folder DAILY_FOLDER_ID, files like "LH Trip 17 Nov 26" = copy of "raw data"):
 *   5. Run "testDaily" once -> Allow (Drive + TTB sheet) -> check the log
 *   6. Optional: run "installDailyTrigger" once -> also saves the raw data tab every day at 14:00
 *      ("saveTodayNow" = save right now). The LH Trip page lists/reads the files
 *      (page=listdaily / readdaily / refs) and computes the Table logic itself.
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
  HEADER_ROW: 1,
  // ---- Daily raw-data archive (one Google Sheet per day in this Drive folder) ----
  DAILY_FOLDER_ID: "1Hfh6tB1_6j2en2LiR1V98ER0q-_qXaCQ",
  DAILY_FILE_PREFIX: "LH Trip ",         // + "17 Nov 26"
  DAILY_SAVE_HOUR: 14,                   // auto save time (installDailyTrigger)
  RAW_SHEET_NAME: "raw data",
  TTB_SPREADSHEET_ID: "1uQhxe1w3CBhXfWeOzg5y-3Udb6_m52SbBBmUzFJzdL4",
  // [SPX-SOCN] Outbound Daily Report - 2026: 'Outbound Email'!B:C = hub -> zone A/B/C (Hourly Tracker)
  OBD_SPREADSHEET_ID: "1b23i0TPw1NHQAoj-D3YeDe4khnXFn_d0MmxfFniuq-k",
  TIME_ZONE: "Asia/Bangkok"
};

const RELAY_VERSION_ = "2026-11-19 productivity-tab";

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
  const page = String(params.page || "lhtrip").toLowerCase();
  // no key needed: shows which code version is deployed at this URL
  if (page === "version") return { success: true, page: "version", version: RELAY_VERSION_ };
  if (!params.key) return { success: false, error: "Unauthorized: missing key (version " + RELAY_VERSION_ + ")" };
  if (params.key !== LH_TRIP_SOURCE_CONFIG.API_SECRET_KEY) {
    return { success: false, error: "Unauthorized: Invalid API Key (version " + RELAY_VERSION_ + ")" };
  }
  if (page === "lhtrip") return readLhTrip_(params.spreadsheetId, params.gid, params.sheetName);
  if (page === "listdaily") return listDailyRaw_();
  if (page === "readdaily") return readDailyRaw_(params.fileId, params.sheetName);
  if (page === "refs") return readRefs_();
  if (page === "savedaily") return saveDailyRaw_(params.date);
  if (page === "sheetinfo") return sheetInfo_(params.spreadsheetId);
  if (page === "dump") return dumpSheet_(params.spreadsheetId, params.sheetName, params.startRow, params.maxRows, params.maxCols);
  return { success: false, error: "Unknown page: " + page };
}

// =========================================================================================
// Daily raw-data archive. Files in DAILY_FOLDER_ID are copies of the "raw data" tab, named
// like "LH Trip 17 Nov 26" (saved by hand or by dailySaveJob). The dashboard lists and reads
// them and computes the Table logic itself, using the reference tables from page=refs.
// =========================================================================================
const MONTHS_ = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// raw-data columns the dashboard needs (by header name) — keeps the JSONP response small
const RAW_KEEP_HEADERS_ = [
  "LH Trip Number", "LH Trip Name", "Station Number", "Station Name", "Vehicle Type",
  "Vehicle Plate Number", "Driver", "Assign time", "Actual Departure Time",
  "Outbound(order)", "Outbound(weight)(KG)", "Sealed time"
];

function dailyFolder_() {
  return DriveApp.getFolderById(LH_TRIP_SOURCE_CONFIG.DAILY_FOLDER_ID);
}

/** "LH Trip 17 Nov 26" / "LH Trip 2026-11-17" -> "2026-11-17" ("" if no date in the name). */
function dateFromName_(name) {
  let m = /(\d{4})-(\d{2})-(\d{2})/.exec(name);
  if (m) return m[1] + "-" + m[2] + "-" + m[3];
  m = /(\d{1,2})\s*([A-Za-z]{3})[A-Za-z]*\s*(\d{2,4})/.exec(name);
  if (m) {
    const mon = MONTHS_.map(x => x.toLowerCase()).indexOf(m[2].toLowerCase());
    if (mon >= 0) {
      const y = m[3].length === 2 ? "20" + m[3] : m[3];
      return y + "-" + String(mon + 1).padStart(2, "0") + "-" + String(m[1]).padStart(2, "0");
    }
  }
  return "";
}

function dailyFileName_(dateStr) {
  const p = dateStr.split("-");
  return LH_TRIP_SOURCE_CONFIG.DAILY_FILE_PREFIX + Number(p[2]) + " " + MONTHS_[Number(p[1]) - 1] + " " + p[0].slice(2);
}

function todayStr_() {
  return Utilities.formatDate(new Date(), LH_TRIP_SOURCE_CONFIG.TIME_ZONE, "yyyy-MM-dd");
}

/** List the daily files (newest date first). */
function listDailyRaw_() {
  const cfg = LH_TRIP_SOURCE_CONFIG;
  const it = dailyFolder_().getFilesByType(MimeType.GOOGLE_SHEETS);
  const files = [];
  while (it.hasNext()) {
    const f = it.next();
    const d = dateFromName_(f.getName());
    files.push({
      date: d, fileId: f.getId(), name: f.getName(), url: f.getUrl(),
      updatedAt: Utilities.formatDate(f.getLastUpdated(), cfg.TIME_ZONE, "yyyy-MM-dd HH:mm:ss")
    });
  }
  files.sort((a, b) => (b.date || "").localeCompare(a.date || "") || b.updatedAt.localeCompare(a.updatedAt));
  return { success: true, folderId: cfg.DAILY_FOLDER_ID, files: files };
}

function findRawSheet_(ss) {
  return ss.getSheetByName("raw data") ||
    ss.getSheets().filter(s => String(s.getRange(1, 1).getDisplayValue()).trim() === "LH Trip Number")[0] ||
    ss.getSheets()[0];
}

/** Read one daily file (by fileId) — only the columns the dashboard needs. sheetName = a specific tab
 *  (e.g. "Copy of raw data" in the test sheet for the Hourly Tracker); default = the "raw data" tab. */
function readDailyRaw_(fileId, sheetName) {
  if (!fileId) return { success: false, error: "ต้องระบุ fileId" };
  const file = DriveApp.getFileById(fileId);
  const ss = SpreadsheetApp.openById(fileId);
  const sh = sheetName ? ss.getSheetByName(String(sheetName)) : findRawSheet_(ss);
  if (!sh) return { success: false, error: `ไม่พบแท็บ "${sheetName}" ในไฟล์ ${file.getName()}` };
  const values = sh.getDataRange().getDisplayValues();
  const hdr = (values[0] || []).map(h => String(h).trim());
  const idx = RAW_KEEP_HEADERS_.map(h => hdr.indexOf(h));
  if (idx[0] < 0) return { success: false, error: `ไฟล์ ${file.getName()} ไม่มีคอลัมน์ "LH Trip Number" (ต้องเป็นข้อมูลแบบ raw data)` };
  const opsIdx = hdr.length > 48 ? 48 : -1;   // AW = ops date column (when the file has it)
  const rows = [];
  for (let r = 1; r < values.length; r++) {
    const row = values[r];
    if (!String(row[idx[0]] || "").trim()) continue;
    const out = idx.map(i => (i >= 0 ? row[i] : ""));
    out.push(opsIdx >= 0 ? row[opsIdx] : "");
    rows.push(out);
  }
  return {
    success: true, page: "readdaily", fileId: fileId, fileName: file.getName(), fileUrl: file.getUrl(),
    date: dateFromName_(file.getName()), sheet: sh.getName(),
    updatedAt: Utilities.formatDate(file.getLastUpdated(), LH_TRIP_SOURCE_CONFIG.TIME_ZONE, "yyyy-MM-dd HH:mm:ss"),
    headers: RAW_KEEP_HEADERS_.concat(["_opsDate"]), totalRows: rows.length, rows: rows
  };
}

/** Reference tables used by the Table formulas: Hub, Cut times, TTB. */
function readRefs_() {
  const cfg = LH_TRIP_SOURCE_CONFIG;
  const ss = SpreadsheetApp.openById(cfg.DEFAULT_SPREADSHEET_ID);
  const grab = (name, a1) => { const s = ss.getSheetByName(name); return s ? s.getRange(a1).getDisplayValues() : []; };

  // Hub: B=Station Name, E=Region, I=Intentional, L=OBD Zone
  const hub = grab("Hub", "B2:L").filter(r => r[0]).map(r => [r[0], r[3], r[7], r[10]]);
  // Cut sheets: G=LM Station Name, K=Cut0 SOC OB, N=Cut1, R=Cut2, V=Cut3 (rows from 3)
  const cutRows = name => grab(name, "G3:V").filter(r => r[0]).map(r => [r[0], r[4], r[7], r[11], r[15]]);
  const cuts = { gbkk: cutRows("SOCN_GBKK"), upcDirect: cutRows("SOCN_UPC_Direct"), upcMilkrun: cutRows("SOCN_UPC_Milkrun") };

  const ttb = {};
  let ttbError = "";
  try {
    const t = SpreadsheetApp.openById(cfg.TTB_SPREADSHEET_ID);
    ["Mon TTB", "Tue TTB", "Sun TTB", "Wed-Sat TTB"].forEach(n => {
      const s = t.getSheetByName(n);
      if (!s) return;
      const v = s.getRange("A1:N3000").getDisplayValues();
      const h = v[0].map(x => String(x).trim());
      const ri = h.indexOf("Route"), si = h.indexOf("Standby"), di = h.indexOf("Depart");
      if (ri < 0) return;
      ttb[n] = v.slice(1).filter(r => r[ri]).map(r => [r[ri], si >= 0 ? r[si] : "", di >= 0 ? r[di] : ""]);
    });
  } catch (e) {
    ttbError = "อ่านชีท TTB ไม่ได้: " + e;
  }
  // hub -> zone A/B/C used by "Productivity Orders ZONE" (optional: the board falls back to its saved copy)
  const obdZones = {};
  let obdZoneError = "";
  try {
    const v = SpreadsheetApp.openById(cfg.OBD_SPREADSHEET_ID).getSheetByName("Outbound Email").getRange("B2:C").getDisplayValues();
    v.forEach(r => { if (r[0] && r[1] && r[1] !== "#N/A" && !(r[0] in obdZones)) obdZones[r[0]] = r[1]; });
  } catch (e) {
    obdZoneError = "อ่าน Outbound Email ไม่ได้: " + e;
  }
  return {
    success: true, page: "refs",
    fetchedAt: Utilities.formatDate(new Date(), cfg.TIME_ZONE, "yyyy-MM-dd HH:mm:ss"),
    hub: hub, cuts: cuts, ttb: ttb, ttbError: ttbError, obdZones: obdZones, obdZoneError: obdZoneError
  };
}

/** Save a copy of the "raw data" tab as "LH Trip d MMM yy" (overwrites that day's file). */
function saveDailyRaw_(dateStr) {
  const cfg = LH_TRIP_SOURCE_CONFIG;
  const date = /^\d{4}-\d{2}-\d{2}$/.test(String(dateStr || "")) ? String(dateStr) : todayStr_();
  const src = SpreadsheetApp.openById(cfg.DEFAULT_SPREADSHEET_ID).getSheetByName(cfg.RAW_SHEET_NAME);
  if (!src) return { success: false, error: `ไม่พบแท็บ "${cfg.RAW_SHEET_NAME}" ในชีทต้นทาง` };
  const values = src.getDataRange().getDisplayValues().filter((r, i) => i === 0 || String(r[0]).trim() !== "");
  if (values.length < 2) return { success: false, error: "แท็บ raw data ว่าง ไม่มีข้อมูลให้บันทึก" };
  const nCols = values[0].length;

  const name = dailyFileName_(date);
  const existing = dailyFolder_().getFilesByName(name);
  let ss;
  if (existing.hasNext()) {
    ss = SpreadsheetApp.openById(existing.next().getId());
  } else {
    ss = SpreadsheetApp.create(name, values.length, nCols);
    DriveApp.getFileById(ss.getId()).moveTo(dailyFolder_());
  }
  const sh = ss.getSheets()[0];
  sh.setName("raw data");
  sh.clear();
  if (sh.getMaxRows() < values.length) sh.insertRowsAfter(sh.getMaxRows(), values.length - sh.getMaxRows());
  if (sh.getMaxColumns() < nCols) sh.insertColumnsAfter(sh.getMaxColumns(), nCols - sh.getMaxColumns());
  const rng = sh.getRange(1, 1, values.length, nCols);
  rng.setNumberFormat("@");          // keep the text exactly as displayed
  rng.setValues(values);
  sh.setFrozenRows(1);
  SpreadsheetApp.flush();
  return {
    success: true, date: date, fileName: name, fileId: ss.getId(), fileUrl: ss.getUrl(),
    totalRows: values.length - 1, savedAt: Utilities.formatDate(new Date(), cfg.TIME_ZONE, "yyyy-MM-dd HH:mm:ss")
  };
}

/** Time-trigger target: saves today's copy. */
function dailySaveJob() {
  const r = saveDailyRaw_();
  Logger.log(JSON.stringify({ success: r.success, file: r.fileName, rows: r.totalRows, error: r.error }));
}

/** Run ONCE in the editor: installs the daily auto-save at DAILY_SAVE_HOUR (replaces an old one). */
function installDailyTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === "dailySaveJob")
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger("dailySaveJob").timeBased()
    .atHour(LH_TRIP_SOURCE_CONFIG.DAILY_SAVE_HOUR).nearMinute(0).everyDays(1)
    .inTimezone(LH_TRIP_SOURCE_CONFIG.TIME_ZONE).create();
  Logger.log("Installed daily trigger at " + LH_TRIP_SOURCE_CONFIG.DAILY_SAVE_HOUR + ":00 " + LH_TRIP_SOURCE_CONFIG.TIME_ZONE);
}

/** Run in the editor to save today's file right now. */
function saveTodayNow() {
  dailySaveJob();
}

/** Run in the editor to check the folder, the reference tables and the TTB access. */
function testDaily() {
  const l = listDailyRaw_();
  Logger.log("files: " + JSON.stringify(l.files.slice(0, 5)));
  const r = readRefs_();
  Logger.log(`refs: hub=${r.hub.length} gbkk=${r.cuts.gbkk.length} upcDirect=${r.cuts.upcDirect.length} upcMilkrun=${r.cuts.upcMilkrun.length} ttb=${Object.keys(r.ttb).map(k => k + ":" + r.ttb[k].length).join(", ")} ${r.ttbError}`);
  if (l.files.length) {
    const d = readDailyRaw_(l.files[0].fileId);
    Logger.log(`${d.fileName}: ${d.totalRows} rows ${d.error || ""}`);
  }
}

// =========================================================================================
// Sheet dump (page=sheetinfo / page=dump): formulas + display values of any sheet the company
// account can open. sheet_dump.html calls this from the browser and saves the result on the
// dashboard server (data/sheet_dumps) so the sheet logic can be read and mirrored.
// =========================================================================================
function sheetInfo_(spreadsheetId) {
  if (!spreadsheetId) return { success: false, error: "ต้องระบุ spreadsheetId" };
  const ss = SpreadsheetApp.openById(spreadsheetId);
  return {
    success: true, page: "sheetinfo", spreadsheetId: spreadsheetId, name: ss.getName(),
    sheets: ss.getSheets().map(s => ({
      name: s.getName(), gid: s.getSheetId(), lastRow: s.getLastRow(), lastCol: s.getLastColumn(), hidden: s.isSheetHidden()
    }))
  };
}

function dumpSheet_(spreadsheetId, sheetName, startRow, maxRows, maxCols) {
  if (!spreadsheetId || !sheetName) return { success: false, error: "ต้องระบุ spreadsheetId และ sheetName" };
  const ss = SpreadsheetApp.openById(spreadsheetId);
  const sh = ss.getSheetByName(sheetName);
  if (!sh) return { success: false, error: `ไม่พบแท็บ "${sheetName}"` };
  const lastRow = sh.getLastRow(), lastCol = sh.getLastColumn();
  const r0 = Math.max(1, Number(startRow) || 1);
  const nRows = Math.max(0, Math.min(Number(maxRows) || 200, 2000, lastRow - r0 + 1));
  const nCols = Math.max(0, Math.min(Number(maxCols) || 80, lastCol));
  const out = {
    success: true, page: "dump", spreadsheetId: spreadsheetId, spreadsheetName: ss.getName(),
    sheet: sheetName, gid: sh.getSheetId(), lastRow: lastRow, lastCol: lastCol,
    startRow: r0, rows: nRows, cols: nCols, values: [], formulas: [], merges: [], dataValidations: []
  };
  if (!nRows || !nCols) return out;
  const rng = sh.getRange(r0, 1, nRows, nCols);
  out.values = rng.getDisplayValues();
  // formulas only where present: [[row, col, formula], ...] (keeps the response small)
  const f = rng.getFormulas();
  out.formulas = [];
  f.forEach((row, i) => row.forEach((x, j) => { if (x) out.formulas.push([r0 + i, j + 1, x]); }));
  out.merges = rng.getMergedRanges().map(m => m.getA1Notation());
  return out;
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
