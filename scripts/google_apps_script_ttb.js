/**
 * Google Apps Script for SOC Operations Portal & TTB Timetable Sync
 * =========================================================================================
 * 1. Source Master Sheet (ต้นทาง): https://docs.google.com/spreadsheets/d/11Se39YEz-mpyduJ3DU--Dfdlut6rzf9xcNYBxe9jHL0/edit?gid=719250654
 *    - Sheet: "[OG] TimetableFullSocn" Range A3:AU
 * 2. Target Working Sheet (ปลายทางที่ใช้แก้): https://docs.google.com/spreadsheets/d/1fcW2_deyDFDN9Dp9JfOv1NOinS1de6KMDcNZp2EOL9w/edit?gid=719250654
 * =========================================================================================
 * 📌 วิธีติดตั้งและนำไปใช้งาน:
 * 1. เปิด Google Sheet ปลายทาง (1fcW2_deyDFDN9Dp9JfOv1NOinS1de6KMDcNZp2EOL9w)
 * 2. ไปที่เมนู "ส่วนขยาย" (Extensions) > "Apps Script"
 * 3. ลบโค้ดเดิมทั้งหมดออก แล้ววางโค้ดนี้ทั้งหมดลงไป แล้วกดปุ่ม "บันทึก" (Save 💾)
 * 4. รีเฟรชหน้า Google Sheet จะพบเมนูใหม่ด้านบนชื่อ "🚚 SOC Portal Tools"
 * 5. กดเมนู "🚚 SOC Portal Tools" > "🔄 ดึงข้อมูลจาก Source Master (Import A3:AU)" เพื่อนำเข้าข้อมูลสดทันที!
 * 6. กดปุ่ม "การทำให้ใช้งานได้" (Deploy) > "การทำให้ใช้งานได้รายการใหม่" (New deployment)
 *    - เลือก "เว็บแอป" (Web app)
 *    - Execute as: ฉัน (Me)
 *    - Who has access: ทุกคน (Anyone) หรือ ทุกคนใน SPX Express
 *    - กด Deploy แล้วนำ Web App URL ไปวางใน Dashboard ได้เลยครับ!
 */

// รหัส ID ของ Google Sheet ต้นทางและปลายทาง
var SOURCE_SPREADSHEET_ID = "11Se39YEz-mpyduJ3DU--Dfdlut6rzf9xcNYBxe9jHL0";
var SHEET_TAB_NAME = "[OG] TimetableFullSocn";
var SOURCE_GID = "719250654";

// ----------------------------------------------------------------------------
// 1. เพิ่มเมนูลัดบน Google Sheet (UI Menu)
// ----------------------------------------------------------------------------
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("🚚 SOC Portal Tools")
    .addItem("🔄 ดึงข้อมูลจาก Source Master (Import A3:AU)", "importFromSourceMaster")
    .addItem("⏰ ตั้งเวลาดึงข้อมูลอัตโนมัติ (Auto-Sync ทุก 15 นาที)", "installTimeTrigger")
    .addItem("🛑 ยกเลิกการตั้งเวลาอัตโนมัติ", "removeTimeTrigger")
    .addSeparator()
    .addItem("ℹ️ ตรวจสอบการเชื่อมต่อชีท", "checkSheetConnection")
    .addToUi();
}

