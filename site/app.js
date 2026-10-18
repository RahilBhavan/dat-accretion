'use strict';
// Hand-drawn inline SVG, no chart library. Charts render at the container's pixel width (viewBox = pixels) so text
// stays 11px on phones; they redraw on resize and on theme change.
// Graphics follow Tufte (The Visual Display of Quantitative Information): ink for data, gray for context, one accent
// for the comparison a caption names; compared panels share one scale; labels sit on the data; no boxes or shadows.

let DATA = null;
const ACTIVE = {};  // index of the column that holds a chart's one tab stop, per chart element id (kept across redraws)
// Firm hue and shape are used only where firms share an axis (the break-even map). Elsewhere a panel title names the firm.
const FIRM = {
  MSTR: { name: 'Strategy', color: '--f1', shape: 'circle' }, BMNR: { name: 'BitMine', color: '--f2', shape: 'square' },
  SBET: { name: 'SharpLink', color: '--f3', shape: 'triangle' },
};
// Bar categories: ink for common, the accent for preferred (the rotation's other leg), grays for coins and carry,
// hatched gray for the residual (it is not an action). The tooltip and table still list every category.
const CAT = {
  issue_common: ['Issue common', '--ink2'], buyback_common: ['Buy back common', '--ink2'], issue_pref: ['Issue preferred', '--accent'],
  retire_pref: ['Retire preferred', '--accent'], coins: ['Coin trades', '--gray1'], carry: ['Carry (dividends, interest, staking)', '--gray2'],
  residual: ['Residual', '--neutral'],
};
const GROUP = { common: ['Common', '--ink2'], pref: ['Preferred', '--accent'], coins: ['Coin trades', '--gray1'],
  carry: ['Carry (dividends, interest, staking)', '--gray2'], residual: ['Residual', '--neutral'] };
const EST = 'Estimated issuance (BitMine)';
const RESID_FILL = id => 'url(#' + id + ')';
// Hatches, one direction each everywhere (bars, legend, tooltip swatch, totals strip): residual "\", estimated issuance "/".
// In SVG's y-down space, rotate(45) turns the pattern's vertical line into "/" and rotate(-45) into "\".
function hatchPattern(id, color, angle) {
  return '<pattern id="' + id + '" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(' + angle + ')">'
    + '<rect width="5" height="5" style="fill:var(' + color + ');fill-opacity:0.2"/><line x1="0" y1="0" x2="0" y2="5" style="stroke:var(' + color + ');stroke-width:2"/></pattern>';
}
const RESID_SWATCH = '<rect x="1" y="1" width="12" height="12" style="fill:var(--neutral);fill-opacity:0.2"/><path d="M1,9 L5,13 M1,5 L9,13 M1,1 L13,13 M5,1 L13,9 M9,1 L13,5" style="stroke:var(--neutral);stroke-width:1.5"/>';
const EST_SWATCH = '<rect x="1" y="1" width="12" height="12" style="fill:var(--ink2);fill-opacity:0.2"/><path d="M1,9 L9,1 M5,13 L13,5" style="stroke:var(--ink2);stroke-width:2"/>';
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

function bps(x, signed) {
  if (x == null || isNaN(x)) return '-';
  return (x < 0 ? MINUS : signed && x > 0 ? '+' : '') + Math.abs(x).toFixed(Math.abs(x) < 10 ? 1 : 0) + ' bp';
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
  el.addEventListener('pointermove', ev => { const t = target(ev); if (t) showTip(wrap, html(t, ev.target), ...at(t, ev)); else hideTip(wrap); });
  el.addEventListener('pointerleave', () => hideTip(wrap));
  el.addEventListener('focusin', ev => { const t = target(ev); if (t) showTip(wrap, html(t, null), ...at(t)); });
  el.addEventListener('focusout', () => hideTip(wrap));
}

// Touch: a tap opens a column's or mark's details in the sheet instead of navigating; the sheet links to the filings.
// Mouse and keyboard follow the link directly. pick(ev) returns the link to describe (default: the one tapped);
// head(a) is the sheet's title, rows(a) its detail rows, urls(a) its filings.
function touchSheet(el, head, rows, urls, pick) {
  let touch = false;
  el.onpointerdown = ev => { touch = ev.pointerType === 'touch'; };
  el.onclick = ev => {
    if (!touch) return;
    const a = pick ? pick(ev) : ev.target.closest('a[data-tip]');
    if (ev.target.closest('a')) ev.preventDefault();
    if (!a) return;
    hideTip(el.parentElement);
    // urls(a): plain URLs, or [url, what it covers] pairs; each filing is listed once.
    const seen = new Set(), list = urls(a).map(u => Array.isArray(u) ? u : [u, '']).filter(([u]) => !seen.has(u) && seen.add(u));
    const links = list.map(([u, what]) => '<a href="' + esc(doc(u)) + '" target="_blank" rel="noopener">View filing' + (what ? ' for ' + esc(what) : '')
      + ' (' + esc(fileName(u)) + ')</a>').join('<br>');
    openSheet('<h4 id="sheet-title">' + head(a) + '</h4><div class="data-rows">' + rows(a) + links + '</div>', a);
  };
}
const whenLabel = w => (w.firm === 'SBET' ? 'filed date ' : 'week ending ') + w.week_end;
// doc(u): the restyled copy of a filing (site/filings/, dat/filings.py) when built, else the SEC URL itself.
const doc = u => (DATA && DATA.pages && DATA.pages[u]) || u;
const filingRow = urls => '<div>Filing: ' + urls.map(u => esc(fileName(u))).join(', ') + '</div>';

function markSvg(firm, cx, cy, r, cls, style) {
  if (FIRM[firm].shape === 'triangle') {  // equilateral, area of the circle of radius r
    const a = r * 2.694, h = a * 0.866, top = cy - h * 2 / 3;
    return '<path class="' + cls + '" d="M' + cx + ',' + top + 'L' + (cx + a / 2) + ',' + (top + h) + 'L' + (cx - a / 2) + ',' + (top + h) + 'Z" style="' + style + '"/>';
  }
  if (FIRM[firm].shape === 'circle') return '<circle class="' + cls + '" cx="' + cx + '" cy="' + cy + '" r="' + r + '" style="' + style + '"/>';
  const h = r * 0.886;  // square of equal area
  return '<rect class="' + cls + '" x="' + (cx - h) + '" y="' + (cy - h) + '" width="' + 2 * h + '" height="' + 2 * h + '" style="' + style + '"/>';
}

function swatch(inner) {
  return '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">' + inner + '</svg>';
}

// Days from an ISO date to today (UTC). The page is static, so staleness is computed when it is read.
function daysAgo(iso) {
  return Math.floor((Date.now() - Date.parse(iso + 'T00:00:00Z')) / 864e5);
}

