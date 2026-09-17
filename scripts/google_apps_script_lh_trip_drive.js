/**
 * =========================================================================================
 * 🚚 Google Apps Script: Auto-Export LH Trip & Dashboard Charts to Google Drive Folder
 * Target Folder ID: 1AwxaJv04MQ4g1l3MSOCSsC5bQrAaXoI1
 * File Name Format: "Dashboard Charts - YYYY-MM-DD" (Ops Date)
 * =========================================================================================
 * 
 * 📋 วิธีการติดตั้งและ Deploy ภายใน 1 นาที:
 * 1. เปิด https://script.google.com แล้วกดปุ่ม "+ โครงการใหม่ (New project)"
 * 2. คัดลอกโค้ดนี้ทั้งหมดไปวางแทนที่ Code.gs
 * 3. กด "บันทึก (Save - Ctrl+S)"
 * 4. กดปุ่ม "ทำให้ใช้งานได้ (Deploy)" ด้านบนขวา -> เลือก "การทำให้ใช้งานได้ใหม่ (New deployment)"
 * 5. เลือกประเภท: "เว็บแอป (Web app)"
 *    - คำอธิบาย: LH Trip Drive Exporter
 *    - ปฏิบัติการในฐานะ: ตัวฉัน (Me)
 *    - ผู้ที่มีสิทธิ์เข้าถึง: ทุกคน (Anyone)
 * 6. กด "ทำให้ใช้งานได้ (Deploy)" และกด "ให้สิทธิ์การเข้าถึง (Authorize Access)"
 * 7. คัดลอก URL ของเว็บแอป (ขึ้นต้นด้วย https://script.google.com/macros/s/.../exec) 
 *    มาใส่ในระบบ Dashboard หรือหน้า lh_trip.html ได้เลยครับ!
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
    var rawData = e.postData ? e.postData.contents : "";
    var payload = {};
    try {
      payload = JSON.parse(rawData);
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
  // 1. Determine Ops Date (Date - 1 day)
  var dateStr = data.date || Utilities.formatDate(new Date(), "GMT+7", "yyyy-MM-dd");
  var dt = new Date(dateStr);
  if (isNaN(dt.getTime())) {
    dt = new Date();
  }
  // Ops Date = Date - 1 day
  dt.setDate(dt.getDate() - 1);
  var opsDateFormatted = Utilities.formatDate(dt, "GMT+7", "yyyy-MM-dd");
  var fileName = "Dashboard Charts - " + opsDateFormatted;

  // 2. Get Target Drive Folder
  var folder;
  try {
    folder = DriveApp.getFolderById(TARGET_FOLDER_ID);
  } catch(fErr) {
    folder = DriveApp.getRootFolder();
  }

  // Check if file with same name already exists in folder, trash it or reuse
  var existingFiles = folder.getFilesByName(fileName);
  while (existingFiles.hasNext()) {
    var oldFile = existingFiles.next();
    oldFile.setTrashed(true);
  }

  // 3. Create New Spreadsheet
  var newSpreadsheet = SpreadsheetApp.create(fileName);
  var file = DriveApp.getFileById(newSpreadsheet.getId());
  file.moveTo(folder);

  var summary = data.summary || {};
  var rows = data.outboundRawRows || data.rows || [];

  // ==========================================
  // SHEET 1: Executive Summary & Hourly
  // ==========================================
  var sheet1 = newSpreadsheet.getActiveSheet();
  sheet1.setName("Executive Summary & Hourly");
  sheet1.setTabColor("#2563EB");
  sheet1.setShowGridLines(true);

  // Title Banner
  sheet1.getRange("A1:H1").merge().setValue("🚚 LH TRIP & OB LATE EXECUTIVE REPORT (" + fileName + ")")
    .setBackground("#0F172A").setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(14).setHorizontalAlignment("center");
  sheet1.getRange("A2:H2").merge().setValue("รอบบันทึกข้อมูล: " + (data.archivedAt || new Date().toLocaleString()) + " | Ops Date: " + opsDateFormatted)
    .setBackground("#1E293B").setFontColor("#94A3B8").setFontSize(10).setHorizontalAlignment("center");

  // KPI Section
  var totalTrips = summary.totalTrips || rows.length || 0;
  var onTimeTrips = summary.onTimeTrips || (totalTrips - (summary.lateTrips || 0));
  var lateTrips = summary.lateTrips || 0;
  var onTimeRate = summary.onTimeRate || (totalTrips ? ((onTimeTrips/totalTrips)*100).toFixed(1) : 0);
  var totalOrders = summary.totalOrders || 0;
  var lateOrders = summary.lateOrders || 0;
  var onTimeOrders = summary.onTimeOrders || (totalOrders - lateOrders);
  var obLateCount = summary.obLateCount || 0;
  var lhLateCount = summary.lhLateCount || 0;

  sheet1.getRange("A4:B4").merge().setValue("TOTAL TRIPS (เที่ยวรถ)").setBackground("#F8FAFC").setFontWeight("bold");
  sheet1.getRange("A5:B5").merge().setValue(totalTrips).setFontSize(16).setFontWeight("bold").setHorizontalAlignment("center");
  sheet1.getRange("A6:B6").merge().setValue(totalOrders.toLocaleString() + " Orders").setFontColor("#64748B").setHorizontalAlignment("center");

  sheet1.getRange("C4:D4").merge().setValue("ON TIME (ตรงเวลา)").setBackground("#DCFCE7").setFontColor("#15803D").setFontWeight("bold");
  sheet1.getRange("C5:D5").merge().setValue(onTimeTrips + " (" + onTimeRate + "%)").setFontSize(16).setFontColor("#15803D").setFontWeight("bold").setHorizontalAlignment("center");
  sheet1.getRange("C6:D6").merge().setValue(onTimeOrders.toLocaleString() + " Orders").setFontColor("#15803D").setHorizontalAlignment("center");

  sheet1.getRange("E4:F4").merge().setValue("LATE (ล่าช้าทั้งหมด)").setBackground("#FEE2E2").setFontColor("#B91C1C").setFontWeight("bold");
  sheet1.getRange("E5:F5").merge().setValue(lateTrips + " เที่ยว").setFontSize(16).setFontColor("#B91C1C").setFontWeight("bold").setHorizontalAlignment("center");
  sheet1.getRange("E6:F6").merge().setValue(lateOrders.toLocaleString() + " Orders").setFontColor("#B91C1C").setHorizontalAlignment("center");

  sheet1.getRange("G4:H4").merge().setValue("OB vs LH LATE").setBackground("#FEF3C7").setFontColor("#B45309").setFontWeight("bold");
  sheet1.getRange("G5:H5").merge().setValue("OB: " + obLateCount + " | LH: " + lhLateCount).setFontSize(14).setFontWeight("bold").setHorizontalAlignment("center");
  sheet1.getRange("G6:H6").merge().setValue("OB: " + (summary.obLateOrders || 0).toLocaleString() + " Ord | LH: " + (summary.lhLateOrders || 0).toLocaleString() + " Ord").setFontColor("#B45309").setHorizontalAlignment("center");

  sheet1.getRange("A4:H6").setBorder(true, true, true, true, true, true, "#CBD5E1", SpreadsheetApp.BorderStyle.SOLID);

  // Hourly Breakdown Table
  sheet1.getRange("A8:H8").merge().setValue("📊 HOURLY BREAKDOWN & VEHICLE TYPE STATS (สถิติรายชั่วโมง)")
    .setBackground("#2563EB").setFontColor("#FFFFFF").setFontWeight("bold");

  var hourlyHeaders = ["Time Range", "4W", "4WJ", "6W", "Semi trailer", "Other", "Total Trips", "Total Orders"];
  sheet1.getRange(9, 1, 1, 8).setValues([hourlyHeaders]).setBackground("#F1F5F9").setFontWeight("bold").setHorizontalAlignment("center");

  var hourlyData = [];
  for (var h = 0; h < 24; h++) {
    var startH = (h < 10 ? "0" : "") + h + ":00";
    var endH = ((h+1)%24 < 10 ? "0" : "") + ((h+1)%24) + ":00";
    var rangeStr = startH + " - " + endH;
    
    var c4W = 0, c4WJ = 0, c6W = 0, cSemi = 0, cOther = 0;
    var totTrips = 0, totOrders = 0;
    
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var dep = String(r.actual_dep_cut || (r.cells ? r.cells[21] : "") || "");
      var rH = parseHourString(dep);
      if (rH === h) {
        totTrips++;
        var ord = Number(r.outbound_order || (r.cells ? r.cells[30] : 0)) || 0;
        totOrders += ord;
        var v = String(r.vehicle_type || (r.cells ? r.cells[3] : "")).toLowerCase();
        if (v.indexOf("4wj") !== -1 || v.indexOf("จัมโบ้") !== -1) c4WJ++;
        else if (v.indexOf("4w") !== -1 || v.indexOf("4ล้อ") !== -1) c4W++;
        else if (v.indexOf("6w") !== -1 || v.indexOf("6ล้อ") !== -1) c6W++;
        else if (v.indexOf("semi") !== -1 || v.indexOf("พ่วง") !== -1 || v.indexOf("trailer") !== -1) cSemi++;
        else cOther++;
      }
    }
    hourlyData.push([rangeStr, c4W, c4WJ, c6W, cSemi, cOther, totTrips, totOrders]);
  }

  sheet1.getRange(10, 1, hourlyData.length, 8).setValues(hourlyData);
  sheet1.getRange(10, 2, hourlyData.length, 7).setHorizontalAlignment("right");
  sheet1.getRange(9, 1, hourlyData.length + 1, 8).setBorder(true, true, true, true, true, true, "#CBD5E1", SpreadsheetApp.BorderStyle.SOLID);

  // ==========================================
  // SHEET 2: Top 50 Hubs
  // ==========================================
  var sheet2 = newSpreadsheet.insertSheet("Top 50 Hubs");
  sheet2.setTabColor("#DC2626");
  sheet2.setShowGridLines(true);

  sheet2.getRange("A1:E1").merge().setValue("🏆 TOP 50 LH LATE HUBS").setBackground("#DC2626").setFontColor("#FFFFFF").setFontWeight("bold").setHorizontalAlignment("center");
  sheet2.getRange("G1:K1").merge().setValue("🏆 TOP 50 OB LATE HUBS").setBackground("#EA580C").setFontColor("#FFFFFF").setFontWeight("bold").setHorizontalAlignment("center");

  var hubHeaders = ["Rank", "Destination Hub", "Late Trips", "Late Orders", "% Late Share"];
  sheet2.getRange(2, 1, 1, 5).setValues([hubHeaders]).setBackground("#FEE2E2").setFontWeight("bold").setHorizontalAlignment("center");
  sheet2.getRange(2, 7, 1, 5).setValues([hubHeaders]).setBackground("#FFEDD5").setFontWeight("bold").setHorizontalAlignment("center");

  // Calculate Top Hubs
  var lhHubMap = {}, obHubMap = {};
  for (var k = 0; k < rows.length; k++) {
    var item = rows[k];
    var isLate = String(item.status || "").toLowerCase().indexOf("late") !== -1;
    if (!isLate) continue;
    var hub = item.dest_station_name || "Unknown";
    var rmk = String(item.rmk || "").toLowerCase();
    var ord = Number(item.outbound_order || 0) || 0;
    
    if (rmk.indexOf("lh late") !== -1) {
      if (!lhHubMap[hub]) lhHubMap[hub] = { count: 0, orders: 0 };
      lhHubMap[hub].count++;
      lhHubMap[hub].orders += ord;
    } else {
      if (!obHubMap[hub]) obHubMap[hub] = { count: 0, orders: 0 };
      obHubMap[hub].count++;
      obHubMap[hub].orders += ord;
    }
  }

  var lhHubList = Object.keys(lhHubMap).map(function(h) { return { hub: h, count: lhHubMap[h].count, orders: lhHubMap[h].orders }; })
    .sort(function(a, b) { return b.count - a.count || b.orders - a.orders; }).slice(0, 50);

  var obHubList = Object.keys(obHubMap).map(function(h) { return { hub: h, count: obHubMap[h].count, orders: obHubMap[h].orders }; })
    .sort(function(a, b) { return b.count - a.count || b.orders - a.orders; }).slice(0, 50);

  var lhRows = lhHubList.map(function(r, idx) {
    var pct = lateTrips ? ((r.count / lateTrips) * 100).toFixed(1) + "%" : "0%";
    return [idx + 1, r.hub, r.count, r.orders, pct];
  });
  if (lhRows.length > 0) {
    sheet2.getRange(3, 1, lhRows.length, 5).setValues(lhRows);
  }

  var obRows = obHubList.map(function(r, idx) {
    var pct = lateTrips ? ((r.count / lateTrips) * 100).toFixed(1) + "%" : "0%";
    return [idx + 1, r.hub, r.count, r.orders, pct];
  });
  if (obRows.length > 0) {
    sheet2.getRange(3, 7, obRows.length, 5).setValues(obRows);
  }

  // ==========================================
  // SHEET 3: Raw Data
  // ==========================================
  var sheet3 = newSpreadsheet.insertSheet("Raw Data");
  sheet3.setTabColor("#10B981");
  sheet3.setShowGridLines(true);

  var rawHeaders = [
    "No.", "LH Trip Number", "Trip Category", "Vehicle Type", "Vehicle Plate", "Driver",
    "Origin", "Destination", "Outbound Orders", "Outbound Weight (KG)", "Standby Time", "Assign Time",
    "Cut 0", "Cut 1", "Cut 2", "Cut 3", "Actual Dep Cut", "RMK", "Status"
  ];
  sheet3.getRange(1, 1, 1, rawHeaders.length).setValues([rawHeaders])
    .setBackground("#0F172A").setFontColor("#FFFFFF").setFontWeight("bold").setHorizontalAlignment("center");

  var rawTableData = [];
  for (var m = 0; m < rows.length; m++) {
    var tr = rows[m];
    var isLateTr = String(tr.status || "").toLowerCase().indexOf("late") !== -1;
    rawTableData.push([
      m + 1,
      tr.shipment_id || "",
      tr.trip_category || "",
      tr.vehicle_type || "",
      tr.vehicle_plate || "",
      tr.driver || "",
      tr.origin || "SOCN",
      tr.dest_station_name || "",
      Number(tr.outbound_order || 0),
      Number(tr.outbound_weight || 0),
      tr.standby_time || "",
      tr.assign_time || "",
      tr.cut0 || "",
      tr.cut1 || "",
      tr.cut2 || "",
      tr.cut3 || "",
      tr.actual_dep_cut || "",
      tr.rmk || "",
      isLateTr ? "Late" : "On time"
    ]);
  }

  if (rawTableData.length > 0) {
    // Write in chunks of 2000 to prevent timeout
    var chunkSize = 2000;
    for (var c = 0; c < rawTableData.length; c += chunkSize) {
      var slice = rawTableData.slice(c, c + chunkSize);
      sheet3.getRange(c + 2, 1, slice.length, rawHeaders.length).setValues(slice);
    }
  }

  return {
    success: true,
    message: "บันทึกไฟล์ " + fileName + " เข้าโฟลเดอร์ Google Drive เรียบร้อยแล้ว!",
    fileName: fileName,
    fileId: newSpreadsheet.getId(),
    fileUrl: newSpreadsheet.getUrl(),
    folderId: TARGET_FOLDER_ID,
    folderUrl: folder.getUrl(),
    totalTrips: totalTrips,
    totalOrders: totalOrders,
    opsDate: opsDateFormatted
  };
}

function parseHourString(s) {
  if (!s) return null;
  var str = String(s).trim();
  var match = str.match(/(\d{1,2})[:.](\d{2})/);
  if (match) {
    var h = parseInt(match[1], 10);
    if (!isNaN(h) && h >= 0 && h <= 23) return h;
  }
  return null;
}
