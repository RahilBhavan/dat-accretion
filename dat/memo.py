"""Step 6 (`python -m dat.memo`): one-page memo -> docs/memo.md, docs/memo.html, docs/map.svg. stdlib only.

Figures come from data/weekly.csv (title counts) and dat.build_site.build (headline sentences, map points).
The map is a static, light-theme copy of the page's break-even map (site/app.js drawMap). The PDF is built
from memo.html (README, "Memo"); refresh.yml builds it weekly, CI does not.
"""
import html, math, os, sys
from dat.balances import read, bmnr_s_bias
from dat.build_site import build, FIRMS, ADDS, counts, title  # noqa: F401 (ADDS re-exported)

PAGE = 'https://rahilbhavan.github.io/dat-accretion/'
REPO = 'https://github.com/RahilBhavan/dat-accretion'
FWP = 'https://www.sec.gov/Archives/edgar/data/1050446/000119312526363557/d431748dfwp.htm'
COLOR = {'MSTR': '#2a78d6', 'BMNR': '#eb6834', 'SBET': '#4a3aa7'}


def week_biases(data_dir, weekly):
    """{BitMine week with m and q: its own S bias} (dat.balances.bmnr_s_bias as of that week)."""
    return {r['week_end']: bmnr_s_bias(data_dir, r['week_end'])[0] for r in weekly
            if r['firm'] == 'BMNR' and r['m'] and r['q']}


def closest(weekly, biases):
    """Footnote on the weeks nearest m = q, from weekly.csv. biases: {BitMine week: S bias as a share of S at that
    week} (dat.balances.bmnr_s_bias). Each week is tested against its own bias; the text states the latest."""
    rows = lambda f: [r for r in weekly if r['firm'] == f and r['m'] and r['q']]
    near = {}
    for f in ('MSTR', 'BMNR'):
        r = min(rows(f), key=lambda r: abs(float(r['m']) / float(r['q']) - 1))
        d = float(r['m']) / float(r['q']) - 1
        near[f] = f"{FIRMS[f]['name']} {r['week_end']}, m {abs(d):.2%} {'above' if d > 0 else 'below'} q"
    missing = [r['week_end'] for r in rows('BMNR') if r['week_end'] not in biases]
    if missing:  # raise, not assert: must hold under python -O too
        raise ValueError(f'BitMine weeks {missing} have no S bias: rerun dat.balances')
    asof = max(r['week_end'] for r in rows('BMNR'))
    b = biases[asof]
    cross = [r['week_end'] for r in rows('BMNR') if not float(r['m']) * (1 - biases[r['week_end']]) > float(r['q'])]
    tail = ("removing it leaves m above q in every BitMine week." if not cross else
            f"removing it puts m at or below q in {len(cross)} of {len(rows('BMNR'))} BitMine weeks "
            f"({', '.join(cross)}), where BitMine's rotation would add.")
    return (f"Closest weeks to the line: {near['MSTR']}; {near['BMNR']}. BitMine's estimated share count carries a "
            f"known upward bias of up to {b:.2%} of S by {asof} (staked ETH costed as purchases), which raises "
            f"m by the same proportion; {tail}")


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


def ticks(lo, hi, step=0.05):
    return [round(lo + i * step, 2) for i in range(int(round((hi - lo) / step)) + 1)]


