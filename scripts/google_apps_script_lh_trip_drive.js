/**
 * =========================================================================================
 * 🚚 Google Apps Script: Auto-Export LH Trip & Dashboard Charts to Google Drive Folder
 * Target Folder ID: 1AwxaJv04MQ4g1l3MSOCSsC5bQrAaXoI1 (SOCN OBD On Time)
 * File Name Format: "Dashboard Charts - YYYY-MM-DD" (Ops Date)
 * Ultra-Fast Batched Execution (< 3 Seconds)
 * =========================================================================================
 */

var TARGET_FOLDER_ID = "1AwxaJv04MQ4g1l3MSOCSsC5bQrAaXoI1";

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({
    success: true,
    message: "LH Trip Google Drive Auto-Exporter Webhook is active and ready!",
    targetFolderId: TARGET_FOLDER_ID,
    timestamp: new Date().toISOString()
  })).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    var rawData = "";
    if (e && e.parameter && e.parameter.payload) {
      rawData = e.parameter.payload;
    } else if (e && e.postData && e.postData.contents) {
      rawData = e.postData.contents;
    }
    
    var payload = {};
    try {
      payload = typeof rawData === 'object' ? rawData : JSON.parse(rawData);
    } catch(err) {
      return ContentService.createTextOutput(JSON.stringify({
        success: false,
        error: "Invalid JSON payload: " + err.message
      })).setMimeType(ContentService.MimeType.JSON);
    }

    var result = createDashboardChartsSpreadsheet(payload);
    return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      error: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function createDashboardChartsSpreadsheet(data) {
  var opsDateFormatted = data.opsDate || "";
  if (!opsDateFormatted) {
    var dateStr = data.date || Utilities.formatDate(new Date(), "GMT+7", "yyyy-MM-dd");
    var dt = new Date(dateStr);
    if (isNaN(dt.getTime())) dt = new Date();
    dt.setDate(dt.getDate() - 1);
    opsDateFormatted = Utilities.formatDate(dt, "GMT+7", "yyyy-MM-dd");
  }
  var fileName = "Dashboard Charts - " + opsDateFormatted;

  // 1. Target Folder Validation
  var folder;
  try {
    folder = DriveApp.getFolderById(TARGET_FOLDER_ID);
    if (!folder) {
      throw new Error("ไม่พบโฟลเดอร์เป้าหมาย ID: " + TARGET_FOLDER_ID);
    }
  } catch(fErr) {
    return {
      success: false,
      error: "Gmail ที่ใช้ Deploy ยังไม่ได้รับสิทธิ์เข้าถึงโฟลเดอร์เป้าหมาย! 👉 กรุณาใช้เมลบริษัทเปิดโฟลเดอร์นี้ https://drive.google.com/drive/folders/" + TARGET_FOLDER_ID + " แล้วกด 'แชร์' ให้ Gmail ส่วนตัวนี้โดยเลือกสิทธิ์เป็น 'ผู้แก้ไข (Editor)' ครับ"
    };
  }

  // 2. Fast check if file already exists in target folder -> Update in-place
  var targetSpreadsheet = null;
  try {
    var existingFiles = folder.getFilesByName(fileName);
    if (existingFiles.hasNext()) {
      var existingFile = existingFiles.next();
      targetSpreadsheet = SpreadsheetApp.openById(existingFile.getId());
      while (existingFiles.hasNext()) {
        existingFiles.next().setTrashed(true);
      }
    }
  } catch(e) {}

  if (!targetSpreadsheet) {
    targetSpreadsheet = SpreadsheetApp.create(fileName);
    try {
      var file = DriveApp.getFileById(targetSpreadsheet.getId());
      file.moveTo(folder);
    } catch(moveErr) {
      try {
        folder.addFile(file);
        DriveApp.getRootFolder().removeFile(file);
      } catch(addErr) {}
    }
  }

  var sheet = targetSpreadsheet.getSheetByName("LH Trip Dashboard Report");
  if (sheet) {
    sheet.clear();
    sheet.clearFormats();
  } else {
    sheet = targetSpreadsheet.getActiveSheet();
    sheet.setName("LH Trip Dashboard Report");
  }
  sheet.setTabColor("#10B981");

  // Format full content matching exact user layout (High Speed Batching)
  buildDashboardReportSheet(sheet, data, fileName, opsDateFormatted);

  SpreadsheetApp.flush();

  return {
    success: true,
    message: "บันทึกไฟล์ " + fileName + " เข้าโฟลเดอร์ Google Drive เรียบร้อยแล้ว!",
    fileName: fileName,
    fileId: targetSpreadsheet.getId(),
    fileUrl: targetSpreadsheet.getUrl(),
    folderId: TARGET_FOLDER_ID,
    folderUrl: folder.getUrl(),
    opsDate: opsDateFormatted
  };
}

