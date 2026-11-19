/* Shared loading popup (SweetAlert2): line bar + % + elapsed seconds instead of a spinner.
 *   Swal.fire(withProgress({ title, text, ... }, expectedMs))  -> one generic step up to 95%
 *   const pg = openProgressModal(title); pg.step(label, endPct, expectedMs); ... pg.done();
 * Requests give no real progress, so each step eases toward its end % and jumps when it ends. */
function _pgEsc(t) {
  return String(t == null ? '' : t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// Loading popups: line bar + % instead of a spinner. The requests give no real progress
// (JSONP / one POST), so the bar eases toward the step's end % and jumps when the step ends.
// withProgress(opts, expectedMs) turns any Swal options with `text` into such a popup.
let _pg = null;
function withProgress(opts, expectedMs) {
  const pg = {};
  const text = opts.text ? `<div class="mb-3">${_pgEsc(opts.text)}</div>` : '';
  const o = Object.assign({}, opts, {
    html: `${text}<div class="text-start">
             <div class="d-flex justify-content-between small mb-1">
               <span id="pgStep" class="text-muted">กำลังดำเนินการ...</span>
               <span id="pgPct" class="fw-bold" style="font-variant-numeric:tabular-nums;">0%</span>
             </div>
             <div class="progress" role="progressbar" aria-label="ความคืบหน้า" aria-valuemin="0" aria-valuemax="100" style="height:10px;">
               <div id="pgBar" class="progress-bar" style="width:0%; background:#ee4d2d; transition:width .25s linear;"></div>
             </div>
             <div id="pgElapsed" class="small text-muted mt-2">0 วินาที</div>
           </div>`,
    showConfirmButton: false,
    // a step set by the caller before the popup rendered wins; otherwise one generic step
    didOpen: () => { if (pg.started) pg.step(pg.label, pg.to, pg.ms, true); else pg.step('กำลังดำเนินการ...', 95, expectedMs || 12000); },
    didDestroy: () => pg.stop()
  });
  delete o.text;
  if (_pg) _pg.stop();
  const t0 = Date.now();
  let pct = 0, from = 0, to = 0, stepStart = t0, expectMs = 1000, timer = null;
  const paint = () => {
    const bar = document.getElementById('pgBar');
    if (!bar) return;
    const p = Math.min(100, Math.floor(pct));
    bar.style.width = p + '%';
    bar.parentElement.setAttribute('aria-valuenow', p);
    document.getElementById('pgPct').textContent = p + '%';
    document.getElementById('pgElapsed').textContent = Math.round((Date.now() - t0) / 1000) + ' วินาที';
  };
  const tick = () => {
    const k = 1 - Math.exp(-(Date.now() - stepStart) / expectMs);   // 63% of the step at expectMs
    pct = Math.max(pct, from + (to - from) * Math.min(k, 0.97));
    paint();
  };
  Object.assign(pg, {
    label: '', started: false, to: 0, ms: 0,
    step(label, endPct, ms, keepStart) {
      if (!timer) timer = setInterval(tick, 200);
      pg.started = true; pg.label = label; pg.to = endPct; pg.ms = ms;
      if (!keepStart) { from = pct; stepStart = Date.now(); }
      to = endPct; expectMs = ms || 3000;
      const el = document.getElementById('pgStep'); if (el) el.textContent = label;
      tick();
    },
    done() { clearInterval(timer); timer = null; pct = 100; const el = document.getElementById('pgStep'); if (el) el.textContent = 'เสร็จแล้ว'; paint(); },
    stop() { clearInterval(timer); timer = null; }
  });
  _pg = pg;
  return o;
}

function openProgressModal(title) {
  Swal.fire(withProgress({ title, allowOutsideClick: true, showCloseButton: true }, 3000));
  return _pg;
}

