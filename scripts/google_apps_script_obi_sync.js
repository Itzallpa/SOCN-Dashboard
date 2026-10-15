/**
 * =========================================================================================
 * 🚀 SOCN · OBI Performance Monitor — Column B (RAW_Productivity by Min) Sync (Values Only & Fast)
 * =========================================================================================
 * 
 * ⚡ Data Pipeline:
 * 1. เปิด Master Sheet ("09_2026_OBI_Daily Operate Report" / แท็บ "หน้า link")
 * 2. ค้นหาแถวตามวันที่ (Day-1 หรือวันที่ที่เลือก) ใน Column A (วันที่)
 * 3. ดึงลิงก์จาก Column B (RAW_Productivity by Min)
 * 4. คัดลอกเฉพาะค่า Text / Values ล้วน (ไม่เอาสูตร เพื่อความรวดเร็วสูงสุดและไม่หน่วงเครื่อง)
 *    (พร้อมโครงสร้างการจัดหน้า สี ฟอนต์ เส้นตาราง และความกว้างคอลัมน์)
 * 5. ส่งต่อไปยัง External Destination Sheet (ถ้ามี) แบบ Values Only
 * 6. ⏰ ทุก 1 ชั่วโมง: อัปเดตข้อมูล Text/Values ลงในชีตอัตโนมัติ
 * 7. ⏰ เวลา 15:00 น.: ดึงข้อมูล + บันทึกสร้างไฟล์สำรอง (Save Backup) ลง Google Drive Folder อัตโนมัติ
 * =========================================================================================
 */

const SYNC_CONFIG = {
  // 🔗 1. Master Sheet ต้นทาง (09_2026_OBI_Daily Operate Report)
  MASTER_SPREADSHEET_ID: "1JAMosfZfMOepZy3Vhfr-TKTj2zSY9QqnrwE3SDeNQjg",
  INDEX_SHEET_NAME: "หน้า link",

  // 📤 2. External Destination Sheet (ชีตปลายทาง)
  EXTERNAL_SPREADSHEET_ID: "1g0IHBi77Da6rUnWHfyzH4KJwzK2Ks8wJz4Agg5-eUI8",

  // 📁 3. Google Drive Backup Folder
  DRIVE_BACKUP_FOLDER_ID: "1Px3K3Iui2jZoPB_8-XIFXllRifij290i",

  // 🎯 คอลัมน์เป้าหมายในตาราง Master Index (1-indexed)
  COLUMNS: {
    DATE: 1,                 // Column A: วันที่ (Date)
    PROD_MIN_URL: 2,         // Column B: RAW_Productivity by Min (เป้าหมายหลัก)
    PROD_MIN_CHECK: 3        // Column C: Check
  }
};

/**
 * 🔘 เมนูบนแถบเครื่องมือ Google Sheets
 */
function onOpen() {
  SpreadsheetApp.getUi().createMenu("🚀 OBI Control")
    .addItem("⚡ 1. ดึงข้อมูล Column B (Day - 1 อัตโนมัติ + ติด Format)", "menuSyncYesterday")
    .addItem("📅 2. เลือกวันที่ต้องการดึงข้อมูลเอง...", "menuSyncCustomDate")
    .addItem("💾 3. บันทึก Backup ลง Google Drive ทันที", "menuManualBackupDrive")
    .addSeparator()
    .addItem("⏰ 4. ติดตั้ง Trigger อัตโนมัติ (Update ทุก 1 ชม. + 15:00 น. Save Drive)", "setupCompleteAutomationTriggers")
    .addItem("🛑 5. ยกเลิก Trigger อัตโนมัติทั้งหมด", "removeAllTriggers")
    .addToUi();
}

/**
 * 🔘 ปุ่มลัดบนหน้าชีต
 */
function btnClickSyncNow() {
  menuSyncYesterday();
}

/**
 * 🎯 แกะ Spreadsheet ID จาก URL
 */
function extractSpreadsheetId(url) {
  if (!url || typeof url !== 'string') return null;
  const match = url.match(/\/d\/([a-zA-Z0-9-_]+)/);
  return match ? match[1] : null;
}

/**
 * 📅 แปลงค่าวันที่ในเซลล์ให้เป็น Date Object
 */
