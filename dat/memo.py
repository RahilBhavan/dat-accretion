"""Step 6 (`python -m dat.memo`): one-page memo -> docs/memo.md, docs/memo.html, docs/map.svg. stdlib only.

Figures come from data/weekly.csv (title counts) and dat.build_site.build (headline sentences, map points, totals by
cause), so every memo figure matches site/data.json. The map is a static, light-theme copy of the page's break-even
map (site/app.js drawMap), drawn with equal units on both axes so m = q is a true 45° line. The PDF is built from
memo.html (README, "Memo"); refresh.yml builds it weekly, CI does not. Fonts (M25) load from ../site/fonts, which
resolves from docs/ both locally and in refresh.yml (file://$PWD/docs/memo.html).
"""
import html, math, os, sys
from dat.balances import read, bmnr_s_bias
from dat.build_site import build, FIRMS, ADDS, counts, title, s_bias_text  # noqa: F401 (ADDS re-exported)

PAGE = 'https://rahilbhavan.github.io/dat-accretion/'
REPO = 'https://github.com/RahilBhavan/dat-accretion'
FWP = 'https://www.sec.gov/Archives/edgar/data/1050446/000119312526363557/d431748dfwp.htm'
COLOR = {'MSTR': '#2a78d6', 'BMNR': '#eb6834', 'SBET': '#4a3aa7'}
DASH = {'MSTR': 'none', 'BMNR': '5 2.5', 'SBET': '1.2 2.4'}  # each firm's joining line, legible in grayscale
FONTS = '../site/fonts/'  # relative to docs/, where memo.html and map.svg live
FONT_FACE = (f'@font-face {{ font-family: "Source Serif 4"; src: url("{FONTS}source-serif-4.woff2") format("woff2"); '
             'font-weight: 200 900; }\n'
             f'@font-face {{ font-family: "IBM Plex Mono"; src: url("{FONTS}ibm-plex-mono-400.woff2") format("woff2"); '
             'font-weight: 400; }\n'
             f'@font-face {{ font-family: "IBM Plex Mono"; src: url("{FONTS}ibm-plex-mono-500.woff2") format("woff2"); '
             'font-weight: 500 700; }')
MONO = '"IBM Plex Mono", Menlo, Consolas, monospace'
SERIF = '"Source Serif 4", Georgia, serif'


def week_biases(data_dir, weekly):
    """{BitMine week with m and q: its own S bias} (dat.balances.bmnr_s_bias as of that week)."""
    return {r['week_end']: bmnr_s_bias(data_dir, r['week_end'])[0] for r in weekly
            if r['firm'] == 'BMNR' and r['m'] and r['q']}


def _bmnr(weekly):
    return [r for r in weekly if r['firm'] == 'BMNR' and r['m'] and r['q']]


def bias_flips(weekly, biases):
    """BitMine weeks where removing that week's own S bias puts m at or below q (the rotation would add there)."""
    missing = [r['week_end'] for r in _bmnr(weekly) if r['week_end'] not in biases]
    if missing:  # raise, not assert: must hold under python -O too
        raise ValueError(f'BitMine weeks {missing} have no S bias: rerun dat.balances')
    return [r['week_end'] for r in _bmnr(weekly) if not float(r['m']) * (1 - biases[r['week_end']]) > float(r['q'])]