def map_svg(weeks, W=800, H=480):
    """Break-even map: x = q, y = m on one shared domain, m = q diagonal (as on the page, site/app.js drawMap).
    Tufte edits: no grid; range-frame axes span only the data and are labeled at their ends (and at 1.00); region
    labels and the latest week's label sit on the plot. Earlier weeks are open marks joined in date order."""
    # SharpLink has no preferred (q None): its marks sit at q = 1, where m = q is m = 1 (as on the page).
    pts = [{**w, 'qx': 1.0 if w['q'] is None else w['q']} for w in weeks
           if w['m'] is not None and (w['q'] is not None or w['firm'] == 'SBET')]
    M = {'l': 58, 'r': 16, 't': 14, 'b': 70}
    vals = [v for w in pts for v in (w['m'], w['qx'])]
    lo, hi = math.floor((min(vals) - 0.05) * 20) / 20, math.ceil((max(vals) + 0.05) * 20) / 20
    X = lambda v: M['l'] + (v - lo) / (hi - lo) * (W - M['l'] - M['r'])
    Y = lambda v: H - M['b'] - (v - lo) / (hi - lo) * (H - M['t'] - M['b'])
    R = 5
    qs, ms = [w['qx'] for w in pts], [w['m'] for w in pts]
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="Break-even map: net mNAV m against preferred price over notional q, one mark per firm-week" '
         'font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#222">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>']
    # Range frames: each axis line spans only the data's range.
    s.append(f'<line x1="{X(min(qs)):.1f}" x2="{X(max(qs)):.1f}" y1="{H - M["b"] + 8}" y2="{H - M["b"] + 8}" stroke="#888"/>')
    s.append(f'<line x1="{M["l"] - 8}" x2="{M["l"] - 8}" y1="{Y(max(ms)):.1f}" y2="{Y(min(ms)):.1f}" stroke="#888"/>')
    for v in (min(qs), max(qs)):
        s.append(f'<text x="{X(v):.1f}" y="{H - M["b"] + 24}" text-anchor="middle" fill="#555">{v:.2f}</text>')
    for v in (min(ms), 1.0, max(ms)):
        s.append(f'<text x="{M["l"] - 13}" y="{Y(v) + 4:.1f}" text-anchor="end" fill="#555">{v:.2f}</text>')
    s.append(f'<text x="{W - M["r"]}" y="{H - M["b"] + 44}" text-anchor="end" fill="#555">'
             'q = preferred close / $100 notional (STRC, BMNP; SharpLink, no preferred, at q = 1) →</text>')
    s.append(f'<text x="{M["l"]}" y="{M["t"] + 4}" fill="#555">↑ m = net mNAV</text>')
    s.append(f'<line x1="{X(lo):.1f}" y1="{Y(lo):.1f}" x2="{X(hi):.1f}" y2="{Y(hi):.1f}" stroke="#222" stroke-dasharray="5 4" stroke-opacity="0.7"/>')
    s.append(f'<text x="{X(hi) - 40:.1f}" y="{Y(hi) + 6:.1f}" text-anchor="end">m = q</text>')  # above-left, clear of the diagonal
    s.append(f'<text x="{M["l"] + 10}" y="{M["t"] + 24}" font-weight="bold">Strategy\'s rotation adds here (m &gt; q)</text>')
    s.append(f'<text x="{W - M["r"] - 10}" y="{H - M["b"] - 12}" text-anchor="end" font-weight="bold">'
             'BitMine\'s rotation adds here (m &lt; q)</text>')
    latest = {}
    for firm in ('MSTR', 'BMNR', 'SBET'):
        path = sorted((w for w in pts if w['firm'] == firm), key=lambda w: w['week_end'])
        if not path:
            continue
        latest[firm] = path[-1]
        c = COLOR[firm]
        if len(path) > 1:
            s.append(f'<polyline points="{" ".join(f"{X(w["qx"]):.1f},{Y(w["m"]):.1f}" for w in path)}" '
                     f'fill="none" stroke="{c}" stroke-opacity="0.5" stroke-width="1"/>')
        for w in path[:-1]:
            s.append(mark(firm, X(w['qx']), Y(w['m']), R, f'fill:#fff;stroke:{c};stroke-width:1.25'))
    for firm, w in latest.items():
        c, cx, cy = COLOR[firm], X(w['qx']), Y(w['m'])
        s.append(mark(firm, cx, cy, R + 1.5, f'fill:{c};stroke:{c};stroke-width:1.25'))
        s.append(f'<text x="{cx + 11:.1f}" y="{cy + 4:.1f}" font-weight="bold">{FIRMS[firm]["name"]} {w["week_end"]}</text>')
    s.append(f'<text x="{M["l"]}" y="{H - 8}" fill="#555">Open marks: earlier weeks, joined in date order. Solid: latest, labeled. '
             'Circle Strategy, square BitMine, triangle SharpLink.</text>')
    return '\n'.join(s + ['</svg>']) + '\n'