// Readable date for page text ("Oct 4, 2026"); data and tooltips keep ISO dates.
function nice_date(iso) {
  return new Date(iso + 'T00:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
}
function short_date(iso) {
  return new Date(iso + 'T00:00:00Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
}

// ---- shared ruler: preferred close as a percent of break-even ----
// r = q / m × 100 (STRC or BMNP close over $100 × m). SharpLink has no preferred, so its q is 1: r = 100 / m.
// Strategy's rotation adds while r < 100; BitMine's while r > 100; SharpLink's buyback adds while r > 100 (m < 1).
function ratioPts(firm) {
  const sbet = firm === 'SBET';
  return DATA.weeks.filter(w => w.firm === firm && w.m != null && (sbet || w.q != null))
    .map(w => ({ w, t: Date.parse(w.week_end), r: (sbet ? 1 : w.q) / w.m * 100, close: sbet ? w.m : w.q * 100, be: sbet ? 1 : w.m * 100 }));
}
let RULER = null;  // one y domain and one x domain for the sparklines and the small multiples
function ruler() {
  const all = Object.keys(FIRM).flatMap(ratioPts), rs = all.map(p => p.r).concat(100);
  const lo = Math.floor(Math.min(...rs) / 10) * 10, hi = Math.ceil(Math.max(...rs) / 10) * 10;
  RULER = { lo, hi, t0: Math.min(...all.map(p => p.t)), t1: Math.max(...all.map(p => p.t)) };
}
const ADDS = { MSTR: ['below', 'Rotation adds below 100%'], BMNR: ['above', 'Rotation adds above 100%'], SBET: ['above', 'Buyback adds above 100% (m below 1)'] };

function spark(firm) {
  const pts = ratioPts(firm), W = 156, H = 32, P = 3, R = 34;  // R: room at the right for the 100% label (12px)
  const X = t => P + (t - RULER.t0) / (RULER.t1 - RULER.t0) * (W - R - P), Y = v => P + (RULER.hi - v) / (RULER.hi - RULER.lo) * (H - 2 * P);
  const l = pts[pts.length - 1], below = ADDS[firm][0] === 'below', y0 = below ? Y(100) : P, y1 = below ? H - P : Y(100);
  return '<svg class="spark" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" aria-hidden="true">'
    + '<rect class="band" x="' + P + '" y="' + y0.toFixed(1) + '" width="' + (W - R - P) + '" height="' + (y1 - y0).toFixed(1) + '"/>'
    + '<line class="ref" x1="' + P + '" x2="' + (W - R) + '" y1="' + Y(100) + '" y2="' + Y(100) + '"/>'
    + '<text x="' + (W - R + 4) + '" y="' + (Y(100) + 3.5) + '">100%</text>'
    + (firm === 'SBET' ? pts.slice(0, -1).map(p => '<circle cx="' + X(p.t) + '" cy="' + Y(p.r) + '" r="2"/>').join('') : '<path d="' + pts.map((p, i) => (i ? 'L' : 'M') + X(p.t).toFixed(1) + ',' + Y(p.r).toFixed(1)).join('') + '"/>')
    + '<circle cx="' + X(l.t).toFixed(1) + '" cy="' + Y(l.r).toFixed(1) + '" r="2.6"/></svg>';
}

// ---- 1. headline ----
// Meta line under the dek: what the figures cover, how old that is, where each number comes from. The definition
// ("Strategy's own net coins per share definition, applied to all three firms") is stated in the method section.
// Weekly firms file on Mondays for the week ending Sunday, so more than 9 days since the latest week means a missed refresh.
function asof() {
  const weekly = DATA.headline.filter(h => h.break_even != null);
  const through = weekly.map(h => h.week_end).sort()[0], age = daysAgo(through);
  let s = 'Data through <span class="num-m">' + nice_date(through) + '</span> (<span class="num-m">' + age + '</span> days ago) · '
    + 'Every figure links to its SEC filing (<a href="filings/index.html">all filings, restyled</a>) · <a href="#built">How this is built</a>';
  if (age > 9) s += ' <strong class="stale">Behind: filings after <span class="num-m">' + esc(through) + '</span> are not yet included.</strong>';
  document.getElementById('asof').innerHTML = s;
}

// Dek: the headline's answer in plain words, one sentence per firm, figures from data.json.
const TERMS = {
  rotation: ['Rotation', 'The pair of trades a firm repeats. Strategy sells common stock to buy back STRC, its preferred stock. BitMine sells BMNP, its preferred stock, to buy back common.'],
  breakeven: ['Break-even', '$100 × net mNAV. The two rotations run in opposite directions: Strategy\'s adds while STRC is below it, BitMine\'s while BMNP is above it.'],
  mnav: ['Net mNAV (m)', 'The share price divided by the coin value behind each share, net of debt and preferred. Above 1, new common sells for more than the coins it claims.'],
  sats: ['Sats', 'Coins per share for bitcoin are counted in sats: 1 sat = 0.00000001 BTC.'],
};
const term = (k, text) => '<button type="button" class="term" data-term="' + k + '" aria-controls="sheet" aria-expanded="false">' + text + '</button>';
function dek() {
  document.getElementById('dek').innerHTML =
    'These companies pair stock issuance with repurchases. A ' + term('rotation', 'rotation')
    + ' adds net coins per common share only on one side of its ' + term('breakeven', 'break-even')
    + ' price. The trade directions below explain why that side differs.';
}

// Break-even table: nine numbers, so a table (Tufte: tables beat graphics for small data), with a sparkline per row on
// the shared percent-of-break-even ruler.
// Percent of break-even. Within 2 points of 100, one decimal, so rounding never hides which side of the line a close is on.
const pct = r => (Math.abs(r - 100) < 2 ? r.toFixed(1) : r.toFixed(0)) + '%';

function headline() {
  asof();
  dek();
  // One row per firm. Desktop reads across (firm, three figures, condition with its sparkline); phones stack the same
  // elements, each figure carrying its own label.
  const fig = (lbl, v, cls) => '<p class="lr-fig' + (cls ? ' ' + cls : '') + '"><span class="lbl">' + lbl + '</span>' + v + '</p>';
  const rows = DATA.headline.map(h => {
    const sbet = h.break_even == null, r = sbet ? 100 / h.m : h.q / h.m * 100;
    const when = sbet ? short_date(h.week_end) + ', last filed (' + daysAgo(h.week_end) + ' days ago)'
      : 'close ' + short_date(h.price_date) + ' · m ' + h.m.toFixed(3);
    // The condition names the line the percent is read against, so 84% (below) or 124% (above) needs no legend.
    const cond = '<span>' + (sbet ? 'Buyback adds while m is <span class="side">below 1</span>, so while 1 ÷ m is above 100%'
      : esc(h.name) + (h.firm === 'MSTR' ? '\'s rotation adds bitcoin per share while ' : '\'s rotation adds ether per share while ') + esc(h.pref) + ' is <span class="side">' + ADDS[h.firm][0] + '</span> break-even (100%)') + '</span>';
    return '<article class="lr" aria-label="' + esc(h.name) + '"><div class="lr-name"><h3 class="lr-firm">' + esc(h.name) + (sbet ? '' : '<span class="tk">' + esc(h.pref) + '</span>') + '</h3>'
      + '<p class="lr-when">' + when + '</p></div>'
      // SharpLink has no preferred: one cell across the price columns instead of placeholder figures.
      + (sbet ? '<p class="lr-span">No preferred · m ' + h.m.toFixed(3) + ' · 1 ÷ m = ' + pct(r) + '</p>'
        : fig('Close', '$' + h.pref_close.toFixed(2)) + fig('Break-even', '$' + h.break_even.toFixed(2), 'be') + fig('Of break-even', pct(r), 'pct-col'))
      + '<p class="lr-trade">' + (sbet ? 'Common-share buyback; no preferred stock' : h.firm === 'MSTR' ? 'Sell common → retire preferred' : 'Issue preferred → buy back common') + '</p>'
      + '<p class="lr-cond">' + cond + spark(h.firm) + '</p></article>';
  }).join('');
  document.getElementById('headline-text').innerHTML = '<div class="ledger"><div class="ledger-head" aria-hidden="true"><span>Latest filed week</span>'
    + '<span style="text-align:right">Pref. close</span><span style="text-align:right">Break-even</span><span style="text-align:right">Of break-even</span></div>' + rows + '</div>'
    + '<p class="caption">Break-even = $100 × net mNAV. History: close ÷ break-even each week since June, on one shared scale; the shaded side is where each rotation adds. '
    + 'SharpLink has no preferred, so its dots show 1 ÷ m on filed dates only. BitMine uses estimated share counts between filings; see <a href="#method">estimated figures</a>.</p>';
  document.getElementById('counts').textContent = DATA.counts;
  example();
}

// "How this is built": live figures only (computed from data.json and the latest check record), so nothing goes stale.
function built() {
  const filings = new Set(DATA.weeks.flatMap(w => w.filing_urls)).size;
  const weeks = DATA.weeks.filter(w => w.firm !== 'SBET').length;
  const c = DATA.check || {}, checks = Array.isArray(c.checks) ? c.checks : [];
  const api = checks.find(x => /netSatsPerShare/.test(x.name)), pct = api && (api.compared.match(/([+-]\d+\.\d+)%/) || [])[1];
  // M16: a check run before the latest filed week says so, so a pass never vouches for weeks it did not see.
  const run = (c.run_at || '').slice(0, 10), latest = DATA.weeks.map(w => w.week_end).sort().pop();
  const runText = run && run < latest ? 'Last run ' + nice_date(run) + ', before the week ending ' + nice_date(latest) + '; the page deploys only on a pass.'
    : 'Run ' + esc(run) + '; the page deploys only on a pass.';
  const tiles = [[filings, 'SEC filings parsed', 'Every action row links to its filing.'],
    [weeks, 'firm-weeks rebuilt', 'Coin holdings rolled from each trade and reconciled to the filed total.'],
    ...(pct ? [[pct.replace('-', '−') + '%', 'from Strategy\'s published net sats per share', 'The rebuild of Strategy\'s own KPI, checked against its API.']] : []),
    [checks.filter(x => x.ok).length + ' of ' + checks.length, 'checks pass', runText]];
  document.getElementById('built-grid').innerHTML = tiles.map(([v, k, d]) =>
    '<div class="tile"><p class="tile-value">' + v + '</p><p class="tile-key">' + k + '</p><p class="tile-desc">' + d + '</p></div>').join('');
}

// ---- 1b. the mechanism first: a toy balance sheet, the rotation at one m, then the real filed trade ----
// Toy numbers are labeled on the figure. The real trade is too small to draw at true scale; the text says how small.
const TOY = { coins: 1000, cash: 90, pref: 300, paid: 90, retired: 100 };
function sheet(after) {
  const t = TOY, assets = after ? [['Coins', t.coins]] : [['Cash', t.cash], ['Coins', t.coins]];
  const pref = after ? t.pref - t.retired : t.pref, total = assets.reduce((a, x) => a + x[1], 0);
  const claims = [['Preferred', pref], ['Common', total - pref]];
  const W = 370, H = 236, top = 30, unit = 190 / (t.coins + t.cash), colW = 56, xs = [8, 160];
  let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc((after ? 'After' : 'Before') + ': assets '
    + assets.map(a => a[0] + ' ' + a[1]).join(', ') + '; preferred ' + pref + ', common ' + (total - pref)) + '">';
  s += '<text class="label" x="0" y="14">' + (after ? 'After: retire a $100 claim for $90' : 'Before') + '</text>';
  [[assets, 'Assets'], [claims, 'Claims']].forEach(([segs, title], c) => {
    let y = top + (t.coins + t.cash - total) * unit;  // same scale: a smaller total is a shorter column, bottoms aligned
    if (after && c === 0) s += '<rect class="gone" x="' + xs[0] + '" y="' + top + '" width="' + colW + '" height="' + (t.cash * unit).toFixed(1) + '"/>'
      + '<text x="' + (xs[0] + colW + 6) + '" y="' + (top + t.cash * unit / 2 + 4).toFixed(1) + '">cash −90</text>';
    segs.forEach(([name, v]) => {
      const h = v * unit, common = name === 'Common';
      s += '<rect class="' + (common ? 'seg-common' : 'seg') + '" x="' + xs[c] + '" y="' + y.toFixed(1) + '" width="' + colW + '" height="' + h.toFixed(1) + '"/>';
      s += '<text x="' + (xs[c] + colW + 6) + '" y="' + (y + h / 2 + 4).toFixed(1) + '"' + (common ? ' class="label"' : '') + '>' + name + ' ' + v.toLocaleString('en-US')
        + (after && common ? ' +10' : after && name === 'Preferred' ? ' −100' : '') + '</text>';
      y += h;
    });
    s += '<text x="' + (xs[c] + colW / 2) + '" y="' + (H - 4) + '" text-anchor="middle">' + title + '</text>';
  });
  s += '<line class="axis" x1="' + (xs[0] - 6) + '" x2="' + (W - 2) + '" y1="' + (top + 190) + '" y2="' + (top + 190) + '"/>';
  return s + '</svg>';
}

function example() {
  const x = DATA.example, M = v => '$' + (v / 1e6).toFixed(1) + 'M';
  const wk = DATA.weeks.find(w => w.firm === 'MSTR' && w.week_end === x.week_end), net = wk ? wk.n * wk.S * wk.p : null;
  const sg = v => (v < -0.5 ? MINUS : v > 0.5 ? '+' : '') + Math.abs(v).toFixed(0);
  // The rotation at m = 1.2: the toy trade ($90, q = 0.90) and break-even ($120 = $100 × m) are highlighted.
  const m = 1.2, raise = 120, rows = [90, 100, 110, 120, 130].map(P => {
    const sale = raise * (1 - 1 / m), retire = raise * 100 / P - raise;
    const note = P === 90 ? 'the toy trade: q = 0.90' : P === 120 ? 'break-even: $100 × m' : '';
    return '<tr' + (note ? ' class="hl"' : '') + '><td class="num">$' + P + '</td><td class="num">' + (raise * 100 / P).toFixed(0) + '</td><td class="num">' + sg(sale)
      + '</td><td class="num">' + sg(retire) + '</td><td class="num"><b>' + sg(sale + retire) + '</b></td><td>' + note + '</td></tr>';
  }).join('');
  const be = DATA.headline.find(h => h.firm === 'MSTR'), bm = DATA.headline.find(h => h.firm === 'BMNR');
  const fig = v => '<b>' + v + '</b>';
  document.getElementById('example').innerHTML =
    // Step 1: one claim, retired below its notional (toy numbers, assets and claims on one scale). q is defined here.
    '<div class="why-grid"><div class="prose"><p>Start with one share of preferred stock: a $100 claim that ranks ahead of common stock. If the company buys it back '
    + 'for $90, its claims fall by $100 while its cash falls by $90. The $10 difference now belongs to common holders. Paying $90 for a $100 claim '
    + 'is q = 0.90: q is the price paid per $1 of claim.</p></div>'
    + '<figure class="fig"><p class="fig-tag">Illustration, not filed figures</p><div class="pair">' + sheet(false) + sheet(true) + '</div>'
    + '<figcaption>Assets equal claims on both sides, drawn on one scale. Paying $90 removes a $100 claim, so the common block grows by $10.</figcaption></figure></div>'
    // Step 2: the rotation at one m, as a table, then as a balance. Common sells at m per $1 of net coins; STRC retires at q per $1 of claim.
    + '<div class="prose"><p>Strategy pays for these buybacks by selling common stock. At a net mNAV, m, of 1.2, buyers pay $1.20 for each $1 of net coins behind a '
    + 'share, so a $120 sale gives new holders $100 of net coins and leaves $20 with existing holders. The rotation adds coins per share as long as the '
    + 'retirement does not give back more than the sale made.</p></div>'
    + '<div class="rot-table"><p class="fig-tag">Illustration: the rotation at m = 1.2</p><div class="scroll-x"><table class="plain-num">'
    + '<thead><tr><th class="num">STRC price</th><th class="num">Notional retired</th><th class="num">Sale of common</th><th class="num">Retirement</th><th class="num">Rotation, to common</th><th></th></tr></thead><tbody>'
    + rows + '</tbody></table></div><p class="caption">Raise $120 by selling common, spend it retiring STRC. Dollars to existing common holders, first order; '
    + 'the rotation is the sale plus the retirement. At $120, which is $100 × m, the rotation is zero: break-even. Illustration, not filed figures.</p></div>'
    + '<div class="prose"><p>Weigh m against q: the beam is level at a STRC price of $100 × m.</p></div>'
    + '<div class="balance-slot" id="balance"></div>'
    + '<p class="balance-read">Latest filed week, net mNAV ' + fig(be.m.toFixed(3)) + ': Strategy\'s rotation adds while STRC trades below ' + fig('$' + be.break_even.toFixed(2))
    + '; it closed at ' + fig('$' + be.pref_close.toFixed(2)) + '.</p>'
    // Step 3: the filed trade, with its figures and its filing.
    + '<div class="prose"><p>Dollars to common ÷ (coin price × shares) is the change in coins per share.</p></div>'
    + '<div class="filed"><p class="fig-tag">The filed trade · week ending ' + nice_date(x.week_end) + '</p><ul class="filed-figs">'
    + '<li><b>' + M(x.usd) + '</b>paid for STRC</li><li><b>$' + x.avg_price.toFixed(2) + '</b>per $100 share (q = ' + x.q.toFixed(4) + ')</li>'
    + '<li><b>' + M(x.notional) + '</b>of claims removed</li><li><b>+' + M(x.adds_usd) + '</b>to common, +' + x.sats_per_share.toFixed(2) + ' sats per share</li></ul>'
    + '<div class="prose"><p>Common holders gained ' + M(x.adds_usd) + ', or +' + x.sats_per_share.toFixed(2)
    + ' sats across ' + x.shares.toLocaleString('en-US') + ' fully diluted shares (exact recompute).'
    + (net ? ' That is ' + (x.adds_usd / net * 100).toFixed(3) + '% of Strategy\'s net coin value that week (' + usd(net) + '), below one pixel at true scale, '
      + 'which is why the figures above use toy numbers.' : '')
    + ' Source: <a href="' + esc(doc(x.filing_url)) + '" target="_blank" rel="noopener">Strategy 8-K for the week ending ' + esc(x.week_end) + '</a>. Every bar and mark below is built the same way.</p>'
    + '<p>BitMine runs the rotation the other way (sell BMNP, buy back common). In the latest filed week, net mNAV ' + bm.m.toFixed(3) + ', BitMine\'s rotation adds while BMNP trades above $'
    + bm.break_even.toFixed(2) + '; it closed at $' + bm.pref_close.toFixed(2) + '.</p></div></div>';
  // The balance (site/balance.js, built by site-src/balance/build.mjs) starts at the toy trade: m = 1.2, STRC $90 (q = 0.90).
  // It offers the latest filed week.
  if (window.Balance) window.Balance.mount(document.getElementById('balance'), { m: 1.2, price: 90,
    today: { m: +be.m.toFixed(3), price: be.pref_close, label: 'm ' + be.m.toFixed(3) + ', STRC $' + be.pref_close.toFixed(2) + ', week ending ' + short_date(be.week_end) } });
  else document.getElementById('balance').remove();
}

// ---- 2. small multiples: preferred close as a percent of break-even, one shared scale ----
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
  const pts = ratioPts(firm);
  const W = el.clientWidth || 360, H = 200, M = { l: 40, r: 10, t: 22, b: 26 };
  const X = t => M.l + (t - RULER.t0) / (RULER.t1 - RULER.t0 || 1) * (W - M.l - M.r), Y = v => M.t + (RULER.hi - v) / (RULER.hi - RULER.lo) * (H - M.t - M.b);
  const label = sbet ? '1 ÷ m' : h.pref + ' close ÷ break-even';
  let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="' + esc(FIRM[firm].name + ': ' + label + ' by '
    + (sbet ? 'filed date' : 'week') + ', percent. Left and Right arrow keys move between ' + (sbet ? 'dates.' : 'weeks.')) + '">';
  // Range frame on y: the shared domain's ends and 100%, nothing else.
  s += '<line class="axis" x1="' + (M.l - 8) + '" x2="' + (M.l - 8) + '" y1="' + Y(RULER.hi) + '" y2="' + Y(RULER.lo) + '"/>';
  for (const v of [RULER.lo, 100, RULER.hi]) s += '<text x="' + (M.l - 12) + '" y="' + (Y(v) + 4) + '" text-anchor="end">' + v + '%</text>';
  const below0 = ADDS[firm][0] === 'below', b0 = below0 ? Y(100) : Y(RULER.hi), b1 = below0 ? Y(RULER.lo) : Y(100);
  s += '<rect class="band" x="' + M.l + '" y="' + b0 + '" width="' + (W - M.l - M.r) + '" height="' + (b1 - b0) + '"/>';
  s += '<line class="ref" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + Y(100) + '" y2="' + Y(100) + '"/>';
  // Keep the direction in HTML above the plot, outside the observations' drawing area.
  s += '<text x="' + (M.l + 4) + '" y="' + (Y(100) - 6) + '">break-even</text>';
  document.getElementById('reading-' + firm).textContent =
    (sbet ? '1 ÷ net mNAV, as a percent. Filed dates only; no values between points. ' : 'Preferred close ÷ break-even, as a percent. ')
    + ADDS[firm][1] + '. Shading marks that side.';
  // Columns: each point owns the span halfway to its neighbours, and links to its filing (M9).
  const mid = i => i < 0 ? M.l : i >= pts.length - 1 ? W - M.r : (X(pts[i].t) + X(pts[i + 1].t)) / 2;
  const active = ACTIVE[el.id] = Math.min(ACTIVE[el.id] ?? pts.length - 1, pts.length - 1);
  pts.forEach((p, i) => {
    const x0 = Math.min(mid(i - 1), X(p.t) - 6), x1 = Math.max(mid(i), X(p.t) + 6);
    s += '<a class="col" href="' + esc(doc(p.w.filing_urls[0])) + '" target="_blank" rel="noopener" tabindex="' + (i === active ? 0 : -1) + '" data-tip="' + i + '" aria-label="'
      + esc(FIRM[firm].name + ' ' + whenLabel(p.w) + ': ' + label + ' ' + p.r.toFixed(1) + '%. Opens filing.') + '">'
      + '<rect class="hit" x="' + x0 + '" y="' + M.t + '" width="' + Math.max(1, x1 - x0) + '" height="' + (H - M.t - M.b) + '"/></a>';
  });
  s += '<text x="' + M.l + '" y="' + (H - 6) + '">' + short_date(new Date(RULER.t0).toISOString().slice(0, 10)) + '</text>';
  s += '<text x="' + (W - M.r) + '" y="' + (H - 6) + '" text-anchor="end">' + short_date(new Date(RULER.t1).toISOString().slice(0, 10)) + '</text>';
  if (!sbet) s += '<path class="data" d="' + pts.map((p, i) => (i ? 'L' : 'M') + X(p.t).toFixed(1) + ',' + Y(p.r).toFixed(1)).join('') + '"/>';
  if (sbet) s += pts.slice(0, -1).map(p => '<circle class="pt" cx="' + X(p.t) + '" cy="' + Y(p.r) + '" r="2.5"/>').join('');
  const l = pts[pts.length - 1];
  s += '<circle class="last" cx="' + X(l.t) + '" cy="' + Y(l.r) + '" r="4"/>';
  const room = X(l.t) < W - M.r - 40;  // SharpLink's last filed date is mid-range: label to the right of the dot
  // The end label goes on the side the line does not come from, so the line never runs through it.
  const prev = pts[pts.length - 2], over = prev ? prev.r <= l.r : l.r > 100;
  s += '<text class="label" x="' + (X(l.t) + (room ? 8 : -7)) + '" y="' + (room ? Y(l.r) + 4 : Y(l.r) + (over ? -9 : 17)) + '" text-anchor="' + (room ? 'start' : 'end') + '">' + pct(l.r) + '</text>';
  el.innerHTML = s + '</svg>';
  const rows = t => {
    const p = pts[+t.dataset.tip], g = p.close - p.be;
    const gap = sbet ? Math.abs(g).toFixed(3) + (g < 0 ? ' below 1' : ' above 1') : '$' + Math.abs(g).toFixed(2) + (g < 0 ? ' below' : ' above');
    return '<div class="row"><span>' + (sbet ? 'm (net mNAV)' : esc(h.pref) + ' close') + '</span><span>' + (sbet ? p.close.toFixed(3) : '$' + p.close.toFixed(2)) + '</span></div>'
      + '<div class="row"><span>Break-even' + (sbet ? '' : ' (100 × m)') + '</span><span>' + (sbet ? '1' : '$' + p.be.toFixed(2)) + '</span></div>'
      + '<div class="row"><span>' + (sbet ? '1 ÷ m' : 'Close ÷ break-even') + '</span><span>' + p.r.toFixed(1) + '%</span></div>'
      + '<div class="row on"><span>Gap</span><span>' + gap + '</span></div>';
  };
  const w = t => pts[+t.dataset.tip].w;
  bindTips(el, t => '<b>' + FIRM[firm].name + '</b>, ' + whenLabel(w(t)) + rows(t) + filingRow(w(t).filing_urls));
  touchSheet(el, t => FIRM[firm].name + ', ' + whenLabel(w(t)), rows, t => w(t).filing_urls);
  colKeys(el);
  const n = new Set(pts.flatMap(p => p.w.filing_urls)).size;
  document.getElementById('src-' + firm).innerHTML = (sbet ? 'Last: m ' + l.close.toFixed(3) : 'Last: ' + esc(h.pref) + ' $' + l.close.toFixed(2) + ', break-even $' + l.be.toFixed(2))
    + '. ' + n + (sbet ? ' SEC filings; no observations between filed dates.' : ' SEC filings; closes from Yahoo Finance.');
}