function parseCellDate(cellValue) {
  if (!cellValue) return null;
  if (cellValue instanceof Date && !isNaN(cellValue.getTime())) {
    return cellValue;
  }
  
  const str = String(cellValue).trim();
  
  // Format: "Sep/26/2026" หรือ "Sep/26/26"
  const mmmDdYyyy = str.match(/^([a-zA-Z]+)\/(\d{1,2})\/(\d{2,4})$/);
  if (mmmDdYyyy) {
    const monthNames = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
    const mIdx = monthNames.indexOf(mmmDdYyyy[1].toLowerCase());
    if (mIdx !== -1) {
      let year = parseInt(mmmDdYyyy[3], 10);
      if (year < 100) year += 2000;
      return new Date(year, mIdx, parseInt(mmmDdYyyy[2], 10));
    }
  }

  // Format: "YYYY-MM-DD" หรือ "DD/MM/YYYY"
  const parsed = new Date(str);
  if (!isNaN(parsed.getTime())) {
    return parsed;
  }

  return null;
}

/**
 * 📅 ตรวจสอบว่าเป็นวันเดียวกันหรือไม่
 */
function isSameDate(d1, d2) {
  if (!d1 || !d2) return false;
  const s1 = Utilities.formatDate(d1, "Asia/Bangkok", "yyyy-MM-dd");
  const s2 = Utilities.formatDate(d2, "Asia/Bangkok", "yyyy-MM-dd");
  return s1 === s2;
}

/**
 * 🔍 ค้นหา Link ใน Column B จาก Master Index ตามวันที่
 */
function getColumnBLinkForDate(targetDate) {
  const masterSS = SpreadsheetApp.openById(SYNC_CONFIG.MASTER_SPREADSHEET_ID);
  let indexSheet = masterSS.getSheetByName(SYNC_CONFIG.INDEX_SHEET_NAME);
  
  if (!indexSheet) {
    indexSheet = masterSS.getSheets()[0];
  }

  const lastRow = indexSheet.getLastRow();
  const lastCol = Math.max(indexSheet.getLastColumn(), 10);
  if (lastRow < 2) {
    throw new Error(`ชีต Master Index (${SYNC_CONFIG.INDEX_SHEET_NAME}) ไม่มีข้อมูล`);
  }

  const values = indexSheet.getRange(1, 1, lastRow, lastCol).getValues();
  const targetFormatted = Utilities.formatDate(targetDate, "Asia/Bangkok", "yyyy-MM-dd (MMM/dd/yyyy)");

  Logger.log(`Searching Master Index for date: ${targetFormatted} in Column A...`);

  for (let r = 0; r < values.length; r++) {
    const rawDate = values[r][SYNC_CONFIG.COLUMNS.DATE - 1];
    const cellDate = parseCellDate(rawDate);

    if (cellDate && isSameDate(cellDate, targetDate)) {
      const prodMinUrl = String(values[r][SYNC_CONFIG.COLUMNS.PROD_MIN_URL - 1] || "").trim();
      const checkStatus = String(values[r][SYNC_CONFIG.COLUMNS.PROD_MIN_CHECK - 1] || "").trim();
      const rowDateDisplay = Utilities.formatDate(cellDate, "Asia/Bangkok", "yyyy-MM-dd");

      Logger.log(`Found row ${r + 1}: Date=${rowDateDisplay}, Col B URL=${prodMinUrl}, Check=${checkStatus}`);

      if (!prodMinUrl) {
        throw new Error(`พบแถววันที่ ${rowDateDisplay} (แถวที่ ${r + 1}) แต่ใน Column B ไม่มี Link`);
      }

      return {
        rowIndex: r + 1,
        date: cellDate,
        dateDisplay: rowDateDisplay,
        sheetUrl: prodMinUrl,
        spreadsheetId: extractSpreadsheetId(prodMinUrl),
        checkStatus: checkStatus
      };
    }
  }

  throw new Error(`ไม่พบข้อมูลวันที่ ${targetFormatted} ใน Master Index (Column A)`);
}

/**
 * 🛡️ คัดลอกข้อมูลและจัด Format ทุกอย่างผ่าน Range (ป้องกัน 'This operation is not supported' 100%)
 */
