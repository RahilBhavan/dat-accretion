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
function hatchPattern(id, color, angle) {
  return '<pattern id="' + id + '" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(' + angle + ')">'
    + '<rect width="5" height="5" style="fill:var(' + color + ');fill-opacity:0.2"/><line x1="0" y1="0" x2="0" y2="5" style="stroke:var(' + color + ');stroke-width:2"/></pattern>';
}
const RESID_SWATCH = '<rect x="1" y="1" width="12" height="12" style="fill:var(--neutral);fill-opacity:0.2"/><path d="M1,5 L5,1 M1,9 L9,1 M1,13 L13,1 M5,13 L13,5 M9,13 L13,9" style="stroke:var(--neutral);stroke-width:1.5"/>';
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
  const pts = ratioPts(firm), W = 150, H = 32, P = 3, R = 28;  // R: room at the right for the 100% label
  const X = t => P + (t - RULER.t0) / (RULER.t1 - RULER.t0) * (W - R - P), Y = v => P + (RULER.hi - v) / (RULER.hi - RULER.lo) * (H - 2 * P);
  const l = pts[pts.length - 1], below = ADDS[firm][0] === 'below', y0 = below ? Y(100) : P, y1 = below ? H - P : Y(100);
  return '<svg class="spark" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" aria-hidden="true">'
    + '<rect class="band" x="' + P + '" y="' + y0.toFixed(1) + '" width="' + (W - R - P) + '" height="' + (y1 - y0).toFixed(1) + '"/>'
    + '<line class="ref" x1="' + P + '" x2="' + (W - R) + '" y1="' + Y(100) + '" y2="' + Y(100) + '"/>'
    + '<text x="' + (W - R + 4) + '" y="' + (Y(100) + 3.5) + '">100%</text>'
    + '<path d="' + pts.map((p, i) => (i ? 'L' : 'M') + X(p.t).toFixed(1) + ',' + Y(p.r).toFixed(1)).join('') + '"/>'
    + '<circle cx="' + X(l.t).toFixed(1) + '" cy="' + Y(l.r).toFixed(1) + '" r="2.6"/></svg>';
}

// ---- 1. headline ----
// Meta line under the dek: what the figures cover, how old that is, where each number comes from, the definition.
// Weekly firms file on Mondays for the week ending Sunday, so more than 9 days since the latest week means a missed refresh.
function asof() {
  const weekly = DATA.headline.filter(h => h.break_even != null);
  const through = weekly.map(h => h.week_end).sort()[0], age = daysAgo(through);
  let s = 'Data through ' + nice_date(through) + ' (' + age + ' days ago) · Every figure links to its SEC filing · '
    + 'Measured with Strategy\'s own net coins per share definition, applied to all three firms · '
    + '<a href="#built">How this is built</a>';
  if (age > 9) s += ' <strong class="stale">Behind: filings after ' + esc(through) + ' are not yet included.</strong>';
  document.getElementById('asof').innerHTML = s;
}