function buildDashboardReportSheet(sheet, data, fileName, opsDateFormatted) {
  var hasPrecalculated = !!(data && data.summary && data.lateMatrixStats && data.lateMatrixStats.length > 0);

  var totalTrips = 0, lateTrips = 0, onTimeTrips = 0, totalOrders = 0, lateOrders = 0, onTimeOrders = 0;
  var onTimePct = "0.00", latePct = "0.00";
  var obLateCount = 0, lhLateCount = 0, obLateOrders = 0, lhLateOrders = 0;
  var obTripShare = "0.0", lhTripShare = "0.0", obOrdShare = "0.0", lhOrdShare = "0.0";
  var obLateIntent = 0, obLateNonIntent = 0, lhLateIntent = 0, lhLateNonIntent = 0;
  var upcLateCount = 0, upcLateOrders = 0, gbkkLateCount = 0, gbkkLateOrders = 0;
  var upcTripShare = "0.0", upcOrdShare = "0.0", gbkkTripShare = "0.0", gbkkOrdShare = "0.0";
  var obZoneA = 0, obZoneB = 0, obZoneC = 0, lhZoneA = 0, lhZoneB = 0, lhZoneC = 0;

  var lateMatrix = [], onTimeMatrix = [], totalMatrix = [], hourList = [];
  var vehStatsList = [], topLHHubs = [], topOBHubs = [];
  var normalizedRows = [];

  if (hasPrecalculated) {
    var s = data.summary || {};
    var ex = data.executiveLate || {};
    totalTrips = Number(s.totalTrips || 0);
    onTimeTrips = Number(s.onTimeTrips || 0);
    lateTrips = Number(s.lateTrips || 0);
    totalOrders = Number(s.totalOrders || 0);
    onTimeOrders = Number(s.onTimeOrders || 0);
    lateOrders = Number(s.lateOrders || 0);
    onTimePct = String(s.onTimePct || "0.00");
    latePct = String(s.latePct || "0.00");

    obLateCount = Number(ex.obLateCount || 0);
    lhLateCount = Number(ex.lhLateCount || 0);
    obLateOrders = Number(ex.obLateOrders || 0);
    lhLateOrders = Number(ex.lhLateOrders || 0);
    obTripShare = String(ex.obLateTripShare || "0.0");
    lhTripShare = String(ex.lhLateTripShare || "0.0");
    obOrdShare = String(ex.obLateOrderShare || "0.0");
    lhOrdShare = String(ex.lhLateOrderShare || "0.0");
    obLateIntent = Number(ex.obLateIntent || 0);
    obLateNonIntent = Number(ex.obLateNonIntent || 0);
    lhLateIntent = Number(ex.lhLateIntent || 0);
    lhLateNonIntent = Number(ex.lhLateNonIntent || 0);

    upcLateCount = Number(ex.upcLateCount || 0);
    upcLateOrders = Number(ex.upcLateOrders || 0);
    upcTripShare = String(ex.upcLateTripShare || "0.0");
    upcOrdShare = String(ex.upcOrderShare || "0.0");

    gbkkLateCount = Number(ex.gbkkLateCount || 0);
    gbkkLateOrders = Number(ex.gbkkLateOrders || 0);
    gbkkTripShare = String(ex.gbkkLateTripShare || "0.0");
    gbkkOrdShare = String(ex.gbkkOrderShare || "0.0");

    obZoneA = Number(ex.obZoneA || 0);
    obZoneB = Number(ex.obZoneB || 0);
    obZoneC = Number(ex.obZoneC || 0);
    lhZoneA = Number(ex.lhZoneA || 0);
    lhZoneB = Number(ex.lhZoneB || 0);
    lhZoneC = Number(ex.lhZoneC || 0);

    lateMatrix = data.lateMatrixStats || [];
    onTimeMatrix = data.onTimeMatrixStats || [];
    totalMatrix = data.totalMatrixStats || [];
    hourList = data.hourStats || [];
    vehStatsList = data.vehStats || [];
    topLHHubs = data.top50LHHubs || [];
    topOBHubs = data.top50OBHubs || [];

    if (data.compactRawRows && data.compactRawRows.length > 0) {
      for (var cr = 0; cr < data.compactRawRows.length; cr++) {
        var it = data.compactRawRows[cr];
        normalizedRows.push({
          no: it[0] || (cr + 1),
          shipment_id: it[1] || "",
          trip_category: it[2] || "",
          vehicle_type: it[3] || "",
          vehicle_plate: it[4] || "",
          driver: it[5] || "",
          origin: it[6] || "SOCN",
          dest_station_name: it[7] || "",
          outbound_order: Number(it[8]) || 0,
          outbound_weight: Number(it[9]) || 0,
          standby_time: it[10] || "",
          assign_time: it[11] || "",
          cut0: it[12] || "",
          cut1: it[13] || "",
          cut2: it[14] || "",
          cut3: it[15] || "",
          actual_dep_cut: it[16] || "",
          rmk: it[17] || "",
          status: String(it[18] || "").toLowerCase().indexOf("late") !== -1 ? "Late" : "On time"
        });
      }
    }
  }

  // Deduplicate and fallback compute if needed
  if (!hasPrecalculated || normalizedRows.length === 0) {
    var rawList = data.compactRawRows || data.outboundRawRows || data.rows || [];
    var rawItems = [];
    for (var i = 0; i < rawList.length; i++) {
      var item = rawList[i];
      if (Array.isArray(item)) {
        rawItems.push({
          no: item[0] || (i + 1),
          shipment_id: item[1] || "",
          trip_category: item[2] || "",
          vehicle_type: item[3] || "",
          vehicle_plate: item[4] || "",
          driver: item[5] || "",
          origin: item[6] || "SOCN",
          dest_station_name: item[7] || "",
          outbound_order: Number(item[8]) || (Number(item[30]) || 0),
          outbound_weight: Number(item[9]) || (Number(item[31]) || 0),
          standby_time: item[10] || (item[19] || ""),
          assign_time: item[11] || (item[20] || ""),
          cut0: item[12] || (item[15] || ""),
          cut1: item[13] || (item[16] || ""),
          cut2: item[14] || (item[17] || ""),
          cut3: item[15] || (item[18] || ""),
          actual_dep_cut: item[16] || (item[21] || ""),
          rmk: item[17] || (item[24] || ""),
          status: String(item[18] || item[23] || "").toLowerCase().indexOf("late") !== -1 ? "Late" : "On time"
        });
      }
    }
    normalizedRows = rawItems;
    totalTrips = normalizedRows.length;
  }

  // 4. Construct Sheet Cells Array
  var allCells = [];
  var blockFormats = []; // Batched range formats

  function addRow(arr) {
    var row = [];
    for (var c = 0; c < 19; c++) {
      row.push(arr[c] !== undefined ? arr[c] : "");
    }
    allCells.push(row);
    return allCells.length; // 1-indexed row number
  }

  function addEmptyRow() {
    addRow([]);
  }

  // Title Banner
  var rTitle = addRow(["🚚 LH TRIP & OB LATE EXECUTIVE REPORT (สรุปรายชั่วโมง + OUTBOUND ORDERS + RAW DATA)"]);
  blockFormats.push({ range: "A" + rTitle + ":S" + rTitle, merge: true, bold: true, size: 14, color: "#0F172A", align: "left" });

  // Subtitle
  var rSub = addRow(["ส่งออกข้อมูลเมื่อ: " + (data.archivedAt || new Date().toLocaleString('th-TH')) + " | เที่ยวรถทั้งหมด: " + totalTrips.toLocaleString() + " เที่ยว | พัสดุ Outbound ทั้งหมด: " + totalOrders.toLocaleString() + " ชิ้น"]);
  blockFormats.push({ range: "A" + rSub + ":S" + rSub, merge: true, bold: false, size: 9, color: "#475569", align: "left" });

  // KPI Summary Cards
  var rKpiHead = addRow(["รวมเที่ยวรถทั้งหมด (TOTAL TRIPS)", "ตรงเวลา (ON TIME)", "สาย (LATE)", "อัตราตรงเวลา (ON-TIME RATE)", "อัตราสาย (LATE RATE)"]);
  blockFormats.push({ range: "A" + rKpiHead + ":E" + rKpiHead, bg: "#E2E8F0", color: "#0F172A", bold: true, size: 10, align: "center", border: true });

  var rKpiVal1 = addRow([
    totalTrips.toLocaleString() + " เที่ยว",
    onTimeTrips.toLocaleString() + " เที่ยว",
    lateTrips.toLocaleString() + " เที่ยว",
    onTimePct + "%",
    latePct + "%"
  ]);
  blockFormats.push({ range: "A" + rKpiVal1 + ":E" + rKpiVal1, bold: true, size: 12, align: "center", border: true });

  var rKpiVal2 = addRow([
    totalOrders.toLocaleString() + " Orders",
    onTimeOrders.toLocaleString() + " Orders",
    lateOrders.toLocaleString() + " Orders",
    "On-Time Orders",
    "Late Orders"
  ]);
  blockFormats.push({ range: "A" + rKpiVal2 + ":E" + rKpiVal2, bold: false, size: 9, color: "#64748B", align: "center", border: true });
  addEmptyRow();

  // Executive Breakdown Table
  var rExBan = addRow(["📊 สรุปเจาะลึกเที่ยวรถที่สาย (Executive Late Breakdown) - ฝั่ง Outbound vs Linehaul & ภูมิภาค"]);
  blockFormats.push({ range: "A" + rExBan + ":H" + rExBan, merge: true, bg: "#FEF2F2", color: "#991B1B", bold: true, size: 10, align: "left", border: true });

  var rExHead = addRow(["กลุ่มการวิเคราะห์ (Category)", "จำนวนเที่ยวสาย (Late Trips)", "สัดส่วนเที่ยวสาย (% Share)", "จำนวนพัสดุสาย (Late Orders)", "สัดส่วนพัสดุสาย (% Share)", "Intentional Late", "Non-Intentional Late", "กระจายตามโซน"]);
  blockFormats.push({ range: "A" + rExHead + ":H" + rExHead, bg: "#F1F5F9", color: "#0F172A", bold: true, size: 9, align: "center", border: true });

  var rEx1 = addRow(["🔴 OB Late (คลังโหลดช้า)", obLateCount + " เที่ยว", obTripShare + "%", obLateOrders.toLocaleString() + " ชิ้น", obOrdShare + "%", obLateIntent + " เที่ยว", obLateNonIntent + " เที่ยว", "A:" + obZoneA + " | B:" + obZoneB + " | C:" + obZoneC]);
  var rEx2 = addRow(["🟡 LH Late (ขนส่งสาย)", lhLateCount + " เที่ยว", lhTripShare + "%", lhLateOrders.toLocaleString() + " ชิ้น", lhOrdShare + "%", lhLateIntent + " เที่ยว", lhLateNonIntent + " เที่ยว", "A:" + lhZoneA + " | B:" + lhZoneB + " | C:" + lhZoneC]);
  var rEx3 = addRow(["🌐 UPC (ต่างจังหวัด)", upcLateCount + " เที่ยว", upcTripShare + "%", upcLateOrders.toLocaleString() + " ชิ้น", upcOrdShare + "%", "-", "-", "-"]);
  var rEx4 = addRow(["🏙️ GBKK (กรุงเทพฯ/ปริมณฑล)", gbkkLateCount + " เที่ยว", gbkkTripShare + "%", gbkkLateOrders.toLocaleString() + " ชิ้น", gbkkOrdShare + "%", "-", "-", "-"]);
  blockFormats.push({ range: "A" + rEx1 + ":H" + rEx4, border: true, size: 9 });
  blockFormats.push({ range: "A" + rEx1 + ":A" + rEx4, bold: true, align: "left" });
  blockFormats.push({ range: "B" + rEx1 + ":H" + rEx4, align: "center" });
  addEmptyRow();

  // Helper for rendering 24-hour matrix tables in bulk
  function render24HrMatrixTable(title, bannerBg, bannerColor, matrixData, colHeaderPrefix) {
    var rBan = addRow([title]);
    blockFormats.push({ range: "A" + rBan + ":G" + rBan, merge: true, bg: bannerBg, color: bannerColor, bold: true, size: 10, align: "left", border: true });

    var rHead = addRow(["ช่วงเวลา (Time Range)", "4W", "4WJ", "6W", "Semi trailer", "อื่นๆ (Other)", colHeaderPrefix + " (Total)"]);
    blockFormats.push({ range: "A" + rHead + ":G" + rHead, bg: "#F1F5F9", color: "#0F172A", bold: true, size: 9, align: "center", border: true });

    var startRow = allCells.length + 1;
    var s4W = 0, s4WJ = 0, s6W = 0, sSemi = 0, sOther = 0, sTot = 0;
    for (var h = 0; h < 24; h++) {
      var item = matrixData[h] || { timeRange: (h < 10 ? "0" + h : h) + ":00 - " + ((h+1)%24 < 10 ? "0" + (h+1)%24 : (h+1)%24) + ":00", c4W: 0, c4WJ: 0, c6W: 0, cSemi: 0, cOther: 0, totalLate: 0, totalOnTime: 0, totalTrips: 0 };
      var tVal = item.totalLate !== undefined ? item.totalLate : (item.totalOnTime !== undefined ? item.totalOnTime : (item.totalTrips || 0));
      s4W += (item.c4W || 0); s4WJ += (item.c4WJ || 0); s6W += (item.c6W || 0); sSemi += (item.cSemi || 0); sOther += (item.cOther || 0); sTot += tVal;
      addRow([item.timeRange, item.c4W || 0, item.c4WJ || 0, item.c6W || 0, item.cSemi || 0, item.cOther || 0, tVal]);
    }
    var endRow = allCells.length;
    blockFormats.push({ range: "A" + startRow + ":G" + endRow, border: true, size: 9 });
    blockFormats.push({ range: "A" + startRow + ":A" + endRow, align: "left" });
    blockFormats.push({ range: "B" + startRow + ":G" + endRow, align: "center" });

    var rGrand = addRow(["รวมทั้งสิ้น (Grand Total)", s4W, s4WJ, s6W, sSemi, sOther, sTot]);
    blockFormats.push({ range: "A" + rGrand + ":G" + rGrand, bg: "#E2E8F0", color: "#0F172A", bold: true, align: "center", border: true });
    addEmptyRow();
  }

  // 1. Table 1: Late Matrix
  render24HrMatrixTable("🔴 1. ตารางเที่ยวรถที่สาย (Late Trips by Vehicle & Actual Dep Cut)", "#FEE2E2", "#991B1B", lateMatrix, "รวมเที่ยวสาย");

  // 2. Table 2: On-Time Matrix
  render24HrMatrixTable("🟢 2. ตารางเที่ยวรถที่ตรงเวลา (On-Time Trips by Vehicle & Actual Dep Cut)", "#DCFCE7", "#166534", onTimeMatrix, "รวมเที่ยวตรงเวลา");

  // 3. Table 3: Total Matrix
  render24HrMatrixTable("📊 3. ตารางเที่ยวรถทั้งหมด (Total Trips by Vehicle & Actual Dep Cut)", "#F1F5F9", "#0F172A", totalMatrix, "รวมเที่ยวทั้งหมด");

  // 4. Table 4: Hourly On-Time vs Late
  var rH4Ban = addRow(["⏰ 4. สรุปภาพรวมรายชั่วโมง: เที่ยวรถตรงเวลา vs สาย และจำนวน Orders (Hourly Summary)"]);
  blockFormats.push({ range: "A" + rH4Ban + ":G" + rH4Ban, merge: true, bg: "#FEF3C7", color: "#92400E", bold: true, size: 10, align: "left", border: true });

  var rH4Head = addRow(["ช่วงเวลา (Time Range)", "ตรงเวลา (Trips)", "📦 Orders ตรงเวลา", "สาย (Trips)", "📦 Orders ที่สาย", "รวมเที่ยว (Total)", "อัตราสาย (% Late)"]);
  blockFormats.push({ range: "A" + rH4Head + ":G" + rH4Head, bg: "#F1F5F9", color: "#0F172A", bold: true, size: 9, align: "center", border: true });

  var rH4Start = allCells.length + 1;
  var sOnT = 0, sOnO = 0, sLt = 0, sLtO = 0;
  for (var hr = 0; hr < 24; hr++) {
    var hObj = hourList[hr] || { timeRange: (hr < 10 ? "0" + hr : hr) + ":00 - " + ((hr+1)%24 < 10 ? "0" + (hr+1)%24 : (hr+1)%24) + ":00", onTime: 0, onTimeOrders: 0, late: 0, lateOrders: 0, total: 0, latePct: "0.0%" };
    sOnT += (hObj.onTime || 0); sOnO += (hObj.onTimeOrders || 0); sLt += (hObj.late || 0); sLtO += (hObj.lateOrders || 0);
    addRow([hObj.timeRange, hObj.onTime || 0, Number(hObj.onTimeOrders||0).toLocaleString(), hObj.late || 0, Number(hObj.lateOrders||0).toLocaleString(), hObj.total || 0, hObj.latePct || "0.0%"]);
  }
  var rH4End = allCells.length;
  blockFormats.push({ range: "A" + rH4Start + ":G" + rH4End, border: true, size: 9 });
  blockFormats.push({ range: "A" + rH4Start + ":A" + rH4End, align: "left" });
  blockFormats.push({ range: "B" + rH4Start + ":B" + rH4End, align: "center" });
  blockFormats.push({ range: "C" + rH4Start + ":C" + rH4End, align: "right" });
  blockFormats.push({ range: "D" + rH4Start + ":D" + rH4End, align: "center", color: "#B91C1C" });
  blockFormats.push({ range: "E" + rH4Start + ":E" + rH4End, align: "right", color: "#B91C1C" });
  blockFormats.push({ range: "F" + rH4Start + ":G" + rH4End, align: "center" });

  var sTotTrips = sOnT + sLt;
  var rH4Grand = addRow(["รวมทั้งสิ้น (Grand Total)", sOnT, sOnO.toLocaleString(), sLt, sLtO.toLocaleString(), sTotTrips, (sTotTrips ? ((sLt/sTotTrips)*100).toFixed(1) + "%" : "0.0%")]);
  blockFormats.push({ range: "A" + rH4Grand + ":G" + rH4Grand, bg: "#E2E8F0", color: "#0F172A", bold: true, align: "center", border: true });
  addEmptyRow();

  // 5. Table 5: Vehicle Type Breakdown
  var rVBan = addRow(["🚛 5. สรุปจำนวนเที่ยวรถและยอด Orders แยกตามประเภทรถ (Vehicle Type Breakdown)"]);
  blockFormats.push({ range: "A" + rVBan + ":H" + rVBan, merge: true, bg: "#DBEAFE", color: "#1E3A8A", bold: true, size: 10, align: "left", border: true });

  var rVHead = addRow(["ลำดับ", "ประเภทรถ (Vehicle Type)", "ตรงเวลา (Trips)", "📦 Orders ตรงเวลา", "สาย (Trips)", "📦 Orders ที่สาย", "รวมเที่ยว (Total)", "อัตราสาย (% Late)"]);
  blockFormats.push({ range: "A" + rVHead + ":H" + rVHead, bg: "#F1F5F9", color: "#0F172A", bold: true, size: 9, align: "center", border: true });

  var rVStart = allCells.length + 1;
  for (var v = 0; v < vehStatsList.length; v++) {
    var vs = vehStatsList[v];
    addRow([v + 1, vs.vehType, Number(vs.onTime||0), Number(vs.onTimeOrders||0).toLocaleString(), Number(vs.late||0), Number(vs.lateOrders||0).toLocaleString(), Number(vs.total||0), vs.latePct]);
  }
  var rVEnd = allCells.length;
  if (vehStatsList.length > 0) {
    blockFormats.push({ range: "A" + rVStart + ":H" + rVEnd, border: true, size: 9 });
    blockFormats.push({ range: "A" + rVStart + ":A" + rVEnd, align: "center" });
    blockFormats.push({ range: "B" + rVStart + ":B" + rVEnd, align: "left", bold: true });
    blockFormats.push({ range: "C" + rVStart + ":C" + rVEnd, align: "center" });
    blockFormats.push({ range: "D" + rVStart + ":D" + rVEnd, align: "right" });
    blockFormats.push({ range: "E" + rVStart + ":E" + rVEnd, align: "center", color: "#B91C1C" });
    blockFormats.push({ range: "F" + rVStart + ":F" + rVEnd, align: "right", color: "#B91C1C" });
    blockFormats.push({ range: "G" + rVStart + ":H" + rVEnd, align: "center" });
  }
  addEmptyRow();

  // 6A. Table 6A: Top 50 LH Late Hubs
  var rLhBan = addRow(["🏆 6A. Top 50 Hubs ที่ LH Late สูงสุด (Top 50 LH Late Hubs - ฝั่งขนส่ง Linehaul)"]);
  blockFormats.push({ range: "A" + rLhBan + ":F" + rLhBan, merge: true, bg: "#FEF3C7", color: "#92400E", bold: true, size: 10, align: "left", border: true });

  var rLhHead = addRow(["อันดับ", "Hub ปลายทาง (Destination)", "จำนวนเที่ยว LH Late", "📦 พัสดุที่สาย (Late Orders)", "รวมเที่ยวทั้งหมด (Total)", "อัตราสาย (% LH Late)"]);
  blockFormats.push({ range: "A" + rLhHead + ":F" + rLhHead, bg: "#F1F5F9", color: "#0F172A", bold: true, size: 9, align: "center", border: true });

  var rLhStart = allCells.length + 1;
  for (var lh = 0; lh < topLHHubs.length; lh++) {
    var itemLH = topLHHubs[lh];
    addRow([lh + 1, itemLH.hub, Number(itemLH.late||0), Number(itemLH.lateOrders||0).toLocaleString(), Number(itemLH.total||0), itemLH.pct]);
  }
  var rLhEnd = allCells.length;
  if (topLHHubs.length > 0) {
    blockFormats.push({ range: "A" + rLhStart + ":F" + rLhEnd, border: true, size: 9 });
    blockFormats.push({ range: "A" + rLhStart + ":A" + rLhEnd, align: "center" });
    blockFormats.push({ range: "B" + rLhStart + ":B" + rLhEnd, align: "left", color: "#B45309", bold: true });
    blockFormats.push({ range: "C" + rLhStart + ":C" + rLhEnd, align: "center", color: "#B45309", bold: true });
    blockFormats.push({ range: "D" + rLhStart + ":D" + rLhEnd, align: "right", color: "#B45309", bold: true });
    blockFormats.push({ range: "E" + rLhStart + ":F" + rLhEnd, align: "center" });
  }
  addEmptyRow();

  // 6B. Table 6B: Top 50 OB Late Hubs
  var rObBan = addRow(["🏆 6B. Top 50 Hubs ที่ OB Late สูงสุด (Top 50 OB Late Hubs - ฝั่งคลัง Outbound)"]);
  blockFormats.push({ range: "A" + rObBan + ":F" + rObBan, merge: true, bg: "#FEE2E2", color: "#991B1B", bold: true, size: 10, align: "left", border: true });

  var rObHead = addRow(["อันดับ", "Hub ปลายทาง (Destination)", "จำนวนเที่ยว OB Late", "📦 พัสดุที่สาย (Late Orders)", "รวมเที่ยวทั้งหมด (Total)", "อัตราสาย (% OB Late)"]);
  blockFormats.push({ range: "A" + rObHead + ":F" + rObHead, bg: "#F1F5F9", color: "#0F172A", bold: true, size: 9, align: "center", border: true });

  var rObStart = allCells.length + 1;
  for (var ob = 0; ob < topOBHubs.length; ob++) {
    var itemOB = topOBHubs[ob];
    addRow([ob + 1, itemOB.hub, Number(itemOB.late||0), Number(itemOB.lateOrders||0).toLocaleString(), Number(itemOB.total||0), itemOB.pct]);
  }
  var rObEnd = allCells.length;
  if (topOBHubs.length > 0) {
    blockFormats.push({ range: "A" + rObStart + ":F" + rObEnd, border: true, size: 9 });
    blockFormats.push({ range: "A" + rObStart + ":A" + rObEnd, align: "center" });
    blockFormats.push({ range: "B" + rObStart + ":B" + rObEnd, align: "left", color: "#B91C1C", bold: true });
    blockFormats.push({ range: "C" + rObStart + ":C" + rObEnd, align: "center", color: "#B91C1C", bold: true });
    blockFormats.push({ range: "D" + rObStart + ":D" + rObEnd, align: "right", color: "#B91C1C", bold: true });
    blockFormats.push({ range: "E" + rObStart + ":F" + rObEnd, align: "center" });
  }
  addEmptyRow();

  // 7. Table 7: Complete Raw Data
  var rRawBan = addRow(["📋 7. ข้อมูลดิบทั้งหมด (Complete Raw Data - รวม " + totalTrips.toLocaleString() + " เที่ยวรถ)"]);
  blockFormats.push({ range: "A" + rRawBan + ":S" + rRawBan, merge: true, bg: "#DBEAFE", color: "#1E3A8A", bold: true, size: 10, align: "left", border: true });

  var rawHeaders = [
    "NO.", "LH TRIP NUMBER", "TRIP CATEGORY", "VEHICLE TYPE", "VEHICLE PLATE", "DRIVER",
    "ต้นทาง", "ปลายทาง (DESTINATION)", "📦 OUTBOUND (ORDER)", "⚖️ WEIGHT (KG)",
    "STANDBY TIME", "ASSIGN TIME", "CUT 0", "CUT 1", "CUT 2", "CUT 3",
    "ACTUAL DEP CUT", "RMK", "STATUS"
  ];
  var rRawHead = addRow(rawHeaders);
  blockFormats.push({ range: "A" + rRawHead + ":S" + rRawHead, bg: "#0F172A", color: "#FFFFFF", bold: true, size: 9, align: "center", border: true });

  var rRawStart = allCells.length + 1;
  for (var rw = 0; rw < normalizedRows.length; rw++) {
    var rowObj = normalizedRows[rw];
    addRow([
      rw + 1,
      rowObj.shipment_id,
      rowObj.trip_category,
      rowObj.vehicle_type,
      rowObj.vehicle_plate,
      rowObj.driver,
      rowObj.origin,
      rowObj.dest_station_name,
      rowObj.outbound_order,
      rowObj.outbound_weight,
      rowObj.standby_time,
      rowObj.assign_time,
      rowObj.cut0,
      rowObj.cut1,
      rowObj.cut2,
      rowObj.cut3,
      rowObj.actual_dep_cut,
      rowObj.rmk,
      rowObj.status
    ]);
  }
  var rRawEnd = allCells.length;
  if (normalizedRows.length > 0) {
    blockFormats.push({ range: "A" + rRawStart + ":S" + rRawEnd, border: true, size: 9 });
    blockFormats.push({ range: "A" + rRawStart + ":A" + rRawEnd, align: "center" });
    blockFormats.push({ range: "B" + rRawStart + ":H" + rRawEnd, align: "left" });
    blockFormats.push({ range: "I" + rRawStart + ":J" + rRawEnd, align: "right" });
    blockFormats.push({ range: "K" + rRawStart + ":S" + rRawEnd, align: "center" });
  }

  // 🚀 FAST SINGLE BATCH WRITE
  if (allCells.length > 0) {
    var fullRange = sheet.getRange(1, 1, allCells.length, 19);
    fullRange.setValues(allCells);
    fullRange.setFontFamily("Segoe UI");
    fullRange.setFontSize(9);
    fullRange.setVerticalAlignment("middle");
  }

  // Set explicit column widths in single loop
  var colWidths = [170, 100, 90, 90, 160, 90, 120, 140, 110, 100, 90, 90, 80, 80, 80, 80, 100, 140, 90];
  for (var w = 0; w < colWidths.length; w++) {
    sheet.setColumnWidth(w + 1, colWidths[w]);
  }

  // 🚀 FAST BATCHED FORMATTING (< 30 calls total)
  for (var b = 0; b < blockFormats.length; b++) {
    var fmt = blockFormats[b];
    try {
      var tgt = sheet.getRange(fmt.range);
      if (fmt.merge) tgt.merge();
      if (fmt.bg) tgt.setBackground(fmt.bg);
      if (fmt.color) tgt.setFontColor(fmt.color);
      if (fmt.bold !== undefined) tgt.setFontWeight(fmt.bold ? "bold" : "normal");
      if (fmt.size) tgt.setFontSize(fmt.size);
      if (fmt.align) tgt.setHorizontalAlignment(fmt.align);
      if (fmt.border) {
        tgt.setBorder(true, true, true, true, true, true, "#CBD5E1", SpreadsheetApp.BorderStyle.SOLID);
      }
    } catch(err) {}
  }
}