// ----------------------------------------------------------------------------
// 2. ฟังก์ชันดึงข้อมูลจาก Source Master เข้ามาลง Sheet ปลายทาง (เหมือน IMPORTRANGE)
//    - ฉลาดกว่า ImportRange ตรงที่ไม่พังเวลาชีทใหญ่ และคงค่าที่แก้ใน Column Z, AA ไว้ได้!
// ----------------------------------------------------------------------------
function importFromSourceMaster() {
  var ui = null;
  try { ui = SpreadsheetApp.getUi(); } catch (e) {}

  try {
    // 1. เปิด Sheet ต้นทาง
    var sourceSS = SpreadsheetApp.openById(SOURCE_SPREADSHEET_ID);
    var sourceSheet = getSheetByGidOrName(sourceSS, SOURCE_GID, SHEET_TAB_NAME);
    if (!sourceSheet) {
      throw new Error("ไม่พบชีท '" + SHEET_TAB_NAME + "' ใน Spreadsheet ต้นทาง");
    }

    var sourceLastRow = sourceSheet.getLastRow();
    var sourceLastCol = Math.min(47, sourceSheet.getLastColumn()); // Column AU คือ Col 47
    if (sourceLastRow < 3) {
      throw new Error("ไม่พบแถวข้อมูลในชีทต้นทาง (แถวข้อมูลต้องเริ่มตั้งแต่แถวที่ 3)");
    }

    // ดึงข้อมูล A3:AU ทั้งหมดจากต้นทาง
    var sourceData = sourceSheet.getRange(3, 1, sourceLastRow - 2, sourceLastCol).getValues();

    // 2. เปิด Sheet ปลายทาง (Active Spreadsheet)
    var targetSS = SpreadsheetApp.getActiveSpreadsheet();
    var targetSheet = getSheetByGidOrName(targetSS, SOURCE_GID, SHEET_TAB_NAME);
    if (!targetSheet) {
      targetSheet = targetSS.getActiveSheet();
    }

    // ดึงข้อมูลเดิมในชีทปลายทางเพื่อคงค่าที่คนแก้ไขไว้ (เช่น Arrival Z, Remark AA)
    var targetLastRow = targetSheet.getLastRow();
    var existingEditsMap = {};
    if (targetLastRow >= 3) {
      var existingData = targetSheet.getRange(3, 1, targetLastRow - 2, targetSheet.getLastColumn()).getValues();
      for (var e = 0; e < existingData.length; e++) {
        var exRow = existingData[e];
        var exTrip = String(exRow[10] || "").trim(); // Col K = LH Trips
        if (exTrip) {
          existingEditsMap[exTrip] = {
            arrivalStatus: exRow[25], // Col Z
            remarkOb: exRow[26],      // Col AA
            newTrip: exRow[22],       // Col W
            remarkLh: exRow[23]       // Col X
          };
        }
      }
    }

    // ผสานข้อมูล: หากในปลายทางมีกรอก Arrival/Remark ไว้แล้ว ให้คงค่านั้นไว้
    for (var i = 0; i < sourceData.length; i++) {
      var row = sourceData[i];
      var tripKey = String(row[10] || "").trim();
      if (tripKey && existingEditsMap[tripKey]) {
        var saved = existingEditsMap[tripKey];
        if (saved.arrivalStatus !== undefined && saved.arrivalStatus !== "") row[25] = saved.arrivalStatus;
        if (saved.remarkOb !== undefined && saved.remarkOb !== "") row[26] = saved.remarkOb;
        if (saved.newTrip !== undefined && saved.newTrip !== "") row[22] = saved.newTrip;
        if (saved.remarkLh !== undefined && saved.remarkLh !== "") row[23] = saved.remarkLh;
      }
    }

    // 3. เขียนข้อมูลลงในชีทปลายทางตั้งแต่ A3:AU...
    var targetRange = targetSheet.getRange(3, 1, sourceData.length, sourceData[0].length);
    targetRange.setValues(sourceData);
    SpreadsheetApp.flush();

    var msg = "✅ ดึงข้อมูลสำเร็จ! นำเข้าข้อมูลทั้งหมด " + sourceData.length + " แถวจาก Source Master เรียบร้อยแล้ว";
    if (ui) ui.alert("ผลการทำงาน", msg, ui.ButtonSet.OK);
    return { success: true, count: sourceData.length, message: msg };

  } catch (err) {
    var errMsg = "❌ เกิดข้อผิดพลาดในการ Import: " + err.toString();
    if (ui) ui.alert("เกิดข้อผิดพลาด", errMsg, ui.ButtonSet.OK);
    return { success: false, error: errMsg };
  }
}