def table(d):
    """Answer first: each firm's latest m, preferred close and break-even. -> (header, rows, caption)."""
    h = {x['firm']: x for x in d['headline']}
    rows = []
    for f in ('MSTR', 'BMNR'):
        x, side = h[f], FIRMS[f]['side']
        rows.append([FIRMS[f]['name'], x['week_end'], f"{x['m']:.3f}", f"{x['pref']} ${x['pref_close']:.2f}",
                     f"${x['break_even']:.2f}", f"{x['pref']} {side} break-even"])
    x = h['SBET']
    rows.append(['SharpLink', f"{x['week_end']} (last filed)", f"{x['m']:.3f}", 'no preferred', 'm = 1',
                 'issuance while m > 1; buyback while m < 1'])
    header = ['Firm', 'Week ending', 'Net mNAV m', 'Preferred close', 'Break-even ($100 × m)', 'Rotation adds while']
    caption = ' '.join(h[f]['close_sentence'] for f in ('MSTR', 'BMNR', 'SBET'))
    return header, rows, caption


def residual_sentence(d):
    """The residual against filed actions, with Strategy's split at its first R-checked week (as on the page)."""
    t = d['totals']
    m, b, s = t['MSTR'], t['BMNR'], t['SBET']
    usd = lambda v: ('+' if v >= 0 else '−') + f'${abs(v) / 1e6:,.1f}M'
    return (f"Value to common since each firm's first week, by cause: filed actions {usd(m['actions'])} for Strategy, "
            f"{usd(b['actions'])} for BitMine and {usd(s['actions'])} for SharpLink. The residual, the change the filings "
            f"leave unexplained, is {usd(m['residual'])} for Strategy: {usd(m['residual'] - m['residual_checked'])} before "
            f"{m['checked_from']}, when the 8-Ks did not itemize cash flows, and {usd(m['residual_checked'])} in the weeks "
            f"since, each checked against the filings. BitMine's is {usd(b['residual'])} and SharpLink's "
            f"{usd(s['residual'])}, both report only.")


def paragraphs(d):
    ruler = ("Digital asset treasury (DAT) companies hold bitcoin or ether and raise money by selling stock. This memo "
             "measures each share sale, buyback and preferred trade since 2026-06-01 with Strategy's own net coins per "
             "share definition, applied to all three firms (glossary, Strategy's 2026-08-24 FWP). Net coins N are coins "
             "held plus USD assets, less out-of-the-money convertible debt and preferred notional, converted to coins at "
             "the coin price; n is N per fully diluted share. m is net mNAV, the share price over the net coin value per "
             "share. q is the preferred's close over its $100 notional.")
    line = ("Issuing common adds to n while m is above 1; retiring preferred adds while q is below 1. Strategy's rotation "
            "sells common and retires STRC, so it adds while m > q: it stops adding when STRC trades above $100 × m. "
            "BitMine's rotation sells BMNP and buys back common, so it adds while m < q: it stops adding when BMNP trades "
            "below $100 × m. SharpLink has no preferred, so no rotation line applies.")
    return ruler, line, d['counts'] + ' ' + residual_sentence(d)


def footnote(c, weekly, biases):
    (_, n, m0, m1), (_, k, b0, b1), (_, y, s0, s1) = c['MSTR'], c['BMNR'], c['SBET']
    return [closest(weekly, biases),
        f"Period: Strategy weeks ending {m0} to {m1} ({n} filed dates, including the 2026-06-30 quarter-end holdings "
        f"row); BitMine weeks ending {b0} to {b1} ({k} weeks with a BMNP price; BMNP was issued 2026-06-10); SharpLink "
        f"filed holdings dates {s0} to {s1} ({y} dates; SharpLink states holdings only on those dates, and nothing is "
        "carried forward between them).",
        "Sources: Strategy weekly 8-Ks and Q2 10-Q (EDGAR CIK 1050446); BitMine weekly 8-K releases and 10-Q (EDGAR CIK "
        "1829311); SharpLink 8-K releases and Q2 10-Q (EDGAR CIK 1981535); Yahoo Finance daily closes for MSTR, STRC, "
        "STRK, STRF, STRD, BMNR, BMNP and SBET; CoinGecko BTC and ETH "
        "closes. Each week uses closes from the last US trading day on or before the week's end.",
        "Labeled estimates: BitMine S is estimated between filings, anchored to the 10-Q share counts for 2026-05-31 "
        "and 2026-07-09, with unreported issuance estimated as the week's unexplained change in cash divided by the "
        "BMNR close. BitMine R is its stated cash and marketable securities, so it includes securities. The USD of each "
        "BitMine ETH purchase is units × that week's ETH close. SharpLink C includes LsETH and weETH at their stated "
        "as-if-redeemed ETH equivalence; its ETH change beyond stated purchases is inferred staking and LST accrual; "
        "its R is 2026-06-30 balance-sheet cash rolled by filed cash flows.",
    ]