// ---- 3. break-even map ----
function mapPoints() {
  // qx: map x. SharpLink has no preferred (q null); its marks sit at q = 1, where m = q is m = 1.
  return DATA.weeks.filter(w => w.m != null && (w.q != null || w.firm === 'SBET')).map(w => ({ ...w, qx: w.q ?? 1 }));
}

function drawMap() {
  const el = document.getElementById('map');
  const pts = mapPoints();
  const W = el.clientWidth || 640, M = { l: 48, r: 14, t: 12, b: 40 };
  const H = W - M.l - M.r + M.t + M.b;  // a square plot: one range on both axes makes m = q a true 45° line (M7)
  const vals = pts.flatMap(w => [w.m, w.qx]);
  // One domain for both axes so m = q is a true diagonal: [min − 0.05, max + 0.05] rounded out to 0.05.
  const lo = Math.floor((Math.min(...vals) - 0.05) * 20) / 20, hi = Math.ceil((Math.max(...vals) + 0.05) * 20) / 20;
  const X = v => M.l + (v - lo) / (hi - lo) * (W - M.l - M.r), Y = v => H - M.b - (v - lo) / (hi - lo) * (H - M.t - M.b);
  // One mark size: position carries m and q; dollars moved are in the tooltip (area is read least accurately,
  // Cleveland & McGill 1984). Each firm's weeks are joined in date order; its latest mark is solid.
  const R = W < 500 ? 4 : 5, rad = () => R;
  const latest = {};
  pts.forEach((w, i) => { if (!(w.firm in latest) || w.week_end > pts[latest[w.firm]].week_end) latest[w.firm] = i; });
  let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="Break-even map: net mNAV against preferred price over notional, one mark per firm-week">';
  // Range frames: each axis line spans only the data's own range, labeled at its ends and at 1.00.
  const qs = pts.map(w => w.qx), ms = pts.map(w => w.m), qlo = Math.min(...qs), qhi = Math.max(...qs), mlo = Math.min(...ms), mhi = Math.max(...ms);
  s += '<line class="axis" x1="' + X(qlo) + '" x2="' + X(qhi) + '" y1="' + (H - M.b + 6) + '" y2="' + (H - M.b + 6) + '"/>';
  s += '<line class="axis" x1="' + (M.l - 6) + '" x2="' + (M.l - 6) + '" y1="' + Y(mhi) + '" y2="' + Y(mlo) + '"/>';
  for (const v of [qlo, qhi]) s += '<text x="' + X(v) + '" y="' + (H - M.b + 20) + '" text-anchor="middle">' + v.toFixed(2) + '</text>';
  for (const v of [mlo, 1, mhi]) s += '<text x="' + (M.l - 10) + '" y="' + (Y(v) + 4) + '" text-anchor="end">' + v.toFixed(2) + '</text>';
  s += '<text x="' + (W - M.r) + '" y="' + (H - 4) + '" text-anchor="end">q = preferred close / $100 notional →</text>';
  s += '<text x="' + M.l + '" y="' + (M.t + 4) + '">↑ m = net mNAV</text>';
  s += '<line class="ref" x1="' + X(lo) + '" y1="' + Y(lo) + '" x2="' + X(hi) + '" y2="' + Y(hi) + '"/>';
  // A narrow plot takes it on three short lines, right-aligned just left of the diagonal: the marks sit at low q, so that corner is empty.
  const diagX = y => X(mhi - (y - Y(mhi)) / (Y(mlo) - Y(mhi)) * (mhi - mlo)), sx = Math.min(W - M.r, diagX(M.t + 50) - 10);
  s += W < 500 || 36 * 7.2 > W - M.l - M.r - 8
    ? ['Strategy\'s', 'rotation adds', 'here (m &gt; q)'].map((t, k) => '<text class="label" x="' + sx + '" y="' + (M.t + 22 + 14 * k) + '" text-anchor="end">' + t + '</text>').join('')
    : '<text class="label" x="' + (M.l + 8) + '" y="' + (M.t + 22) + '">Strategy\'s rotation adds here (m &gt; q)</text>';
  // BitMine's region label sits at the right edge, a third of the way up, clear of the marks near q = 1 (SharpLink's sit low there).
  const by = Y(lo + (hi - lo) * 0.3);
  s += W < 500
    ? '<text class="label" x="' + (W - M.r) + '" y="' + by + '" text-anchor="end">BitMine\'s rotation</text><text class="label" x="' + (W - M.r) + '" y="' + (by + 14) + '" text-anchor="end">adds here (m &lt; q)</text>'
    : '<text class="label" x="' + (W - M.r) + '" y="' + by + '" text-anchor="end">BitMine\'s rotation adds here (m &lt; q)</text>';
  if (W >= 500) s += '<text x="' + (X(hi) - 40) + '" y="' + (Y(hi) + 6) + '" text-anchor="end">m = q</text>';
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
    s += '<a href="' + esc(doc(w.filing_urls[0])) + '" target="_blank" rel="noopener" data-tip="' + i + '" aria-label="' + esc(label) + '">'
      + markSvg(w.firm, cx, cy, Math.max(r, 12), 'hit', 'fill:transparent')
      + markSvg(w.firm, cx, cy, last ? r + 1.5 : r, 'mark', 'fill:' + (last ? c : 'var(--bg)') + ';stroke:' + c + ';stroke-width:1.25') + '</a>';
  }
  // Direct label on each firm's latest week: right, left, above, below at growing distance; the first box that stays
  // inside the plot and hits no mark or placed label wins. Box width is estimated at 7.2px per character (12px monospace).
  const boxes = pts.map(w => { const r = rad(w); return [X(w.qx) - r, Y(w.m) - r, X(w.qx) + r, Y(w.m) + r]; });
  const hit = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
  for (const firm of Object.keys(FIRM)) {
    const i = latest[firm];
    if (i == null) continue;
    const w = pts[i], cx = X(w.qx), cy = Y(w.m), r = rad(w), text = FIRM[firm].name + ' ' + short_date(w.week_end), tw = text.length * 7.2;
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
  // Marks that overlap (SharpLink's 6/28 and 6/30 sit about a pixel apart) share one tooltip and one sheet that list both.
  const near = i => pts.map((w, j) => j).filter(j => j === i || Math.hypot(X(pts[j].qx) - X(pts[i].qx), Y(pts[j].m) - Y(pts[i].m)) < 2 * R + 2)
    .sort((a, b) => a === i ? -1 : b === i ? 1 : pts[a].week_end < pts[b].week_end ? -1 : 1);
  const one = w => '<div class="row"><span>m (net mNAV)</span><span>' + fix(w.m, 3) + '</span></div>'
      + '<div class="row"><span>q (preferred / notional)</span><span>' + (w.q == null ? 'no preferred, plotted at 1' : fix(w.q, 4)) + '</span></div>'
      + '<div class="row"><span>Dollars moved</span><span>' + usd(w.dollars_moved) + '</span></div>'
      + '<div class="row"><span>Value to common of actions</span><span>' + (w.actions_value == null ? 'anchor week' : usd(w.actions_value, true)) + '</span></div>';
  const ids = t => near(+t.dataset.tip);
  bindTips(el, t => ids(t).map((j, k) => (k ? '<div class="also">' : '<div>') + '<b>' + FIRM[pts[j].firm].name + '</b>, ' + whenLabel(pts[j])
    + one(pts[j]) + filingRow(pts[j].filing_urls) + '</div>').join(''));
  const first = t => pts[+t.dataset.tip];
  touchSheet(el, t => FIRM[first(t).firm].name + ', ' + whenLabel(first(t)) + (ids(t).length > 1 ? ', and ' + (ids(t).length - 1) + ' more at the same spot' : ''),
    t => ids(t).map((j, k) => (k ? '<div class="also"><b>' + whenLabel(pts[j]) + '</b>' : '<div>') + one(pts[j]) + '</div>').join(''),
    t => ids(t).flatMap(j => pts[j].filing_urls.map(u => [u, whenLabel(pts[j])])),
    // A tap goes to the nearest mark within 22px, whatever sits on top.
    ev => {
      const svg = el.querySelector('svg'), b = svg.getBoundingClientRect(), k = W / b.width;
      const px = (ev.clientX - b.left) * k, py = (ev.clientY - b.top) * k;
      let best = -1, dist = 22 * k;
      pts.forEach((w, i) => { const d = Math.hypot(X(w.qx) - px, Y(w.m) - py); if (d <= dist) { dist = d; best = i; } });
      return best < 0 ? null : el.querySelector('a[data-tip="' + best + '"]');
    });
}

