"""`python -m dat.social`: post-ready X cards and drafts -> private/social/<latest MSTR week_end>/. stdlib only.

Cards are 1200x675 dark SVGs; PNG, MP4 and GIF rendering lives outside the repo in private/social/render.mjs.
Figures come from dat.build_site.build and data/attribution.csv; framing.md applies to every string.
"""
import html, math, os, re, shutil, sys
from datetime import date
from dat.balances import read
from dat.build_site import build, FIRMS, LIQ_PREF

# Theme
W, H, PAD = 1200, 675, 64
SURFACE, PANEL, TEXT, SECOND, MUTED, GRID, BORDER = '#0d1015', '#131820', '#f3f5f7', '#a1aab7', '#6b7480', '#222a33', '#2b333e'
COLOR = {'MSTR': '#3987e5', 'BMNR': '#d95926', 'SBET': '#199e70'}
FONT = 'Inter, -apple-system, &quot;SF Pro Display&quot;, system-ui, sans-serif'
MINUS = '−'
FOOT_L = "Strategy's own net coins per share definition, applied to all three firms"
FOOT_R = 'rahilbhavan.github.io/dat-accretion'
FRAMES, HOLD_END, HOLD_NEAR = 10, 30, 20
TOP_N = 8
ACTION_WORDS = {'issue_common': 'issued common', 'buyback_common': 'repurchased common', 'issue_pref': 'issued',
                'retire_pref': 'retired', 'buy_coin': 'added', 'sell_coin': 'disposed of'}
e = html.escape


def usd(x, signed=False):
    """3 significant figures: +$1.81B, −$344M, $3.89M, $281k; signed values get + or U+2212."""
    a, body = abs(x), None
    for div, unit in ((1e9, 'B'), (1e6, 'M'), (1e3, 'k')):
        if a >= div * 0.9995:
            v = a / div
            body = f"${v:.{2 if v < 9.995 else 1 if v < 99.95 else 0}f}{unit}"
            break
    body = body or f'${a:.0f}'
    return (MINUS if x < 0 and body != '$0' else '+' if signed and x > 0 and body != '$0' else '') + body


def tick_usd(v, top):
    """Compact axis money: $2B, −$4B, $500M, −$5. top: largest |tick|, sets the unit."""
    if v == 0:
        return '$0'
    div, unit = next(((d, u) for d, u in ((1e9, 'B'), (1e6, 'M'), (1e3, 'k')) if top >= d), (1, ''))
    return (MINUS if v < 0 else '') + f'${abs(v) / div:g}{unit}'


def dollars(x):
    return f'${abs(x):.2f}'


def nice(lo, hi, count=5):
    """Tick values covering [lo, hi] (site/app.js nice)."""
    raw = (hi - lo) / count or 1
    p = 10 ** math.floor(math.log10(raw))
    step = next(k * p for k in (1, 2, 2.5, 5, 10) if k * p >= raw)
    out, v = [], math.floor(lo / step) * step
    while v <= hi + step * 1e-9:
        out.append(round(v, 10))
        v += step
    if out[-1] < hi:
        out.append(out[-1] + step)
    return out


def domain(vals, head=0.08):
    """Data range plus ~8% headroom (0 included), and 4 to 6 nice ticks that fall inside it."""
    lo, hi = min(vals + [0]), max(vals + [0])
    span = hi - lo or 1
    lo, hi = lo - head * span if lo < 0 else lo, hi + head * span if hi > 0 else hi
    for count in (4, 5, 6, 8):
        ticks = [t for t in nice(lo, hi, count) if lo - 1e-9 <= t <= hi + 1e-9]
        if len(ticks) >= 4:
            break
    return lo, hi, ticks


def tw(s, size):
    """Rough text width in px for layout (system sans)."""
    return len(s) * size * 0.56


def chip(x, y, firm):
    """Ticker chip with its left edge at x, centered on baseline y; returns (svg, width)."""
    c, w = COLOR[firm], 16 + len(firm) * 10
    return (f'<rect x="{x}" y="{y - 17}" width="{w}" height="24" rx="6" fill="{c}" fill-opacity="0.15" stroke="{c}"/>'
            f'<text x="{x + w / 2}" y="{y}" font-size="14" font-weight="600" letter-spacing="0.06em" text-anchor="middle" fill="{c}">{firm}</text>'), w


