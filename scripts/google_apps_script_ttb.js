/**
 * Google Apps Script for SOC Operations Portal & TTB Timetable Sync
 * =========================================================================================
 * 1. Source Master Sheet (ต้นทาง): https://docs.google.com/spreadsheets/d/11Se39YEz-mpyduJ3DU--Dfdlut6rzf9xcNYBxe9jHL0/edit?gid=719250654
 *    - Sheet: "[OG] TimetableFullSocn" Range A3:Y (Column 1 ถึง 25)
 * 2. Target Working Sheet (ปลายทางที่ใช้แก้): https://docs.google.com/spreadsheets/d/1fcW2_deyDFDN9Dp9JfOv1NOinS1de6KMDcNZp2EOL9w/edit?gid=719250654
 *    - Column Z (26)  = Arrival On-time/Late (แก้ใน Dashboard / Sheet)
 *    - Column AA (27) = Remark OB (แก้ใน Dashboard / Sheet)
 *    - Column AB (28) = Late Type (ARRAYFORMULA ปลอดภัย ไม่โดนทับ)
 * =========================================================================================
 * 📌 ขั้นตอนการติดตั้งและ Deploy:
 * 1. เปิด Google Sheet ปลายทาง (1fcW2_deyDFDN9Dp9JfOv1NOinS1de6KMDcNZp2EOL9w)
 * 2. ไปที่เมนู "ส่วนขยาย" (Extensions) > "Apps Script"
 * 3. ลบโค้ดเดิมทั้งหมดออก แล้ววางโค้ดไฟล์นี้ทั้งหมดลงไป แล้วกดปุ่ม "บันทึก" (Save 💾 หรือ Ctrl+S)
 * 4. รีเฟรชหน้า Google Sheet จะพบเมนูใหม่ด้านบนชื่อ "🚚 SOC Portal Tools"
 * 5. กดปุ่มสีน้ำเงินขวาบน "การทำให้ใช้งานได้" (Deploy) > "การทำให้ใช้งานได้รายการใหม่" (New deployment)
 *    - เลือกประเภท: "เว็บแอป" (Web app)
 *    - ดำเนินการในฐานะ (Execute as): "ฉัน" (Me)
 *    - ผู้มีสิทธิ์เข้าถึง (Who has access): "ทุกคน" (Anyone) หรือ "ทุกคนใน SPX Express"
 *    - กด Deploy แล้วนำ Web App URL ไปวางใน Dashboard ได้เลยครับ!
 */

var SOURCE_SPREADSHEET_ID = "11Se39YEz-mpyduJ3DU--Dfdlut6rzf9xcNYBxe9jHL0";
var TARGET_SPREADSHEET_ID = "1fcW2_deyDFDN9Dp9JfOv1NOinS1de6KMDcNZp2EOL9w";
var SHEET_TAB_NAME = "[OG] TimetableFullSocn";
var SHEET_GID = "719250654";

// ----------------------------------------------------------------------------
// 1. เมนูลัดบน Google Sheet (UI Menu)
// ----------------------------------------------------------------------------
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("🚚 SOC Portal Tools")
    .addItem("🔄 ดึงข้อมูลจาก Source Master (Import A3:Y)", "importFromSourceMaster")
    .addItem("⏰ ตั้งเวลาดึงข้อมูลอัตโนมัติ (Auto-Sync ทุก 15 นาที)", "installTimeTrigger")
    .addItem("🛑 ยกเลิกการตั้งเวลาอัตโนมัติ", "removeTimeTrigger")
    .addSeparator()
    .addItem("ℹ️ ตรวจสอบการเชื่อมต่อชีท", "checkSheetConnection")
    .addToUi();
}

