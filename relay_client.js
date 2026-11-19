/* Company Apps Script relay (scripts/google_apps_script_lh_trip_source.js) called from the browser.
 * Access is "Anyone within Shopee Mobile", so only a browser logged in with the company account can call it
 * (JSONP); the page then forwards the result to the dashboard server.
 *   await callRelay('readdaily', { fileId })   -> relay JSON (throws on errors)
 *   await getRelayCfg()                        -> { url, key, sourceSheetId }
 */
let _relayCfg = null;

async function getRelayCfg() {
  if (_relayCfg) return _relayCfg;
  const res = await (await fetch('/api/lh-trip/drive-settings')).json();
  const st = (res && res.settings) || {};
  const url = String((res && res.dailyRelayUrl) || st.sheetRelayUrl || '').trim();
  if (!url) throw new Error('ยังไม่ได้ตั้งค่า Apps Script URL (เมลบริษัท) — ตั้งได้ที่หน้า LH Trip > เพิ่มเติม > ตั้งค่าแหล่งข้อมูล');
  const m = String(st.sourceSheetUrl || '').match(/\/d\/([a-zA-Z0-9_-]{20,})/);
  _relayCfg = { url, key: (res && res.relayKey) || '', sourceSheetId: m ? m[1] : '1gH3gDAuf0CWKYthnua50qLWC3gUWYovMVMN1hUKyFJo' };
  return _relayCfg;
}

function relayJsonp(baseUrl, params, timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    const cb = '__relayCb_' + Date.now() + '_' + Math.floor(Math.random() * 1e6);
    const s = document.createElement('script');
    let done = false;
    const finish = () => { done = true; clearTimeout(timer); try { delete window[cb]; } catch (e) { window[cb] = undefined; } s.remove(); };
    const fail = (m) => { if (!done) { finish(); reject(new Error(m)); } };
    const loginMsg = 'เรียก Apps Script ไม่ได้ — กรุณา Login Google ด้วยเมลบริษัท (spxexpress.com) ใน Browser นี้ก่อน';
    const timer = setTimeout(() => fail('หมดเวลารอข้อมูลจาก Apps Script'), timeoutMs);
    window[cb] = (d) => { if (!done) { finish(); resolve(d); } };
    s.onerror = () => fail(loginMsg);
    // JSONP runs the callback before "load"; load without callback = Google sign-in page
    s.onload = () => setTimeout(() => fail(loginMsg), 300);
    s.src = baseUrl + (baseUrl.includes('?') ? '&' : '?') + new URLSearchParams(Object.assign({}, params, { callback: cb, _ts: Date.now() }));
    document.body.appendChild(s);
  });
}

async function callRelay(page, extra, timeoutMs) {
  const cfg = await getRelayCfg();
  const res = await relayJsonp(cfg.url, Object.assign({ key: cfg.key, page }, extra || {}), timeoutMs);
  if (!res || res.success === false) {
    const e = (res && res.error) || 'Apps Script ตอบกลับไม่สำเร็จ';
    if (/Unknown page|Unauthorized/i.test(e)) {
      throw new Error(`Apps Script ยังไม่ใช่เวอร์ชันล่าสุด (${e}) — วางโค้ดใหม่แล้ว Deploy > Manage deployments > New version`);
    }
    throw new Error(e);
  }
  return res;
}