def card(firms, body, asof):
    head = [f'<text x="{PAD}" y="56" font-size="13" font-weight="600" letter-spacing="0.14em" fill="{SECOND}">DAT ACCRETION</text>']
    x = PAD + 152
    for f in firms:
        svg, w = chip(x, 56, f)
        head.append(svg)
        x += w + 8
    return '\n'.join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'font-family="{FONT}" style="font-variant-numeric: tabular-nums" fill="{TEXT}">',
        f'<rect width="{W}" height="{H}" fill="{SURFACE}"/>', *head,
        f'<text x="{W - PAD}" y="56" font-size="16" text-anchor="end" fill="{SECOND}">Filings through {asof}</text>',
        *body,
        f'<text x="{PAD}" y="{H - PAD + 6}" font-size="18" fill="{MUTED}">{e(FOOT_L)}</text>',
        f'<text x="{W - PAD}" y="{H - PAD + 6}" font-size="18" text-anchor="end" fill="{MUTED}">{FOOT_R}</text>',
        '</svg>']) + '\n'


def hero(eyebrow, number, label, context):
    return [f'<text x="{PAD}" y="104" font-size="22" fill="{SECOND}">{e(eyebrow)}</text>',
            f'<text x="{PAD}" y="184"><tspan font-size="88" font-weight="750" letter-spacing="-2.64">{e(number)}</tspan>'
            f'<tspan dx="18" font-size="26" fill="{SECOND}">{e(label)}</tspan></text>',
            f'<text x="{PAD}" y="226" font-size="26" fill="{SECOND}">{e(context)}</text>']


def vbar(x, w, y0, y1, fill, op):
    """Vertical bar from the zero line y0 to y1, square at y0, 4px rounded at the far end."""
    sg, r = (1 if y1 > y0 else -1), min(4, w / 2, abs(y1 - y0))
    return (f'<path d="M{x:.1f},{y0:.1f}H{x + w:.1f}V{y1 - sg * r:.1f}Q{x + w:.1f},{y1:.1f} {x + w - r:.1f},{y1:.1f}'
            f'H{x + r:.1f}Q{x:.1f},{y1:.1f} {x:.1f},{y1 - sg * r:.1f}Z" fill="{fill}" fill-opacity="{op}"/>')


def hbar(y, h, x0, x1, fill):
    sg, r = (1 if x1 > x0 else -1), min(4, h / 2, abs(x1 - x0))
    return (f'<path d="M{x0:.1f},{y:.1f}H{x1 - sg * r:.1f}Q{x1:.1f},{y:.1f} {x1:.1f},{y + r:.1f}V{y + h - r:.1f}'
            f'Q{x1:.1f},{y + h:.1f} {x1 - sg * r:.1f},{y + h:.1f}H{x0:.1f}Z" fill="{fill}"/>')


def text_out(svg):
    """Visible text of an SVG (for the framing test)."""
    return html.unescape(' '.join(re.sub(r'<[^>]+>', ' ', t) for t in re.findall(r'<text[^>]*>(.*?)</text>', svg, re.S)))


# 1. split: value to common with and without the coin price step

def split_series(weeks, firm):
    ws = [w for w in weeks if w['firm'] == firm]
    obs, ex = [0.0], [0.0]
    for w in ws[1:]:
        obs.append(obs[-1] + w['observed'])
        ex.append(ex[-1] + w['observed'] - w['price'])
    return ws, obs, ex