// The h2 says what the map shows; the standfirst under it carries the latest m and q (M18).
function mapTitle() {
  const h = Object.fromEntries(DATA.headline.map(x => [x.firm, x])), a = h.MSTR, b = h.BMNR;
  document.getElementById('map-standfirst').textContent = 'Week ending ' + nice_date(a.week_end) + ': Strategy at m ' + a.m.toFixed(3) + ', q ' + a.q.toFixed(3)
    + '; BitMine at m ' + b.m.toFixed(3) + ', q ' + b.q.toFixed(3) + '. Select a mark to open its filing.';
}

function mapLegend() {
  mapTitle();
  document.getElementById('map-legend').innerHTML = Object.entries(FIRM).map(([f, v]) =>
    '<span>' + swatch(markSvg(f, 7, 7, 5, '', 'fill:var(' + v.color + ');stroke:var(' + v.color + ')')) + v.name
    + (f === 'SBET' ? ' (no preferred: at q = 1)' : '') + '</span>').join('')
    + '<span>' + swatch('<line x1="1" y1="13" x2="13" y2="1" style="stroke:var(--fg);stroke-dasharray:3 2"/>') + 'm = q</span>'
    + '<span>Open marks: earlier weeks, joined in date order. Solid: latest.</span>';
}

// ---- 4. attribution bars: one shared scale in basis points of net coin value ----
// bp = value to common ÷ (n × S × p) × 10,000, using that week's n, S and p: the week's change in n as a fraction of n.
// Firms of very different size then sit on one ruler; dollars stay in the tooltip, table and totals.
const toBp = w => 1e4 / (w.n * w.S * w.p);
function stack(w) {
  // [key, label, color var, value $, hatched]; issue_common splits into filed and estimated parts.
  const v = w.value, est = w.est_issuance || 0;
  const out = [['issue_common', CAT.issue_common[0], '--ink2', v.issue_common - est, false]];
  if (est) out.push(['est_issuance', EST, '--ink2', est, true]);
  for (const k of Object.keys(CAT).slice(1)) out.push([k, CAT[k][0], CAT[k][1], v[k], false]);
  return out.filter(d => Math.abs(d[3]) >= 0.005);
}
let BARS = null;  // shared y domain across the three firms, in bp, and the shared time axis
function barDomain() {
  let lo = 0, hi = 0;
  const weeks = DATA.weeks.filter(w => w.value);
  for (const w of weeks) {
    const st = stack(w), k = toBp(w);
    hi = Math.max(hi, st.reduce((a, d) => a + Math.max(d[3], 0), 0) * k);
    lo = Math.min(lo, st.reduce((a, d) => a + Math.min(d[3], 0), 0) * k);
  }
  // The data's range plus 5% on each side that has data, zero always inside (bars start at zero); ticks outside are dropped.
  const pad = (hi - lo || 1) * 0.05, dlo = lo < 0 ? lo - pad : 0, dhi = hi > 0 ? hi + pad : 0;
  const ticks = nice(dlo, dhi, 4).filter(t => t >= dlo - 1e-9 && t <= dhi + 1e-9);
  // x: the same dates as the panels above (the ruler's span), widened only if a bar falls outside it.
  const ts = weeks.map(w => Date.parse(w.week_end));
  BARS = { lo: dlo, hi: dhi, ticks, t0: Math.min(RULER.t0, ...ts), t1: Math.max(RULER.t1, ...ts) };
}