// ----------------------------------------------------------------------------
// 2. ฟังก์ชันดึงข้อมูลจาก Source Master (ดึงเฉพาะ A3:Y ไม่ทับ Column Z และ AA)
// ----------------------------------------------------------------------------
function importFromSourceMaster() {
  var ui = null;
  try { ui = SpreadsheetApp.getUi(); } catch (e) {}

  try {
    var sourceSS = SpreadsheetApp.openById(SOURCE_SPREADSHEET_ID);
    var sourceSheet = getSheetByGidOrName(sourceSS, SHEET_GID, SHEET_TAB_NAME);
    if (!sourceSheet) {
      throw new Error("ไม่พบชีท '" + SHEET_TAB_NAME + "' ใน Spreadsheet ต้นทาง");
    }

    var sourceLastRow = sourceSheet.getLastRow();
    var importCols = 25; // 📌 ดึงเฉพาะ Column A ถึง Y (25 คอลัมน์) ไม่แตะ Column Z (26) และ AA (27)
    
    if (sourceLastRow < 3) {
      throw new Error("ไม่พบแถวข้อมูลในชีทต้นทาง (แถวข้อมูลต้องเริ่มตั้งแต่แถวที่ 3)");
    }

    var numRows = sourceLastRow - 2;
    var sourceData = sourceSheet.getRange(3, 1, numRows, importCols).getValues();

    var targetSheet = getTargetSheet();
    if (!targetSheet) {
      throw new Error("ไม่สามารถเปิด Sheet ปลายทางได้");
    }

    // ดึงข้อมูลเดิมในชีทปลายทางเพื่อคงค่า New trip W (23) และ Remark LH X (24) ที่อาจมีการแก้ไว้
    var targetLastRow = targetSheet.getLastRow();
    var existingEditsMap = {};
    if (targetLastRow >= 3) {
      var checkRows = Math.min(numRows, targetLastRow - 2);
      var existingData = targetSheet.getRange(3, 1, checkRows, importCols).getValues();
      for (var e = 0; e < existingData.length; e++) {
        var exRow = existingData[e];
        var exTrip = String(exRow[10] || "").trim(); // Col K = LH Trips (0-indexed = 10)
        if (exTrip) {
          existingEditsMap[exTrip] = {
            newTrip: exRow[22], // Col W (0-indexed = 22)
            remarkLh: exRow[23] // Col X (0-indexed = 23)
          };
        }
      }
    }

    // ผสานข้อมูล Col W และ Col X ถ้ามีการกรอกไว้ในปลายทาง
    for (var i = 0; i < sourceData.length; i++) {
      var row = sourceData[i];
      var tripKey = String(row[10] || "").trim();
      if (tripKey && existingEditsMap[tripKey]) {
        var saved = existingEditsMap[tripKey];
        if (saved.newTrip !== undefined && saved.newTrip !== "") row[22] = saved.newTrip;
        if (saved.remarkLh !== undefined && saved.remarkLh !== "") row[23] = saved.remarkLh;
      }
    }

    // เขียนลงเฉพาะช่วง A3:Y ใน Sheet ปลายทาง (Column Z, AA, AB จะปลอดภัย 100%)
    var targetRange = targetSheet.getRange(3, 1, sourceData.length, importCols);
    targetRange.setValues(sourceData);
    SpreadsheetApp.flush();

    var msg = "✅ ดึงข้อมูลสำเร็จ! นำเข้าข้อมูล A3:Y ทั้งหมด " + sourceData.length + " แถวเรียบร้อยแล้ว (Column Z และ AA ไม่ถูกเขียนทับ)";
    if (ui) ui.alert("ผลการทำงาน", msg, ui.ButtonSet.OK);
    return { success: true, count: sourceData.length, message: msg };

  } catch (err) {
    var errMsg = "❌ เกิดข้อผิดพลาดในการ Import: " + err.toString();
    if (ui) ui.alert("เกิดข้อผิดพลาด", errMsg, ui.ButtonSet.OK);
    return { success: false, error: errMsg };
  }
}

function installTimeTrigger() {
  removeTimeTrigger();
  ScriptApp.newTrigger("importFromSourceMaster")
    .timeBased()
    .everyMinutes(15)
    .create();

  var ui = null;
  try { ui = SpreadsheetApp.getUi(); } catch (e) {}
  if (ui) ui.alert("สำเร็จ", "✅ ติดตั้งระบบดึงข้อมูลอัตโนมัติ (A3:Y) ทุกๆ 15 นาทีเรียบร้อยแล้ว", ui.ButtonSet.OK);
}

function removeTimeTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "importFromSourceMaster") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
}

function checkSheetConnection() {
  var res = importFromSourceMaster();
  var ui = null;
  try { ui = SpreadsheetApp.getUi(); } catch (e) {}
  if (ui) {
    ui.alert("ผลการตรวจสอบ", res.success ? res.message : res.error, ui.ButtonSet.OK);
  }
}