def closest(weekly, biases):
    """Footnote on the weeks nearest m = q, from weekly.csv. biases: {BitMine week: S bias as a share of S at that
    week} (dat.balances.bmnr_s_bias). Each week is tested against its own bias; the text states the latest."""
    rows = lambda f: [r for r in weekly if r['firm'] == f and r['m'] and r['q']]
    near = {}
    for f in ('MSTR', 'BMNR'):
        r = min(rows(f), key=lambda r: abs(float(r['m']) / float(r['q']) - 1))
        d = float(r['m']) / float(r['q']) - 1
        near[f] = f"{FIRMS[f]['name']} {r['week_end']}, m {abs(d):.2%} {'above' if d > 0 else 'below'} q"
    cross = bias_flips(weekly, biases)
    asof = max(r['week_end'] for r in rows('BMNR'))
    tail = ("removing it leaves m above q in every BitMine week." if not cross else
            f"removing it puts m at or below q in {len(cross)} of {len(rows('BMNR'))} BitMine weeks "
            f"({', '.join(cross)}), where BitMine's rotation would add.")
    return (f"Closest weeks to the line: {near['MSTR']}; {near['BMNR']}. BitMine's estimated diluted share count S "
            f"carries {s_bias_text(biases[asof], asof)} because its releases count staked ETH as purchased, which this "
            f"memo costs as cash; the bias raises m by the same proportion, and {tail}")


def mark(firm, cx, cy, r, style):
    if firm == 'SBET':  # equilateral triangle of equal area, as on the page
        a = r * 2.694
        h = a * 0.866
        top = cy - h * 2 / 3
        return (f'<path d="M{cx:.1f},{top:.1f}L{cx + a / 2:.1f},{top + h:.1f}L{cx - a / 2:.1f},{top + h:.1f}Z" '
                f'style="{style}"/>')
    if firm == 'MSTR':
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" style="{style}"/>'
    h = r * 0.886  # square of equal area, as on the page
    return f'<rect x="{cx - h:.1f}" y="{cy - h:.1f}" width="{2 * h:.1f}" height="{2 * h:.1f}" rx="1" style="{style}"/>'


def domain(pts, pad=0.02):
    """Each axis cropped to its data plus pad, rounded out to 0.01. -> ((qlo, qhi), (mlo, mhi))."""
    lo = lambda v: math.floor((min(v) - pad) * 100) / 100
    hi = lambda v: math.ceil((max(v) + pad) * 100) / 100
    qs, ms = [w['qx'] for w in pts], [w['m'] for w in pts]
    return (lo(qs), hi(qs)), (lo(ms), hi(ms))


