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
  var dateStr = data.date || Utilities.formatDate(new Date(), "GMT+7", "yyyy-MM-dd");
  var dt = new Date(dateStr);
  if (isNaN(dt.getTime())) dt = new Date();
  dt.setDate(dt.getDate() - 1);
  var opsDateFormatted = Utilities.formatDate(dt, "GMT+7", "yyyy-MM-dd");
  var fileName = "Dashboard Charts - " + opsDateFormatted;

  // 1. Target Folder
  var folder;
  try {
    folder = DriveApp.getFolderById(TARGET_FOLDER_ID);
  } catch(fErr) {
    folder = DriveApp.getRootFolder();
  }

  // Remove existing file with same name if any
  try {
    var existingFiles = folder.getFilesByName(fileName);
    while (existingFiles.hasNext()) {
      existingFiles.next().setTrashed(true);
    }
  } catch(e) {}

  // 2. Create Spreadsheet in Folder directly
  var newSpreadsheet = SpreadsheetApp.create(fileName);
  try {
    var file = DriveApp.getFileById(newSpreadsheet.getId());
    file.moveTo(folder);
  } catch(e) {}

  var summary = data.summary || {};
  var rows = data.outboundRawRows || data.rows || [];

  // ==========================================
  // SHEET 1: Executive Summary & Hourly
  // ==========================================
  var sheet1 = newSpreadsheet.getActiveSheet();
  sheet1.setName("Executive Summary & Hourly");
  sheet1.setTabColor("#2563EB");

  var totalTrips = summary.totalTrips || rows.length || 0;
  var onTimeTrips = summary.onTimeTrips || (totalTrips - (summary.lateTrips || 0));
  var lateTrips = summary.lateTrips || 0;
  var onTimeRate = summary.onTimeRate || (totalTrips ? ((onTimeTrips/totalTrips)*100).toFixed(1) : 0);
  var totalOrders = summary.totalOrders || 0;
  var lateOrders = summary.lateOrders || 0;
  var onTimeOrders = summary.onTimeOrders || (totalOrders - lateOrders);
  var obLateCount = summary.obLateCount || 0;
  var lhLateCount = summary.lhLateCount || 0;

  var s1Data = [
    ["🚚 LH TRIP & OB LATE EXECUTIVE REPORT (" + fileName + ")", "", "", "", "", "", "", ""],
    ["รอบบันทึกข้อมูล: " + (data.archivedAt || new Date().toLocaleString()) + " | Ops Date: " + opsDateFormatted, "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", ""],
    ["TOTAL TRIPS", "ON TIME", "LATE (ทั้งหมด)", "OB vs LH LATE", "TOTAL ORDERS", "ON TIME ORDERS", "LATE ORDERS", "ON-TIME RATE %"],
    [totalTrips, onTimeTrips, lateTrips, "OB: " + obLateCount + " | LH: " + lhLateCount, totalOrders, onTimeOrders, lateOrders, onTimeRate + "%"],
    ["", "", "", "", "", "", "", ""],
    ["📊 HOURLY BREAKDOWN (สถิติรายชั่วโมง)", "", "", "", "", "", "", ""],
    ["Time Range", "4W", "4WJ", "6W", "Semi trailer", "Other", "Total Trips", "Total Orders"]
  ];

  // Fast Hourly aggregation
  var hourlyBuckets = [];
  for (var h = 0; h < 24; h++) {
    hourlyBuckets.push({ c4W: 0, c4WJ: 0, c6W: 0, cSemi: 0, cOther: 0, trips: 0, orders: 0 });
  }

  var lhHubMap = {}, obHubMap = {};
  var rawTableData = [];

  if (data.compactRawRows && data.compactRawRows.length > 0) {
    rawTableData = data.compactRawRows;
    for (var i = 0; i < rawTableData.length; i++) {
      var cr = rawTableData[i];
      var dest = cr[7] || "Unknown";
      var ord = Number(cr[8]) || 0;
      var vStr = String(cr[3] || "").toLowerCase();
      var dep = String(cr[16] || "");
      var rmk = String(cr[17] || "");
      var isLate = String(cr[18] || "").toLowerCase().indexOf("late") !== -1;

      var match = dep.match(/(\d{1,2})[:.](\d{2})/);
      if (match) {
        var rH = parseInt(match[1], 10);
        if (rH >= 0 && rH < 24) {
          var b = hourlyBuckets[rH];
          b.trips++;
          b.orders += ord;
          if (vStr.indexOf("4wj") !== -1 || vStr.indexOf("จัมโบ้") !== -1) b.c4WJ++;
          else if (vStr.indexOf("4w") !== -1 || vStr.indexOf("4ล้อ") !== -1) b.c4W++;
          else if (vStr.indexOf("6w") !== -1 || vStr.indexOf("6ล้อ") !== -1) b.c6W++;
          else if (vStr.indexOf("semi") !== -1 || vStr.indexOf("พ่วง") !== -1 || vStr.indexOf("trailer") !== -1) b.cSemi++;
          else b.cOther++;
        }
      }

      if (isLate) {
        if (rmk.toLowerCase().indexOf("lh late") !== -1) {
          if (!lhHubMap[dest]) lhHubMap[dest] = { count: 0, orders: 0 };
          lhHubMap[dest].count++; lhHubMap[dest].orders += ord;
        } else {
          if (!obHubMap[dest]) obHubMap[dest] = { count: 0, orders: 0 };
          obHubMap[dest].count++; obHubMap[dest].orders += ord;
        }
      }
    }
  } else {
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var isLateTr = String(r.status || "").toLowerCase().indexOf("late") !== -1;
      var ord = Number(r.outbound_order || (r.cells ? r.cells[30] : 0)) || 0;
      var wt = Number(r.outbound_weight || (r.cells ? r.cells[31] : 0)) || 0;
      var dep = String(r.actual_dep_cut || (r.cells ? r.cells[21] : "") || "");
      var hub = r.dest_station_name || "Unknown";
      var rmk = String(r.rmk || "");
      var rmkLower = rmk.toLowerCase();

      // Hourly
      var match = dep.match(/(\d{1,2})[:.](\d{2})/);
      if (match) {
        var rH = parseInt(match[1], 10);
        if (rH >= 0 && rH < 24) {
          var b = hourlyBuckets[rH];
          b.trips++;
          b.orders += ord;
          var v = String(r.vehicle_type || "").toLowerCase();
          if (v.indexOf("4wj") !== -1 || v.indexOf("จัมโบ้") !== -1) b.c4WJ++;
          else if (v.indexOf("4w") !== -1 || v.indexOf("4ล้อ") !== -1) b.c4W++;
          else if (v.indexOf("6w") !== -1 || v.indexOf("6ล้อ") !== -1) b.c6W++;
          else if (v.indexOf("semi") !== -1 || v.indexOf("พ่วง") !== -1 || v.indexOf("trailer") !== -1) b.cSemi++;
          else b.cOther++;
        }
      }

      // Top Hubs
      if (isLateTr) {
        if (rmkLower.indexOf("lh late") !== -1) {
          if (!lhHubMap[hub]) lhHubMap[hub] = { count: 0, orders: 0 };
          lhHubMap[hub].count++; lhHubMap[hub].orders += ord;
        } else {
          if (!obHubMap[hub]) obHubMap[hub] = { count: 0, orders: 0 };
          obHubMap[hub].count++; obHubMap[hub].orders += ord;
        }
      }

      // Raw Row
      rawTableData.push([
        i + 1, r.shipment_id || "", r.trip_category || "", r.vehicle_type || "", r.vehicle_plate || "", r.driver || "",
        r.origin || "SOCN", hub, ord, wt, r.standby_time || "", r.assign_time || "",
        r.cut0 || "", r.cut1 || "", r.cut2 || "", r.cut3 || "", dep, rmk, isLateTr ? "Late" : "On time"
      ]);
    }
  }

  for (var hour = 0; hour < 24; hour++) {
    var sH = (hour < 10 ? "0" : "") + hour + ":00";
    var eH = ((hour+1)%24 < 10 ? "0" : "") + ((hour+1)%24) + ":00";
    var bk = hourlyBuckets[hour];
    s1Data.push([sH + " - " + eH, bk.c4W, bk.c4WJ, bk.c6W, bk.cSemi, bk.cOther, bk.trips, bk.orders]);
  }

  sheet1.getRange(1, 1, s1Data.length, 8).setValues(s1Data);
  sheet1.getRange("A1:H1").merge().setBackground("#0F172A").setFontColor("#FFFFFF").setFontWeight("bold").setFontSize(14).setHorizontalAlignment("center");
  sheet1.getRange("A2:H2").merge().setBackground("#1E293B").setFontColor("#94A3B8").setFontSize(10).setHorizontalAlignment("center");
  sheet1.getRange("A4:H4").setBackground("#F1F5F9").setFontWeight("bold").setHorizontalAlignment("center");
  sheet1.getRange("A5:H5").setFontSize(12).setFontWeight("bold").setHorizontalAlignment("center");
  sheet1.getRange("A7:H7").merge().setBackground("#2563EB").setFontColor("#FFFFFF").setFontWeight("bold");
  sheet1.getRange("A8:H8").setBackground("#F1F5F9").setFontWeight("bold").setHorizontalAlignment("center");

  // ==========================================
  // SHEET 2: Top 50 Hubs
  // ==========================================
  var sheet2 = newSpreadsheet.insertSheet("Top 50 Hubs");
  sheet2.setTabColor("#DC2626");

  var lhHubList = Object.keys(lhHubMap).map(function(h) { return { hub: h, count: lhHubMap[h].count, orders: lhHubMap[h].orders }; })
    .sort(function(a, b) { return b.count - a.count || b.orders - a.orders; }).slice(0, 50);
  var obHubList = Object.keys(obHubMap).map(function(h) { return { hub: h, count: obHubMap[h].count, orders: obHubMap[h].orders }; })
    .sort(function(a, b) { return b.count - a.count || b.orders - a.orders; }).slice(0, 50);

  var s2Data = [
    ["🏆 TOP 50 LH LATE HUBS", "", "", "", "", "", "🏆 TOP 50 OB LATE HUBS", "", "", "", ""],
    ["Rank", "Destination Hub", "Late Trips", "Late Orders", "% Late Share", "", "Rank", "Destination Hub", "Late Trips", "Late Orders", "% Late Share"]
  ];

  var maxRows = Math.max(lhHubList.length, obHubList.length, 1);
  for (var rIdx = 0; rIdx < maxRows; rIdx++) {
    var lhItem = lhHubList[rIdx] || { hub: "", count: "", orders: "" };
    var obItem = obHubList[rIdx] || { hub: "", count: "", orders: "" };
    var lhPct = (lhItem.count && lateTrips) ? ((lhItem.count / lateTrips) * 100).toFixed(1) + "%" : "";
    var obPct = (obItem.count && lateTrips) ? ((obItem.count / lateTrips) * 100).toFixed(1) + "%" : "";
    s2Data.push([
      lhItem.hub ? (rIdx + 1) : "", lhItem.hub, lhItem.count, lhItem.orders, lhPct,
      "",
      obItem.hub ? (rIdx + 1) : "", obItem.hub, obItem.count, obItem.orders, obPct
    ]);
  }

  sheet2.getRange(1, 1, s2Data.length, 11).setValues(s2Data);
  sheet2.getRange("A1:E1").merge().setBackground("#DC2626").setFontColor("#FFFFFF").setFontWeight("bold").setHorizontalAlignment("center");
  sheet2.getRange("G1:K1").merge().setBackground("#EA580C").setFontColor("#FFFFFF").setFontWeight("bold").setHorizontalAlignment("center");
  sheet2.getRange("A2:E2").setBackground("#FEE2E2").setFontWeight("bold").setHorizontalAlignment("center");
  sheet2.getRange("G2:K2").setBackground("#FFEDD5").setFontWeight("bold").setHorizontalAlignment("center");

  // ==========================================
  // SHEET 3: Raw Data (Bulk write in 1 call)
  // ==========================================
  var sheet3 = newSpreadsheet.insertSheet("Raw Data");
  sheet3.setTabColor("#10B981");

  var rawHeaders = [
    "No.", "LH Trip Number", "Trip Category", "Vehicle Type", "Vehicle Plate", "Driver",
    "Origin", "Destination", "Outbound Orders", "Outbound Weight (KG)", "Standby Time", "Assign Time",
    "Cut 0", "Cut 1", "Cut 2", "Cut 3", "Actual Dep Cut", "RMK", "Status"
  ];

  sheet3.getRange(1, 1, 1, rawHeaders.length).setValues([rawHeaders])
    .setBackground("#0F172A").setFontColor("#FFFFFF").setFontWeight("bold").setHorizontalAlignment("center");

  if (rawTableData.length > 0) {
    sheet3.getRange(2, 1, rawTableData.length, rawHeaders.length).setValues(rawTableData);
  }

  SpreadsheetApp.flush();

  return {
    success: true,
    message: "บันทึกไฟล์ " + fileName + " เข้าโฟลเดอร์ Google Drive เรียบร้อยแล้ว!",
    fileName: fileName,
    fileId: newSpreadsheet.getId(),
    fileUrl: newSpreadsheet.getUrl(),
    folderId: TARGET_FOLDER_ID,
    folderUrl: folder.getUrl(),
    opsDate: opsDateFormatted
  };
}