// Dek: the headline's answer in plain words, one sentence per firm, figures from data.json.
const TERMS = {
  rotation: ['Rotation', 'The pair of trades a firm repeats. Strategy sells common stock to buy back STRC, its preferred stock. BitMine sells BMNP, its preferred stock, to buy back common.'],
  breakeven: ['Break-even', '$100 × net mNAV. The two rotations run in opposite directions: Strategy\'s adds while STRC is below it, BitMine\'s while BMNP is above it.'],
  mnav: ['Net mNAV (m)', 'The share price divided by the coin value behind each share, net of debt and preferred. Above 1, new common sells for more than the coins it claims.'],
  sats: ['Sats', 'Coins per share for bitcoin are counted in sats: 1 sat = 0.00000001 BTC.'],
};
const term = (k, text) => '<button type="button" class="term" data-term="' + k + '">' + text + '</button>';
function dek() {
  const h = Object.fromEntries(DATA.headline.map(x => [x.firm, x])), a = h.MSTR, b = h.BMNR;
  document.getElementById('dek').innerHTML =
    'Strategy\'s ' + term('rotation', 'rotation') + ' adds bitcoin per share while STRC trades below <strong>$'
    + a.break_even.toFixed(2) + '</strong>; it closed at <span class="fig">$' + a.pref_close.toFixed(2) + '</span>. '
    + 'BitMine\'s adds ether per share while BMNP trades above <strong>$'
    + b.break_even.toFixed(2) + '</strong>; it closed at <span class="fig">$' + b.pref_close.toFixed(2) + '</span>. '
    + 'Each ' + term('breakeven', 'break-even') + ' is $100 × ' + term('mnav', 'net mNAV') + '.';
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
    const when = sbet ? 'm ' + h.m.toFixed(3) + ' · ' + short_date(h.week_end) + ', last filed (' + daysAgo(h.week_end) + ' days ago)'
      : 'close ' + short_date(h.price_date) + ' · m ' + h.m.toFixed(3);
    // The condition names the line the percent is read against, so 84% (below) or 124% (above) needs no legend.
    const cond = '<span>' + (sbet ? 'Buyback adds while m is <span class="side">below 1</span>, so while 1 ÷ m is above 100%'
      : 'Adds while ' + esc(h.pref) + ' is <span class="side">' + ADDS[h.firm][0] + '</span> break-even (100%)') + '</span>';
    return '<article class="lr" aria-label="' + esc(h.name) + '"><div class="lr-name"><h3 class="lr-firm">' + esc(h.name) + (sbet ? '' : '<span class="tk">' + esc(h.pref) + '</span>') + '</h3>'
      + '<p class="lr-when">' + when + '</p></div>'
      + fig('Close', sbet ? 'none' : '$' + h.pref_close.toFixed(2)) + fig('Break-even', sbet ? 'm = 1' : '$' + h.break_even.toFixed(2), 'be') + fig('Of break-even', pct(r), 'pct-col')
      + '<p class="lr-cond">' + cond + spark(h.firm) + '</p></article>';
  }).join('');
  document.getElementById('headline-text').innerHTML = '<div class="ledger"><div class="ledger-head" aria-hidden="true"><span>Latest filed week</span>'
    + '<span style="text-align:right">Pref. close</span><span style="text-align:right">Break-even</span><span style="text-align:right">Of break-even</span></div>' + rows + '</div>'
    + '<p class="caption">Break-even = $100 × net mNAV. Lines: close ÷ break-even each week since June, on one shared scale; the shaded side is where each rotation adds. '
    + 'SharpLink has no preferred, so its row shows 1 ÷ m.</p>';
  document.getElementById('counts').textContent = DATA.counts;
  example();
}