def map_svg(weeks, ppu=420):
    """Break-even map: x = q, y = m, m = q diagonal (as on the page, site/app.js drawMap). One unit of q and one of m
    span the same ppu pixels, so the diagonal is a true 45° line; each axis is cropped to its data. Drawn at 1 SVG
    px = 1 CSS px, so the 10px labels print at 7.5pt. Tufte edits: no grid; range-frame axes span only the data and
    are labeled at their ends (and at 1.00); region labels and the latest week's labels sit on the plot. Earlier
    weeks are open marks joined in date order, each firm's line in its own dash pattern."""
    # SharpLink has no preferred (q None): its marks sit at q = 1, where m = q is m = 1 (as on the page).
    pts = [{**w, 'qx': 1.0 if w['q'] is None else w['q']} for w in weeks
           if w['m'] is not None and (w['q'] is not None or w['firm'] == 'SBET')]
    (qlo, qhi), (mlo, mhi) = domain(pts)
    mlo -= 0.07  # a strip under the data for the BitMine region label (below the diagonal, as q > m there)
    M = {'l': 36, 'r': 78, 't': 52, 'b': 88}
    pw, ph = (qhi - qlo) * ppu, (mhi - mlo) * ppu
    W, H = round(M['l'] + pw + M['r']), round(M['t'] + ph + M['b'])
    X = lambda v: M['l'] + (v - qlo) * ppu
    Y = lambda v: M['t'] + (mhi - v) * ppu
    R = 3.6
    qs, ms = [w['qx'] for w in pts], [w['m'] for w in pts]
    base = M['t'] + ph
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="Break-even map: net mNAV m against preferred price over notional q, one mark per firm-week" '
         f'font-family=\'{MONO}\' font-size="10" fill="#222">',
         f'<style>\n{FONT_FACE}\n</style>',
         f'<rect width="{W}" height="{H}" fill="#fff"/>']
    tx = lambda x, y, t, a='start', extra='': s.append(
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{a}"{extra}>{t}</text>')
    # Axis titles above and below the plot.
    tx(M['l'] - 8, 14, 'm = net mNAV', extra=' fill="#333"')
    # Range frames: each axis line spans only the data's range.
    s.append(f'<line x1="{X(min(qs)):.1f}" x2="{X(max(qs)):.1f}" y1="{base + 6:.1f}" y2="{base + 6:.1f}" stroke="#777"/>')
    s.append(f'<line x1="{M["l"] - 6}" x2="{M["l"] - 6}" y1="{Y(max(ms)):.1f}" y2="{Y(min(ms)):.1f}" stroke="#777"/>')
    for v, a in ((min(qs), 'start'), (max(qs), 'end')):
        tx(X(v), base + 18, f'{v:.2f}', a, ' fill="#333"')
    for v in (min(ms), 1.0, max(ms)):
        tx(M['l'] - 9, Y(v) + 3.5, f'{v:.2f}', 'end', ' fill="#333"')
    tx(M['l'] - 8, base + 32, 'q = preferred close / $100', extra=' fill="#333"')
    tx(M['l'] - 8, base + 44, '(SharpLink, no preferred, at q = 1)', extra=' fill="#333"')
    d0, d1 = max(qlo, mlo), min(qhi, mhi)
    s.append(f'<line x1="{X(d0):.1f}" y1="{Y(d0):.1f}" x2="{X(d1):.1f}" y2="{Y(d1):.1f}" stroke="#222" '
             'stroke-width="0.9" stroke-dasharray="7 3.5"/>')
    tx(X(d0) + 10, Y(d0) + 2, 'm = q')  # the empty lower-left end of the line
    # Region labels, each inside its region: upper left is m > q, the strip under the data is m < q.
    tx(M['l'] + 2, M['t'] - 22, "Strategy's rotation", extra=' font-weight="500"')
    tx(M['l'] + 2, M['t'] - 10, 'adds above the line (m &gt; q)', extra=' font-weight="500"')
    tx(X(qhi) - 2, base - 16, "BitMine's rotation adds", 'end', ' font-weight="500"')
    tx(X(qhi) - 2, base - 4, 'below the line (m &lt; q)', 'end', ' font-weight="500"')
    latest = {}
    for firm in ('MSTR', 'BMNR', 'SBET'):
        path = sorted((w for w in pts if w['firm'] == firm), key=lambda w: w['week_end'])
        if not path:
            continue
        latest[firm] = path[-1]
        c = COLOR[firm]
        if len(path) > 1:
            s.append(f'<polyline points="{" ".join(f"{X(w["qx"]):.1f},{Y(w["m"]):.1f}" for w in path)}" '
                     f'fill="none" stroke="{c}" stroke-opacity="0.75" stroke-width="1" stroke-dasharray="{DASH[firm]}"/>')
        for w in path[:-1]:
            s.append(mark(firm, X(w['qx']), Y(w['m']), R, f'fill:#fff;stroke:{c};stroke-width:1.1'))
    for firm, w in latest.items():
        c, cx, cy = COLOR[firm], X(w['qx']), Y(w['m'])
        s.append(mark(firm, cx, cy, R + 1.3, f'fill:{c};stroke:{c};stroke-width:1.1'))
        lx = X(qhi) + 6
        tx(lx, cy - 1, FIRMS[firm]['name'], extra=' font-weight="500"')
        tx(lx, cy + 10, w['week_end'], extra=' fill="#333"')
    for i, line in enumerate(('Open marks: earlier weeks, joined', 'in date order. Circle Strategy,',
                              'square BitMine, triangle SharpLink.')):
        tx(M['l'] - 8, H - 25 + 12 * i, line, extra=' fill="#333"')
    return '\n'.join(s + ['</svg>']) + '\n'


def table(d, flips=()):
    """Answer first: each firm's latest m, preferred close and break-even. -> (header, rows, caption).
    flips: BitMine weeks where the S bias puts m at or below q (bias_flips); the BitMine row is marked when its week
    is one of them, and the caption says why."""
    h = {x['firm']: x for x in d['headline']}
    rows, extra = [], []
    for f in ('MSTR', 'BMNR'):
        x, side = h[f], FIRMS[f]['side']
        cond = f"{x['pref']} {side} break-even"
        if f == 'BMNR' and x['week_end'] in flips:
            cond += '*'
            extra.append(f"*BitMine's {x['week_end']} gap between m and q is within the S-estimate bias; see the "
                         "note under the map.")
        rows.append([FIRMS[f]['name'], x['week_end'], f"{x['m']:.3f}", f"{x['pref']} ${x['pref_close']:.2f}",
                     f"${x['break_even']:.2f}", cond])
    x = h['SBET']
    rows.append(['SharpLink', f"{x['week_end']} (last filed)", f"{x['m']:.3f}", 'no preferred', 'm = 1',
                 'issue if m > 1; buy back if m < 1'])
    header = ['Firm', 'Week ending', 'Net mNAV m', 'Preferred close', 'Break-even ($100 × m)', 'Rotation adds while']
    caption = ' '.join([h[f]['close_sentence'] for f in ('MSTR', 'BMNR', 'SBET')] + extra)
    return header, rows, caption


KEY = ("Key. m, net mNAV: share price over net coin value per share. q: preferred close over its $100 notional. "
       "Net sats: net bitcoin per share in satoshis (100 million per BTC). Rotation: Strategy sells common and retires "
       "STRC; BitMine sells BMNP and buys back common. STRC: Strategy's perpetual preferred, $100 stated amount. "
       "BMNP: BitMine's 9.50% cumulative preferred, $100 liquidation preference.")

CAUSES = [('Coin price', 'price'), ('In-the-money flips', 'itm_flip'), ('Filed actions', 'actions'),
          ('Estimated issuance', 'est_issuance'), ('Carry', 'carry'), ('Residual', 'residual'),
          ('Observed', 'observed')]


def usd_m(v):
    return ('+' if v >= 0 else '−') + f'${abs(v) / 1e6:,.1f}M'


def causes(d):
    """Value to common by cause since each firm's first week, from build()'s totals (site/data.json "totals").
    -> (header, rows, caption). Estimated issuance applies to BitMine only (method.md)."""
    t = d['totals']
    firms = ('MSTR', 'BMNR', 'SBET')
    rows = [[label] + [('n/a' if k == 'est_issuance' and f != 'BMNR' else usd_m(t[f][k])) for f in firms]
            for label, k in CAUSES]
    m = t['MSTR']
    since = {}
    for f in firms:  # firms sharing a first week are named together
        since.setdefault(t[f]['since'], []).append(FIRMS[f]['name'])
    since = ', '.join(' and '.join(names) + ' ' + w for w, names in since.items())
    caption = (f"Value to common (change in n × S × coin price) by cause, summed from each firm's first week "
               f"({since}); the parts sum to the observed change before rounding. Strategy's residual is {usd_m(m['residual'] - m['residual_checked'])} before "
               f"{m['checked_from']}, when the 8-Ks did not itemize cash flows, and {usd_m(m['residual_checked'])} in "
               "the weeks since, which the R check tests against the filings. BitMine's and SharpLink's residuals are "
               "report only.")
    return ['Since first week'] + [FIRMS[f]['name'] for f in firms], rows, caption


def count_sentence(c):
    """The weekly counts (M12), without restating the rule the table and the second paragraph give."""
    (a, n, _, _), (b, k, _, _), (x, y, _, _) = c['MSTR'], c['BMNR'], c['SBET']
    return (f"STRC closed below its break-even in {a} of {n} filed weeks, and BMNP closed below its break-even in "
            f"{k - b} of {k}. SharpLink's m was below 1 on {x} of {y} filed dates.")


def paragraphs(c):
    ruler = ("Digital asset treasury (DAT) companies hold bitcoin or ether and raise money by selling stock. This memo "
             "measures each share sale, buyback and preferred trade since 2026-06-01 with Strategy's own net coins per "
             "share definition, applied to all three firms (glossary, Strategy's 2026-08-24 free writing prospectus, "
             "FWP). Net coins N are coins held (C) plus USD assets (R), less out-of-the-money convertible debt and "
             "preferred notional, converted to coins at the coin price; n is N per fully diluted share, and S is that "
             "share count.")
    line = ("Issuing common adds to n while m is above 1; retiring preferred adds while q is below 1. So Strategy's "
            "rotation adds while m > q and stops adding when STRC trades above $100 × m; BitMine's adds while m < q "
            "and stops adding when BMNP trades below $100 × m. SharpLink has no preferred, so no rotation line applies.")
    return ruler, line, count_sentence(c)


def footnote(c, weekly, biases):
    (_, n, m0, m1), (_, k, b0, b1), (_, y, s0, s1) = c['MSTR'], c['BMNR'], c['SBET']
    return [closest(weekly, biases),
        f"Period: Strategy weeks ending {m0} to {m1} ({n} filed dates, including the 2026-06-30 quarter-end holdings "
        f"row); BitMine weeks ending {b0} to {b1} ({k} weeks with a BMNP price; BMNP was issued 2026-06-10); SharpLink "
        f"filed holdings dates {s0} to {s1} ({y} dates; SharpLink states holdings only on those dates, and this memo "
        "carries nothing forward between them).",
        "Sources: Strategy weekly 8-Ks and Q2 10-Q (EDGAR CIK 1050446); BitMine weekly 8-K releases and 10-Q (EDGAR CIK "
        "1829311); SharpLink 8-K releases and Q2 10-Q (EDGAR CIK 1981535); Yahoo Finance daily closes for MSTR, STRC, "
        "STRK, STRF, STRD, BMNR, BMNP and SBET; CoinGecko BTC and ETH "
        "closes. Each week uses closes from the last US trading day on or before the week's end.",
        "Labeled estimates: this memo estimates BitMine's diluted share count S between filings. It anchors S to the "
        "10-Q share counts for 2026-05-31 and 2026-07-09 and estimates unreported issuance as the week's unexplained "
        "change in cash divided by the BMNR close. BitMine's USD assets R are its stated cash and marketable "
        "securities, so R includes securities. The USD of each BitMine ETH purchase is units × that week's ETH close. "
        "SharpLink's coins held C include the liquid staking tokens (LSTs) LsETH and weETH at their stated "
        "as-if-redeemed ETH equivalence; its ETH change beyond stated purchases is inferred staking and LST accrual; "
        "its R is 2026-06-30 balance-sheet cash rolled by filed cash flows.",
    ]


def md_grid(header, rows):
    return '\n'.join(['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)] +
                     ['| ' + ' | '.join(r) + ' |' for r in rows])


def md(t, tab, key, paras, cause, notes):
    header, rows, caption = tab
    ch, crows, ccap = cause
    return '\n\n'.join([f'# {t}', md_grid(header, rows), f'<sub>{caption}</sub>', f'<sub>{key}</sub>', *paras,
                        md_grid(ch, crows), f'<sub>{ccap}</sub>',
                        '![Break-even map: m against q, one mark per firm-week](map.svg)',
                        '---', *(f'<sub>{x}</sub>' for x in notes),
                        f'<sub>Page: {PAGE}. Method: {REPO}/blob/main/docs/methodology.md. '
                        f'Code and data: {REPO}. Definition source: {FWP}.</sub>']) + '\n'


CSS = f"""{FONT_FACE}
@page {{ size: Letter; margin: 0.5in; }}
body {{ font: 9.2pt/1.34 {SERIF}; color: #222; max-width: 7.5in; margin: 0 auto; }}
h1 {{ font-size: 13pt; line-height: 1.22; margin: 0 0 0.08in; font-weight: 600; }}
p {{ margin: 0 0 0.08in; }}
figure {{ float: right; margin: 0.02in 0 0.04in 0.18in; }}
figure svg {{ display: block; }}
table {{ border-collapse: collapse; margin: 0 0 0.04in; font-size: 8.4pt; }}
table.be {{ width: 100%; }}
th, td {{ text-align: left; padding: 2px 6px 2px 0; border-bottom: 1px solid #ddd; white-space: nowrap; }}
th {{ border-bottom: 1.2px solid #222; font-weight: 600; }}
td.n {{ font-family: {MONO}; font-size: 7.8pt; }}
table.cause td.n {{ text-align: right; padding-left: 16px; }}
table.cause th + th {{ text-align: right; padding-left: 16px; }}
table.cause tr:last-child td {{ border-top: 1.2px solid #222; border-bottom: none; font-weight: 600; }}
.note {{ font-size: 7pt; line-height: 1.25; color: #444; margin: 0 0 0.04in; }}
.note.cap {{ margin-bottom: 0.08in; }}
.foot {{ clear: both; padding-top: 0.02in; }}
a {{ color: #1a5aa6; }}
@media screen {{ body {{ margin: 0.6in auto; }} }}"""


def html_table(header, rows, cls, num):
    """num(i): whether column i holds figures (set in IBM Plex Mono)."""
    e = html.escape
    return (f'<table class="{cls}"><thead><tr>' + ''.join(f'<th>{e(h)}</th>' for h in header) + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join(('<td class="n">' if num(i) else '<td>') + f'{e(c)}</td>' for i, c in enumerate(r))
                      + '</tr>' for r in rows) + '</tbody></table>')


def page(t, tab, key, paras, cause, notes, svg):
    e = html.escape
    header, rows, caption = tab
    ch, crows, ccap = cause
    links = (f'Page: <a href="{PAGE}">{PAGE}</a>. Method: <a href="{REPO}/blob/main/docs/methodology.md">'
             f'docs/methodology.md</a>. Code and data: <a href="{REPO}">{REPO}</a>. '
             f'Definition source: <a href="{FWP}">Strategy FWP, 2026-08-24</a>.')
    body = [f'<h1>{e(t)}</h1>', html_table(header, rows, 'be', lambda i: i in (2, 3, 4)),
            f'<p class="note">{e(caption)}</p>', f'<p class="note cap">{e(key)}</p>',
            f'<figure>{svg}</figure>', *(f'<p>{e(p)}</p>' for p in paras),
            html_table(ch, crows, 'cause', lambda i: i > 0), f'<p class="note cap">{e(ccap)}</p>',
            '<div class="foot">', *(f'<p class="note">{e(x)}</p>' for x in notes), f'<p class="note">{links}</p>', '</div>']
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<title>{e(t)}</title>\n<style>\n{CSS}\n</style></head>\n<body>\n' + '\n'.join(body) + '\n</body></html>\n')


def main(data_dir='data', out='docs'):
    d = build(data_dir, online=False)
    weekly = read(os.path.join(data_dir, 'weekly.csv'))
    c = counts(weekly)
    biases = week_biases(data_dir, weekly)
    t, paras, notes, svg = title(d['headline']), paragraphs(c), footnote(c, weekly, biases), map_svg(d['weeks'])
    tab, cause = table(d, bias_flips(weekly, biases)), causes(d)
    files = {'map.svg': svg, 'memo.md': md(t, tab, KEY, paras, cause, notes),
             'memo.html': page(t, tab, KEY, paras, cause, notes, svg)}
    for name, text in files.items():
        with open(os.path.join(out, name), 'w') as f:
            f.write(text)
    print(t)
    print('wrote ' + ', '.join(os.path.join(out, n) for n in files))
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