function copyRangeWithFullFormatting(sourceSheet, targetSheet) {
  const lastRow = sourceSheet.getLastRow();
  const lastCol = sourceSheet.getLastColumn();
  if (lastRow === 0 || lastCol === 0) return;

  targetSheet.clear();

  const sourceRange = sourceSheet.getRange(1, 1, lastRow, lastCol);
  const targetRange = targetSheet.getRange(1, 1, lastRow, lastCol);

  // 1. คัดลอกเฉพาะค่า Text / Values เท่านั้น (ไม่เอาสูตร เพื่อความเร็วสูงสุดและไม่หน่วงเครื่อง)
  targetRange.setValues(sourceRange.getValues());

  // 2. คัดลอกการจัดแต่งสไตล์ (Styles & Colors)
  try { targetRange.setBackgrounds(sourceRange.getBackgrounds()); } catch(e){}
  try { targetRange.setFontColors(sourceRange.getFontColors()); } catch(e){}
  try { targetRange.setFontWeights(sourceRange.getFontWeights()); } catch(e){}
  try { targetRange.setFontSizes(sourceRange.getFontSizes()); } catch(e){}
  try { targetRange.setFontFamilies(sourceRange.getFontFamilies()); } catch(e){}
  try { targetRange.setHorizontalAlignments(sourceRange.getHorizontalAlignments()); } catch(e){}
  try { targetRange.setVerticalAlignments(sourceRange.getVerticalAlignments()); } catch(e){}
  try { targetRange.setNumberFormats(sourceRange.getNumberFormats()); } catch(e){}
  try { targetRange.setWrapStrategies(sourceRange.getWrapStrategies()); } catch(e){}

  // 3. ปรับขนาดความกว้างคอลัมน์ (Column Widths)
  const maxColToResize = Math.min(lastCol, 50);
  for (let col = 1; col <= maxColToResize; col++) {
    try {
      const w = sourceSheet.getColumnWidth(col);
      if (w > 0) targetSheet.setColumnWidth(col, w);
    } catch(e){}
  }

  // 4. คัดลอก Merged Cells (การรวมเซลล์)
  try {
    const mergedRanges = sourceRange.getMergedRanges();
    for (let m = 0; m < mergedRanges.length; m++) {
      const mr = mergedRanges[m];
      targetSheet.getRange(mr.getRow(), mr.getColumn(), mr.getNumRows(), mr.getNumColumns()).merge();
    }
  } catch(e){}
}

/**
 * 🎨 คัดลอกแท็บพร้อม Format และแปลงข้อมูลเป็น Text/Values ล้วน (ไม่ติดสูตร เพื่อความเร็ว)
 */
function cloneSheetWithFormat(sourceSheet, destSpreadsheet, targetTabName) {
  try {
    // วิธีที่ 1: ลอง copyTo ก่อน แล้วแปลงสูตรทั้งหมดให้เป็น Text/Values ทันที
    const copiedSheet = sourceSheet.copyTo(destSpreadsheet);
    
    // ล้างสูตรทั้งหมดออกให้เหลือเฉพาะค่า Text / Value เพื่อความเร็วสูงและไม่ติดสูตรภายนอก
    const dataRange = copiedSheet.getDataRange();
    if (dataRange.getLastRow() > 0 && dataRange.getLastColumn() > 0) {
      dataRange.setValues(dataRange.getValues());
    }
    
    const existingSheet = destSpreadsheet.getSheetByName(targetTabName);
    if (existingSheet && existingSheet.getSheetId() !== copiedSheet.getSheetId()) {
      destSpreadsheet.deleteSheet(existingSheet);
    }

    copiedSheet.setName(targetTabName);
    copiedSheet.showSheet();
    return copiedSheet;
  } catch (err) {
    Logger.log(`Notice: copyTo failed (${err.message}), falling back to safe Range-based clone.`);
    
    // วิธีที่ 2 (Fallback): คัดลอกผ่าน Range-based (Values Only + Styles)
    let targetSheet = destSpreadsheet.getSheetByName(targetTabName);
    if (!targetSheet) {
      targetSheet = destSpreadsheet.insertSheet(targetTabName);
    }
    
    copyRangeWithFullFormatting(sourceSheet, targetSheet);
    targetSheet.showSheet();
    return targetSheet;
  }
}

/**
 * 🚀 ฟังก์ชันหลัก: ดึงข้อมูลจาก Column B พร้อม Format 1:1 และอัปเดตลงชีต
 */
