'use strict';
// Hand-drawn inline SVG, no chart library. Charts render at the container's pixel width (viewBox = pixels) so text
// stays 11px on phones; they redraw on resize and on theme change.

let DATA = null;
const ACTIVE = {};  // index of the column that holds a chart's one tab stop, per chart element id (kept across redraws)
const FIRM = {
  MSTR: { name: 'Strategy', color: '--s1', shape: 'circle' }, BMNR: { name: 'BitMine', color: '--s2', shape: 'square' },
  SBET: { name: 'SharpLink', color: '--s7', shape: 'triangle' },
};
// Bar categories: label and colour group. Five colours (--c1..--c4 kept clear of the firm colours); residual uses the
// neutral token (it is not an action). The tooltip and table still list every category.
const GROUP = { common: ['Common', '--c1'], pref: ['Preferred', '--c2'], coins: ['Coin trades', '--c3'],
  carry: ['Carry (dividends, interest, staking)', '--c4'], residual: ['Residual', '--neutral'] };
const CAT = {
  issue_common: ['Issue common', '--c1'], buyback_common: ['Buy back common', '--c1'], issue_pref: ['Issue preferred', '--c2'],
  retire_pref: ['Retire preferred', '--c2'], coins: ['Coin trades', '--c3'], carry: ['Carry (dividends, interest, staking)', '--c4'],
  residual: ['Residual', '--neutral'],
};
const EST = 'Estimated issuance (BitMine)';
// Residual: what the filings leave unexplained. Hatched neutral on every chart so it never reads as an action.
const RESID_FILL = id => 'url(#' + id + ')';
function residPattern(id) {
  return '<pattern id="' + id + '" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">'
    + '<rect width="5" height="5" style="fill:var(--neutral);fill-opacity:0.25"/><line x1="0" y1="0" x2="0" y2="5" style="stroke:var(--neutral);stroke-width:2"/></pattern>';
}
const RESID_SWATCH = '<rect x="1" y="1" width="12" height="12" rx="2" style="fill:var(--neutral);fill-opacity:0.25"/><path d="M1,5 L5,1 M1,9 L9,1 M1,13 L13,1 M5,13 L13,5 M9,13 L13,9" style="stroke:var(--neutral);stroke-width:1.5"/>';
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
  if (FIRM[firm].shape === 'triangle') {  // equilateral, area of the circle of radius r
    const a = r * 2.694, h = a * 0.866, top = cy - h * 2 / 3;
    return '<path class="' + cls + '" d="M' + cx + ',' + top + 'L' + (cx + a / 2) + ',' + (top + h) + 'L' + (cx - a / 2) + ',' + (top + h) + 'Z" style="' + style + '"/>';
  }
  if (FIRM[firm].shape === 'circle') return '<circle class="' + cls + '" cx="' + cx + '" cy="' + cy + '" r="' + r + '" style="' + style + '"/>';
  const h = r * 0.886;  // square of equal area
  return '<rect class="' + cls + '" x="' + (cx - h) + '" y="' + (cy - h) + '" width="' + 2 * h + '" height="' + 2 * h + '" rx="1" style="' + style + '"/>';
}

function swatch(inner) {
  return '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">' + inner + '</svg>';
}

// ---- 1. headline ----
// Bullet track: a grey band on the side where the program adds, a tick at break-even, a dot in the firm colour at the
// close. Scale spans both values with 30% padding. SharpLink: m against 1 (buyback side below, issue side above).
function track(h) {
  const sbet = h.break_even == null, v = sbet ? h.m : h.pref_close, be = sbet ? 1 : h.break_even;
  const lo = Math.min(v, be), hi = Math.max(v, be), pad = (hi - lo) * 0.3 || 0.1, a = lo - pad, b = hi + pad;
  const pct = x => (x - a) / (b - a) * 100;
  const pos = x => { const p = pct(x); return 'left:' + p.toFixed(1) + '%;transform:translateX(' + (p < 22 ? '0' : p > 78 ? '-100%' : '-50%') + ')'; };
  const bandLeft = h.firm === 'BMNR' ? pct(be) : 0, bandW = h.firm === 'BMNR' ? 100 - pct(be) : pct(be);
  const beLabel = sbet ? 'm = 1' : 'Break-even $' + be.toFixed(2), vLabel = sbet ? 'm ' + v.toFixed(3) : h.pref + ' $' + v.toFixed(2);
  const sides = sbet ? ['Buyback adds', 'Issuance adds'] : h.firm === 'MSTR' ? ['Rotation adds', ''] : ['', 'Rotation adds'];
  return '<div class="bullet" role="img" aria-label="' + esc(vLabel + ', ' + beLabel) + '">'
    + '<div class="bullet-top"><span style="' + pos(be) + '">' + esc(beLabel) + '</span></div>'
    + '<div class="bullet-track"><i class="band" style="left:' + bandLeft.toFixed(1) + '%;width:' + bandW.toFixed(1) + '%"></i>'
    + '<i class="tick" style="left:' + pct(be).toFixed(1) + '%"></i><i class="dot" style="left:' + pct(v).toFixed(1) + '%;background:var(' + FIRM[h.firm].color + ')"></i></div>'
    + '<div class="bullet-bottom"><span style="' + pos(v) + '">' + esc(vLabel) + '</span></div>'
    + '<div class="bullet-sides"><span>' + sides[0] + '</span><span>' + sides[1] + '</span></div></div>';
}