function segPath(x, y0, y1, w) {
  const top = Math.min(y0, y1), h = Math.abs(y1 - y0);
  return 'M' + x + ',' + top + 'h' + w + 'v' + h + 'h' + (-w) + 'Z';
}

// Rows under 0.05 bp round to zero, so the tooltip leaves them out; the table keeps every cause.
const TINY_BP = 0.05;
function weekRows(w, on) {
  const k = toBp(w), big = v => Math.abs(v * k) >= TINY_BP;
  const rows = stack(w).filter(d => big(d[3]) || d[0] === on).map(d => '<div class="row' + (d[0] === on ? ' on' : '') + '"><span><i class="sw'
    + (d[0] === 'residual' ? ' resid' : d[4] ? ' est' : '') + '" style="background:var(' + d[2] + ')'
    + '"></i>' + d[1] + '</span><span>' + bps(d[3] * k, true) + ' · ' + usd(d[3], true) + '</span></div>').join('');
  return rows
    + (big(w.price) ? '<div class="row"><span>Coin price (not stacked)</span><span>' + bps(w.price * k, true) + ' · ' + usd(w.price, true) + '</span></div>' : '')
    + (big(w.itm_flip) ? '<div class="row"><span>In-the-money flips (not stacked)</span><span>' + bps(w.itm_flip * k, true) + ' · ' + usd(w.itm_flip, true) + '</span></div>' : '')
    + '<div class="row on"><span>Observed change</span><span>' + bps(w.observed * k, true) + ' · ' + usd(w.observed, true) + '</span></div>';
}
function weekTip(w, on) {
  return '<b>' + FIRM[w.firm].name + '</b>, ' + whenLabel(w) + weekRows(w, on) + filingRow(w.filing_urls);
}

