/**
 * Google Apps Script for Two-Way Sync between SPX Google Sheet and SOC Operations Portal
 * Spreadsheet: [OG] TimetableFullSocn / TTB - Registration
 * Target URL: https://docs.google.com/spreadsheets/d/1fcW2_deyDFDN9Dp9JfOv1NOinS1de6KMDcNZp2EOL9w/edit?gid=719250654#gid=719250654
 * ------------------------------------------------------------------------------------------------------
 * 📌 วิธีติดตั้งและนำไปใช้งานใน Google Sheets (ทำครั้งเดียว):
 * 1. เปิด Google Sheet ของบริษัท (ลิงก์ด้านบน)
 * 2. ไปที่เมนู "ส่วนขยาย" (Extensions) > "Apps Script"
 * 3. ลบโค้ดเดิมทั้งหมดออก แล้ววางโค้ดนี้ทั้งหมดลงไป
 * 4. กดปุ่ม "บันทึก" (Save 💾)
 * 5. กดปุ่มสีน้ำเงิน "การทำให้ใช้งานได้" (Deploy) > "การทำให้ใช้งานได้รายการใหม่" (New deployment)
 * 6. กดที่ไอคอนฟันเฟือง ⚙️ ด้านซ้าย > เลือกประเภท "เว็บแอป" (Web app)
 *    - คำอธิบาย (Description): SOC Portal Live Write & Read API
 *    - ดำเนินการในฐานะ (Execute as): ฉัน (Me)  <-- สำคัญมาก! เพื่อให้ใช้สิทธิ์แก้ไขของคุณ
 *    - ผู้ที่มีสิทธิ์เข้าถึง (Who has access): ทุกคน (Anyone) หรือ ภายในองค์กร
 * 7. กด "ทำให้ใช้งานได้" (Deploy) > ให้สิทธิ์ (Authorize access) หากมีแจ้งเตือน
 * 8. คัดลอก "URL เว็บแอป" (Web App URL) ที่ได้ (ขึ้นต้นด้วย https://script.google.com/macros/s/.../exec)
 * 9. นำมาวางในช่อง "Google Apps Script Web App URL สำหรับเขียนข้อมูล" ในหน้าเว็บ SOC Dashboard
 */

function getTargetSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  // พยายามหาชีท "[OG] TimetableFullSocn" หรือ "TTB - Registration" หรือชีทปัจจุบัน
  var sheet = ss.getSheetByName("[OG] TimetableFullSocn") || 
              ss.getSheetByName("TTB - Registration") || 
              ss.getActiveSheet();
  return sheet;
}