// ----------------------------------------------------------------------------
// 3. ตั้งเวลาดึงข้อมูลอัตโนมัติ (Auto-Sync Trigger ทุก 15 นาที)
// ----------------------------------------------------------------------------
function installTimeTrigger() {
  removeTimeTrigger(); // ลบ Trigger เดิมออกก่อน
  ScriptApp.newTrigger("importFromSourceMaster")
    .timeBased()
    .everyMinutes(15)
    .create();

  var ui = null;
  try { ui = SpreadsheetApp.getUi(); } catch (e) {}
  if (ui) ui.alert("สำเร็จ", "✅ ติดตั้งระบบดึงข้อมูลอัตโนมัติทุกๆ 15 นาทีเรียบร้อยแล้ว", ui.ButtonSet.OK);
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
// 4. WEB APP API: ให้ SOC Dashboard ส่งค่ามาแก้ หรือดึงข้อมูลสด
// ----------------------------------------------------------------------------
function doGet(e) {
  try {
    var p = (e && e.parameter) ? e.parameter : {};
    var action = p.action || "GET_ALL";
    
    // คำสั่งสั่งให้ดึงข้อมูลจาก Source Master เข้ามาทันที
    if (action === "SYNC_FROM_SOURCE" || action === "IMPORT") {
      var syncRes = importFromSourceMaster();
      return jsonResponse(syncRes);
    }
    
    var sheet = getTargetSheet();
    var dataRange = sheet.getDataRange();
    var data = dataRange.getValues();
    var colMap = getColumnMapping(data);
    
    // คำสั่ง UPDATE ROW ผ่าน GET URL
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
      
      var updates = {};
      if (p.arrivalStatus !== undefined && p.arrivalStatus !== "") updates.arrivalStatus = p.arrivalStatus;
      if (p.remarkOb !== undefined) updates.remarkOb = p.remarkOb;
      if (p.newTrip !== undefined) updates.newTrip = p.newTrip;
      if (p.remarkLh !== undefined) updates.remarkLh = p.remarkLh;
      if (p.plate !== undefined && p.plate !== "") updates.plate = p.plate;
      if (p.driverName !== undefined && p.driverName !== "") updates.driverName = p.driverName;
      if (p.dock !== undefined && p.dock !== "") updates.dock = p.dock;
      if (p.lateType !== undefined && p.lateType !== "") updates.lateType = p.lateType;
      
      applyRowUpdates(sheet, rowIndex, updates, colMap);
      
      return jsonResponse({
        success: true,
        message: "✅ อัปเดตข้อมูลลงชีท '" + sheet.getName() + "' แถวที่ " + rowIndex + " (" + lhTrip + ") สำเร็จเรียบร้อยแล้ว",
        sheetName: sheet.getName(),
        rowIndex: rowIndex,
        lhTrip: lhTrip,
        updates: updates
      });
    }
    
    // ดึงข้อมูลทริปทั้งหมด (READ)
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
        cot: String(r[colMap.cot - 1] || "").trim(),
        newTrip: String(r[colMap.newTrip - 1] || "").trim(),
        remarkLh: String(r[colMap.remarkLh - 1] || "").trim(),
        obZone: String(r[colMap.obZone - 1] || "").trim(),
        arrivalStatus: String(r[colMap.arrivalStatus - 1] || "").trim(),
        remarkOb: String(r[colMap.remarkOb - 1] || "").trim(),
        lateType: String(r[colMap.lateType - 1] || "").trim(),
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

function doPost(e) {
  try {
    var contents = e.postData ? e.postData.contents : "{}";
    var payload = JSON.parse(contents);
    var action = payload.action || "UPDATE_ROW";
    
    if (action === "SYNC_FROM_SOURCE" || action === "IMPORT") {
      var syncRes = importFromSourceMaster();
      return jsonResponse(syncRes);
    }
    
    var sheet = getTargetSheet();
    var dataRange = sheet.getDataRange();
    var data = dataRange.getValues();
    var colMap = getColumnMapping(data);
    
    if (action === "UPDATE_ROW") {
      var rowIndex = payload.rowIndex ? parseInt(payload.rowIndex, 10) : null;
      var lhTrip = payload.lhTrip ? String(payload.lhTrip).trim() : "";
      var updates = payload.updates || {};
      
      var foundRow = findRowByLHTrip(data, lhTrip, colMap.lhTrip - 1);
      if (foundRow) rowIndex = foundRow;
      
      if (!rowIndex || rowIndex < 3 || rowIndex > data.length) {
        return jsonResponse({
          success: false,
          error: "ไม่พบแถวที่ตรงกับ LH Trip: " + lhTrip + " ในชีท " + sheet.getName()
        });
      }
      
      applyRowUpdates(sheet, rowIndex, updates, colMap);
      
      return jsonResponse({
        success: true,
        message: "✅ อัปเดตข้อมูลลงชีท '" + sheet.getName() + "' แถวที่ " + rowIndex + " (" + lhTrip + ") สำเร็จเรียบร้อยแล้ว",
        sheetName: sheet.getName(),
        rowIndex: rowIndex,
        lhTrip: lhTrip,
        updates: updates
      });
    }
    
    return jsonResponse({ success: false, error: "ไม่รู้จักคำสั่ง: " + action });
  } catch (err) {
    return jsonResponse({ success: false, error: err.toString() });
  }
}

// ----------------------------------------------------------------------------
// 5. HELPER FUNCTIONS
// ----------------------------------------------------------------------------
function getTargetSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = getSheetByGidOrName(ss, SOURCE_GID, SHEET_TAB_NAME);
  return sheet || ss.getActiveSheet();
}

function getSheetByGidOrName(spreadsheet, gid, name) {
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
    driverId: 2, driverName: 3, plate: 4, vehicleType: 5, status: 9, assignStatus: 10,
    lhTrip: 11, standbyTime: 14, loadingTime: 15, departureTime: 16, destination: 17,
    dock: 20, subcon: 21, cot: 22, newTrip: 23, remarkLh: 24, obZone: 25,
    arrivalStatus: 26, remarkOb: 27, lateType: 28, cutoff: 30
  };
  
  for (var r = 0; r < Math.min(3, data.length); r++) {
    var row = data[r];
    for (var c = 0; c < row.length; c++) {
      var val = String(row[c] || "").trim().toLowerCase();
      var col1Based = c + 1;
      if (val === "lh trips" || val === "lh trip" || val === "lh_trip") colMap.lhTrip = col1Based;
      else if (val.indexOf("arrival") !== -1 || val.indexOf("on-time/late") !== -1) colMap.arrivalStatus = col1Based;
      else if (val.indexOf("remark ob") !== -1 || val === "remark_ob") colMap.remarkOb = col1Based;
      else if (val.indexOf("new trip") !== -1 || val === "new_trip") colMap.newTrip = col1Based;
      else if (val.indexOf("remark lh") !== -1 || val.indexOf("สลับรถ") !== -1) colMap.remarkLh = col1Based;
      else if (val === "dock" || val === "ช่องจอด") colMap.dock = col1Based;
      else if (val === "ทะเบียน" || val === "plate") colMap.plate = col1Based;
      else if (val.indexOf("ชื่อพนักงาน") !== -1 || val.indexOf("driver name") !== -1) colMap.driverName = col1Based;
      else if (val.indexOf("late type") !== -1) colMap.lateType = col1Based;
      else if (val === "destination" || val === "สถานี" || val === "ปลายทาง") colMap.destination = col1Based;
    }
  }
  return colMap;
}

