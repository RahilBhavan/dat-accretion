'use strict';
// Hand-drawn inline SVG, no chart library. Charts render at the container's pixel width (viewBox = pixels) so text
// stays 11px on phones; they redraw on resize and on theme change.

let DATA = null;
const ACTIVE = {};  // bars: index of the week that holds the chart's one tab stop, per firm (kept across redraws)
const FIRM = { MSTR: { name: 'Strategy', color: '--s1', shape: 'circle' }, BMNR: { name: 'BitMine', color: '--s2', shape: 'square' } };
// Bar categories in the fixed palette order; residual uses the neutral token, not slot 7 (it is not an action).
const CAT = {
  issue_common: ['Issue common', '--s1'], buyback_common: ['Buy back common', '--s2'], issue_pref: ['Issue preferred', '--s3'],
  retire_pref: ['Retire preferred', '--s4'], coins: ['Coin trades', '--s5'], carry: ['Carry (dividends, interest)', '--s6'],
  residual: ['Residual', '--neutral'],
};
const EST = 'Estimated issuance (BitMine)';
const MINUS = '−';

function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

// $9.2M, $281k, $1.5B; signed values get + or a minus sign.
function usd(x, signed) {
  if (x == null || isNaN(x)) return '-';
  const a = Math.abs(x);
  const [div, unit] = a >= 1e9 ? [1e9, 'B'] : a >= 1e6 ? [1e6, 'M'] : a >= 1e3 ? [1e3, 'k'] : [1, ''];
  const body = '$' + (a / div).toFixed(unit ? 1 : 0) + unit;
  return (x < 0 ? MINUS : signed && x > 0 ? '+' : '') + body;
}

function fix(x, d) {
  return x == null ? '-' : x.toFixed(d);
}