// ----------------------------------------------------------------------------
// 3. WEB APP API (doGet / doPost): ให้ SOC Dashboard อ่าน/เขียนค่าลง Sheet
// ----------------------------------------------------------------------------
function doGet(e) {
  return handleRequest(e, "GET");
}

function doPost(e) {
  return handleRequest(e, "POST");
}

function handleRequest(e, method) {
  try {
    var p = {};
    
    // Parse GET parameters
    if (e && e.parameter) {
      for (var key in e.parameter) {
        p[key] = e.parameter[key];
      }
    }
    
    // Parse POST Body (JSON or Form-urlencoded)
    if (e && e.postData && e.postData.contents) {
      try {
        var jsonBody = JSON.parse(e.postData.contents);
        for (var jKey in jsonBody) {
          p[jKey] = jsonBody[jKey];
        }
      } catch (jsonErr) {
        // Form-urlencoded already populated in e.parameter
      }
    }

    var action = p.action || "GET_ALL";
    
    // ACTION: SYNC FROM SOURCE (A3:Y)
    if (action === "SYNC_FROM_SOURCE" || action === "IMPORT") {
      var syncRes = importFromSourceMaster();
      return jsonResponse(syncRes);
    }
    
    var sheet = getTargetSheet();
    if (!sheet) {
      return jsonResponse({ success: false, error: "ไม่พบชีท " + SHEET_TAB_NAME + " ใน Google Sheet" });
    }
    
    var dataRange = sheet.getDataRange();
    var data = dataRange.getValues();
    var colMap = getColumnMapping(data);
    
    // ACTION: UPDATE ROW (แก้ไข Column Z และ Column AA)
    if (action === "UPDATE_ROW") {
      var rowIndex = p.rowIndex ? parseInt(p.rowIndex, 10) : null;
      var lhTrip = p.lhTrip ? String(p.lhTrip).trim() : "";
      
      var foundRow = findRowByLHTrip(data, lhTrip, colMap.lhTrip - 1);
      if (foundRow) rowIndex = foundRow;
      
      if (!rowIndex || rowIndex < 3 || rowIndex > data.length) {
        return jsonResponse({
          success: false,
          error: "ไม่พบแถวที่ตรงกับ LH Trip: " + lhTrip + " ในชีท " + sheet.getName()
        });
      }
      
      var updates = p.updates || {};
      if (p.arrivalStatus !== undefined) updates.arrivalStatus = p.arrivalStatus;
      if (p.remarkOb !== undefined) updates.remarkOb = p.remarkOb;
      if (p.newTrip !== undefined) updates.newTrip = p.newTrip;
      if (p.remarkLh !== undefined) updates.remarkLh = p.remarkLh;
      
      applyRowUpdates(sheet, rowIndex, updates, colMap);
      
      return jsonResponse({
        success: true,
        message: "✅ บันทึกข้อมูลลงชีท '" + sheet.getName() + "' แถวที่ " + rowIndex + " (Column Z = " + (updates.arrivalStatus || '-') + ", AA = " + (updates.remarkOb || '-') + ") เรียบร้อยแล้ว",
        sheetName: sheet.getName(),
        rowIndex: rowIndex,
        lhTrip: lhTrip,
        updates: updates
      });
    }
    
    // ACTION: GET_ALL (ดึงข้อมูลทริปทั้งหมด)
    if (!data || data.length < 3) {
      return jsonResponse({ success: false, error: "ไม่พบข้อมูลใน Sheet" });
    }
    
    var rows = [];
    for (var i = 2; i < data.length; i++) {
      var r = data[i];
      var lhTripVal = String(r[colMap.lhTrip - 1] || "").trim();
      var destinationVal = String(r[colMap.destination - 1] || "").trim();
      if (!lhTripVal && !destinationVal) continue;
      
      rows.push({
        rowIndex: i + 1,
        driverId: String(r[colMap.driverId - 1] || "").trim(),
        driverName: String(r[colMap.driverName - 1] || "").trim(),
        plate: String(r[colMap.plate - 1] || "").trim(),
        vehicleType: String(r[colMap.vehicleType - 1] || "").trim(),
        status: String(r[colMap.status - 1] || "").trim(),
        assignStatus: String(r[colMap.assignStatus - 1] || "").trim(),
        lhTrip: lhTripVal,
        standbyTime: formatTimeValue(r[colMap.standbyTime - 1]),
        loadingTime: formatTimeValue(r[colMap.loadingTime - 1]),
        departureTime: formatTimeValue(r[colMap.departureTime - 1]),
        destination: destinationVal,
        dock: String(r[colMap.dock - 1] || "").trim(),
        subcon: String(r[colMap.subcon - 1] || "").trim(),
        newTrip: String(r[colMap.newTrip - 1] || "").trim(),
        remarkLh: String(r[colMap.remarkLh - 1] || "").trim(),
        obZone: String(r[colMap.obZone - 1] || "").trim(),
        arrivalStatus: String(r[colMap.arrivalStatus - 1] || "").trim(),
        remarkOb: String(r[colMap.remarkOb - 1] || "").trim(),
        lateType: String(r[colMap.lateType - 1] || "").trim(),
        cot: String(r[colMap.cot - 1] || "").trim(),
        cutoff: formatTimeValue(r[colMap.cutoff - 1])
      });
    }
    
    return jsonResponse({
      success: true,
      sheetName: sheet.getName(),
      updatedAt: Utilities.formatDate(new Date(), "Asia/Bangkok", "yyyy-MM-dd HH:mm:ss"),
      total: rows.length,
      rows: rows
    });
    
  } catch (err) {
    return jsonResponse({ success: false, error: err.toString() });
  }
}