function runMasterSyncProcess(targetDate = null, isSilent = false) {
  const startTime = new Date().getTime();

  if (!targetDate) {
    targetDate = new Date();
    targetDate.setDate(targetDate.getDate() - 1);
  }

  const targetDateStr = Utilities.formatDate(targetDate, "Asia/Bangkok", "yyyy-MM-dd");
  Logger.log(`=== Starting Column B Sync (With 100% Formats) for Date: ${targetDateStr} ===`);

  // 1. ค้นหา Link จาก Column B ตามวันที่
  const sourceInfo = getColumnBLinkForDate(targetDate);
  const currentSS = SpreadsheetApp.getActiveSpreadsheet();

  // 2. เปิด Spreadsheet ต้นทางของ Column B
  Logger.log(`Opening Column B Source Sheet ID: ${sourceInfo.spreadsheetId}`);
  const sourceSS = SpreadsheetApp.openById(sourceInfo.spreadsheetId);
  const sourceSheets = sourceSS.getSheets();

  if (!sourceSheets || sourceSheets.length === 0) {
    throw new Error(`ไม่พบแท็บข้อมูลในไฟล์ Column B (ID: ${sourceInfo.spreadsheetId})`);
  }

  const syncedTabs = [];
  const createdSheetIds = [];

  // 3. คัดลอกทุกแท็บพร้อม Format ทั้งหมดมาลงชีตปัจจุบัน
  for (let s = 0; s < sourceSheets.length; s++) {
    const sSheet = sourceSheets[s];
    const originalTabName = sSheet.getName();
    
    const newSheet = cloneSheetWithFormat(sSheet, currentSS, originalTabName);
    createdSheetIds.push(newSheet.getSheetId());
    syncedTabs.push(`${originalTabName} (${sSheet.getLastRow()} แถว)`);
    Logger.log(`✅ Cloned tab with exact format: ${originalTabName}`);
  }

  // 4. ลบแท็บเก่าหรือ Sheet1 ที่ไม่ได้อยู่ในรายการที่ซิงก์
  const allCurrentSheets = currentSS.getSheets();
  for (let i = 0; i < allCurrentSheets.length; i++) {
    const sh = allCurrentSheets[i];
    if (!createdSheetIds.includes(sh.getSheetId()) && allCurrentSheets.length > createdSheetIds.length) {
      try {
        currentSS.deleteSheet(sh);
      } catch (e) {
        Logger.log(`Notice: Could not delete leftover sheet ${sh.getName()}: ${e.message}`);
      }
    }
  }

  // 5. ส่งต่อไปยัง External Sheet พร้อม Format (ถ้ามีการตั้งค่าไว้)
  if (SYNC_CONFIG.EXTERNAL_SPREADSHEET_ID) {
    try {
      const extSS = SpreadsheetApp.openById(SYNC_CONFIG.EXTERNAL_SPREADSHEET_ID);
      const extCreatedIds = [];

      for (let s = 0; s < sourceSheets.length; s++) {
        const sSheet = sourceSheets[s];
        const newExtSheet = cloneSheetWithFormat(sSheet, extSS, sSheet.getName());
        extCreatedIds.push(newExtSheet.getSheetId());
      }

      const allExtSheets = extSS.getSheets();
      for (let i = 0; i < allExtSheets.length; i++) {
        const eSh = allExtSheets[i];
        if (!extCreatedIds.includes(eSh.getSheetId()) && allExtSheets.length > extCreatedIds.length) {
          try { extSS.deleteSheet(eSh); } catch(e){}
        }
      }
      Logger.log("✅ Synced all tabs with format to External Sheet.");
    } catch (extErr) {
      Logger.log(`Notice: External sheet sync warning: ${extErr.message}`);
    }
  }

  const elapsed = ((new Date().getTime() - startTime) / 1000).toFixed(2);
  Logger.log(`🎉 Sync completed with full formatting for ${targetDateStr} in ${elapsed}s.`);

  return {
    targetDateStr,
    sourceInfo,
    syncedTabs,
    elapsed
  };
}

/**
 * ⚡ เมนู: ดึงข้อมูล Day - 1 (เมื่อวาน) จาก Column B พร้อม Format
 */