def md(t, tab, paras, notes):
    header, rows, caption = tab
    grid = '\n'.join(['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)] + ['| ' + ' | '.join(r) + ' |' for r in rows])
    return '\n\n'.join([f'# {t}', grid, f'<sub>{caption}</sub>', *paras, '![Break-even map: m against q, one mark per firm-week](map.svg)',
                        '---', *(f'<sub>{x}</sub>' for x in notes),
                        f'<sub>Page: {PAGE}. Method: {REPO}/blob/main/docs/methodology.md. '
                        f'Code and data: {REPO}. Definition source: {FWP}.</sub>']) + '\n'


CSS = """@page { size: Letter; margin: 0.5in; }
body { font: 9.2pt/1.34 Helvetica, Arial, sans-serif; color: #222; max-width: 7.5in; margin: 0 auto; }
h1 { font-size: 13pt; line-height: 1.22; margin: 0 0 0.08in; }
p { margin: 0 0 0.09in; }
figure { margin: 0.04in 0 0.06in; text-align: center; }
figure svg { width: 4.3in; height: auto; }
table { border-collapse: collapse; width: 100%; margin: 0 0 0.04in; font-size: 8.6pt; }
th, td { text-align: left; padding: 2px 6px; border-bottom: 1px solid #ddd; }
th { border-bottom: 1.5px solid #222; }
td:nth-child(3), td:nth-child(4), td:nth-child(5) { font-variant-numeric: tabular-nums; }
.note { font-size: 7pt; line-height: 1.25; color: #444; margin: 0 0 0.04in; }
a { color: #1a5aa6; }
@media screen { body { margin: 0.6in auto; } }"""


def page(t, tab, paras, notes, svg):
    e = html.escape
    header, rows, caption = tab
    grid = ('<table><thead><tr>' + ''.join(f'<th>{e(h)}</th>' for h in header) + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join(f'<td>{e(c)}</td>' for c in r) + '</tr>' for r in rows) + '</tbody></table>'
            + f'<p class="note">{e(caption)}</p>')
    links = (f'Page: <a href="{PAGE}">{PAGE}</a>. Method: <a href="{REPO}/blob/main/docs/methodology.md">'
             f'docs/methodology.md</a>. Code and data: <a href="{REPO}">{REPO}</a>. '
             f'Definition source: <a href="{FWP}">Strategy FWP, 2026-08-24</a>.')
    body = [f'<h1>{e(t)}</h1>', grid, *(f'<p>{e(p)}</p>' for p in paras), f'<figure>{svg}</figure>',
            *(f'<p class="note">{e(x)}</p>' for x in notes), f'<p class="note">{links}</p>']
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<title>{e(t)}</title>\n<style>\n{CSS}\n</style></head>\n<body>\n' + '\n'.join(body) + '\n</body></html>\n')


def main(data_dir='data', out='docs'):
    d = build(data_dir, online=False)
    weekly = read(os.path.join(data_dir, 'weekly.csv'))
    c = counts(weekly)
    t, paras, notes, svg = title(d['headline']), paragraphs(d), footnote(c, weekly, week_biases(data_dir, weekly)), map_svg(d['weeks'])
    tab = table(d)
    files = {'map.svg': svg, 'memo.md': md(t, tab, paras, notes), 'memo.html': page(t, tab, paras, notes, svg)}
    for name, text in files.items():
        with open(os.path.join(out, name), 'w') as f:
            f.write(text)
    print(t)
    print('wrote ' + ', '.join(os.path.join(out, n) for n in files))
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