// ----------------------------------------------------------------------------
// 4. HELPER FUNCTIONS
// ----------------------------------------------------------------------------
function getTargetSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) {
    try {
      ss = SpreadsheetApp.openById(TARGET_SPREADSHEET_ID);
    } catch (e) {}
  }
  var sheet = getSheetByGidOrName(ss, SHEET_GID, SHEET_TAB_NAME);
  return sheet || (ss ? ss.getActiveSheet() : null);
}

function getSheetByGidOrName(spreadsheet, gid, name) {
  if (!spreadsheet) return null;
  var sheets = spreadsheet.getSheets();
  if (gid) {
    for (var i = 0; i < sheets.length; i++) {
      if (String(sheets[i].getSheetId()) === String(gid)) return sheets[i];
    }
  }
  if (name) {
    var sh = spreadsheet.getSheetByName(name);
    if (sh) return sh;
  }
  for (var j = 0; j < sheets.length; j++) {
    var sName = sheets[j].getName().toLowerCase();
    if (sName.indexOf("timetable") !== -1 || sName.indexOf("ttb") !== -1) {
      return sheets[j];
    }
  }
  return null;
}

function getColumnMapping(data) {
  var colMap = {
    driverId: 2,        // Col B (2)
    driverName: 3,      // Col C (3)
    plate: 4,           // Col D (4)
    vehicleType: 5,     // Col E (5)
    status: 9,          // Col I (9)
    assignStatus: 10,   // Col J (10)
    lhTrip: 11,         // Col K (11)
    standbyTime: 14,    // Col N (14)
    loadingTime: 15,    // Col O (15)
    departureTime: 16,  // Col P (16)
    destination: 17,    // Col Q (17)
    dock: 20,           // Col T (20)
    subcon: 21,         // Col U (21)
    newTrip: 23,        // Col W (23)
    remarkLh: 24,       // Col X (24)
    obZone: 25,         // Col Y (25)
    arrivalStatus: 26,  // Col Z (26) -> STRICTLY COLUMN Z!
    remarkOb: 27,       // Col AA (27) -> STRICTLY COLUMN AA!
    lateType: 28,       // Col AB (28) -> STRICTLY COLUMN AB!
    cot: 29,            // Col AC (29) -> STRICTLY COLUMN AC!
    cutoff: 30,         // Col AD (30) -> STRICTLY COLUMN AD!
    dockedTime: 31,     // Col AE (31)
    planDeparture: 33,  // Col AG (33)
    completeTime: 34    // Col AH (34)
  };
  
  if (!data || data.length < 2) return colMap;
  
  // Scan Header Row 2 (index 1) for precise header names
  var headerRow = data.length > 1 ? data[1] : data[0];
  for (var c = 0; c < headerRow.length; c++) {
    var val = String(headerRow[c] || "").trim().toLowerCase();
    var colNum = c + 1;
    if (val === "lh trips" || val === "lh trip" || val === "lh_trip") colMap.lhTrip = colNum;
    else if (val === "arrival on-time/late" || val === "arrival status" || (val.indexOf("arrival") !== -1 && val.indexOf("hour") === -1 && val.indexOf("%") === -1 && val.indexOf("truck") === -1 && val.indexOf("time") === -1)) {
      colMap.arrivalStatus = colNum;
    }
    else if (val === "remark ob" || val === "remark_ob") colMap.remarkOb = colNum;
    else if (val === "new trip" || val === "new_trip") colMap.newTrip = colNum;
    else if (val === "remark lh" || val.indexOf("สลับรถ") !== -1) colMap.remarkLh = colNum;
    else if (val === "ob zone" || val === "obzone") colMap.obZone = colNum;
    else if (val === "dock" || val === "ช่องจอด") colMap.dock = colNum;
    else if (val === "ทะเบียน" || val === "plate") colMap.plate = colNum;
    else if (val.indexOf("ชื่อพนักงาน") !== -1 || val.indexOf("driver name") !== -1 || val.indexOf("ชื่อ พนักงาน") !== -1) colMap.driverName = colNum;
    else if (val === "late type" || val === "late_type") colMap.lateType = colNum;
    else if (val === "destination" || val === "สถานี" || val === "ปลายทาง") colMap.destination = colNum;
    else if (val === "cot" && colNum >= 25) colMap.cot = colNum;
    else if ((val === "cutoff" || val === "cut off") && val.indexOf("2") === -1) colMap.cutoff = colNum;
  }
  
  return colMap;
}

