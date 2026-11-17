/**
 * =========================================================================================
 * SOCN Volume (SOC row 11) -> OB Dashboard Skip Process Volume Tracker
 * =========================================================================================
 * Reads "[SPX-BI-BTP] Performance Dashboard 2026", tab "SOC":
 *   - Value row : "SOCN Operational Outbound cut-off 1p.m." (row 11, found by label in column D)
 *   - Date row  : row 8 e.g. "11/15 (Sun)"  (rows 4/5 hold ISO dates and are used first;
 *                 a column where row 4 != row 5 is a weekly column and is skipped)
 * Returns JSON: { success, days: [{date:"2026-11-15", volume:938152}, ...] }
 *
 * Deploy (once):
 *   1. https://script.google.com -> New project -> paste this file
 *   2. Deploy -> New deployment -> type "Web app"
 *        Execute as: Me   |   Who has access: Anyone
 *   3. Copy the Web app URL (.../exec) and paste it in the Skip page:
 *        SOCN Volume Tracker -> "ดึง Volume จาก Sheet SOC (row 11)"
 *   (Your account only needs view access to the Performance Dashboard sheet.)
 * =========================================================================================
 */

const SOCN_VOLUME_CONFIG = {
  SPREADSHEET_ID: "1Z5sAcsGSQBu1A_7crK51a1wnWvSO_NnmXVBrx3te32s",
  SHEET_NAME: "SOC",
  LABEL_COLUMN: 4,                                   // column D = Key Metrics
  LABEL_MATCH: "socn operational outbound cut-off",  // row to read (case-insensitive)
  FALLBACK_VALUE_ROW: 11,
  DATE_ROW: 8,                                       // "11/15 (Sun)"
  ISO_DATE_ROWS: [4, 5],                             // "2026-11-15" (start / end of the column's period)
  MAX_ROWS_TO_SCAN: 40,
  TOKEN: ""                                          // optional: set a secret and add ?token=... to the URL
};

function doGet(e) {
  const params = (e && e.parameter) || {};
  if (SOCN_VOLUME_CONFIG.TOKEN && params.token !== SOCN_VOLUME_CONFIG.TOKEN) {
    return jsonOut_({ success: false, error: "invalid token" });
  }
  try {
    return jsonOut_(readSocnVolume_());
  } catch (err) {
    return jsonOut_({ success: false, error: String(err && err.message || err) });
  }
}

function readSocnVolume_() {
  const cfg = SOCN_VOLUME_CONFIG;
  const ss = SpreadsheetApp.openById(cfg.SPREADSHEET_ID);
  const sh = ss.getSheetByName(cfg.SHEET_NAME);
  if (!sh) throw new Error(`ไม่พบชีต "${cfg.SHEET_NAME}"`);
  const tz = ss.getSpreadsheetTimeZone();

  const lastCol = sh.getLastColumn();
  const nRows = Math.min(cfg.MAX_ROWS_TO_SCAN, sh.getLastRow());
  const range = sh.getRange(1, 1, nRows, lastCol);
  const values = range.getValues();
  const display = range.getDisplayValues();

  // find the value row by its label (falls back to row 11)
  let valueRow = cfg.FALLBACK_VALUE_ROW;
  for (let r = 0; r < nRows; r++) {
    const label = String(display[r][cfg.LABEL_COLUMN - 1] || "").toLowerCase();
    if (label.indexOf(cfg.LABEL_MATCH) >= 0) { valueRow = r + 1; break; }
  }
  const rowLabel = display[valueRow - 1][cfg.LABEL_COLUMN - 1];

  const isoRowA = cfg.ISO_DATE_ROWS[0] - 1, isoRowB = cfg.ISO_DATE_ROWS[1] - 1;
  const fmt = d => Utilities.formatDate(d, tz, "yyyy-MM-dd");
  const days = {};

  for (let c = cfg.LABEL_COLUMN; c < lastCol; c++) {
    const a = toIso_(values[isoRowA][c], display[isoRowA][c], fmt);
    const b = toIso_(values[isoRowB][c], display[isoRowB][c], fmt);
    let date = null;
    if (a && b) {
      if (a !== b) continue;            // weekly column (e.g. 10/12 - 10/18)
      date = a;
    } else {
      // fallback: row 8 "11/15 (Sun)" + year from row 4/5 or today
      const m = String(display[cfg.DATE_ROW - 1][c] || "").match(/^\s*(\d{1,2})\/(\d{1,2})\b/);
      if (!m) continue;
      const year = (a || b || fmt(new Date())).slice(0, 4);
      date = `${year}-${("0" + m[1]).slice(-2)}-${("0" + m[2]).slice(-2)}`;
    }
    const v = values[valueRow - 1][c];
    const num = typeof v === "number" ? v : Number(String(v).replace(/,/g, ""));
    if (!isFinite(num) || num <= 0) continue;  // "Loading...", "-", blank
    days[date] = Math.round(num);
  }

  return {
    success: true,
    sheet: cfg.SHEET_NAME,
    row: valueRow,
    rowLabel: rowLabel,
    fetchedAt: Utilities.formatDate(new Date(), tz, "yyyy-MM-dd HH:mm:ss"),
    days: Object.keys(days).sort().map(d => ({ date: d, volume: days[d] }))
  };
}

function toIso_(value, shown, fmt) {
  if (value instanceof Date && !isNaN(value)) return fmt(value);
  const m = String(shown || "").match(/(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[1]}-${m[2]}-${m[3]}` : null;
}

function jsonOut_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/** Run this once in the editor to authorize and check the output in the log. */
function testReadSocnVolume() {
  Logger.log(JSON.stringify(readSocnVolume_(), null, 1));
}