function drawBars(firm) {
  const el = document.getElementById('bars-' + firm);
  const weeks = DATA.weeks.filter(w => w.firm === firm && w.value);
  const W = el.clientWidth || 640, H = W < 500 ? 220 : 250, M = { l: 52, r: 8, t: 16, b: 28 };
  const { lo, hi, ticks, t0, t1 } = BARS;
  const Y = v => M.t + (hi - v) / (hi - lo) * (H - M.t - M.b);
  // Bars sit on the real time axis, shared by the three firms (M24): a full week is 62% of seven days wide; rows a few
  // days apart (quarter ends, SharpLink's filed dates) become narrow neighbours that do not overlap.
  const day = 864e5, plotW = W - M.l - M.r, full0 = 7 * 0.62 * plotW / ((t1 - t0) / day + 7);
  const X = t => M.l + full0 / 2 + (t - t0) / (t1 - t0 || 1) * (plotW - full0);
  const pxDay = (plotW - full0) / ((t1 - t0) / day || 1), full = Math.min(36, Math.max(3, 7 * 0.62 * pxDay));
  const xs = weeks.map(w => X(Date.parse(w.week_end)));
  const widths = xs.map((x, i) => {
    const gap = Math.min(i ? x - xs[i - 1] : Infinity, i < xs.length - 1 ? xs[i + 1] - x : Infinity);
    return Math.max(2, Math.min(full, gap * 0.8));
  });
  const hatch = 'hatch-' + firm, resid = 'resid-' + firm;
  let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="' + FIRM[firm].name
    + ': weekly change in net coins per share by cause, basis points, by date. Left and Right arrow keys move between weeks; each opens its filing.">'
    + '<defs>' + hatchPattern(hatch, '--ink2', 45) + hatchPattern(resid, '--neutral', -45) + '</defs>';
  for (const t of ticks) {  // labels only; the zero line is the one rule
    s += '<text x="' + (M.l - 8) + '" y="' + (Y(t) + 4) + '" text-anchor="end">' + (t > 0 ? '+' : t < 0 ? MINUS : '') + Math.abs(t) + (t ? '' : ' bp') + '</text>';
    if (t) s += '<line class="tick" x1="' + (M.l - 4) + '" x2="' + M.l + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/>';
  }
  // Time axis: a tick and a label at each month start inside the span.
  const d0 = new Date(t0);
  for (let mth = new Date(Date.UTC(d0.getUTCFullYear(), d0.getUTCMonth() + (d0.getUTCDate() > 1 ? 1 : 0), 1)); +mth <= t1; mth.setUTCMonth(mth.getUTCMonth() + 1)) {
    const x = X(+mth);
    s += '<line class="tick" x1="' + x + '" x2="' + x + '" y1="' + (H - M.b + 2) + '" y2="' + (H - M.b + 6) + '"/>'
      + '<text x="' + x + '" y="' + (H - M.b + 19) + '" text-anchor="middle">' + mth.toLocaleDateString('en-US', { month: 'short', timeZone: 'UTC' }) + '</text>';
  }
  const active = ACTIVE[el.id] = Math.min(ACTIVE[el.id] ?? weeks.length - 1, weeks.length - 1);
  const mid = i => i < 0 ? M.l : i >= xs.length - 1 ? W - M.r : (xs[i] + xs[i + 1]) / 2;
  let big = null;
  weeks.forEach((w, i) => {
    const bw = widths[i], x = xs[i] - bw / 2, st = stack(w), k = toBp(w);
    const c0 = Math.min(mid(i - 1), x - 3), c1 = Math.max(mid(i), x + bw + 3);
    // Each week is one link to its filing (M9): a transparent hit column with the week's segments inside it.
    s += '<a class="col" href="' + esc(doc(w.filing_urls[0])) + '" target="_blank" rel="noopener" tabindex="' + (i === active ? 0 : -1) + '" data-tip="' + i + '" aria-label="'
      + esc(FIRM[firm].name + ' ' + whenLabel(w) + ': observed ' + bps(w.observed * k, true) + ', ' + usd(w.observed, true) + '. Opens filing.') + '">'
      + '<rect class="hit" x="' + c0 + '" y="' + M.t + '" width="' + (c1 - c0) + '" height="' + (H - M.t - M.b) + '"/>';
    let up = 0, dn = 0;
    st.forEach(d => {
      const v = d[3] * k, a = v > 0 ? up : dn, b = a + v;
      if (v > 0) up = b; else dn = b;
      const fill = d[0] === 'residual' ? RESID_FILL(resid) : d[4] ? 'url(#' + hatch + ')' : 'var(' + d[2] + ')';
      s += '<path class="seg' + (bw < 8 ? ' thin' : '') + '" data-cat="' + d[0] + '" d="' + segPath(x, Y(a), Y(b), bw) + '" style="fill:' + fill + '"/>';
      if (!big || Math.abs(v) > Math.abs(big.v)) big = { v, label: d[1], x, w: bw, y: v < 0 ? Math.max(Y(a), Y(b)) - 4 : Math.min(Y(a), Y(b)) + 12, week: w.week_end };
    });
    if (st.length) s += '<line class="net" x1="' + (x - 3) + '" x2="' + (x + bw + 3) + '" y1="' + Y(up + dn) + '" y2="' + Y(up + dn) + '"/>';
    s += '</a>';
  });
  s += '<line class="zero" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>';
  if (big) {  // the one direct label: largest segment in this chart, beside its bar at the segment's far end (clear of shorter neighbours)
    const narrow = W < 500, right = big.x < W * 0.6, x = narrow ? M.l + 4 : right ? big.x + big.w + 6 : big.x - 6;
    const tail = big.label + ' ' + bps(big.v, true), long = 'Largest: ' + short_date(big.week) + ' ' + tail;
    const mid2 = short_date(big.week) + ' ' + tail, fits = t => t.length * 7.2 <= W - x;
    const text = narrow ? (fits(long) ? long : fits(mid2) ? mid2 : tail) : tail;
    s += '<text class="label" x="' + x + '" y="' + (narrow ? M.t + 4 : big.y + 4) + '" text-anchor="' + (narrow || right ? 'start' : 'end') + '">' + esc(text) + '</text>';
  }
  el.innerHTML = s + '</svg>';
  const w = t => weeks[+t.dataset.tip];
  bindTips(el, (t, src) => weekTip(w(t), src && src.dataset ? src.dataset.cat : null));
  touchSheet(el, t => FIRM[firm].name + ', ' + whenLabel(w(t)), t => weekRows(w(t)), t => w(t).filing_urls);
  colKeys(el);
}