function findRowByLHTrip(data, lhTrip, lhColIdx) {
  if (!lhTrip) return null;
  var target = String(lhTrip).trim().toLowerCase();
  var colIdx = (lhColIdx !== undefined && lhColIdx >= 0) ? lhColIdx : 10; // Default Column K (index 10)
  
  for (var i = 2; i < data.length; i++) {
    if (String(data[i][colIdx] || "").trim().toLowerCase() === target) return i + 1;
  }
  for (var r = 2; r < data.length; r++) {
    for (var c = 0; c < data[r].length; c++) {
      if (String(data[r][c] || "").trim().toLowerCase() === target) return r + 1;
    }
  }
  return null;
}

function applyRowUpdates(sheet, rowIndex, updates, colMap) {
  // 📌 ล็อคคอลัมน์แบบตายตัว 100% สำหรับตาราง Timetable
  var colZ = 26;  // Column Z  = Arrival On-time/Late (Ontime / Late / เลื่อนเวลาปล่อยรถ / ไม่ใช้รถ)
  var colAA = 27; // Column AA = Remark OB
  var colW = 23;  // Column W  = New trip / สลับรถ
  var colX = 24;  // Column X  = Remark LH
  
  // 1. แก้ไข Column Z (Arrival Status)
  if (updates.arrivalStatus !== undefined && updates.arrivalStatus !== null) {
    sheet.getRange(rowIndex, colZ).setValue(String(updates.arrivalStatus).trim());
  }
  
  // 2. แก้ไข Column AA (Remark OB)
  if (updates.remarkOb !== undefined && updates.remarkOb !== null) {
    sheet.getRange(rowIndex, colAA).setValue(String(updates.remarkOb).trim());
  }
  
  // 3. ทริปใหม่ / สลับรถ (ถ้ามีระบุ)
  if (updates.newTrip !== undefined && updates.newTrip !== null && String(updates.newTrip).trim() !== "") {
    sheet.getRange(rowIndex, colW).setValue(String(updates.newTrip).trim());
  }
  if (updates.remarkLh !== undefined && updates.remarkLh !== null && String(updates.remarkLh).trim() !== "") {
    sheet.getRange(rowIndex, colX).setValue(String(updates.remarkLh).trim());
  }
  
  SpreadsheetApp.flush();
}

function formatTimeValue(val) {
  if (val === null || val === undefined) return "";
  if (val instanceof Date) {
    return Utilities.formatDate(val, "Asia/Bangkok", "HH:mm");
  }
  var str = String(val).trim();
  if (str === "#N/A" || str === "NaN" || str === "nan") return "";
  return str;
}

function jsonResponse(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
