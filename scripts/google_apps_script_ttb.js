/**
 * Google Apps Script for Two-Way Sync between SPX Google Sheet and SOC Operations Portal
 * Spreadsheet: [OG] TimetableFullSocn / TTB - Registration
 * Target URL: https://docs.google.com/spreadsheets/d/1fcW2_deyDFDN9Dp9JfOv1NOinS1de6KMDcNZp2EOL9w/edit?gid=719250654#gid=719250654
 * ------------------------------------------------------------------------------------------------------
 * 📌 วิธีติดตั้งและนำไปใช้งานใน Google Sheets:
 * 1. เปิด Google Sheet ของบริษัท (ลิงก์ด้านบน)
 * 2. ไปที่เมนู "ส่วนขยาย" (Extensions) > "Apps Script"
 * 3. ลบโค้ดเดิมทั้งหมดออก แล้ววางโค้ดนี้ทั้งหมดลงไป
 * 4. กดปุ่ม "บันทึก" (Save 💾)
 * 5. กดปุ่มสีน้ำเงิน "การทำให้ใช้งานได้" (Deploy) > "การทำให้ใช้งานได้รายการใหม่" (New deployment)
 * 6. กดที่รูปเฟือง ⚙️ ด้านซ้าย > เลือก "เว็บแอป" (Web app)
 *    - คำอธิบาย (Description): SOC Portal Live Write & Read API
 *    - ดำเนินการในฐานะ (Execute as): ฉัน (Me)  <-- สำคัญมาก! เพื่อให้ใช้สิทธิ์ของคุณในการแก้ไข Sheet
 *    - ผู้ที่มีสิทธิ์เข้าถึง (Who has access): ทุกคน (Anyone) หรือ ทุกคนใน SPX Express
 * 7. กด "ทำให้ใช้งานได้" (Deploy) > ให้สิทธิ์ (Authorize access)
 * 8. คัดลอก "URL เว็บแอป" (Web App URL) ที่ได้ (ขึ้นต้นด้วย https://script.google.com/macros/s/.../exec)
 * 9. นำมาวางในช่อง "2. Google Apps Script Web App URL" ในเมนู "⚙️ ตั้งค่า Sheet" ของหน้าเว็บ SOC Dashboard
 */

function getTargetSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // 1. หาจาก Sheet ID (GID: 719250654) โดยตรง
  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    if (String(sheets[i].getSheetId()) === "719250654") {
      return sheets[i];
    }
  }
  
  // 2. หาจากชื่อชีท
  var nameList = ["[OG] TimetableFullSocn", "TTB - Registration", "TimetableFullSocn", "TimetableFullSocn "];
  for (var j = 0; j < nameList.length; j++) {
    var sh = ss.getSheetByName(nameList[j]);
    if (sh) return sh;
  }
  
  // 3. หาชีทที่มีคำว่า timetable หรือ ttb ในชื่อ
  for (var k = 0; k < sheets.length; k++) {
    var sName = sheets[k].getName().toLowerCase();
    if (sName.indexOf("timetable") !== -1 || sName.indexOf("ttb") !== -1) {
      return sheets[k];
    }
  }
  
  return ss.getActiveSheet();
}