def split_svg(d, firm, asof):
    ws, obs, ex = split_series(d['weeks'], firm)
    t = d['totals'][firm]
    assert abs(obs[-1] - t['observed']) < 1 and abs(ex[-1] - (t['observed'] - t['price'])) < 1, firm
    name = FIRMS[firm]['name']
    eyebrow = f"{name} · since {ws[0]['week_end']}"
    context = f"Coin price step {usd(t['price'], True)}; all other steps {usd(t['observed'] - t['price'], True)}."
    L, R, T, B = 128, 880, 272, 540
    days = [date.fromisoformat(w['week_end']).toordinal() for w in ws]
    X = lambda i: L + (days[i] - days[0]) / (days[-1] - days[0]) * (R - L)
    lo, hi, yt = domain(obs + ex)
    Y = lambda v: B - (v - lo) / (hi - lo) * (B - T)
    c, s = COLOR[firm], []
    for v in yt:
        s.append(f'<line x1="{L}" x2="{R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L - 12}" y="{Y(v) + 5:.1f}" font-size="16" text-anchor="end" fill="{MUTED}">'
                 f'{tick_usd(v, max(abs(x) for x in yt))}</text>')
    s.append(f'<line x1="{L}" x2="{R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="{TEXT}" stroke-width="1.5"/>')
    lastx = -99
    for i, w in enumerate(ws):
        if X(i) - lastx < 62:  # keep x labels apart (e.g. 06-28 and the 06-30 quarter-end row)
            continue
        lastx = X(i)
        s.append(f'<text x="{X(i):.1f}" y="{B + 28}" font-size="16" text-anchor="middle" fill="{MUTED}">{w["week_end"][5:]}</text>')
    band = [f'{X(i):.1f},{Y(v):.1f}' for i, v in enumerate(obs)] + [f'{X(i):.1f},{Y(v):.1f}' for i, v in reversed(list(enumerate(ex)))]
    s.append(f'<polygon points="{" ".join(band)}" fill="{c}" fill-opacity="0.18"/>')
    s.append(f'<polyline points="{" ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(ex))}" fill="none" stroke="{SECOND}" stroke-width="2" stroke-linejoin="round"/>')
    s.append(f'<polyline points="{" ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(obs))}" fill="none" stroke="{c}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
    # band label: where the band (with the total's sign, so the label reads true where it sits) is tallest
    # across the label's whole width
    lab = ('coin price step', usd(t['price'], True))
    half = tw(lab[0], 15) / 2 + 6
    sgn = 1 if t['price'] >= 0 else -1
    xs = [X(i) for i in range(len(ws))]
    upper, lower = (obs, ex) if sgn > 0 else (ex, obs)

    def at(vals, x):  # line's screen y at screen x
        k = max([i for i in range(len(xs) - 1) if xs[i] <= x] + [0])
        f = (x - xs[k]) / (xs[k + 1] - xs[k])
        return Y(vals[k] + (vals[k + 1] - vals[k]) * f)
    Y0 = Y(0)
    best, out = None, None
    for cx in range(int(L + half), int(R - half) + 1, 4):
        span = [cx - half + j * (2 * half) / 8 for j in range(9)]
        top = max(at(upper, x) for x in span)   # lowest point of the upper line under the label
        bot = min(at(lower, x) for x in span)   # highest point of the lower line under the label
        for a, b in ((top, min(bot, Y0 - 2)), (max(top, Y0 + 2), bot)):  # keep off the zero line
            if best is None or b - a > best[0]:
                best = (b - a, cx, (a + b) / 2)
        # fallback spot: just below the band, clear of the zero line and the x labels
        cy = max(max(at(obs, x), at(ex, x)) for x in span) + 34
        if cy + 20 < B and (cy + 20 < Y0 - 4 or cy - 18 > Y0 + 4):
            h = abs(at(obs, cx) - at(ex, cx))
            if out is None or h > out[0]:
                out = (h, cx, cy)
    room, cx, cy = best
    if room < 36 and out:  # band too thin for the label inside it
        _, cx, cy = out
    s.append(f'<text x="{cx:.1f}" y="{cy - 3:.1f}" font-size="15" font-weight="600" text-anchor="middle" '
             f'stroke="{SURFACE}" stroke-width="5" stroke-linejoin="round" paint-order="stroke">'
             f'<tspan x="{cx:.1f}" fill="{SECOND}">{lab[0]}</tspan><tspan x="{cx:.1f}" dy="18">{lab[1]}</tspan></text>')
    ya, yb = Y(obs[-1]), Y(ex[-1])
    for vals, col in ((obs, c), (ex, SECOND)):
        s.append(f'<circle cx="{R:.1f}" cy="{Y(vals[-1]):.1f}" r="5" fill="{col}" stroke="{SURFACE}" stroke-width="2"/>')
    if abs(ya - yb) < 56:  # keep the two end labels apart
        mid = (ya + yb) / 2
        ya, yb = (mid - 28, mid + 28) if ya <= yb else (mid + 28, mid - 28)
    for vals, y, label in ((obs, ya, 'value to common'), (ex, yb, 'excluding the coin price step')):
        s.append(f'<text x="{R + 18}" y="{y - 2:.1f}" font-size="24" font-weight="700">{usd(vals[-1], True)}</text>')
        s.append(f'<text x="{R + 18}" y="{y + 20:.1f}" font-size="16" fill="{SECOND}">{label}</text>')
    body = hero(eyebrow, usd(t['observed'], True), 'value to common', context) + s
    return card([firm], body, asof), f"{name} since {ws[0]['week_end']}: {usd(t['observed'], True)} to common. {context}"


# 2. gap: preferred close minus break-even, per week

def gap_rows(weeks, firm):
    return [{'week_end': w['week_end'], 'close': round(LIQ_PREF * w['q'], 2), 'be': round(LIQ_PREF * w['m'], 2),
             'gap': round(round(LIQ_PREF * w['q'], 2) - round(LIQ_PREF * w['m'], 2), 2)}
            for w in weeks if w['firm'] == firm and w['m'] is not None and w['q'] is not None]


def gap_counts(rows):
    return sum(r['gap'] < 0 for r in rows), len(rows)


def side(g):
    return 'below' if g < 0 else 'above' if g > 0 else 'at'


def gap_text(firm, rows):
    last, (below, n) = rows[-1], gap_counts(rows)
    f = FIRMS[firm]
    eyebrow = f"{f['pref']} {dollars(last['close'])} · break-even {dollars(last['be'])}"
    context = (f"Below in {below} of {n} filed weeks; Strategy's rotation adds below it." if firm == 'MSTR' else
               f"Below in {below} of {n} weeks; BitMine's rotation adds above it.")
    return eyebrow, f"{dollars(last['gap'])} {side(last['gap'])}", context


def gap_svg(d, firm, asof):
    rows = gap_rows(d['weeks'], firm)
    last, near = rows[-1], min(rows, key=lambda r: abs(r['gap']))
    eyebrow, number, context = gap_text(firm, rows)
    L, R, T, B = 96, W - PAD, 272, 540
    lo, hi, yt = domain([r['gap'] for r in rows])
    Y = lambda v: B - (v - lo) / (hi - lo) * (B - T)
    bw, c, s = (R - L) / len(rows), COLOR[firm], []
    for v in yt:
        s.append(f'<line x1="{L}" x2="{R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L - 12}" y="{Y(v) + 5:.1f}" font-size="16" text-anchor="end" fill="{MUTED}">{tick_usd(v, 1)}</text>')
    cx = lambda i: L + i * bw + bw / 2
    for i, r in enumerate(rows):
        s.append(vbar(L + i * bw + 1, bw - 2, Y(0), Y(r['gap']), c, 1 if r is last else 0.35))
        s.append(f'<text x="{cx(i):.1f}" y="{B + 28}" font-size="16" text-anchor="middle" fill="{MUTED}">{r["week_end"][5:]}</text>')
    i = len(rows) - 1
    vy = Y(last['gap']) + (22 if last['gap'] < 0 else -8)
    s.append(f'<text x="{R:.1f}" y="{vy:.1f}" font-size="16" font-weight="700" text-anchor="end">'
             f'{MINUS if last["gap"] < 0 else "+"}{dollars(last["gap"])}</text>')
    if near is not last:  # callout below the deepest bar the label spans, with a leader to the bar's end
        j = rows.index(near)
        lab = f"{near['week_end']} · {dollars(near['gap'])} {side(near['gap'])}"
        half = tw(lab, 16) / 2 + 6
        lx = min(max(cx(j), L + half), R - half)
        span = [k for k in range(len(rows)) if abs(cx(k) - lx) < half + bw / 2]
        deep = max(Y(rows[k]['gap']) for k in span)
        ly = min(deep + 46, B - 8)
        s.append(f'<line x1="{cx(j):.1f}" x2="{cx(j):.1f}" y1="{Y(near["gap"]) + 4:.1f}" y2="{ly - 20:.1f}" stroke="{SECOND}"/>')
        s.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="16" font-weight="600" text-anchor="middle">{e(lab)}</text>')
    s.append(f'<line x1="{L}" x2="{R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="{TEXT}" stroke-width="1.5"/>')
    s.append(f'<text x="{L + 4}" y="{Y(0) - 8:.1f}" font-size="16" fill="{SECOND}">break-even ($100 × net mNAV)</text>')
    return card([firm], hero(eyebrow, number, '', context) + s, asof), f'{eyebrow}: {number}. {context}', near


# 3. replay: the (q, m) map week by week

def nearest_date(d):
    """Date with both MSTR and BMNR on the map whose summed |gap| is smallest, and its caption."""
    g = {f: {r['week_end']: r for r in gap_rows(d['weeks'], f)} for f in ('MSTR', 'BMNR')}
    both = sorted(set(g['MSTR']) & set(g['BMNR']))
    w = min(both, key=lambda w: abs(g['MSTR'][w]['gap']) + abs(g['BMNR'][w]['gap']))
    a, b = g['MSTR'][w]['gap'], g['BMNR'][w]['gap']
    return w, f"{w}: STRC {dollars(a)} {side(a)} break-even, BMNP {dollars(b)} {side(b)}"


def ease(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def replay(d, asof):
    pts = {f: {w['week_end']: (w['q'], w['m']) for w in d['weeks']
               if w['firm'] == f and w['m'] is not None and w['q'] is not None} for f in ('MSTR', 'BMNR')}
    dates = sorted(set(pts['MSTR']) | set(pts['BMNR']))
    qs = [q for f in pts for q, _ in pts[f].values()]
    ms = [m for f in pts for _, m in pts[f].values()]
    pad = lambda v: (max(v) - min(v)) * 0.08
    qlo, qhi, mlo, mhi = min(qs) - pad(qs), max(qs) + pad(qs), min(ms) - pad(ms), max(ms) + pad(ms)
    L, R, T, B = 124, 744, 128, 488
    X = lambda v: L + (v - qlo) / (qhi - qlo) * (R - L)
    Y = lambda v: B - (v - mlo) / (mhi - mlo) * (B - T)
    near, caption = nearest_date(d)
    a, b = min(qlo, mlo) - 1, max(qhi, mhi) + 1  # diagonal endpoints well outside the plot, clipped
    base = [f'<clipPath id="plot"><rect x="{L}" y="{T}" width="{R - L}" height="{B - T}"/></clipPath>',
            f'<rect x="{L}" y="{T}" width="{R - L}" height="{B - T}" fill="{PANEL}"/>',
            '<g clip-path="url(#plot)">',
            f'<polygon points="{X(a):.1f},{Y(a):.1f} {X(b):.1f},{Y(b):.1f} {X(a):.1f},{Y(b):.1f}" fill="{COLOR["MSTR"]}" fill-opacity="0.06"/>',
            f'<polygon points="{X(a):.1f},{Y(a):.1f} {X(b):.1f},{Y(b):.1f} {X(b):.1f},{Y(a):.1f}" fill="{COLOR["BMNR"]}" fill-opacity="0.06"/>']
    for t in nice(qlo, qhi, 5):
        if qlo <= t <= qhi:
            base.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{T}" y2="{B}" stroke="{GRID}"/>')
    for t in nice(mlo, mhi, 5):
        if mlo <= t <= mhi:
            base.append(f'<line x1="{L}" x2="{R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="{GRID}"/>')
    base.append(f'<line x1="{X(a):.1f}" y1="{Y(a):.1f}" x2="{X(b):.1f}" y2="{Y(b):.1f}" stroke="{TEXT}" stroke-width="1.5" stroke-dasharray="7 6"/>')
    base.append('</g>')
    for t in nice(qlo, qhi, 5):
        if qlo <= t <= qhi:
            base.append(f'<text x="{X(t):.1f}" y="{B + 24}" font-size="16" text-anchor="middle" fill="{MUTED}">{t:.2f}</text>')
    for t in nice(mlo, mhi, 5):
        if mlo <= t <= mhi:
            base.append(f'<text x="{L - 10}" y="{Y(t) + 5:.1f}" font-size="16" text-anchor="end" fill="{MUTED}">{t:.2f}</text>')
    # m = q label: just below the diagonal, 70% along its visible part, rotated to its on-screen slope
    v0, v1 = max(qlo, mlo), min(qhi, mhi)
    v = v0 + 0.7 * (v1 - v0)
    ang = math.degrees(math.atan2(-(B - T) / (mhi - mlo), (R - L) / (qhi - qlo)))
    base += [f'<text x="{X(v):.1f}" y="{Y(v):.1f}" dy="22" font-size="16" text-anchor="middle" fill="{TEXT}" '
             f'transform="rotate({ang:.1f} {X(v):.1f} {Y(v):.1f})">m = q</text>',
             f'<text x="{L + 14}" y="{T + 28}" font-size="16" fill="{COLOR["MSTR"]}">Strategy\'s rotation adds (m &gt; q)</text>',
             f'<text x="{R - 14}" y="{B - 14}" font-size="16" text-anchor="end" fill="{COLOR["BMNR"]}">BitMine\'s rotation adds (m &lt; q)</text>',
             f'<text x="{R}" y="{B + 50}" font-size="16" text-anchor="end" fill="{MUTED}">q = preferred close / $100 →</text>',
             f'<text transform="translate({L - 62} {(T + B) / 2}) rotate(-90)" font-size="16" text-anchor="middle" fill="{MUTED}">m = net mNAV →</text>',
             f'<text x="{PAD}" y="100" font-size="22" fill="{SECOND}">Net mNAV m against preferred q · weekly since {dates[0]}</text>']
    TY = 578  # timeline
    TX = lambda k: L + k / (len(dates) - 1) * (R - L)
    base.append(f'<line x1="{L}" x2="{R}" y1="{TY}" y2="{TY}" stroke="{GRID}" stroke-width="4" stroke-linecap="round"/>')
    base += [f'<line x1="{TX(k):.1f}" x2="{TX(k):.1f}" y1="{TY - 7}" y2="{TY + 7}" stroke="{MUTED}"/>' for k in range(len(dates))]
    PX = 784

    def frame(i, t, cap):
        u = ease(t)
        s = list(base)
        s.append(f'<line x1="{L}" x2="{TX(i + u):.1f}" y1="{TY}" y2="{TY}" stroke="{TEXT}" stroke-opacity="0.6" stroke-width="4" stroke-linecap="round"/>')
        s.append(f'<circle cx="{TX(i + u):.1f}" cy="{TY}" r="7" fill="{TEXT}" stroke="{SURFACE}" stroke-width="2"/>')
        now = {}
        for f in ('MSTR', 'BMNR'):
            c, have = COLOR[f], [w for w in dates[:i + 1] if w in pts[f]]
            if not have:
                continue
            q, m = pts[f][have[-1]]
            nxt = dates[i + 1] if i + 1 < len(dates) else None
            if u and nxt in pts[f] and have[-1] == dates[i]:
                q2, m2 = pts[f][nxt]
                q, m = q + (q2 - q) * u, m + (m2 - m) * u
            now[f] = (q, m)
            trail = [pts[f][w] for w in have] + [(q, m)]
            n = len(trail) - 1
            for k in range(n):  # trail segments fade from 0.15 (oldest) to 0.6 (now)
                (q0, m0), (q1, m1) = trail[k], trail[k + 1]
                op = 0.15 + 0.45 * (k + 1) / n
                s.append(f'<line x1="{X(q0):.1f}" y1="{Y(m0):.1f}" x2="{X(q1):.1f}" y2="{Y(m1):.1f}" stroke="{c}" stroke-width="2" stroke-opacity="{op:.2f}" stroke-linecap="round"/>')
            for k, (q0, m0) in enumerate(trail[:-1]):
                s.append(f'<circle cx="{X(q0):.1f}" cy="{Y(m0):.1f}" r="3" fill="{c}" fill-opacity="{0.25 + 0.5 * (k + 1) / n:.2f}"/>')
            s.append(f'<circle cx="{X(q):.1f}" cy="{Y(m):.1f}" r="24" fill="{c}" fill-opacity="0.2"/>')
            s.append(f'<circle cx="{X(q):.1f}" cy="{Y(m):.1f}" r="7" fill="{c}" stroke="{SURFACE}" stroke-width="3"/>')
        s.append(f'<text x="{W - PAD}" y="{T + 46}" font-size="56" font-weight="750" letter-spacing="-1.5" text-anchor="end">{dates[i]}</text>')
        y = T + 104
        for f in ('MSTR', 'BMNR'):
            svg, _ = chip(PX, y, f)
            s.append(svg)
            pref = FIRMS[f]['pref']
            if f in now:
                q, m = now[f]
                close, be = round(LIQ_PREF * q, 2), round(LIQ_PREF * m, 2)
                g = round(close - be, 2)
                s.append(f'<text x="{PX}" y="{y + 34}" font-size="22" fill="{SECOND}">{pref} {dollars(close)} · break-even {dollars(be)}</text>')
                s.append(f'<text x="{PX}" y="{y + 70}" font-size="30" font-weight="700" fill="{COLOR[f]}">{dollars(g)} {side(g)}</text>')
            else:
                s.append(f'<text x="{PX}" y="{y + 34}" font-size="22" fill="{MUTED}">{pref} not yet issued</text>')
            y += 120
        if cap:
            s.append(f'<rect x="{PX}" y="{y - 16}" width="{W - PAD - PX}" height="52" rx="12" fill="{PANEL}" stroke="{BORDER}"/>')
            s.append(f'<text x="{PX + 18}" y="{y + 17}" font-size="20" font-weight="600">Closest week for both firms</text>')
        return card(['MSTR', 'BMNR'], s, asof)

    out = []
    for i in range(len(dates)):
        cap = caption if dates[i] == near else None
        hold = HOLD_END if i == len(dates) - 1 else HOLD_NEAR if cap else 0
        out += [frame(i, 0, cap)] * (1 + hold)
        if i + 1 < len(dates):
            out += [frame(i, k / FRAMES, None) for k in range(1, FRAMES)]
    return out, dates, caption


# 4. receipts, top actions card, posts

def receipt_rows(data_dir, weeks):
    """Filed actions from attribution.csv with value to common, sorted by |value| desc."""
    at = {(w['firm'], w['week_end']): w for w in weeks}
    rows = []
    for a in read(os.path.join(data_dir, 'attribution.csv')):
        if a['action'] not in ACTION_WORDS:
            continue
        w = at[(a['firm'], a['week_end'])]
        words = ACTION_WORDS[a['action']]
        if a['action'] in ('issue_pref', 'retire_pref', 'buy_coin', 'sell_coin'):
            words += ' ' + a['ticker']
        at_ = f" at m {float(a['m']):.3f}" if a['m'] else f" at q {float(a['q']):.4f}" if a['q'] else ''
        rows.append({'firm': a['firm'], 'week_end': a['week_end'], 'what': f"{words} {usd(float(a['usd']))}{at_}",
                     'value': float(a['dn_exact']) * w['S'] * w['p'], 'url': a['filing_url']})
    return sorted(rows, key=lambda r: -abs(r['value']))


def receipts(rows):
    return '# Receipts: filed actions by value to common\n\n' + '\n'.join(
        f"- {FIRMS[r['firm']]['name']} {r['week_end']}: {r['what']}, value to common {usd(r['value'], True)} {r['url']}"
        for r in rows) + '\n'


def top_svg(rows, since, asof):
    top = rows[:TOP_N]
    s = [f'<text x="{PAD}" y="104" font-size="22" fill="{SECOND}">All three firms · since {since}</text>',
         f'<text x="{PAD}" y="160" font-size="46" font-weight="750" letter-spacing="-1">Largest filed actions by value to common</text>',
         f'<text x="{PAD}" y="200" font-size="22" fill="{SECOND}">Value to common = change in net coins per share × shares × coin price, that week.</text>']
    T, rh = 232, 42
    x0, x1, room = 560, W - PAD, 96  # chart span; room for value labels at each end
    neg = max([-r['value'] for r in top if r['value'] < 0] + [0])
    pos = max([r['value'] for r in top if r['value'] > 0] + [0])
    sc = (x1 - x0 - 2 * room) / (neg + pos)
    Z = x0 + room + neg * sc
    for k, r in enumerate(top):
        y = T + k * rh
        c, v = COLOR[r['firm']], r['value']
        s.append(f'<text x="{PAD}" y="{y + 25}" font-size="17"><tspan font-weight="600" fill="{c}">'
                 f"{FIRMS[r['firm']]['name']} {r['week_end'][5:]}</tspan><tspan fill=\"{SECOND}\"> · {e(r['what'])}</tspan></text>")
        xe = Z + v * sc
        s.append(hbar(y + 8, 24, Z, xe, c))
        s.append(f'<text x="{xe + (8 if v > 0 else -8):.1f}" y="{y + 26}" font-size="17" font-weight="700" '
                 f'text-anchor="{"start" if v > 0 else "end"}">{usd(v, True)}</text>')
    s.append(f'<line x1="{Z}" x2="{Z}" y1="{T - 4}" y2="{T + len(top) * rh + 4}" stroke="{TEXT}" stroke-width="1.5"/>')
    return card(list(COLOR), s, asof)


def posts(d, data_dir, gaps, dates, caption, rows):
    t = d['totals']
    out = []
    for f in ('MSTR', 'BMNR', 'SBET'):
        name = FIRMS[f]['name']
        out.append((f'split-{f}.png', f"{name} since {t[f]['since']}: {usd(t[f]['observed'], True)} in value to common. "
                    f"The coin price step accounts for {usd(t[f]['price'], True)}; all other steps "
                    f"{usd(t[f]['observed'] - t[f]['price'], True)}. Net coins per share, Strategy's own definition."))
    for f, (_, text, near) in gaps.items():
        out.append((f'gap-{f}.png', f"{text} Closest week: {near['week_end']}, {dollars(near['gap'])} {side(near['gap'])}. "
                    f"Break-even = $100 × net mNAV."))
    out.append(('replay.mp4', f"Net mNAV against preferred price, week by week, {dates[0]} to {dates[-1]}. "
                f"Strategy's rotation adds above the line m = q; BitMine's adds below it. Closest week: {caption.replace(': ', ', ', 1)}."))
    top = '; '.join(f"{FIRMS[r['firm']]['name']} {r['week_end'][5:]} {r['what']}: {usd(r['value'], True)}" for r in rows[:3])
    out.append(('receipts-top.png', f"Largest filed actions by value to common since {t['MSTR']['since']}: {top}. "
                "Every row links to its filing."))
    issue = next(a for a in read(os.path.join(data_dir, 'attribution.csv'))
                 if a['firm'] == 'BMNR' and a['action'] == 'issue_pref')
    w = next(x for x in d['weeks'] if x['firm'] == 'BMNR' and x['week_end'] == issue['week_end'])
    prev = max((x for x in d['weeks'] if x['firm'] == 'BMNR' and x['week_end'] < w['week_end']), key=lambda x: x['week_end'])
    q = float(issue['q'])
    v = float(issue['dn_exact']) * w['S'] * w['p']
    out.append(('(poll, no image)', f"Week ending {w['week_end']}: BitMine sold BMNP at q {q:.2f} "
                f"(${LIQ_PREF * q:.0f} per $100 notional), {usd(float(issue['usd']))} net. Its net mNAV was "
                f"{prev['m']:.3f} the week before. Did net ETH per share go up or down that week? Up / Down"))
    dn = w['n'] - prev['n']
    out.append(('(poll answer, no image)', f"{'Down' if dn < 0 else 'Up'}: net ETH per share went from {prev['n']:.9f} "
                f"to {w['n']:.9f}, value to common {usd(w['observed'], True)}. The BMNP sale alone: {usd(v, True)}, "
                f"since q {q:.2f} is below 1."))
    for img, text in out:
        assert len(text) < 280, (img, len(text), text)
    return ('# Draft posts (each under 280 characters)\n\n' +
            '\n\n'.join(f'## {img}\n\n{text}\n\n({len(text)} characters)' for img, text in out) + '\n'), [x for _, x in out]


def main(data_dir='data', root='private/social'):
    d = build(data_dir, online=False)
    asof = max(w['week_end'] for w in d['weeks'] if w['firm'] == 'MSTR')
    out = os.path.join(root, asof)
    os.makedirs(out, exist_ok=True)
    files = {}
    for f in ('MSTR', 'BMNR', 'SBET'):
        files[f'split-{f}.svg'] = split_svg(d, f, asof)[0]
    gaps = {f: gap_svg(d, f, asof) for f in ('MSTR', 'BMNR')}
    for f, g in gaps.items():
        files[f'gap-{f}.svg'] = g[0]
    rows = receipt_rows(data_dir, d['weeks'])
    files['receipts-top.svg'] = top_svg(rows, min(x['since'] for x in d['totals'].values()), asof)
    frames, dates, caption = replay(d, asof)
    files['posts.md'] = posts(d, data_dir, gaps, dates, caption, rows)[0]
    files['receipts.md'] = receipts(rows)
    for name, text in files.items():
        with open(os.path.join(out, name), 'w') as fh:
            fh.write(text)
    rd = os.path.join(out, 'replay')
    shutil.rmtree(rd, ignore_errors=True)
    os.makedirs(rd)
    for i, svg in enumerate(frames):
        with open(os.path.join(rd, f'frame-{i:04d}.svg'), 'w') as fh:
            fh.write(svg)
    for name in files:
        print(os.path.join(out, name))
    print(f'{rd}/frame-0000.svg ... frame-{len(frames) - 1:04d}.svg ({len(frames)} frames, {len(dates)} dates)')
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