function menuSyncYesterday() {
  const ui = SpreadsheetApp.getUi();
  try {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const result = runMasterSyncProcess(yesterday, false);

    ui.alert(
      "✅ ดึงข้อมูล Column B สำเร็จ (พร้อม Format 100%)!",
      `📅 วันที่: ${result.targetDateStr} (Day - 1)\n` +
      `⏱️ ใช้เวลา: ${result.elapsed} วินาที\n` +
      `📋 สถานะ Check: ${result.sourceInfo.checkStatus || 'Ready'}\n\n` +
      `🎨 Tabs ที่ดึงพร้อมรูปแบบ:\n- ` + result.syncedTabs.join("\n- "),
      ui.ButtonSet.OK
    );
  } catch (err) {
    ui.alert("❌ เกิดข้อผิดพลาด", err.message, ui.ButtonSet.OK);
  }
}

/**
 * 📅 เมนู: ระบุวันที่ต้องการดึงข้อมูลเอง พร้อม Format
 */
function menuSyncCustomDate() {
  const ui = SpreadsheetApp.getUi();
  const defaultDate = Utilities.formatDate(new Date(), "Asia/Bangkok", "yyyy-MM-dd");
  
  const response = ui.prompt(
    "📅 ระบุวันที่ต้องการดึงข้อมูลจาก Column B (พร้อม Format)",
    `กรุณากรอกวันที่ในรูปแบบ YYYY-MM-DD หรือ Sep/DD/YYYY (เช่น ${defaultDate} หรือ Sep/26/2026):`,
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() !== ui.Button.OK) return;

  const inputStr = response.getResponseText().trim();
  if (!inputStr) {
    ui.alert("กรุณากรอกวันที่");
    return;
  }

  const targetDate = parseCellDate(inputStr);
  if (!targetDate) {
    ui.alert("❌ รูปแบบวันที่ไม่ถูกต้อง กรุณากรอกเช่น 2026-09-26 หรือ Sep/26/2026");
    return;
  }

  try {
    const result = runMasterSyncProcess(targetDate, false);
    ui.alert(
      "✅ ดึงข้อมูล Column B สำเร็จ (พร้อม Format 100%)!",
      `📅 ข้อมูลวันที่: ${result.targetDateStr}\n` +
      `⏱️ ใช้เวลา: ${result.elapsed} วินาที\n` +
      `📋 สถานะ Check: ${result.sourceInfo.checkStatus || 'Ready'}\n\n` +
      `🎨 Tabs ที่ดึงพร้อมรูปแบบ:\n- ` + result.syncedTabs.join("\n- "),
      ui.ButtonSet.OK
    );
  } catch (err) {
    ui.alert("❌ เกิดข้อผิดพลาด", err.message, ui.ButtonSet.OK);
  }
}

/**
 * 💾 บันทึก Backup พร้อม Format ครบถ้วนลง Google Drive Folder
 */
function saveDailyBackupToDriveFolder(sourceSpreadsheetId, dateStr) {
  if (!SYNC_CONFIG.DRIVE_BACKUP_FOLDER_ID) return null;

  const fileName = `OBI Daily (${dateStr})`;
  const folder = DriveApp.getFolderById(SYNC_CONFIG.DRIVE_BACKUP_FOLDER_ID);

  const existingFiles = folder.getFilesByName(fileName);
  let backupSS;

  if (existingFiles.hasNext()) {
    const file = existingFiles.next();
    backupSS = SpreadsheetApp.openById(file.getId());
  } else {
    backupSS = SpreadsheetApp.create(fileName);
    const createdFile = DriveApp.getFileById(backupSS.getId());
    folder.addFile(createdFile);
    DriveApp.getRootFolder().removeFile(createdFile);
  }

  const sourceSS = SpreadsheetApp.openById(sourceSpreadsheetId);
  const sSheets = sourceSS.getSheets();
  const createdIds = [];

  for (let i = 0; i < sSheets.length; i++) {
    const newSh = cloneSheetWithFormat(sSheets[i], backupSS, sSheets[i].getName());
    createdIds.push(newSh.getSheetId());
  }

  const allBackupSheets = backupSS.getSheets();
  for (let i = 0; i < allBackupSheets.length; i++) {
    const bSh = allBackupSheets[i];
    if (!createdIds.includes(bSh.getSheetId()) && allBackupSheets.length > createdIds.length) {
      try { backupSS.deleteSheet(bSh); } catch(e){}
    }
  }

  return { fileName, fileUrl: backupSS.getUrl() };
}