// ค้นหาตำแหน่งคอลัมน์แบบ Dynamic
function getColumnMapping(data) {
  var colMap = {
    driverId: 2,       // Col B (Index 1 -> Col 2)
    driverName: 3,     // Col C (Index 2 -> Col 3)
    plate: 4,          // Col D (Index 3 -> Col 4)
    vehicleType: 5,    // Col E (Index 4 -> Col 5)
    status: 9,         // Col I (Index 8 -> Col 9)
    assignStatus: 10,  // Col J (Index 9 -> Col 10)
    lhTrip: 11,        // Col K (Index 10 -> Col 11)
    standbyTime: 14,   // Col N (Index 13 -> Col 14)
    loadingTime: 15,   // Col O (Index 14 -> Col 15)
    departureTime: 16, // Col P (Index 15 -> Col 16)
    destination: 17,   // Col Q (Index 16 -> Col 17)
    dock: 20,          // Col T (Index 19 -> Col 20)
    subcon: 21,        // Col U (Index 20 -> Col 21)
    cot: 22,           // Col V (Index 21 -> Col 22)
    newTrip: 23,       // Col W (Index 22 -> Col 23)
    remarkLh: 24,      // Col X (Index 23 -> Col 24)
    obZone: 25,        // Col Y (Index 24 -> Col 25)
    arrivalStatus: 26, // Col Z (Index 25 -> Col 26)
    remarkOb: 27,      // Col AA (Index 26 -> Col 27)
    lateType: 28,      // Col AB (Index 27 -> Col 28)
    cutoff: 30         // Col AD (Index 29 -> Col 30)
  };
  
  // ตรวจสอบหัวตารางจริงในแถวที่ 1-3 เพื่อปรับตำแหน่งคอลัมน์ให้แม่นยำ 100%
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

// ----------------------------------------------------------------------------
// GET REQUEST: รองรับทั้งดึงข้อมูลสด (Read) และอัปเดตข้อมูล (Write ผ่าน GET)
// ----------------------------------------------------------------------------
function doGet(e) {
  try {
    var p = (e && e.parameter) ? e.parameter : {};
    var action = p.action || "GET_ALL";
    
    var sheet = getTargetSheet();
    var dataRange = sheet.getDataRange();
    var data = dataRange.getValues();
    var colMap = getColumnMapping(data);
    
    // CASE 1: อัปเดตข้อมูลผ่าน GET Parameters (แก้ปัญหา CORS & Redirect 302 ได้ 100%)
    if (action === "UPDATE_ROW") {
      var rowIndex = p.rowIndex ? parseInt(p.rowIndex, 10) : null;
      var lhTrip = p.lhTrip ? String(p.lhTrip).trim() : "";
      
      // ค้นหา rowIndex จาก LH Trip ถ้าไม่ได้ระบุหรือต้องการค้นหาซ้ำ
      var foundRowIndex = findRowByLHTrip(data, lhTrip, colMap.lhTrip - 1);
      if (foundRowIndex) {
        rowIndex = foundRowIndex;
      }
      
      if (!rowIndex || rowIndex < 3 || rowIndex > data.length) {
        return jsonResponse({
          success: false,
          error: "ไม่พบแถวที่ตรงกับ LH Trip: " + lhTrip + " ในชีท " + sheet.getName() + " (จำนวนแถวทั้งหมด: " + data.length + ")"
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
    
    // CASE 2: ดึงข้อมูลทริปทั้งหมด (READ)
    if (!data || data.length < 3) {
      return jsonResponse({ success: false, error: "ไม่พบข้อมูลใน Sheet หรือตารางว่างเปล่า" });
    }
    
    var rows = [];
    var startRowIdx = 2; // Row 3
    
    for (var i = startRowIdx; i < data.length; i++) {
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

// ----------------------------------------------------------------------------
// POST REQUEST: รับค่าแก้ไขแบบ POST JSON
// ----------------------------------------------------------------------------
function doPost(e) {
  try {
    var contents = e.postData ? e.postData.contents : "{}";
    var payload = JSON.parse(contents);
    var action = payload.action || "UPDATE_ROW";
    
    var sheet = getTargetSheet();
    var dataRange = sheet.getDataRange();
    var data = dataRange.getValues();
    var colMap = getColumnMapping(data);
    
    if (action === "UPDATE_ROW") {
      var rowIndex = payload.rowIndex ? parseInt(payload.rowIndex, 10) : null;
      var lhTrip = payload.lhTrip ? String(payload.lhTrip).trim() : "";
      var updates = payload.updates || {};
      
      var foundRowIndex = findRowByLHTrip(data, lhTrip, colMap.lhTrip - 1);
      if (foundRowIndex) rowIndex = foundRowIndex;
      
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
    
    return jsonResponse({ success: false, error: "ไม่รู้จักคำสั่ง action: " + action });
    
  } catch (err) {
    return jsonResponse({ success: false, error: err.toString() });
  }
}

// ฟังก์ชันค้นหา Row Index จาก LH Trip แบบครอบคลุม
function findRowByLHTrip(data, lhTrip, lhColIdx) {
  if (!lhTrip) return null;
  var target = String(lhTrip).trim().toLowerCase();
  
  // 1. ค้นหาในคอลัมน์ LH Trip ก่อน
  if (lhColIdx >= 0) {
    for (var i = 2; i < data.length; i++) {
      var cellVal = String(data[i][lhColIdx] || "").trim().toLowerCase();
      if (cellVal === target) return i + 1;
    }
  }
  
  // 2. ถ้าไม่เจอ ให้ค้นหาทุกคอลัมน์ในตาราง
  for (var r = 2; r < data.length; r++) {
    for (var c = 0; c < data[r].length; c++) {
      if (String(data[r][c] || "").trim().toLowerCase() === target) {
        return r + 1;
      }
    }
  }
  
  return null;
}

// ----------------------------------------------------------------------------
// Helper Function สำหรับเขียนค่าลงในคอลัมน์ที่ถูกต้องของ Sheet
// ----------------------------------------------------------------------------
function applyRowUpdates(sheet, rowIndex, updates, colMap) {
  // Col Z: Arrival On-time/Late (Ontime, Late, เลื่อนเวลาปล่อยรถ, ไม่ใช้รถ)
  if (updates.arrivalStatus !== undefined && updates.arrivalStatus !== "") {
    sheet.getRange(rowIndex, colMap.arrivalStatus).setValue(updates.arrivalStatus);
  }
  
  // Col AA: Remark OB (เช่น รอคัดแยก, สลับรถ, LHแจ้งไม่ใช้รถรอบนี้)
  if (updates.remarkOb !== undefined) {
    sheet.getRange(rowIndex, colMap.remarkOb).setValue(updates.remarkOb);
  }
  
  // Col W: New trip (สลับรถ / เลขทริปใหม่)
  if (updates.newTrip !== undefined) {
    sheet.getRange(rowIndex, colMap.newTrip).setValue(updates.newTrip);
  }
  
  // Col X: Remark LH (ว.สลับรถ หรือปัญหาอื่นๆ)
  if (updates.remarkLh !== undefined) {
    sheet.getRange(rowIndex, colMap.remarkLh).setValue(updates.remarkLh);
  }
  
  // Col D: ทะเบียน
  if (updates.plate !== undefined && updates.plate !== "") {
    sheet.getRange(rowIndex, colMap.plate).setValue(updates.plate);
  }
  
  // Col C: ชื่อ พนักงานขับรถ
  if (updates.driverName !== undefined && updates.driverName !== "") {
    sheet.getRange(rowIndex, colMap.driverName).setValue(updates.driverName);
  }
  
  // Col T: Dock (ช่องจอด)
  if (updates.dock !== undefined && updates.dock !== "") {
    sheet.getRange(rowIndex, colMap.dock).setValue(updates.dock);
  }
  
  // Col AB: Late Type
  if (updates.lateType !== undefined && updates.lateType !== "") {
    sheet.getRange(rowIndex, colMap.lateType).setValue(updates.lateType);
  }
  
  // บันทึกการเปลี่ยนแปลงทันที (Flush)
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