// Days from an ISO date to today (UTC). The page is static, so staleness is computed when it is read.
function daysAgo(iso) {
  return Math.floor((Date.now() - Date.parse(iso + 'T00:00:00Z')) / 864e5);
}

// As-of line: what the figures cover, how old that is, and where each number comes from. Weekly firms file on
// Mondays for the week ending Sunday, so more than 9 days since the latest week means a refresh was missed.
function asof() {
  const weekly = DATA.headline.filter(h => h.break_even != null), sbet = DATA.headline.find(h => h.break_even == null);
  const through = weekly.map(h => h.week_end).sort()[0], age = daysAgo(through);
  let s = 'Data through the week ending ' + esc(through) + ' (' + age + ' days ago)';
  if (sbet) s += '; SharpLink through its last filed holdings date, ' + esc(sbet.week_end) + ' (' + daysAgo(sbet.week_end) + ' days ago)';
  s += '. Every action links to its SEC filing.';
  if (age > 9) s += ' <strong class="stale">Behind: filings after ' + esc(through) + ' are not yet included.</strong>';
  document.getElementById('asof').innerHTML = s;
}

function headline() {
  document.getElementById('title').innerHTML = esc(DATA.title).replace(/\d{4}-\d{2}-\d{2}/g, '<span class="nobr">$&</span>');
  asof();
  document.getElementById('headline-text').innerHTML = '<div class="snapshot-grid">' + DATA.headline.map(h => {
    const symbol = h.firm.toLowerCase(), sbet = h.break_even == null;
    const value = sbet ? 'm ' + h.m.toFixed(3) : '$' + h.pref_close.toFixed(2);
    const gap = sbet ? Math.abs(h.m - 1).toFixed(3) + (h.m < 1 ? ' below' : ' above') + ' 1'
      : '$' + Math.abs(h.gap).toFixed(2) + (h.gap < 0 ? ' below' : ' above') + ' break-even $' + h.break_even.toFixed(2);
    return '<article class="snapshot-card"><div class="snapshot-top"><span class="firm-symbol ' + symbol + '">' + esc(h.firm) + '</span><span class="snapshot-date">' + esc(sbet ? 'net mNAV' : h.pref + ' close') + '</span></div>'
      + '<h3>' + esc(h.name) + '</h3><p class="snapshot-value">' + esc(value) + '</p><p class="snapshot-label">' + esc(gap) + '</p>'
      + track(h) + '<p class="snapshot-asof">As of ' + esc(h.price_date) + (sbet ? ' (last filed holdings date, ' + daysAgo(h.week_end) + ' days ago)' : ', net mNAV ' + h.m.toFixed(3)) + '</p>'
      + '</article>';
  }).join('') + '</div><p class="snapshot-footnote">' + DATA.headline.map(h => esc(h.close_sentence)).join(' ') + '</p>';
  document.getElementById('counts').textContent = DATA.counts;
  example();
}

// ---- 1b. worked example: one filed action, from its data row ----
function example() {
  const x = DATA.example, M = v => '$' + (v / 1e6).toFixed(1) + ' million';
  document.getElementById('example-title').textContent = 'One action, step by step: ' + M(x.usd) + ' of STRC retired adds ' + M(x.adds_usd) + ' to common';
  document.getElementById('example').innerHTML = '<ol class="steps">'
    + '<li>Strategy paid <strong>' + M(x.usd) + '</strong> to buy back STRC with <strong>' + M(x.notional) + '</strong> of notional, $' + x.avg_price.toFixed(2) + ' per $100 share (q = ' + x.q.toFixed(4) + ').</li>'
    + '<li>Each STRC share carried a $100 claim on the company ahead of common. Retiring the shares removed ' + M(x.notional) + ' of claims for ' + M(x.usd) + ' of cash.</li>'
    + '<li>The difference, ' + M(x.notional) + ' − ' + M(x.usd) + ' = <strong>' + M(x.adds_usd) + '</strong>, moves to common holders. In the formula: (1/q − 1) × ' + M(x.usd) + '.</li>'
    + '<li>Across ' + x.shares.toLocaleString('en-US') + ' fully diluted shares, net coins per share rose by <strong>' + x.sats_per_share.toFixed(2) + ' sats</strong> (exact recompute).</li>'
    + '</ol><p class="source">Source: <a href="' + esc(x.filing_url) + '" target="_blank" rel="noopener">Strategy 8-K for the week ending ' + esc(x.week_end) + '</a>. Every bar and mark below is built the same way.</p>';
}

