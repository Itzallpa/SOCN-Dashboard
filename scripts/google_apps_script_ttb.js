/**
 * Google Apps Script for Two-way Sync between "TTB - Registration" Google Sheet and SOC Operations Portal
 * ------------------------------------------------------------------------------------------------------
 * วิธีติดตั้งใน Google Sheets:
 * 1. เปิด Google Sheet "TTB - Registration" ของบริษัท
 * 2. ไปที่เมนู "ส่วนขยาย" (Extensions) > "Apps Script"
 * 3. ลบโค้ดเดิมทั้งหมดออก แล้วคัดลอกโค้ดนี้ไปวางแทนที่
 * 4. กดปุ่ม "บันทึก" (Save 💾)
 * 5. กดปุ่ม "การทำให้ใช้งานได้" (Deploy) > "การทำให้ใช้งานได้รายการใหม่" (New deployment)
 * 6. เลือกประเภทเป็น "เว็บแอป" (Web app)
 *    - คำอธิบาย (Description): TTB Live Sync API
 *    - ดำเนินการในฐานะ (Execute as): ฉัน (Me)
 *    - ผู้ที่มีสิทธิ์เข้าถึง (Who has access): ทุกคน (Anyone) หรือ ภายในองค์กร
 * 7. กด "ทำให้ใช้งานได้" (Deploy) แล้วคัดลอก "URL เว็บแอป" (Web App URL)
 * 8. นำ URL นั้นมาวางในเมนูตั้งค่า "Google Sheet Sync" ใน SOC Dashboard ได้ทันที!
 */

function doGet(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getActiveSheet();
    
    // หากต้องการระบุชื่อ Sheet ชัดเจน สามารถใช้:
    // var sheet = ss.getSheetByName("TTB - Registration") || ss.getActiveSheet();
    
    var data = sheet.getDataRange().getValues();
    if (!data || data.length < 3) {
      return jsonResponse({ success: false, error: "ไม่พบข้อมูลใน Sheet หรือตารางว่างเปล่า" });
    }
    
    // แถวที่ 2 (Index 1) คือ Header
    // แถวที่ 3 (Index 2) เป็นต้นไปคือแถวข้อมูลจริง
    var rows = [];
    var startRowIdx = 2; // Row 3 in 1-based indexing
    
    for (var i = startRowIdx; i < data.length; i++) {
      var r = data[i];
      var lhTrip = String(r[11] || "").trim(); // Col L (Index 11): LH Trips
      var destination = String(r[15] || "").trim(); // Col P (Index 15): Destination
      
      // ข้ามแถวที่ไม่มีข้อมูล LH Trip หรือ Destination
      if (!lhTrip && !destination) continue;
      
      rows.push({
        rowIndex: i + 1, // 1-based row index in Google Sheet
        driverId: String(r[0] || "").trim(), // Col A
        driverName: String(r[1] || "").trim(), // Col B: ชื่อพนักงานขับรถ
        plate: String(r[2] || "").trim(), // Col C: ทะเบียน
        vehicleType: String(r[3] || "").trim(), // Col D: ประเภทรถ
        status: String(r[4] || "").trim(), // Col E: Status
        assignStatus: String(r[5] || "").trim(), // Col F: Assign Status
        
        lhTrip: lhTrip, // Col L: LH Trips
        standbyTime: formatTimeValue(r[12]), // Col M: Standby Time
        loadingTime: formatTimeValue(r[13]), // Col N: Loading Time
        departureTime: formatTimeValue(r[14]), // Col O: Departure Time
        
        destination: destination, // Col P: Destination
        truckTypeReq: String(r[16] || "").trim(), // Col Q: truck type
        wheels: String(r[17] || "").trim(), // Col R: ห้ามแก้/ล้อ
        dock: String(r[18] || "").trim(), // Col S: ห้ามแก้/Dock
        subcon: String(r[19] || "").trim(), // Col T: ห้ามแก้/Subcon
        route: String(r[20] || "").trim(), // Col U: ห้ามแก้/สาย
        
        newTrip: String(r[21] || "").trim(), // Col V: New trip
        warningAlert: String(r[22] || "").trim(), // Col W: ว.แจ้งเตือน
        remarkLh: String(r[23] || "").trim(), // Col X: Remark LH
        obZone: String(r[24] || "").trim(), // Col Y: OB zone
        
        arrivalStatus: String(r[25] || "").trim(), // Col Z: Arrival On time/Late
        remarkOb: String(r[26] || "").trim(), // Col AA: Remark OB
        lateType: String(r[27] || "").trim(), // Col AB: Late Type
        cot: String(r[28] || "").trim(), // Col AC: COT
        cutoff: formatTimeValue(r[29]), // Col AD: Cutoff
        bookedTime: formatTimeValue(r[30]) // Col AE: Booked Time
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
    var contents = e.postData.contents;
    var payload = JSON.parse(contents);
    var action = payload.action || "UPDATE_ROW";
    
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getActiveSheet();
    
    if (action === "UPDATE_ROW") {
      var rowIndex = payload.rowIndex;
      var lhTrip = payload.lhTrip;
      var updates = payload.updates || {};
      
      // ถ้าไม่ได้ระบุ rowIndex ให้ค้นหาจาก LH Trip
      if (!rowIndex && lhTrip) {
        var data = sheet.getDataRange().getValues();
        for (var i = 2; i < data.length; i++) {
          if (String(data[i][11] || "").trim() === String(lhTrip).trim()) {
            rowIndex = i + 1;
            break;
          }
        }
      }
      
      if (!rowIndex || rowIndex < 3) {
        return jsonResponse({ success: false, error: "ไม่พบแถวที่ต้องการอัปเดต (LH Trip / rowIndex ไม่ถูกต้อง)" });
      }
      
      // อัปเดตช่องที่ส่งมา
      if (updates.plate !== undefined) sheet.getRange(rowIndex, 3).setValue(updates.plate); // Col C
      if (updates.driverName !== undefined) sheet.getRange(rowIndex, 2).setValue(updates.driverName); // Col B
      if (updates.newTrip !== undefined) sheet.getRange(rowIndex, 22).setValue(updates.newTrip); // Col V
      if (updates.remarkLh !== undefined) sheet.getRange(rowIndex, 24).setValue(updates.remarkLh); // Col X
      if (updates.remarkOb !== undefined) sheet.getRange(rowIndex, 27).setValue(updates.remarkOb); // Col AA
      if (updates.lateType !== undefined) sheet.getRange(rowIndex, 28).setValue(updates.lateType); // Col AB
      if (updates.arrivalStatus !== undefined) sheet.getRange(rowIndex, 26).setValue(updates.arrivalStatus); // Col Z
      
      return jsonResponse({
        success: true,
        message: "อัปเดตข้อมูลลง Google Sheet แถวที่ " + rowIndex + " เรียบร้อยแล้ว",
        rowIndex: rowIndex
      });
    }
    
    return jsonResponse({ success: false, error: "ไม่รู้จักคำสั่ง action: " + action });
    
  } catch (err) {
    return jsonResponse({ success: false, error: err.toString() });
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