// ----------------------------------------------------------------------------
// GET REQUEST: ส่งข้อมูลทริปทั้งหมดกลับไปให้ Dashboard
// ----------------------------------------------------------------------------
function doGet(e) {
  try {
    var sheet = getTargetSheet();
    var data = sheet.getDataRange().getValues();
    if (!data || data.length < 3) {
      return jsonResponse({ success: false, error: "ไม่พบข้อมูลใน Sheet หรือตารางว่างเปล่า" });
    }
    
    // แถวที่ 2 (Index 1) คือ Header คอลัมน์
    // แถวที่ 3 (Index 2) เป็นต้นไปคือข้อมูล
    var rows = [];
    var startRowIdx = 2; // Row 3
    
    for (var i = startRowIdx; i < data.length; i++) {
      var r = data[i];
      var lhTrip = String(r[10] || "").trim();      // Col K (Index 10): LH Trips
      var destination = String(r[16] || "").trim(); // Col Q (Index 16): Destination
      
      if (!lhTrip && !destination) continue;
      
      rows.push({
        rowIndex: i + 1, // Row number in sheet (1-based)
        driverId: String(r[1] || "").trim(),        // Col B: Driver ID
        driverName: String(r[2] || "").trim(),      // Col C: ชื่อ พนักงานขับรถ
        plate: String(r[3] || "").trim(),           // Col D: ทะเบียน
        vehicleType: String(r[4] || "").trim(),     // Col E: ประเภทรถ
        status: String(r[8] || "").trim(),          // Col I: Status
        assignStatus: String(r[9] || "").trim(),    // Col J: Assign Status
        lhTrip: lhTrip,                             // Col K: LH Trips
        standbyTime: formatTimeValue(r[13]),        // Col N: Standby Time
        loadingTime: formatTimeValue(r[14]),        // Col O: Loading Time
        departureTime: formatTimeValue(r[15]),      // Col P: Departure time
        destination: destination,                   // Col Q: Destination
        truckTypeReq: String(r[17] || "").trim(),   // Col R: truck type
        dock: String(r[19] || "").trim(),           // Col T: Dock
        subcon: String(r[20] || "").trim(),         // Col U: Subcon
        cot: String(r[21] || "").trim(),            // Col V: COT
        newTrip: String(r[22] || "").trim(),        // Col W: New trip
        remarkLh: String(r[23] || "").trim(),       // Col X: Remark LH (ว.สลับรถ)
        obZone: String(r[24] || "").trim(),         // Col Y: OB zone
        arrivalStatus: String(r[25] || "").trim(),  // Col Z: Arrival On-time/Late (Ontime/Late)
        remarkOb: String(r[26] || "").trim(),       // Col AA: Remark OB (เช่น รอคัดแยก, สลับรถ)
        lateType: String(r[27] || "").trim(),       // Col AB: Late Type (สูตรคำนวณ)
        cutoff: formatTimeValue(r[29])              // Col AD: Cutoff
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
// POST REQUEST: รับค่าแก้ไขจาก SOC Dashboard ไปเขียนลง Sheet จริง
// ----------------------------------------------------------------------------
function doPost(e) {
  try {
    var contents = e.postData.contents;
    var payload = JSON.parse(contents);
    var action = payload.action || "UPDATE_ROW";
    
    var sheet = getTargetSheet();
    var dataRange = sheet.getDataRange();
    var data = dataRange.getValues();
    
    // 1. UPDATE SINGLE ROW (แก้ไข 1 รายการ)
    if (action === "UPDATE_ROW") {
      var rowIndex = payload.rowIndex;
      var lhTrip = payload.lhTrip;
      var updates = payload.updates || {};
      
      // ถ้าไม่ได้ส่ง rowIndex มา ให้ค้นหาจาก LH Trip (Col K = Index 10)
      if (!rowIndex && lhTrip) {
        for (var i = 2; i < data.length; i++) {
          if (String(data[i][10] || "").trim() === String(lhTrip).trim()) {
            rowIndex = i + 1;
            break;
          }
        }
      }
      
      if (!rowIndex || rowIndex < 3 || rowIndex > data.length) {
        return jsonResponse({ success: false, error: "ไม่พบแถวที่ตรงกับ LH Trip: " + lhTrip + " หรือ rowIndex ไม่ถูกต้อง" });
      }
      
      applyRowUpdates(sheet, rowIndex, updates);
      
      return jsonResponse({
        success: true,
        message: "อัปเดตข้อมูลลง Google Sheet แถวที่ " + rowIndex + " (" + (lhTrip || "") + ") สำเร็จเรียบร้อยแล้ว",
        rowIndex: rowIndex,
        lhTrip: lhTrip,
        updates: updates
      });
    }
    
    // 2. BATCH UPDATE (แก้ไขหลายรายการพร้อมกัน)
    if (action === "UPDATE_BATCH") {
      var items = payload.items || [];
      if (!items || items.length === 0) {
        return jsonResponse({ success: false, error: "ไม่มีรายการที่ส่งมาอัปเดต" });
      }
      
      // สร้าง Lookup Map ของ LH Trip -> RowIndex
      var lhMap = {};
      for (var i = 2; i < data.length; i++) {
        var kTrip = String(data[i][10] || "").trim();
        if (kTrip) lhMap[kTrip] = i + 1;
      }
      
      var updatedCount = 0;
      for (var j = 0; j < items.length; j++) {
        var it = items[j];
        var rIdx = it.rowIndex || lhMap[it.lhTrip];
        if (rIdx && rIdx >= 3) {
          applyRowUpdates(sheet, rIdx, it.updates || {});
          updatedCount++;
        }
      }
      
      return jsonResponse({
        success: true,
        message: "อัปเดตข้อมูลลง Google Sheet สำเร็จทั้งหมด " + updatedCount + " รายการ",
        updatedCount: updatedCount
      });
    }
    
    return jsonResponse({ success: false, error: "ไม่รู้จักคำสั่ง action: " + action });
    
  } catch (err) {
    return jsonResponse({ success: false, error: err.toString() });
  }
}

// ----------------------------------------------------------------------------
// Helper Function สำหรับเขียนค่าลงในคอลัมน์ที่ถูกต้องของ Sheet
// ----------------------------------------------------------------------------
function applyRowUpdates(sheet, rowIndex, updates) {
  // Col Z (Col 26): Arrival On-time/Late (Ontime, Late, เลื่อนเวลาปล่อยรถ, ไม่ใช้รถ)
  if (updates.arrivalStatus !== undefined) {
    sheet.getRange(rowIndex, 26).setValue(updates.arrivalStatus);
  }
  
  // Col AA (Col 27): Remark OB (เช่น รอคัดแยก, สลับรถ, LHแจ้งไม่ใช้รถรอบนี้)
  if (updates.remarkOb !== undefined) {
    sheet.getRange(rowIndex, 27).setValue(updates.remarkOb);
  }
  
  // Col W (Col 23): New trip (สลับรถ / เลขทริปใหม่)
  if (updates.newTrip !== undefined) {
    sheet.getRange(rowIndex, 23).setValue(updates.newTrip);
  }
  
  // Col X (Col 24): Remark LH (ว.สลับรถ หรือปัญหาอื่นๆ)
  if (updates.remarkLh !== undefined) {
    sheet.getRange(rowIndex, 24).setValue(updates.remarkLh);
  }
  
  // Col D (Col 4): ทะเบียน
  if (updates.plate !== undefined) {
    sheet.getRange(rowIndex, 4).setValue(updates.plate);
  }
  
  // Col C (Col 3): ชื่อ พนักงานขับรถ
  if (updates.driverName !== undefined) {
    sheet.getRange(rowIndex, 3).setValue(updates.driverName);
  }
  
  // Col T (Col 20): Dock (ช่องจอด)
  if (updates.dock !== undefined) {
    sheet.getRange(rowIndex, 20).setValue(updates.dock);
  }
  
  // Col AB (Col 28): Late Type (ถ้าผู้ใช้ระบุ override เอง)
  if (updates.lateType !== undefined && updates.lateType !== "") {
    sheet.getRange(rowIndex, 28).setValue(updates.lateType);
  }
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