// "How this is built": live figures only (computed from data.json and the latest check record), so nothing goes stale.
function built() {
  const filings = new Set(DATA.weeks.flatMap(w => w.filing_urls)).size;
  const weeks = DATA.weeks.filter(w => w.firm !== 'SBET').length;
  const c = DATA.check || {}, checks = Array.isArray(c.checks) ? c.checks : [];
  const api = checks.find(x => /netSatsPerShare/.test(x.name)), pct = api && (api.compared.match(/([+-]\d+\.\d+)%/) || [])[1];
  const tiles = [[filings, 'SEC filings parsed', 'Every action row links to its filing.'],
    [weeks, 'firm-weeks rebuilt', 'Coin holdings rolled from each trade and reconciled to the filed total.'],
    ...(pct ? [[pct.replace('-', '−') + '%', 'from Strategy\'s published net sats per share', 'The rebuild of Strategy\'s own KPI, checked against its API.']] : []),
    [checks.filter(x => x.ok).length + ' of ' + checks.length, 'checks pass', 'Run ' + esc((c.run_at || '').slice(0, 10)) + '; the page deploys only on a pass.']];
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
  const m = 1.2, raise = 120, rows = [90, 100, 110, 120, 130].map(P => {
    const sale = raise * (1 - 1 / m), retire = raise * 100 / P - raise;
    return '<tr' + (P === 120 ? ' class="hl"' : '') + '><td class="num">$' + P + '</td><td class="num">' + (raise * 100 / P).toFixed(0) + '</td><td class="num">+' + sale.toFixed(0)
      + '</td><td class="num">' + (retire < 0 ? MINUS : '+') + Math.abs(retire).toFixed(0) + '</td><td class="num"><b>' + (sale + retire < -0.5 ? MINUS : sale + retire > 0.5 ? '+' : '')
      + Math.abs(sale + retire).toFixed(0) + '</b></td><td>' + (P === 120 ? 'break-even: $100 × m' : '') + '</td></tr>';
  }).join('');
  const be = DATA.headline.find(h => h.firm === 'MSTR');
  document.getElementById('example').innerHTML =
    // Step 1: one claim, retired below its notional (toy numbers, assets and claims on one scale).
    '<div class="why-grid"><div class="prose"><p>Start with one share of preferred stock: a $100 claim that ranks ahead of common stock. If the company buys it back '
    + 'for $90, its claims fall by $100 while its cash falls by $90. The $10 difference now belongs to common holders.</p></div>'
    + '<figure class="fig"><p class="fig-tag">Illustration, not filed figures</p><div class="pair">' + sheet(false) + sheet(true) + '</div>'
    + '<figcaption>Assets equal claims on both sides, drawn on one scale. Paying $90 removes a $100 claim, so the common block grows by $10.</figcaption></figure></div>'
    // Step 2: the rotation as a balance. Common sells at m per $1 of net coins; STRC retires at q per $1 of claim.
    + '<div class="prose"><p>Strategy pays for these buybacks by selling common stock. At a net mNAV of 1.2, buyers pay $1.20 for each $1 of net coins behind a '
    + 'share, so a $120 sale gives new holders $100 of net coins and leaves $20 with existing holders. The rotation adds coins per share as long as the '
    + 'retirement does not give back more than the sale made. Weigh m against q: the beam is level at a STRC price of $100 × m.</p></div>'
    + '<div class="balance-slot" id="balance"></div>'
    + '<p class="balance-read">Latest filed week: net mNAV <b>' + be.m.toFixed(3) + '</b>, so break-even is <b>$' + be.break_even.toFixed(2) + '</b>; STRC closed at <b>$'
    + be.pref_close.toFixed(2) + '</b>. BitMine runs the rotation the other way (sell BMNP, buy back common), so it adds while BMNP trades above $100 × m.</p>'
    + '<details class="fold"><summary>The same illustration as a table, m = 1.2</summary><div class="scroll-x"><table class="plain-num">'
    + '<thead><tr><th class="num">STRC price</th><th class="num">Notional retired</th><th class="num">Sale of common</th><th class="num">Retirement</th><th class="num">Rotation, to common</th><th></th></tr></thead><tbody>'
    + rows + '</tbody></table></div><p class="caption">Raise $120 by selling common, spend it retiring STRC. Dollars to existing common holders, first order. Illustration, not filed figures.</p></details>'
    // Step 3: the filed trade, with its figures and its filing.
    + '<div class="filed"><p class="fig-tag">The filed trade · week ending ' + nice_date(x.week_end) + '</p><ul class="filed-figs">'
    + '<li><b>' + M(x.usd) + '</b>paid for STRC</li><li><b>$' + x.avg_price.toFixed(2) + '</b>per $100 share (q = ' + x.q.toFixed(4) + ')</li>'
    + '<li><b>' + M(x.notional) + '</b>of claims removed</li><li><b>+' + M(x.adds_usd) + '</b>to common, +' + x.sats_per_share.toFixed(2) + ' sats per share</li></ul>'
    + '<div class="prose"><p>Common holders gained ' + M(x.adds_usd) + ', or +' + x.sats_per_share.toFixed(2)
    + ' sats across ' + x.shares.toLocaleString('en-US') + ' fully diluted shares (exact recompute).'
    + (net ? ' That is ' + (x.adds_usd / net * 100).toFixed(3) + '% of Strategy\'s net coin value that week (' + usd(net) + '), too small to see at true scale, '
      + 'which is why the figures above use toy numbers.' : '')
    + ' Source: <a href="' + esc(x.filing_url) + '" target="_blank" rel="noopener">Strategy 8-K for the week ending ' + esc(x.week_end) + '</a>. Every bar and mark below is built the same way.</p></div></div>';
  // The balance (site/balance.js, built by site-src/balance/build.mjs) starts at the table's m = 1.2 and offers the latest filed week.
  if (window.Balance) window.Balance.mount(document.getElementById('balance'), { m: 1.2, price: 100,
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
  // Labels on the left, on the side of the line where the program adds (the data sits clear of it there).
  const below = ADDS[firm][0] === 'below';
  s += '<text x="' + (M.l + 4) + '" y="' + (below ? Y(100) - 5 : Y(100) + 14) + '">break-even</text>';
  s += '<text x="' + (M.l + 4) + '" y="' + (below ? Y(100) + 14 : Y(100) - 5) + '" class="adds">' + ADDS[firm][1] + '</text>';
  // Columns: each point owns the span halfway to its neighbours.
  const mid = i => i < 0 ? M.l : i >= pts.length - 1 ? W - M.r : (X(pts[i].t) + X(pts[i + 1].t)) / 2;
  const active = ACTIVE[el.id] = Math.min(ACTIVE[el.id] ?? pts.length - 1, pts.length - 1);
  pts.forEach((p, i) => {
    const x0 = Math.min(mid(i - 1), X(p.t) - 6), x1 = Math.max(mid(i), X(p.t) + 6);
    s += '<rect class="col" tabindex="' + (i === active ? 0 : -1) + '" data-tip="' + i + '" x="' + x0 + '" y="' + M.t + '" width="' + Math.max(1, x1 - x0) + '" height="' + (H - M.t - M.b)
      + '" aria-label="' + esc(FIRM[firm].name + (sbet ? ' filed date ' : ' week ending ') + p.w.week_end + ': ' + label + ' ' + p.r.toFixed(1) + '%') + '"/>';
  });
  s += '<text x="' + M.l + '" y="' + (H - 6) + '">' + short_date(new Date(RULER.t0).toISOString().slice(0, 10)) + '</text>';
  s += '<text x="' + (W - M.r) + '" y="' + (H - 6) + '" text-anchor="end">' + short_date(new Date(RULER.t1).toISOString().slice(0, 10)) + '</text>';
  s += '<path class="data" d="' + pts.map((p, i) => (i ? 'L' : 'M') + X(p.t).toFixed(1) + ',' + Y(p.r).toFixed(1)).join('') + '"/>';
  if (sbet) s += pts.slice(0, -1).map(p => '<circle class="pt" cx="' + X(p.t) + '" cy="' + Y(p.r) + '" r="2.5"/>').join('');
  const l = pts[pts.length - 1];
  s += '<circle class="last" cx="' + X(l.t) + '" cy="' + Y(l.r) + '" r="4"/>';
  const room = X(l.t) < W - M.r - 40;  // SharpLink's last filed date is mid-range: label to the right of the dot
  s += '<text class="label" x="' + (X(l.t) + (room ? 8 : -7)) + '" y="' + (room ? Y(l.r) + 4 : Y(l.r) + (l.r > 100 ? -9 : 17)) + '" text-anchor="' + (room ? 'start' : 'end') + '">' + pct(l.r) + '</text>';
  el.innerHTML = s + '</svg>';
  bindTips(el, t => {
    const p = pts[+t.dataset.tip], g = p.close - p.be;
    const gap = sbet ? Math.abs(g).toFixed(3) + (g < 0 ? ' below 1' : ' above 1') : '$' + Math.abs(g).toFixed(2) + (g < 0 ? ' below' : ' above');
    return '<b>' + FIRM[firm].name + '</b>, ' + (sbet ? 'filed date ' : 'week ending ') + p.w.week_end
      + '<div class="row"><span>' + (sbet ? 'm (net mNAV)' : esc(h.pref) + ' close') + '</span><span>' + (sbet ? p.close.toFixed(3) : '$' + p.close.toFixed(2)) + '</span></div>'
      + '<div class="row"><span>Break-even' + (sbet ? '' : ' (100 × m)') + '</span><span>' + (sbet ? '1' : '$' + p.be.toFixed(2)) + '</span></div>'
      + '<div class="row"><span>' + (sbet ? '1 ÷ m' : 'Close ÷ break-even') + '</span><span>' + p.r.toFixed(1) + '%</span></div>'
      + '<div class="row on"><span>Gap</span><span>' + gap + '</span></div>'
      + '<div>Filing: ' + esc(fileName(p.w.filing_urls[0])) + '</div>';
  });
  colKeys(el);
  const n = new Set(pts.flatMap(p => p.w.filing_urls)).size;
  document.getElementById('src-' + firm).innerHTML = (sbet ? 'Last: m ' + l.close.toFixed(3) : 'Last: ' + esc(h.pref) + ' $' + l.close.toFixed(2) + ', break-even $' + l.be.toFixed(2))
    + '. ' + n + ' SEC filings; closes from Yahoo Finance.';
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
  s += '<text class="label" x="' + (M.l + 8) + '" y="' + (M.t + 22) + '">Strategy\'s rotation adds here (m &gt; q)</text>';
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
    s += '<a href="' + esc(w.filing_urls[0]) + '" target="_blank" rel="noopener" data-tip="' + i + '" aria-label="' + esc(label) + '">'
      + markSvg(w.firm, cx, cy, Math.max(r, 12), 'hit', 'fill:transparent')
      + markSvg(w.firm, cx, cy, last ? r + 1.5 : r, 'mark', 'fill:' + (last ? c : 'var(--bg)') + ';stroke:' + c + ';stroke-width:1.25') + '</a>';
  }
  // Direct label on each firm's latest week: right, left, above, below at growing distance; the first box that stays
  // inside the plot and hits no mark or placed label wins. Box width is estimated at 6.6px per character (10.5px monospace).
  const boxes = pts.map(w => { const r = rad(w); return [X(w.qx) - r, Y(w.m) - r, X(w.qx) + r, Y(w.m) + r]; });
  const hit = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
  for (const firm of Object.keys(FIRM)) {
    const i = latest[firm];
    if (i == null) continue;
    const w = pts[i], cx = X(w.qx), cy = Y(w.m), r = rad(w), text = FIRM[firm].name + ' ' + short_date(w.week_end), tw = text.length * 6.6;
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
  // Touch: a tap on a mark opens its details in the sheet instead of navigating; the sheet's link opens the filing.
  // Mouse and keyboard follow the link directly.
  let touch = false;
  el.onpointerdown = ev => { touch = ev.pointerType === 'touch'; };
  el.onclick = ev => {
    const a = ev.target.closest('a[data-tip]');
    if (!a || !touch) return;
    ev.preventDefault();
    hideTip(el.parentElement);
    openSheet('<div class="data-rows">' + tipHtml(a) + '<a href="' + a.getAttribute('href') + '" target="_blank" rel="noopener">View filing</a></div>', a);
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
let BARS = null;  // shared y domain across the three firms, in bp
function barDomain() {
  let lo = 0, hi = 0;
  for (const w of DATA.weeks.filter(w => w.value)) {
    const st = stack(w), k = toBp(w);
    hi = Math.max(hi, st.reduce((a, d) => a + Math.max(d[3], 0), 0) * k);
    lo = Math.min(lo, st.reduce((a, d) => a + Math.min(d[3], 0), 0) * k);
  }
  const ticks = nice(lo, hi, 4);
  BARS = { lo: Math.min(lo, ticks[0]), hi: Math.max(hi, ticks[ticks.length - 1]), ticks };
}

function segPath(x, y0, y1, w) {
  const top = Math.min(y0, y1), h = Math.abs(y1 - y0);
  return 'M' + x + ',' + top + 'h' + w + 'v' + h + 'h' + (-w) + 'Z';
}

function weekTip(w, on) {
  const k = toBp(w);
  const rows = stack(w).map(d => '<div class="row' + (d[0] === on ? ' on' : '') + '"><span><i class="sw' + (d[0] === 'residual' ? ' resid' : d[4] ? ' est' : '') + '" style="background:var(' + d[2] + ')'
    + '"></i>' + d[1] + '</span><span>' + bps(d[3] * k, true) + ' · ' + usd(d[3], true) + '</span></div>').join('');
  return '<b>' + FIRM[w.firm].name + '</b>, ' + (w.firm === 'SBET' ? 'filed date ' : 'week ending ') + w.week_end + rows
    + '<div class="row"><span>Coin price (not stacked)</span><span>' + bps(w.price * k, true) + ' · ' + usd(w.price, true) + '</span></div>'
    + '<div class="row"><span>In-the-money flips (not stacked)</span><span>' + bps(w.itm_flip * k, true) + ' · ' + usd(w.itm_flip, true) + '</span></div>'
    + '<div class="row on"><span>Observed change</span><span>' + bps(w.observed * k, true) + ' · ' + usd(w.observed, true) + '</span></div>';
}

function drawBars(firm) {
  const el = document.getElementById('bars-' + firm);
  const weeks = DATA.weeks.filter(w => w.firm === firm && w.value);
  const W = el.clientWidth || 640, H = W < 500 ? 220 : 250, M = { l: 52, r: 8, t: 16, b: 28 };
  const { lo, hi, ticks } = BARS;
  const Y = v => M.t + (hi - v) / (hi - lo) * (H - M.t - M.b);
  const bw = (W - M.l - M.r) / weeks.length, barW = Math.min(36, Math.max(4, bw * 0.62));
  const hatch = 'hatch-' + firm, resid = 'resid-' + firm;
  let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="group" aria-label="' + FIRM[firm].name + ': weekly change in net coins per share by cause, basis points. Left and Right arrow keys move between weeks.">'
    + '<defs>' + hatchPattern(hatch, '--ink2', 45) + hatchPattern(resid, '--neutral', -45) + '</defs>';
  for (const t of ticks) {  // labels only; the zero line is the one rule
    s += '<text x="' + (M.l - 8) + '" y="' + (Y(t) + 4) + '" text-anchor="end">' + (t > 0 ? '+' : t < 0 ? MINUS : '') + Math.abs(t) + (t ? '' : ' bp') + '</text>';
    if (t) s += '<line class="tick" x1="' + (M.l - 4) + '" x2="' + M.l + '" y1="' + Y(t) + '" y2="' + Y(t) + '"/>';
  }
  const every = Math.ceil(44 / bw);
  const active = ACTIVE[el.id] = Math.min(ACTIVE[el.id] ?? weeks.length - 1, weeks.length - 1);
  let big = null;
  weeks.forEach((w, i) => {
    const x0 = M.l + i * bw, x = x0 + (bw - barW) / 2, st = stack(w), k = toBp(w);
    s += '<rect class="col" tabindex="' + (i === active ? 0 : -1) + '" data-tip="' + i + '" x="' + x0 + '" y="' + M.t + '" width="' + bw + '" height="' + (H - M.t - M.b) + '" aria-label="'
      + esc(FIRM[firm].name + (firm === 'SBET' ? ' filed date ' : ' week ending ') + w.week_end + ': observed ' + bps(w.observed * k, true) + ', ' + usd(w.observed, true)) + '"/>';
    let up = 0, dn = 0;
    st.forEach(d => {
      const v = d[3] * k, a = v > 0 ? up : dn, b = a + v;
      if (v > 0) up = b; else dn = b;
      const fill = d[0] === 'residual' ? RESID_FILL(resid) : d[4] ? 'url(#' + hatch + ')' : 'var(' + d[2] + ')';
      s += '<path class="seg" data-tip="' + i + '" data-cat="' + d[0] + '" d="' + segPath(x, Y(a), Y(b), barW) + '" style="fill:' + fill + '"/>';
      if (!big || Math.abs(v) > Math.abs(big.v)) big = { v, label: d[1], x, y: (Y(a) + Y(b)) / 2, week: w.week_end };
    });
    if (st.length) s += '<line class="net" x1="' + (x - 3) + '" x2="' + (x + barW + 3) + '" y1="' + Y(up + dn) + '" y2="' + Y(up + dn) + '"/>';
    if (i % every === 0) s += '<text x="' + (x0 + bw / 2) + '" y="' + (H - M.b + 16) + '" text-anchor="middle">' + short_date(w.week_end) + '</text>';
  });
  s += '<line class="zero" x1="' + M.l + '" x2="' + (W - M.r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '"/>';
  if (big) {  // the one direct label: largest segment in this chart, beside its bar at the segment's middle (clear of the net tick)
    const right = big.x < W * 0.6, x = W < 500 ? M.l + 4 : right ? big.x + barW + 6 : big.x - 6;
    s += '<text class="label" x="' + x + '" y="' + (W < 500 ? M.t + 4 : big.y + 4) + '" text-anchor="' + (W < 500 || right ? 'start' : 'end') + '">'
      + (W < 500 ? 'Largest: ' + short_date(big.week) + ' ' : '') + big.label + ' ' + bps(big.v, true) + '</text>';
  }
  el.innerHTML = s + '</svg>';
  bindTips(el, t => weekTip(weeks[+t.dataset.tip], t.dataset.cat));
  colKeys(el);
}

function barsLegend() {
  const items = Object.entries(GROUP).map(([k, [label, c]]) => k === 'residual'
    ? swatch(RESID_SWATCH) + 'Residual: change the filings leave unexplained'
    : swatch('<rect x="1" y="1" width="12" height="12" style="fill:var(' + c + ')"/>') + label);
  items.splice(1, 0, swatch('<rect x="1" y="1" width="12" height="12" style="fill:var(--ink2);fill-opacity:0.2"/><path d="M1,9 L9,1 M5,13 L13,5" style="stroke:var(--ink2);stroke-width:2"/>')
    + EST + ', part of common');
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
      '<div class="strip"><p class="strip-title">Since ' + esc(x.since) + ', value to common by cause, USD</p>'
      + '<p class="strip-note">' + esc(residualSentence(firm, x)) + '</p>' + html + '</div>');
  }
}

function table() {
  const cols = DATA.categories;
  let h = '<thead><tr><th>firm</th><th>week ending (SharpLink: filed date)</th><th>m</th><th>q</th><th>dollars moved ($)</th>'
    + cols.map(c => '<th>' + CAT[c][0].toLowerCase() + ' ($)</th>').join('')
    + '<th>of which estimated issuance ($)</th><th>coin price ($)</th><th>in-the-money flips ($)</th><th>observed ($)</th><th>observed (bp of net value)</th><th>filing</th></tr></thead><tbody>';
  for (const w of DATA.weeks) {
    const v = w.value || {};
    h += '<tr><td>' + FIRM[w.firm].name + '</td><td>' + w.week_end + '</td><td>' + fix(w.m, 3) + '</td><td>' + fix(w.q, 4) + '</td><td>' + usd(w.dollars_moved) + '</td>'
      + cols.map(c => '<td>' + (w.value ? usd(v[c], true) : '-') + '</td>').join('')
      + '<td>' + (w.est_issuance ? usd(w.est_issuance, true) : '-') + '</td><td>' + usd(w.price, true) + '</td><td>' + usd(w.itm_flip, true) + '</td><td>'
      + usd(w.observed, true) + '</td><td>' + (w.observed == null ? '-' : bps(w.observed * toBp(w), true)) + '</td><td>'
      + w.filing_urls.map(u => '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(fileName(u)) + '</a>').join(' ') + '</td></tr>';
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

// ---- the sheet: term definitions and map details ----
// Phones: a bottom sheet (CSS). Desktop: a small card under its trigger, kept inside the viewport.
let SHEET_FROM = null;
function openSheet(html, from) {
  const sh = document.getElementById('sheet');
  sh.querySelector('.sheet-body').innerHTML = html;
  if (sh.matches(':popover-open')) sh.hidePopover();
  SHEET_FROM = from || null;
  sh.style.left = sh.style.top = '';
  sh.showPopover();
  if (from && !matchMedia('(max-width: 720px)').matches) {
    const r = from.getBoundingClientRect(), w = sh.offsetWidth, h = sh.offsetHeight;
    sh.style.left = Math.max(12, Math.min(innerWidth - w - 12, r.left)) + 'px';
    sh.style.top = (r.bottom + h + 12 < innerHeight ? r.bottom + 8 : Math.max(12, r.top - h - 8)) + 'px';
  }
}
function sheetUi() {
  const sh = document.getElementById('sheet');
  sh.addEventListener('toggle', ev => { if (ev.newState === 'closed' && SHEET_FROM && document.contains(SHEET_FROM)) SHEET_FROM.focus({ preventScroll: true }); });
  document.addEventListener('click', ev => {
    const t = ev.target.closest('.term');
    if (!t) return;
    const [title, body] = TERMS[t.dataset.term];
    openSheet('<h4>' + esc(title) + '</h4><p>' + esc(body) + '</p>', t);
  });
}

// ---- phones: one firm at a time on the shared scale; the selection survives redraws ----
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
      if (d == null) return;
      const j = (i + d + tabs.length) % tabs.length;
      pick(tabs[j].dataset.firm);
      tabs[j].focus();
    });
    pick('MSTR');
  });
}

// ---- section links: the current section is marked in the top links and the phone tab bar ----
function sectionNav() {
  const links = [...document.querySelectorAll('[data-sec]')], ids = [...new Set(links.map(a => a.dataset.sec))];
  // The tab bar's "Detail" stands for everything from the map down.
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