/**
 * ⏰ Trigger 1: ทำงานทุก 1 ชั่วโมง (Sync & Update ข้อมูล + Format ในชีต)
 */
function hourlyScheduledSync() {
  Logger.log("⏰ Starting hourly Column B Auto-Sync (Updating sheets with format)...");
  try {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const syncResult = runMasterSyncProcess(yesterday, true);
    Logger.log(`✅ Hourly Auto-Sync finished: ${syncResult.targetDateStr} (${syncResult.elapsed}s)`);
  } catch (err) {
    Logger.log(`❌ Error in hourly Auto-Sync: ${err.message}`);
  }
}

/**
 * ⏰ Trigger 2: ทำงานเวลา 15:00 น. ทุกวัน (Sync ข้อมูล + Save Backup ลง Google Drive Folder)
 */
function dailyScheduledBackup1500() {
  Logger.log("⏰ Starting daily 15:00 Column B Sync & Drive Backup (Save to Folder)...");
  try {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const syncResult = runMasterSyncProcess(yesterday, true);
    
    const backupResult = saveDailyBackupToDriveFolder(syncResult.sourceInfo.spreadsheetId, syncResult.targetDateStr);
    Logger.log(`✅ 15:00 Backup Finished & Saved to Drive: ${JSON.stringify(backupResult)}`);
  } catch (err) {
    Logger.log(`❌ Error in 15:00 Backup Job: ${err.message}`);
  }
}

/**
 * 💾 เมนู: บันทึก Backup ลง Drive ทันทีด้วยตนเอง
 */
function menuManualBackupDrive() {
  const ui = SpreadsheetApp.getUi();
  try {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const syncResult = runMasterSyncProcess(yesterday, false);
    
    const backupResult = saveDailyBackupToDriveFolder(syncResult.sourceInfo.spreadsheetId, syncResult.targetDateStr);

    ui.alert(
      "💾 บันทึก Backup ลง Google Drive สำเร็จ!",
      `📁 บันทึกข้อมูล Column B พร้อม Format ครบถ้วนลงโฟลเดอร์เรียบร้อยแล้ว\n` +
      `📄 ชื่อไฟล์: ${backupResult.fileName}\n` +
      `⏱️ เวลาที่ใช้: ${syncResult.elapsed} วินาที`,
      ui.ButtonSet.OK
    );
  } catch (err) {
    ui.alert("❌ เกิดข้อผิดพลาด", err.message, ui.ButtonSet.OK);
  }
}

/**
 * ⏰ ติดตั้ง Trigger อัตโนมัติ:
 * 1. ทุกๆ 1 ชม. -> Update ข้อมูลและ Format ในชีต
 * 2. ทุกวันเวลา 15:00 น. -> Update ข้อมูล + Save Backup ลง Google Drive Folder
 */
function setupCompleteAutomationTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  for (let i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }

  // 1. Trigger ทุก 1 ชั่วโมง (อัปเดตชีต)
  ScriptApp.newTrigger("hourlyScheduledSync")
    .timeBased()
    .everyHours(1)
    .create();

  // 2. Trigger เวลา 15:00 น. ทุกวัน (บันทึก Save ไฟล์ลง Google Drive)
  ScriptApp.newTrigger("dailyScheduledBackup1500")
    .timeBased()
    .everyDays(1)
    .atHour(15)
    .nearMinute(0)
    .inTimezone("Asia/Bangkok")
    .create();

  SpreadsheetApp.getUi().alert(
    "🎉 ติดตั้ง Triggers อัตโนมัติเรียบร้อยแล้ว!",
    "⏰ การทำงานของระบบ:\n\n" +
    "1. 🔄 อัปเดตข้อมูลและ Format จาก Column B ในชีตให้อัตโนมัติ 'ทุกๆ 1 ชั่วโมง'\n" +
    "2. 💾 บันทึกสร้างไฟล์ Backup (Save ลง Google Drive Folder) 'ทุกวันเวลา 15:00 น.'",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

/**
 * 🛑 ยกเลิก Triggers อัตโนมัติทั้งหมด
 */
function removeAllTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  for (let i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }

  SpreadsheetApp.getUi().alert(
    "🛑 ยกเลิก Triggers เรียบร้อยแล้ว",
    "ระบบหยุดการตั้งเวลาทำงานอัตโนมัติทั้งหมดแล้วครับ",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}