function barsLegend() {
  const items = Object.entries(GROUP).map(([k, [label, c]]) => k === 'residual'
    ? swatch(RESID_SWATCH) + 'Residual: change the filings leave unexplained'
    : swatch('<rect x="1" y="1" width="12" height="12" style="fill:var(' + c + ')"/>') + label);
  items.splice(1, 0, swatch(EST_SWATCH) + EST + ', part of common');
  items.push(swatch('<line x1="1" y1="7" x2="13" y2="7" style="stroke:var(--fg);stroke-width:2"/>') + 'Net of the stacked causes');
  document.getElementById('bars-legend').innerHTML = items.map(x => '<span>' + x + '</span>').join('');
}

// Under each firm's bars: a sentence on the residual, then a diverging strip of the totals since the first week, by
// cause, in dollars. Grays, the residual hatched, the observed total in ink.
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
    const rows = [['Filed actions', x.actions, 'var(--ink2)'], ...(x.est_issuance ? [['Estimated issuance', x.est_issuance, 'est']] : []),
      ['Carry', x.carry, 'var(--gray2)'], ['Residual', x.residual, 'resid'], ['Coin price', x.price, 'var(--gray1)'],
      ['In-the-money flips', x.itm_flip, 'var(--gray1)'], ['Observed', x.observed, 'var(--fg)']];
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
      '<div class="strip"><p class="strip-title">Since ' + esc(x.since) + ', value to common by cause, USD; scale: this firm only</p>'
      + '<p class="strip-note">' + esc(residualSentence(firm, x)) + '</p>' + html + '</div>');
  }
}

// One unit per column: dollars in millions, one decimal; basis points in their own column.
function usdM(x, signed) {
  if (x == null || isNaN(x)) return '-';
  const t = Math.abs(x / 1e6).toFixed(1);
  return (t === '0.0' ? '' : x < 0 ? MINUS : signed ? '+' : '') + t;
}
function table() {
  const cols = DATA.categories;
  let h = '<thead><tr><th>firm</th><th>week ending (SharpLink: filed date)</th><th>m</th><th>q</th><th>dollars moved ($M)</th>'
    + cols.map(c => '<th>' + CAT[c][0].toLowerCase() + ' ($M)</th>').join('')
    + '<th>of which estimated issuance ($M)</th><th>coin price ($M)</th><th>in-the-money flips ($M)</th><th>observed ($M)</th><th>observed (bp of net value)</th><th>filing</th></tr></thead><tbody>';
  for (const w of DATA.weeks) {
    const v = w.value || {};
    h += '<tr><td>' + FIRM[w.firm].name + '</td><td>' + w.week_end + '</td><td>' + fix(w.m, 3) + '</td><td>' + fix(w.q, 4) + '</td><td>' + usdM(w.dollars_moved) + '</td>'
      + cols.map(c => '<td>' + (w.value ? usdM(v[c], true) : '-') + '</td>').join('')
      + '<td>' + (w.est_issuance ? usdM(w.est_issuance, true) : '-') + '</td><td>' + usdM(w.price, true) + '</td><td>' + usdM(w.itm_flip, true) + '</td><td>'
      + usdM(w.observed, true) + '</td><td>' + (w.observed == null ? '-' : bps(w.observed * toBp(w), true)) + '</td><td>'
      + w.filing_urls.map(u => '<a href="' + esc(doc(u)) + '" target="_blank" rel="noopener">' + esc(fileName(u)) + '</a>').join(' ') + '</td></tr>';
  }
  document.getElementById('week-table').innerHTML = h + '</tbody>';
}