function nice(lo, hi, count) {
  const raw = (hi - lo) / count || 1, p = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map(k => k * p).find(v => v >= raw);
  const out = [];
  for (let v = Math.floor(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(+v.toFixed(10));
  if (out[out.length - 1] < hi) out.push(out[out.length - 1] + step);
  return out;
}

function fileName(url) {
  return url.split('/').pop();
}

// Tooltip inside the chart's wrapper, clamped to it so it never widens the page.
function showTip(wrap, html, x, y) {
  const tip = wrap.querySelector('.tip');
  tip.innerHTML = html;
  tip.hidden = false;
  const W = wrap.clientWidth, tw = tip.offsetWidth, th = tip.offsetHeight;
  let left = x + 12, top = y - th - 8;
  if (left + tw > W) left = Math.max(0, x - tw - 12);
  if (top < 0) top = y + 16;
  tip.style.left = left + 'px';
  tip.style.top = top + 'px';
}

function hideTip(wrap) {
  wrap.querySelector('.tip').hidden = true;
}

document.addEventListener('keydown', ev => {  // WCAG 1.4.13: Escape dismisses the tooltip
  if (ev.key === 'Escape') document.querySelectorAll('.tip').forEach(t => { t.hidden = true; });
});

function bindTips(el, html) {
  const wrap = el.parentElement;
  const at = (t, ev) => {
    const r = wrap.getBoundingClientRect();
    if (ev && ev.clientX != null) return [ev.clientX - r.left, ev.clientY - r.top];
    const b = t.getBoundingClientRect();
    return [b.left - r.left + b.width / 2, b.top - r.top];
  };
  const target = ev => ev.target.closest('[data-tip]');
  el.addEventListener('pointermove', ev => { const t = target(ev); if (t) showTip(wrap, html(t), ...at(t, ev)); else hideTip(wrap); });
  el.addEventListener('pointerleave', () => hideTip(wrap));
  el.addEventListener('focusin', ev => { const t = target(ev); if (t) showTip(wrap, html(t), ...at(t)); });
  el.addEventListener('focusout', () => hideTip(wrap));
}

function markSvg(firm, cx, cy, r, cls, style) {
  if (FIRM[firm].shape === 'circle') return '<circle class="' + cls + '" cx="' + cx + '" cy="' + cy + '" r="' + r + '" style="' + style + '"/>';
  const h = r * 0.886;  // square of equal area
  return '<rect class="' + cls + '" x="' + (cx - h) + '" y="' + (cy - h) + '" width="' + 2 * h + '" height="' + 2 * h + '" rx="1" style="' + style + '"/>';
}

function swatch(inner) {
  return '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">' + inner + '</svg>';
}

// ---- 1. headline ----
function headline() {
  document.getElementById('headline-text').innerHTML = DATA.headline.map(h => '<p class="headline">' + esc(h.sentence) + '</p>').join('')
    + '<p class="closes">' + DATA.headline.map(h => esc(h.close_sentence)).join(' ') + '</p>';
}

// ---- 2. break-even map ----
function mapPoints() {
  return DATA.weeks.filter(w => w.q != null && w.m != null);
}

function drawMap() {
  const el = document.getElementById('map');
  const pts = mapPoints();
  const W = el.clientWidth || 640, H = Math.round(Math.max(320, Math.min(480, W * 0.8)));
  const M = { l: 44, r: 14, t: 12, b: 40 };
  const vals = pts.flatMap(w => [w.m, w.q]);
  // One domain for both axes so m = q is a true diagonal: [min − 0.05, max + 0.05] rounded out to 0.05.
  const lo = Math.floor((Math.min(...vals) - 0.05) * 20) / 20, hi = Math.ceil((Math.max(...vals) + 0.05) * 20) / 20;
  const X = v => M.l + (v - lo) / (hi - lo) * (W - M.l - M.r), Y = v => H - M.b - (v - lo) / (hi - lo) * (H - M.t - M.b);
  const RMAX = W < 500 ? 14 : 20, dmax = Math.max(...pts.map(w => w.dollars_moved), 1);
  const rad = w => Math.max(4, Math.sqrt(w.dollars_moved / dmax) * RMAX);
  let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="Break-even map: net mNAV against preferred price over notional, one mark per firm-week">';
  for (const t of nice(lo, hi, 6).filter(t => t >= lo - 1e-9 && t <= hi + 1e-9)) {
    s += '<line class="grid" x1="' + X(t) + '" x2="' + X(t) + '" y1="' + M.t + '" y2="' + (H - M.b) + '"/>';
    s += '<line class="grid" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/>';
    s += '<text x="' + X(t) + '" y="' + (H - M.b + 14) + '" text-anchor="middle">' + t.toFixed(2) + '</text>';
    s += '<text x="' + (M.l - 6) + '" y="' + (Y(t) + 4) + '" text-anchor="end">' + t.toFixed(2) + '</text>';
  }
  s += '<line class="axis" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + (H - M.b) + '" y2="' + (H - M.b) + '"/>';
  s += '<line class="axis" x1="' + M.l + '" x2="' + M.l + '" y1="' + M.t + '" y2="' + (H - M.b) + '"/>';
  s += '<text x="' + (W - M.r) + '" y="' + (H - 6) + '" text-anchor="end">q = preferred close / $100 notional</text>';
  s += '<text transform="translate(12 ' + M.t + ') rotate(-90)" text-anchor="end">m = net mNAV</text>';
  s += '<line class="diag" x1="' + X(lo) + '" y1="' + Y(lo) + '" x2="' + X(hi) + '" y2="' + Y(hi) + '"/>';
  s += '<text class="label" x="' + (M.l + 8) + '" y="' + (M.t + 14) + '">Strategy\'s rotation adds here (m &gt; q)</text>';
  s += '<text class="label" x="' + (W - M.r - 8) + '" y="' + (H - M.b - 10) + '" text-anchor="end">BitMine\'s rotation adds here (m &lt; q)</text>';
  s += '<text x="' + (X(hi) - 4) + '" y="' + (Y(hi) + 14) + '" text-anchor="end">m = q</text>';
  const order = pts.map((w, i) => i).sort((a, b) => pts[b].dollars_moved - pts[a].dollars_moved);  // small marks on top
  for (const i of order) {
    const w = pts[i], c = 'var(' + FIRM[w.firm].color + ')', r = rad(w), cx = X(w.q), cy = Y(w.m);
    const label = FIRM[w.firm].name + ', week ending ' + w.week_end + ': m ' + fix(w.m, 3) + ', q ' + fix(w.q, 3) + '. Opens filing.';
    s += '<a href="' + esc(w.filing_urls[0]) + '" target="_blank" rel="noopener" data-tip="' + i + '" aria-label="' + esc(label) + '">'
      + markSvg(w.firm, cx, cy, Math.max(r, 10), 'hit', 'fill:transparent')
      + markSvg(w.firm, cx, cy, r, 'mark', 'fill:' + c + ';fill-opacity:0.45;stroke:' + c + ';stroke-width:1.5') + '</a>';
  }
  // Direct label on each firm's latest week: right, left, above, below at growing distance; the first box that stays
  // inside the plot and hits no mark or placed label wins. Box width is estimated at 6.3px per character (11px bold).
  const boxes = pts.map(w => { const r = rad(w); return [X(w.q) - r, Y(w.m) - r, X(w.q) + r, Y(w.m) + r]; });
  const hit = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
  for (const firm of Object.keys(FIRM)) {
    const i = pts.map(p => p.firm).lastIndexOf(firm);
    if (i < 0) continue;
    const w = pts[i], cx = X(w.q), cy = Y(w.m), r = rad(w), text = FIRM[firm].name + ' ' + w.week_end, tw = text.length * 6.3;
    const cands = [4, 18, 36].flatMap(d => [[cx + r + d, cy + 4, 'start'], [cx - r - d, cy + 4, 'end'], [cx, cy - r - d - 1, 'middle'],
      [cx, cy + r + d + 9, 'middle']]);
    const box = ([x, y, a]) => { const x0 = a === 'start' ? x : a === 'end' ? x - tw : x - tw / 2; return [x0, y - 10, x0 + tw, y + 2]; };
    const inside = b => b[0] >= M.l && b[2] <= W - M.r && b[1] >= M.t && b[3] <= H - M.b;
    // Nearest clear spot; if every spot hits something, the one that hits the fewest marks.
    const cost = c => { const b = box(c); return inside(b) ? boxes.filter((o, j) => j !== i && hit(b, o)).length : 1e9; };
    const pick = cands.reduce((best, c) => cost(c) < cost(best) ? c : best);
    boxes.push(box(pick));
    s += '<text class="label" x="' + pick[0] + '" y="' + pick[1] + '" text-anchor="' + pick[2] + '">' + text + '</text>';
  }
  el.innerHTML = s + '</svg>';
  bindTips(el, t => {
    const w = pts[+t.dataset.tip];
    return '<b>' + FIRM[w.firm].name + '</b>, week ending ' + w.week_end
      + '<div class="row"><span>m (net mNAV)</span><span>' + fix(w.m, 3) + '</span></div>'
      + '<div class="row"><span>q (preferred / notional)</span><span>' + fix(w.q, 4) + '</span></div>'
      + '<div class="row"><span>Dollars moved</span><span>' + usd(w.dollars_moved) + '</span></div>'
      + '<div class="row"><span>Value to common of actions</span><span>' + (w.actions_value == null ? 'anchor week' : usd(w.actions_value, true)) + '</span></div>'
      + '<div>Filing: ' + esc(fileName(w.filing_urls[0])) + '</div>';
  });
}

function mapLegend() {
  document.getElementById('map-legend').innerHTML = Object.entries(FIRM).map(([f, v]) =>
    '<span>' + swatch(markSvg(f, 7, 7, 6, '', 'fill:var(' + v.color + ');fill-opacity:0.45;stroke:var(' + v.color + ')')) + v.name + '</span>').join('')
    + '<span>' + swatch('<line x1="1" y1="13" x2="13" y2="1" style="stroke:var(--fg);stroke-dasharray:3 2"/>') + 'm = q</span>'
    + '<span class="muted">Mark area: dollars moved that week (filed actions; carry and estimated issuance excluded)</span>';
}

// ---- 3. attribution bars ----
function stack(w) {
  // [key, label, color var, value, hatched]; issue_common splits into filed and estimated parts.
  const v = w.value, est = w.est_issuance || 0;
  const out = [['issue_common', CAT.issue_common[0], '--s1', v.issue_common - est, false]];
  if (est) out.push(['est_issuance', EST, '--s1', est, true]);
  for (const k of Object.keys(CAT).slice(1)) out.push([k, CAT[k][0], CAT[k][1], v[k], false]);
  return out.filter(d => Math.abs(d[3]) >= 0.005);
}

function segPath(x, y0, y1, w, roundFar, up) {
  // Rect from y0 (near zero) to y1 (far end); the far end gets 4px rounded corners when it is the bar's data-end.
  const top = Math.min(y0, y1), h = Math.abs(y1 - y0), r = roundFar ? Math.min(4, h / 2, w / 2) : 0;
  if (!r) return 'M' + x + ',' + top + 'h' + w + 'v' + h + 'h' + (-w) + 'Z';
  if (up) return 'M' + x + ',' + (top + h) + 'V' + (top + r) + 'Q' + x + ',' + top + ' ' + (x + r) + ',' + top
    + 'H' + (x + w - r) + 'Q' + (x + w) + ',' + top + ' ' + (x + w) + ',' + (top + r) + 'V' + (top + h) + 'Z';
  return 'M' + x + ',' + top + 'V' + (top + h - r) + 'Q' + x + ',' + (top + h) + ' ' + (x + r) + ',' + (top + h)
    + 'H' + (x + w - r) + 'Q' + (x + w) + ',' + (top + h) + ' ' + (x + w) + ',' + (top + h - r) + 'V' + top + 'Z';
}

function weekTip(w, on) {
  const rows = stack(w).map(d => '<div class="row' + (d[0] === on ? ' on' : '') + '"><span><i class="sw" style="background:var(' + d[2] + ')'
    + (d[4] ? ';opacity:0.5' : '') + '"></i>' + d[1] + '</span><span>' + usd(d[3], true) + '</span></div>').join('');
  return '<b>' + FIRM[w.firm].name + '</b>, week ending ' + w.week_end + rows
    + '<div class="row"><span>Coin price (not stacked)</span><span>' + usd(w.price, true) + '</span></div>'
    + '<div class="row"><span>In-the-money flips (not stacked)</span><span>' + usd(w.itm_flip, true) + '</span></div>'
    + '<div class="row on"><span>Observed change</span><span>' + usd(w.observed, true) + '</span></div>';
}

function drawBars(firm) {
  const el = document.getElementById('bars-' + firm);
  const weeks = DATA.weeks.filter(w => w.firm === firm && w.value);
  const W = el.clientWidth || 640, H = W < 500 ? 240 : 280, M = { l: 52, r: 8, t: 16, b: 32 };
  const stacks = weeks.map(stack);
  let lo = 0, hi = 0;
  for (const st of stacks) {
    hi = Math.max(hi, st.reduce((a, d) => a + Math.max(d[3], 0), 0));
    lo = Math.min(lo, st.reduce((a, d) => a + Math.min(d[3], 0), 0));
  }
  const ticks = nice(lo / 1e6, hi / 1e6, 5).map(t => t * 1e6);
  lo = Math.min(lo, ticks[0]); hi = Math.max(hi, ticks[ticks.length - 1]);
  const Y = v => M.t + (hi - v) / (hi - lo) * (H - M.t - M.b);
  const bw = (W - M.l - M.r) / weeks.length, barW = Math.max(4, bw * 0.7);
  const hatch = 'hatch-' + firm;
  let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="' + FIRM[firm].name + ': weekly value to common by cause. Left and Right arrow keys move between weeks.">'
    + '<defs><pattern id="' + hatch + '" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    + '<rect width="6" height="6" style="fill:var(--s1);fill-opacity:0.25"/><line x1="0" y1="0" x2="0" y2="6" style="stroke:var(--s1);stroke-width:3"/></pattern></defs>';
  for (const t of ticks) {
    s += '<line class="' + (t === 0 ? 'axis' : 'grid') + '" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/>';
    s += '<text x="' + (M.l - 6) + '" y="' + (Y(t) + 4) + '" text-anchor="end">' + usd(t) + '</text>';
  }
  if (!ticks.includes(0)) s += '<line class="axis" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>';
  const every = Math.ceil(44 / bw);
  const active = ACTIVE[firm] = Math.min(ACTIVE[firm] ?? weeks.length - 1, weeks.length - 1);
  let big = null;
  weeks.forEach((w, i) => {
    const x0 = M.l + i * bw, x = x0 + (bw - barW) / 2;
    s += '<rect class="col" tabindex="' + (i === active ? 0 : -1) + '" data-tip="' + i + '" x="' + x0 + '" y="' + M.t + '" width="' + bw + '" height="' + (H - M.t - M.b) + '" aria-label="'
      + esc(FIRM[firm].name + ' week ending ' + w.week_end + ': observed ' + usd(w.observed, true)) + '"/>';
    let up = 0, dn = 0;
    const st = stacks[i], lastUp = st.map(d => d[3] > 0).lastIndexOf(true), lastDn = st.map(d => d[3] < 0).lastIndexOf(true);
    st.forEach((d, j) => {
      const v = d[3], a = v > 0 ? up : dn, b = a + v;
      if (v > 0) up = b; else dn = b;
      const fill = d[4] ? 'url(#' + hatch + ')' : 'var(' + d[2] + ')';
      s += '<path class="seg" data-tip="' + i + '" data-cat="' + d[0] + '" d="' + segPath(x, Y(a), Y(b), barW, j === (v > 0 ? lastUp : lastDn), v > 0)
        + '" style="fill:' + fill + '"/>';
      if (!big || Math.abs(v) > Math.abs(big.v)) big = { v, label: d[1], x: x + barW / 2, y: Y(b), up: v > 0 };
    });
    if (i % every === 0) s += '<text x="' + (x0 + bw / 2) + '" y="' + (H - M.b + 14) + '" text-anchor="middle">' + w.week_end.slice(5) + '</text>';
  });
  s += '<text x="' + (W - M.r) + '" y="' + (H - 4) + '" text-anchor="end">week ending (2026)</text>';
  if (big) {  // the one direct label: largest segment in this chart
    const anchor = big.x < W / 3 ? 'start' : big.x > 2 * W / 3 ? 'end' : 'middle';
    const y = big.up ? Math.max(big.y - 6, 11) : Math.min(big.y + 14, H - M.b - 2);
    s += '<text class="label" x="' + big.x + '" y="' + y + '" text-anchor="' + anchor + '">' + big.label + ' ' + usd(big.v, true) + '</text>';
  }
  el.innerHTML = s + '</svg>';
  bindTips(el, t => weekTip(weeks[+t.dataset.tip], t.dataset.cat));
  // One tab stop per chart; Left/Right (Home/End) move between weeks and the tooltip follows focus.
  el.onkeydown = ev => {
    const cols = [...el.querySelectorAll('.col')], i = cols.indexOf(ev.target);
    const step = { ArrowLeft: -1, ArrowRight: 1, Home: -Infinity, End: Infinity }[ev.key];
    if (i < 0 || step == null) return;
    ev.preventDefault();
    const j = Math.max(0, Math.min(cols.length - 1, i + step));
    cols[i].setAttribute('tabindex', '-1');
    cols[j].setAttribute('tabindex', '0');
    ACTIVE[firm] = j;
    cols[j].focus();
  };
}

function barsLegend() {
  const items = Object.entries(CAT).map(([k, [label, c]]) => [label, 'fill:var(' + c + ')']);
  items.splice(1, 0, [EST, 'fill:var(--s1);fill-opacity:0.3']);
  document.getElementById('bars-legend').innerHTML = items.map(([label, st], i) => '<span>' + swatch('<rect x="1" y="1" width="12" height="12" rx="2" style="' + st + '"/>'
    + (i === 1 ? '<path d="M1,9 L9,1 M5,13 L13,5" style="stroke:var(--s1);stroke-width:2"/>' : '')) + label + '</span>').join('');
}

function table() {
  const cols = DATA.categories;
  let h = '<thead><tr><th>firm</th><th>week ending</th><th>m</th><th>q</th><th>dollars moved</th>'
    + cols.map(c => '<th>' + CAT[c][0].toLowerCase() + '</th>').join('')
    + '<th>of which estimated issuance</th><th>coin price</th><th>in-the-money flips</th><th>observed</th><th>filing</th></tr></thead><tbody>';
  for (const w of DATA.weeks) {
    const v = w.value || {};
    h += '<tr><td>' + FIRM[w.firm].name + '</td><td>' + w.week_end + '</td><td>' + fix(w.m, 3) + '</td><td>' + fix(w.q, 4) + '</td><td>' + usd(w.dollars_moved) + '</td>'
      + cols.map(c => '<td>' + (w.value ? usd(v[c], true) : '-') + '</td>').join('')
      + '<td>' + (w.est_issuance ? usd(w.est_issuance, true) : '-') + '</td><td>' + usd(w.price, true) + '</td><td>' + usd(w.itm_flip, true) + '</td><td>'
      + usd(w.observed, true) + '</td><td>' + w.filing_urls.map(u => '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(fileName(u)) + '</a>').join(' ') + '</td></tr>';
  }
  document.getElementById('week-table').innerHTML = h + '</tbody>';
}

// ---- 4. method: notes and check ----
function method() {
  document.getElementById('notes').innerHTML = DATA.notes.map(n => '<li>' + esc(n.text)
    + (n.url ? ' <a href="' + esc(n.url) + '" target="_blank" rel="noopener">Release</a>.' : '') + '</li>').join('');
  const c = DATA.check && typeof DATA.check === 'object' ? DATA.check : { status: 'not yet run' }, when = c.run_at || c.generated_at;
  document.getElementById('check').innerHTML = '<p>Status: ' + esc(c.status || 'see below') + (when ? ', run ' + esc(when) : '') + '.</p>'
    + (Object.keys(c).length > 1 ? '<pre>' + esc(JSON.stringify(c, null, 1)) + '</pre>' : '');
  document.getElementById('footer').textContent = 'Data built ' + DATA.generated_at + ' from the CSVs below.';
}

function draw() {
  drawMap();
  drawBars('MSTR');
  drawBars('BMNR');
}

function theme() {
  const btn = document.getElementById('theme'), root = document.documentElement;
  const dark = () => root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  const saved = localStorage.getItem('theme');
  if (saved) root.dataset.theme = saved;
  const label = () => { btn.textContent = dark() ? 'light theme' : 'dark theme'; };
  label();
  btn.addEventListener('click', () => {
    root.dataset.theme = dark() ? 'light' : 'dark';
    localStorage.setItem('theme', root.dataset.theme);
    label();
  });
}

theme();
fetch('data.json').then(r => r.json()).then(d => {
  DATA = d;
  headline();
  mapLegend();
  barsLegend();
  table();
  method();
  draw();
  let lastW = innerWidth;
  addEventListener('resize', () => { if (innerWidth !== lastW) { lastW = innerWidth; draw(); } });
}).catch(e => {
  document.getElementById('headline-text').innerHTML = '<p>Could not load data.json: ' + esc(e.message) + '</p>';
});