// ---- 2. preferred close against break-even, by week ----
// One tab stop per chart: Left/Right (Home/End) move between .col elements and the tooltip follows focus.
function colKeys(el) {
  el.onkeydown = ev => {
    const cols = [...el.querySelectorAll('.col')], i = cols.indexOf(ev.target);
    const step = { ArrowLeft: -1, ArrowRight: 1, Home: -Infinity, End: Infinity }[ev.key];
    if (i < 0 || step == null) return;
    ev.preventDefault();
    const j = Math.max(0, Math.min(cols.length - 1, i + step));
    cols[i].setAttribute('tabindex', '-1');
    cols[j].setAttribute('tabindex', '0');
    ACTIVE[el.id] = j;
    cols[j].focus();
  };
}

function drawPref(firm) {
  const el = document.getElementById('pref-' + firm), sbet = firm === 'SBET', h = DATA.headline.find(x => x.firm === firm);
  // close: preferred close in dollars (SharpLink: m); be: break-even, 100 × m (SharpLink: 1).
  const pts = DATA.weeks.filter(w => w.firm === firm && w.m != null && (sbet || w.q != null))
    .map(w => ({ w, t: Date.parse(w.week_end), close: sbet ? w.m : w.q * 100, be: sbet ? 1 : w.m * 100 }));
  const W = el.clientWidth || 640, H = W < 500 ? 220 : 260, M = { l: 48, r: W < 500 ? 70 : 92, t: 14, b: 32 };
  const vals = pts.flatMap(p => [p.close, p.be]), ticks = nice(Math.min(...vals), Math.max(...vals), 4);
  const lo = ticks[0], hi = ticks[ticks.length - 1], t0 = pts[0].t, t1 = pts[pts.length - 1].t;
  const X = t => M.l + (t - t0) / (t1 - t0 || 1) * (W - M.l - M.r), Y = v => M.t + (hi - v) / (hi - lo) * (H - M.t - M.b);
  const fmt = v => sbet ? v.toFixed(2) : '$' + v.toFixed(0), c = 'var(' + FIRM[firm].color + ')';
  const label = sbet ? 'm' : h.pref + ' close';
  let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="' + esc(FIRM[firm].name + ': ' + label + ' and break-even by '
    + (sbet ? 'filed date' : 'week') + '. Left and Right arrow keys move between ' + (sbet ? 'dates.' : 'weeks.')) + '">';
  for (const t of ticks) {
    s += '<line class="grid" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/>';
    s += '<text x="' + (M.l - 6) + '" y="' + (Y(t) + 4) + '" text-anchor="end">' + fmt(t) + '</text>';
  }
  s += '<line class="axis" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + (H - M.b) + '" y2="' + (H - M.b) + '"/>';
  const line = k => pts.map((p, i) => (i ? 'L' : 'M') + X(p.t).toFixed(1) + ',' + Y(p[k]).toFixed(1)).join('');
  s += '<path class="gapband" d="' + line('close') + pts.slice().reverse().map(p => 'L' + X(p.t).toFixed(1) + ',' + Y(p.be).toFixed(1)).join('') + 'Z"/>';
  // Columns: each point owns the span halfway to its neighbours.
  const mid = i => i < 0 ? M.l : i >= pts.length - 1 ? W - M.r : (X(pts[i].t) + X(pts[i + 1].t)) / 2;
  const active = ACTIVE[el.id] = Math.min(ACTIVE[el.id] ?? pts.length - 1, pts.length - 1);
  const minGap = 44;
  let lastTick = -Infinity;
  pts.forEach((p, i) => {
    const x0 = mid(i - 1), x1 = mid(i);
    s += '<rect class="col" tabindex="' + (i === active ? 0 : -1) + '" data-tip="' + i + '" x="' + x0 + '" y="' + M.t + '" width="' + Math.max(1, x1 - x0) + '" height="' + (H - M.t - M.b)
      + '" aria-label="' + esc(FIRM[firm].name + (sbet ? ' filed date ' : ' week ending ') + p.w.week_end + ': ' + label + ' ' + fix(p.close, sbet ? 3 : 2) + ', break-even ' + fix(p.be, sbet ? 0 : 2)) + '"/>';
    const x = X(p.t);
    if (x - lastTick >= minGap && (i === pts.length - 1 || W - M.r - x >= minGap / 2 || sbet)) {
      s += '<text x="' + x + '" y="' + (H - M.b + 14) + '" text-anchor="middle">' + p.w.week_end.slice(5) + '</text>';
      lastTick = x;
    }
  });
  s += '<path class="be-line" d="' + line('be') + '"/><path d="' + line('close') + '" style="fill:none;stroke:' + c + ';stroke-width:2;pointer-events:none"/>';
  if (sbet) s += pts.map(p => markSvg(firm, X(p.t), Y(p.close), 5, 'dot', 'fill:' + c)).join('');
  // Direct labels at the right end, two lines each, pushed apart if closer than 26px.
  const last = pts[pts.length - 1], xr = W - M.r + 6;
  let yc = Y(last.close), yb = Y(last.be);
  if (Math.abs(yc - yb) < 26) { const m = (yc + yb) / 2, d = yc <= yb ? -13 : 13; yc = m + d; yb = m - d; }
  const two = (y, a, b, st) => '<text class="label" x="' + xr + '" y="' + (y - 2) + '"' + st + '>' + a + '</text><text x="' + xr + '" y="' + (y + 10) + '">' + b + '</text>';
  s += two(yc, sbet ? 'm' : esc(h.pref), sbet ? last.close.toFixed(3) : '$' + last.close.toFixed(2), ' style="fill:' + c + '"');
  s += two(yb, 'Break-even', sbet ? 'm = 1' : '$' + last.be.toFixed(2), '');
  s += '<text x="' + (W - M.r) + '" y="' + (H - 4) + '" text-anchor="end">' + (sbet ? 'filed holdings date (2026)' : 'week ending (2026)') + '</text>';
  el.innerHTML = s + '</svg>';
  bindTips(el, t => {
    const p = pts[+t.dataset.tip], g = p.close - p.be;
    const gap = sbet ? Math.abs(g).toFixed(3) + (g < 0 ? ' below 1' : ' above 1') : '$' + Math.abs(g).toFixed(2) + (g < 0 ? ' below' : ' above');
    return '<b>' + FIRM[firm].name + '</b>, ' + (sbet ? 'filed date ' : 'week ending ') + p.w.week_end
      + '<div class="row"><span>' + (sbet ? 'm (net mNAV)' : esc(h.pref) + ' close') + '</span><span>' + (sbet ? p.close.toFixed(3) : '$' + p.close.toFixed(2)) + '</span></div>'
      + '<div class="row"><span>Break-even' + (sbet ? '' : ' (100 × m)') + '</span><span>' + (sbet ? '1' : '$' + p.be.toFixed(2)) + '</span></div>'
      + '<div class="row on"><span>Gap</span><span>' + gap + '</span></div>'
      + '<div>Filing: ' + esc(fileName(p.w.filing_urls[0])) + '</div>';
  });
  colKeys(el);
  const n = new Set(pts.flatMap(p => p.w.filing_urls)).size;
  document.getElementById('src-' + firm).innerHTML = 'Source: ' + n + ' SEC filings; closes from Yahoo Finance. Data: <a href="data/attribution.csv">attribution.csv</a>';
}