// ---- 5. method: notes and check ----
function method() {
  // Caveats grouped by kind, each group a short list (estimated figures first: they carry numbers a reader may reuse).
  const KIND = [['estimate', 'Estimated figures'], ['coverage', 'What is in, what is out, where data is missing'], ['convention', 'Conventions']];
  const li = n => '<li>' + esc(n.text) + (n.url ? ' <a href="' + esc(n.url) + '" target="_blank" rel="noopener">Release</a>.' : '') + '</li>';
  // Estimated figures stay open; the other groups fold, each summary carrying its count (M21).
  document.getElementById('notes').innerHTML = KIND.map(([k, label]) => {
    const ns = DATA.notes.filter(n => n.group === k), list = '<ul>' + ns.map(li).join('') + '</ul>';
    if (!ns.length) return '';
    return '<li class="note-group">' + (k === 'estimate' ? '<h4>' + label + ' (' + ns.length + ')</h4>' + list
      : '<details class="fold"><summary>' + label + ' (' + ns.length + ')</summary>' + list + '</details>') + '</li>';
  }).join('');
  const c = DATA.check && typeof DATA.check === 'object' ? DATA.check : { status: 'not yet run' }, when = c.run_at || c.generated_at;
  const count = Array.isArray(c.checks) ? c.checks.length : 0;
  document.getElementById('check').innerHTML = '<div class="check-summary"><span class="check-status ' + (c.status === 'pass' ? 'passed' : '') + '">' + esc(c.status || 'see below') + '</span>'
    + '<div><strong>Data validation</strong><p>' + (count ? count + ' checks recorded' : 'No checks recorded')
    + (when ? ' · Run ' + esc(when) : '') + '</p></div></div>'
    + (Object.keys(c).length > 1 ? '<details class="fold check-detail"><summary>View full check record</summary><pre>' + esc(JSON.stringify(c, null, 1)) + '</pre></details>' : '');
  const through = DATA.headline.filter(h => h.break_even != null).map(h => h.week_end).sort()[0];
  document.getElementById('footer').innerHTML = 'Data through the week ending ' + esc(through) + '. Page built ' + esc(DATA.generated_at)
    + ' from the CSVs in <a href="#downloads">Downloads</a>.';
}

// ---- the sheet: term definitions and map details ----
// Phones: a bottom sheet (CSS). Desktop: a small card under its trigger, kept inside the viewport.
// It is a dialog labelled by its h4 (#sheet-title); focus moves into it on open and back to the trigger on close
// (Escape closes it: the popover's own light dismiss).
let SHEET_FROM = null;
const PHONE = '(max-width: 760px)';
function openSheet(html, from) {
  const sh = document.getElementById('sheet');
  if (sh.matches(':popover-open')) sh.hidePopover();
  sh.querySelector('.sheet-body').innerHTML = html;
  SHEET_FROM = from || null;
  if (from && from.hasAttribute('aria-expanded')) from.setAttribute('aria-expanded', 'true');
  sh.style.left = sh.style.top = '';
  sh.showPopover();
  sh.focus({ preventScroll: true });
  if (from && !matchMedia(PHONE).matches) {
    const r = from.getBoundingClientRect(), w = sh.offsetWidth, h = sh.offsetHeight;
    sh.style.left = Math.max(12, Math.min(innerWidth - w - 12, r.left)) + 'px';
    sh.style.top = (r.bottom + h + 12 < innerHeight ? r.bottom + 8 : Math.max(12, r.top - h - 8)) + 'px';
  }
}
function sheetUi() {
  const sh = document.getElementById('sheet');
  sh.addEventListener('toggle', ev => {
    if (ev.newState !== 'closed' || !SHEET_FROM) return;
    if (SHEET_FROM.hasAttribute('aria-expanded')) SHEET_FROM.setAttribute('aria-expanded', 'false');
    if (document.contains(SHEET_FROM)) SHEET_FROM.focus({ preventScroll: true });
  });
  document.addEventListener('click', ev => {
    const t = ev.target.closest('.term');
    if (!t) return;
    const [title, body] = TERMS[t.dataset.term];
    openSheet('<h4 id="sheet-title">' + esc(title) + '</h4><p>' + esc(body) + '</p>', t);
  });
}

// ---- phones (760px and below): one firm at a time on the shared scale; the selection survives redraws ----
function segControls() {
  document.querySelectorAll('.seg-control').forEach(ctl => {
    const box = document.getElementById(ctl.dataset.for), tabs = [...ctl.querySelectorAll('[role="tab"]')];
    box.dataset.solo = '';
    const pick = firm => {
      tabs.forEach(b => { const on = b.dataset.firm === firm; b.setAttribute('aria-selected', on); b.tabIndex = on ? 0 : -1; });
      box.querySelectorAll('.firm-panel').forEach(p => p.classList.toggle('on', p.dataset.firm === firm));
      draw();  // a hidden panel had no width; draw it at its width now
    };
    ctl.addEventListener('click', ev => { const b = ev.target.closest('[role="tab"]'); if (b) pick(b.dataset.firm); });
    ctl.addEventListener('keydown', ev => {
      const i = tabs.findIndex(b => b.getAttribute('aria-selected') === 'true'), d = { ArrowLeft: -1, ArrowRight: 1 }[ev.key];
      const j = ev.key === 'Home' ? 0 : ev.key === 'End' ? tabs.length - 1 : d == null ? -1 : (i + d + tabs.length) % tabs.length;
      if (j < 0) return;
      ev.preventDefault();
      pick(tabs[j].dataset.firm);
      tabs[j].focus();
    });
    pick('MSTR');
  });
}

// ---- section links: the current section is marked in the top links and the phone tab bar ----
function sectionNav() {
  const links = [...document.querySelectorAll('[data-sec]')], ids = [...new Set(links.map(a => a.dataset.sec))];
  // The tab bar's "Map" stands for everything from the map down.
  const group = id => ['bars-section', 'method', 'built', 'downloads'].includes(id) ? 'map-section' : id;
  const secs = [...document.querySelectorAll('main > section')];
  const mark = () => {
    const y = (document.querySelector('.site-bar').offsetHeight || 56) + innerHeight * 0.25;
    let cur = secs[0].id;
    for (const s of secs) if (s.getBoundingClientRect().top <= y) cur = s.id;
    links.forEach(a => {
      const on = a.closest('.tab-bar') ? a.dataset.sec === group(cur) : a.dataset.sec === cur;
      if (on) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
    });
  };
  let raf = 0;
  addEventListener('scroll', () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; mark(); }); }, { passive: true });
  mark();
  return ids;
}

// Panels hidden by the phone's firm switch have no width: skip them, and draw them when selected.
function draw() {
  const shown = id => document.getElementById(id).offsetParent !== null;
  for (const f of Object.keys(FIRM)) if (shown('pref-' + f)) drawPref(f);
  drawMap();
  for (const f of Object.keys(FIRM)) if (shown('bars-' + f)) drawBars(f);
}

function theme() {
  const btn = document.getElementById('theme'), root = document.documentElement;
  const dark = () => root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  const saved = localStorage.getItem('theme');
  if (saved) root.dataset.theme = saved;
  const label = () => {
    root.classList.toggle('is-dark', dark());
    btn.setAttribute('aria-label', dark() ? 'Switch to light theme' : 'Switch to dark theme');
    document.querySelector('meta[name="theme-color"]').content = dark() ? '#0f1216' : '#fbfbf9';
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
  ruler();
  barDomain();
  headline();
  mapLegend();
  barsLegend();
  totals();
  table();
  method();
  built();
  sheetUi();
  segControls();
  sectionNav();
  draw();
  // The page was empty when the browser looked for the hash target; go there now that it has content.
  if (location.hash.length > 1) { const t = document.getElementById(location.hash.slice(1)); if (t) t.scrollIntoView(); }
  let lastW = innerWidth;
  addEventListener('resize', () => { if (innerWidth !== lastW) { lastW = innerWidth; draw(); } });
}).catch(e => {
  document.getElementById('headline-text').innerHTML = '<p>Could not load data.json: ' + esc(e.message) + '</p>';
});