function findRowByLHTrip(data, lhTrip, lhColIdx) {
  if (!lhTrip) return null;
  var target = String(lhTrip).trim().toLowerCase();
  if (lhColIdx >= 0) {
    for (var i = 2; i < data.length; i++) {
      if (String(data[i][lhColIdx] || "").trim().toLowerCase() === target) return i + 1;
    }
  }
  for (var r = 2; r < data.length; r++) {
    for (var c = 0; c < data[r].length; c++) {
      if (String(data[r][c] || "").trim().toLowerCase() === target) return r + 1;
    }
  }
  return null;
}

function applyRowUpdates(sheet, rowIndex, updates, colMap) {
  if (updates.arrivalStatus !== undefined && updates.arrivalStatus !== "") {
    sheet.getRange(rowIndex, colMap.arrivalStatus).setValue(updates.arrivalStatus);
  }
  if (updates.remarkOb !== undefined) {
    sheet.getRange(rowIndex, colMap.remarkOb).setValue(updates.remarkOb);
  }
  if (updates.newTrip !== undefined) {
    sheet.getRange(rowIndex, colMap.newTrip).setValue(updates.newTrip);
  }
  if (updates.remarkLh !== undefined) {
    sheet.getRange(rowIndex, colMap.remarkLh).setValue(updates.remarkLh);
  }
  if (updates.plate !== undefined && updates.plate !== "") {
    sheet.getRange(rowIndex, colMap.plate).setValue(updates.plate);
  }
  if (updates.driverName !== undefined && updates.driverName !== "") {
    sheet.getRange(rowIndex, colMap.driverName).setValue(updates.driverName);
  }
  if (updates.dock !== undefined && updates.dock !== "") {
    sheet.getRange(rowIndex, colMap.dock).setValue(updates.dock);
  }
  if (updates.lateType !== undefined && updates.lateType !== "") {
    sheet.getRange(rowIndex, colMap.lateType).setValue(updates.lateType);
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