function prefLegend() {
  document.getElementById('pref-legend').innerHTML = '<span>' + swatch('<line x1="1" y1="7" x2="13" y2="7" style="stroke:var(--muted);stroke-width:2"/>') + 'Preferred close, in the firm colour (SharpLink: m)</span>'
    + '<span>' + swatch('<line x1="1" y1="7" x2="13" y2="7" style="stroke:var(--fg);stroke-dasharray:3 2"/>') + 'Break-even, $100 × m (SharpLink: 1)</span>'
    + '<span>' + swatch('<rect x="1" y="3" width="12" height="8" style="fill:var(--neutral);fill-opacity:0.22"/>') + 'Gap between them</span>';
}

// ---- 3. break-even map ----
function mapPoints() {
  // qx: map x. SharpLink has no preferred (q null); its marks sit at q = 1, where m = q is m = 1.
  return DATA.weeks.filter(w => w.m != null && (w.q != null || w.firm === 'SBET')).map(w => ({ ...w, qx: w.q ?? 1 }));
}

function drawMap() {
  const el = document.getElementById('map');
  const pts = mapPoints();
  const W = el.clientWidth || 640, H = Math.round(Math.max(320, Math.min(480, W * 0.8)));
  const M = { l: 44, r: 14, t: 12, b: 40 };
  const vals = pts.flatMap(w => [w.m, w.qx]);
  // One domain for both axes so m = q is a true diagonal: [min − 0.05, max + 0.05] rounded out to 0.05.
  const lo = Math.floor((Math.min(...vals) - 0.05) * 20) / 20, hi = Math.ceil((Math.max(...vals) + 0.05) * 20) / 20;
  const X = v => M.l + (v - lo) / (hi - lo) * (W - M.l - M.r), Y = v => H - M.b - (v - lo) / (hi - lo) * (H - M.t - M.b);
  // One mark size: position carries m and q; dollars moved are in the tooltip (area is read least accurately,
  // Cleveland & McGill 1984). Each firm's weeks are joined in date order; its latest mark is solid.
  const R = W < 500 ? 4.5 : 5.5, rad = () => R;
  const latest = {};
  pts.forEach((w, i) => { if (!(w.firm in latest) || w.week_end > pts[latest[w.firm]].week_end) latest[w.firm] = i; });
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
  if (W >= 500) s += '<text x="' + (X(hi) - 40) + '" y="' + (Y(hi) + 6) + '" text-anchor="end">m = q</text>';  // above-left, clear of the diagonal; narrow: legend only
  for (const firm of Object.keys(FIRM)) {
    const path = pts.filter(w => w.firm === firm).sort((a, b) => a.week_end < b.week_end ? -1 : 1);
    if (path.length > 1) s += '<polyline class="trail" points="' + path.map(w => X(w.qx).toFixed(1) + ',' + Y(w.m).toFixed(1)).join(' ')
      + '" style="stroke:var(' + FIRM[firm].color + ')"/>';
  }
  const isLast = i => Object.values(latest).includes(i), order = pts.map((w, i) => i).sort((a, b) => isLast(a) - isLast(b));  // latest on top
  for (const i of order) {
    const w = pts[i], c = 'var(' + FIRM[w.firm].color + ')', r = rad(w), cx = X(w.qx), cy = Y(w.m);
    const last = latest[w.firm] === i;
    const label = FIRM[w.firm].name + (w.firm === 'SBET' ? ', filed date ' : ', week ending ') + w.week_end + ': m ' + fix(w.m, 3)
      + (w.q == null ? ', no preferred (plotted at q = 1)' : ', q ' + fix(w.q, 3)) + '. Opens filing.';
    s += '<a href="' + esc(w.filing_urls[0]) + '" target="_blank" rel="noopener" data-tip="' + i + '" aria-label="' + esc(label) + '">'
      + markSvg(w.firm, cx, cy, Math.max(r, 12), 'hit', 'fill:transparent')
      + markSvg(w.firm, cx, cy, last ? r + 1.5 : r, 'mark', 'fill:' + c + ';fill-opacity:' + (last ? 1 : 0.35) + ';stroke:' + c + ';stroke-width:1.5') + '</a>';
  }
  // Direct label on each firm's latest week: right, left, above, below at growing distance; the first box that stays
  // inside the plot and hits no mark or placed label wins. Box width is estimated at 6.3px per character (11px bold).
  const boxes = pts.map(w => { const r = rad(w); return [X(w.qx) - r, Y(w.m) - r, X(w.qx) + r, Y(w.m) + r]; });
  const hit = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
  for (const firm of Object.keys(FIRM)) {
    const i = latest[firm];
    if (i == null) continue;
    const w = pts[i], cx = X(w.qx), cy = Y(w.m), r = rad(w), text = FIRM[firm].name + ' ' + w.week_end, tw = text.length * 6.3;
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
  const tipHtml = t => {
    const w = pts[+t.dataset.tip];
    return '<b>' + FIRM[w.firm].name + '</b>, ' + (w.firm === 'SBET' ? 'filed date ' : 'week ending ') + w.week_end
      + '<div class="row"><span>m (net mNAV)</span><span>' + fix(w.m, 3) + '</span></div>'
      + '<div class="row"><span>q (preferred / notional)</span><span>' + (w.q == null ? 'no preferred, plotted at 1' : fix(w.q, 4)) + '</span></div>'
      + '<div class="row"><span>Dollars moved</span><span>' + usd(w.dollars_moved) + '</span></div>'
      + '<div class="row"><span>Value to common of actions</span><span>' + (w.actions_value == null ? 'anchor week' : usd(w.actions_value, true)) + '</span></div>'
      + '<div>Filing: ' + esc(fileName(w.filing_urls[0])) + '</div>';
  };
  bindTips(el, tipHtml);
  // Touch: the first tap on a mark pins its details below the chart instead of navigating; a second tap on the same
  // mark, or the pin's link, opens the filing. Mouse and keyboard follow the link directly.
  const pin = el.closest('.chart-panel').querySelector('.pin');
  let touch = false;
  el.onpointerdown = ev => { touch = ev.pointerType === 'touch'; };
  el.onclick = ev => {
    const a = ev.target.closest('a[data-tip]');
    if (!a || !touch || pin.dataset.tip === a.dataset.tip) return;
    ev.preventDefault();
    hideTip(el.parentElement);
    pin.dataset.tip = a.dataset.tip;
    pin.innerHTML = tipHtml(a) + '<a href="' + a.getAttribute('href') + '" target="_blank" rel="noopener">View filing</a>';
    pin.hidden = false;
  };
}

function mapTitle() {
  const h = Object.fromEntries(DATA.headline.map(x => [x.firm, x])), a = h.MSTR, b = h.BMNR;
  document.getElementById('map-title').textContent = 'Break-even map: Strategy at m ' + a.m.toFixed(3) + ', q ' + a.q.toFixed(3)
    + '; BitMine at m ' + b.m.toFixed(3) + ', q ' + b.q.toFixed(3) + ' (week ending ' + a.week_end + ')';
}

function mapLegend() {
  mapTitle();
  document.getElementById('map-legend').innerHTML = Object.entries(FIRM).map(([f, v]) =>
    '<span>' + swatch(markSvg(f, 7, 7, 6, '', 'fill:var(' + v.color + ');fill-opacity:0.45;stroke:var(' + v.color + ')')) + v.name
    + (f === 'SBET' ? ' (no preferred, so its marks sit at q = 1, where the line is m = 1)' : '') + '</span>').join('')
    + '<span>' + swatch('<line x1="1" y1="13" x2="13" y2="1" style="stroke:var(--fg);stroke-dasharray:3 2"/>') + 'm = q</span>'
    + '<span class="muted">Lines join each firm\'s weeks in date order; the solid mark is the latest. Dollars moved are in each mark\'s details.</span>';
}

// ---- 4. attribution bars ----
function stack(w) {
  // [key, label, color var, value, hatched]; issue_common splits into filed and estimated parts.
  const v = w.value, est = w.est_issuance || 0;
  const out = [['issue_common', CAT.issue_common[0], '--c1', v.issue_common - est, false]];
  if (est) out.push(['est_issuance', EST, '--c1', est, true]);
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
  const rows = stack(w).map(d => '<div class="row' + (d[0] === on ? ' on' : '') + '"><span><i class="sw' + (d[0] === 'residual' ? ' resid' : '') + '" style="background:var(' + d[2] + ')'
    + (d[4] ? ';opacity:0.5' : '') + '"></i>' + d[1] + '</span><span>' + usd(d[3], true) + '</span></div>').join('');
  return '<b>' + FIRM[w.firm].name + '</b>, ' + (w.firm === 'SBET' ? 'filed date ' : 'week ending ') + w.week_end + rows
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
  const bw = (W - M.l - M.r) / weeks.length, barW = Math.min(48, Math.max(4, bw * 0.7));
  const hatch = 'hatch-' + firm, resid = 'resid-' + firm;
  let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="' + FIRM[firm].name + ': weekly value to common by cause. Left and Right arrow keys move between weeks.">'
    + '<defs><pattern id="' + hatch + '" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    + '<rect width="6" height="6" style="fill:var(--c1);fill-opacity:0.25"/><line x1="0" y1="0" x2="0" y2="6" style="stroke:var(--c1);stroke-width:3"/></pattern>' + residPattern(resid) + '</defs>';
  for (const t of ticks) {
    s += '<line class="' + (t === 0 ? 'axis' : 'grid') + '" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/>';
    s += '<text x="' + (M.l - 6) + '" y="' + (Y(t) + 4) + '" text-anchor="end">' + usd(t) + '</text>';
  }
  if (!ticks.includes(0)) s += '<line class="axis" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>';
  const every = Math.ceil(44 / bw);
  const active = ACTIVE[el.id] = Math.min(ACTIVE[el.id] ?? weeks.length - 1, weeks.length - 1);
  let big = null;
  weeks.forEach((w, i) => {
    const x0 = M.l + i * bw, x = x0 + (bw - barW) / 2;
    s += '<rect class="col" tabindex="' + (i === active ? 0 : -1) + '" data-tip="' + i + '" x="' + x0 + '" y="' + M.t + '" width="' + bw + '" height="' + (H - M.t - M.b) + '" aria-label="'
      + esc(FIRM[firm].name + (firm === 'SBET' ? ' filed date ' : ' week ending ') + w.week_end + ': observed ' + usd(w.observed, true)) + '"/>';
    let up = 0, dn = 0;
    const st = stacks[i], lastUp = st.map(d => d[3] > 0).lastIndexOf(true), lastDn = st.map(d => d[3] < 0).lastIndexOf(true);
    st.forEach((d, j) => {
      const v = d[3], a = v > 0 ? up : dn, b = a + v;
      if (v > 0) up = b; else dn = b;
      const fill = d[0] === 'residual' ? RESID_FILL(resid) : d[4] ? 'url(#' + hatch + ')' : 'var(' + d[2] + ')';
      s += '<path class="seg" data-tip="' + i + '" data-cat="' + d[0] + '" d="' + segPath(x, Y(a), Y(b), barW, j === (v > 0 ? lastUp : lastDn), v > 0)
        + '" style="fill:' + fill + '"/>';
      if (!big || Math.abs(v) > Math.abs(big.v)) big = { v, label: d[1], x, y: (Y(a) + Y(b)) / 2, week: w.week_end };
    });
    if (st.length) s += '<line class="net" x1="' + (x - 3) + '" x2="' + (x + barW + 3) + '" y1="' + Y(up + dn) + '" y2="' + Y(up + dn) + '"/>';
    if (i % every === 0) s += '<text x="' + (x0 + bw / 2) + '" y="' + (H - M.b + 14) + '" text-anchor="middle">' + w.week_end.slice(5) + '</text>';
  });
  s += '<text x="' + (W - M.r) + '" y="' + (H - 4) + '" text-anchor="end">' + (firm === 'SBET' ? 'filed holdings date (2026)' : 'week ending (2026)') + '</text>';
  if (big) {  // the one direct label: largest segment in this chart, beside its bar at the segment's middle (clear of the net tick)
    // Narrow charts have no room beside a bar; the label moves to the plot's top-left corner with its week.
    const right = big.x < W * 0.6, x = W < 500 ? M.l + 4 : right ? big.x + barW + 6 : big.x - 6;
    s += '<text class="label" x="' + x + '" y="' + (W < 500 ? M.t + 4 : big.y + 4) + '" text-anchor="' + (W < 500 || right ? 'start' : 'end') + '">'
      + (W < 500 ? 'Largest: ' + big.week.slice(5) + ' ' : '') + big.label + ' ' + usd(big.v, true) + '</text>';
  }
  el.innerHTML = s + '</svg>';
  bindTips(el, t => weekTip(weeks[+t.dataset.tip], t.dataset.cat));
  colKeys(el);
}

function barsLegend() {
  const items = Object.entries(GROUP).map(([k, [label, c]]) => k === 'residual'
    ? swatch(RESID_SWATCH) + 'Residual: change the filings leave unexplained'
    : swatch('<rect x="1" y="1" width="12" height="12" rx="2" style="fill:var(' + c + ')"/>') + label);
  items.splice(1, 0, swatch('<rect x="1" y="1" width="12" height="12" rx="2" style="fill:var(--c1);fill-opacity:0.3"/><path d="M1,9 L9,1 M5,13 L13,5" style="stroke:var(--c1);stroke-width:2"/>')
    + EST + ', part of common');
  items.push(swatch('<line x1="1" y1="7" x2="13" y2="7" style="stroke:var(--fg);stroke-width:2"/>') + 'Net of the stacked causes');
  document.getElementById('bars-legend').innerHTML = items.map(x => '<span>' + x + '</span>').join('');
}

// Under each firm's bars: a sentence on the residual, then a diverging strip of the totals since the first week, by
// cause, in the bars' colours. Coin price and flips are not in the bars, so they stay neutral; observed is the firm colour.
function residualSentence(firm, x) {
  const r = x.residual;
  let t = 'Residual ' + usd(r, true) + ', against filed actions of ' + usd(x.actions, true) + '. ';
  if (x.checked_from) {
    t += usd(r - x.residual_checked, true) + ' of it falls before ' + x.checked_from + ', when the 8-Ks did not itemize cash flows; '
      + usd(x.residual_checked, true) + ' falls in the weeks since, each checked against the filings.';
  } else if (firm === 'BMNR') {
    t += 'Report only: BitMine\'s releases do not itemize cash flows, so no week is checked.';
  } else {
    t += 'Report only: mostly shares added to S on filed dates that no filing ties to an action (see caveats).';
  }
  return t;
}

function totals() {
  for (const [firm, x] of Object.entries(DATA.totals)) {
    const rows = [['Filed actions', x.actions, 'var(--fg);opacity:0.55'], ...(x.est_issuance ? [['Estimated issuance', x.est_issuance, 'est']] : []),
      ['Carry', x.carry, 'var(--c4)'], ['Residual', x.residual, 'resid'], ['Coin price', x.price, 'var(--neutral)'],
      ['In-the-money flips', x.itm_flip, 'var(--neutral)'], ['Observed', x.observed, 'var(' + FIRM[firm].color + ')']];
    const lo = Math.min(0, ...rows.map(r => r[1])), hi = Math.max(0, ...rows.map(r => r[1])), pct = v => (v - lo) / (hi - lo || 1) * 100;
    const html = rows.map(([label, v, fill], i) => {
      const obs = i === rows.length - 1, a = pct(Math.min(0, v)), b = pct(Math.max(0, v));
      const cls = fill === 'resid' ? ' class="resid"' : fill === 'est' ? ' class="est"' : '';
      const bg = fill === 'resid' || fill === 'est' ? '' : ';background:' + fill;
      return '<div class="strip-row' + (obs ? ' obs' : '') + '"><span>' + label + '</span><span class="strip-bar"><i class="zero" style="left:' + pct(0).toFixed(1) + '%"></i>'
        + '<i' + cls + ' style="left:' + a.toFixed(1) + '%;width:' + Math.max(b - a, 0.4).toFixed(1) + '%' + bg + '"></i></span>'
        + '<span class="strip-val">' + usd(v, true) + '</span></div>';
    }).join('');
    document.getElementById('bars-' + firm).closest('.firm-panel').insertAdjacentHTML('beforeend',
      '<div class="strip"><p class="strip-title">Since ' + esc(x.since) + ', value to common by cause</p>'
      + '<p class="strip-note">' + esc(residualSentence(firm, x)) + '</p>' + html + '</div>');
  }
}

function table() {
  const cols = DATA.categories;
  let h = '<thead><tr><th>firm</th><th>week ending (SharpLink: filed date)</th><th>m</th><th>q</th><th>dollars moved ($)</th>'
    + cols.map(c => '<th>' + CAT[c][0].toLowerCase() + ' ($)</th>').join('')
    + '<th>of which estimated issuance ($)</th><th>coin price ($)</th><th>in-the-money flips ($)</th><th>observed ($)</th><th>filing</th></tr></thead><tbody>';
  for (const w of DATA.weeks) {
    const v = w.value || {};
    h += '<tr><td>' + FIRM[w.firm].name + '</td><td>' + w.week_end + '</td><td>' + fix(w.m, 3) + '</td><td>' + fix(w.q, 4) + '</td><td>' + usd(w.dollars_moved) + '</td>'
      + cols.map(c => '<td>' + (w.value ? usd(v[c], true) : '-') + '</td>').join('')
      + '<td>' + (w.est_issuance ? usd(w.est_issuance, true) : '-') + '</td><td>' + usd(w.price, true) + '</td><td>' + usd(w.itm_flip, true) + '</td><td>'
      + usd(w.observed, true) + '</td><td>' + w.filing_urls.map(u => '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(fileName(u)) + '</a>').join(' ') + '</td></tr>';
  }
  document.getElementById('week-table').innerHTML = h + '</tbody>';
}

// ---- 5. method: notes and check ----
function method() {
  // Caveats grouped by kind, each group a short list (estimated figures first: they carry numbers a reader may reuse).
  const KIND = [['estimate', 'Estimated figures'], ['coverage', 'What is in, what is out, where data is missing'], ['convention', 'Conventions']];
  const li = n => '<li>' + esc(n.text) + (n.url ? ' <a href="' + esc(n.url) + '" target="_blank" rel="noopener">Release</a>.' : '') + '</li>';
  document.getElementById('notes').innerHTML = KIND.map(([k, label]) => {
    const ns = DATA.notes.filter(n => n.group === k);
    return ns.length ? '<li class="note-group"><h4>' + label + ' (' + ns.length + ')</h4><ul>' + ns.map(li).join('') + '</ul></li>' : '';
  }).join('');
  const c = DATA.check && typeof DATA.check === 'object' ? DATA.check : { status: 'not yet run' }, when = c.run_at || c.generated_at;
  const count = Array.isArray(c.checks) ? c.checks.length : 0;
  document.getElementById('check').innerHTML = '<div class="check-summary"><span class="check-status ' + (c.status === 'pass' ? 'passed' : '') + '">' + esc(c.status || 'see below') + '</span>'
    + '<div><strong>Data validation</strong><p>' + (count ? count + ' checks recorded' : 'No checks recorded')
    + (when ? ' · Run ' + esc(when) : '') + '</p></div></div>'
    + (Object.keys(c).length > 1 ? '<details class="fold check-detail"><summary>View full check record</summary><pre>' + esc(JSON.stringify(c, null, 1)) + '</pre></details>' : '');
  const through = DATA.headline.filter(h => h.break_even != null).map(h => h.week_end).sort()[0];
  document.getElementById('footer').textContent = 'Data through the week ending ' + through + '. Page built ' + DATA.generated_at + ' from the CSVs below.';
}

function draw() {
  drawPref('MSTR');
  drawPref('BMNR');
  drawPref('SBET');
  drawMap();
  drawBars('MSTR');
  drawBars('BMNR');
  drawBars('SBET');
}

function theme() {
  const btn = document.getElementById('theme'), root = document.documentElement;
  const dark = () => root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  const saved = localStorage.getItem('theme');
  if (saved) root.dataset.theme = saved;
  const label = () => {
    btn.textContent = dark() ? 'light theme' : 'dark theme';
    document.querySelector('meta[name="theme-color"]').content = dark() ? '#0d1015' : '#f7f8fa';
  };
  label();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', label);
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
  prefLegend();
  mapLegend();
  barsLegend();
  totals();
  table();
  method();
  draw();
  let lastW = innerWidth;
  addEventListener('resize', () => { if (innerWidth !== lastW) { lastW = innerWidth; draw(); } });
}).catch(e => {
  document.getElementById('headline-text').innerHTML = '<p>Could not load data.json: ' + esc(e.message) + '</p>';
});
