"""Step 6 (`python -m dat.memo`): one-page memo -> docs/memo.md, docs/memo.html, docs/map.svg. stdlib only.

Figures come from data/weekly.csv (title counts) and dat.build_site.build (headline sentences, map points).
The map is a static, light-theme copy of the page's break-even map (site/app.js drawMap). The PDF is built
from memo.html (README, "Memo"); refresh.yml builds it weekly, CI does not.
"""
import html, math, os, sys
from dat.balances import read, bmnr_s_bias
from dat.build_site import build, FIRMS

PAGE = 'https://rahilbhavan.github.io/dat-accretion/'
REPO = 'https://github.com/RahilBhavan/dat-accretion'
FWP = 'https://www.sec.gov/Archives/edgar/data/1050446/000119312526363557/d431748dfwp.htm'
COLOR = {'MSTR': '#2a78d6', 'BMNR': '#eb6834'}
ADDS = {'MSTR': lambda m, q: m > q, 'BMNR': lambda m, q: m < q}  # method.md: the rotation's adding side of m = q


def counts(weekly):
    """{firm: (weeks on the adding side, weeks with m and q, first week, last week)} from weekly.csv rows."""
    out = {}
    for firm in ('MSTR', 'BMNR'):
        ws = sorted((r for r in weekly if r['firm'] == firm and r['m'] and r['q']), key=lambda r: r['week_end'])
        out[firm] = (sum(ADDS[firm](float(r['m']), float(r['q'])) for r in ws), len(ws), ws[0]['week_end'], ws[-1]['week_end'])
    return out


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
    bad = [(r['week_end'], f"{biases[r['week_end']]:.4%}") for r in rows('BMNR')
           if not float(r['m']) * (1 - biases[r['week_end']]) > float(r['q'])]
    if bad:
        raise ValueError(f'BitMine m x (1 - that week\'s S bias) is not above q in weeks {bad}: rewrite the footnote')
    return (f"Closest weeks to the line: {near['MSTR']}; {near['BMNR']}. BitMine's estimated share count carries a "
            f"known upward bias of up to {b:.2%} of S by {asof} (staked ETH costed as purchases), which raises "
            "m by the same proportion; removing it leaves m above q in every BitMine week.")


def title(c):
    (a, n, _, _), (b, k, _, _) = c['MSTR'], c['BMNR']
    return (f"Strategy's STRC rotation sat on its adding side of the break-even line in {a} of {n} filed weeks; "
            f"BitMine's BMNP rotation in {b} of {k}")


def mark(firm, cx, cy, r, style):
    if firm == 'MSTR':
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" style="{style}"/>'
    h = r * 0.886  # square of equal area, as on the page
    return f'<rect x="{cx - h:.1f}" y="{cy - h:.1f}" width="{2 * h:.1f}" height="{2 * h:.1f}" rx="1" style="{style}"/>'


def ticks(lo, hi, step=0.05):
    return [round(lo + i * step, 2) for i in range(int(round((hi - lo) / step)) + 1)]


def map_svg(weeks, W=800, H=500):
    """Break-even map, 16:10: x = q, y = m on one shared domain, m = q diagonal, area ∝ dollars moved."""
    pts = [w for w in weeks if w['q'] is not None and w['m'] is not None]
    M = {'l': 58, 'r': 16, 't': 14, 'b': 78}
    vals = [v for w in pts for v in (w['m'], w['q'])]
    lo, hi = math.floor((min(vals) - 0.05) * 20) / 20, math.ceil((max(vals) + 0.05) * 20) / 20
    X = lambda v: M['l'] + (v - lo) / (hi - lo) * (W - M['l'] - M['r'])
    Y = lambda v: H - M['b'] - (v - lo) / (hi - lo) * (H - M['t'] - M['b'])
    dmax = max([w['dollars_moved'] or 0 for w in pts] + [1])
    rad = lambda w: max(3.0, math.sqrt((w['dollars_moved'] or 0) / dmax) * 22)
    step = 0.05 if (hi - lo) <= 0.8 else 0.1
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         'aria-label="Break-even map: net mNAV m against preferred price over notional q, one mark per firm-week" '
         'font-family="Helvetica, Arial, sans-serif" font-size="13" fill="#222">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>']
    for t in ticks(lo, hi, step):
        s.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{M["t"]}" y2="{H - M["b"]}" stroke="#e3e3e3"/>')
        s.append(f'<line x1="{M["l"]}" x2="{W - M["r"]}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="#e3e3e3"/>')
        s.append(f'<text x="{X(t):.1f}" y="{H - M["b"] + 17}" text-anchor="middle" fill="#555">{t:.2f}</text>')
        s.append(f'<text x="{M["l"] - 7}" y="{Y(t) + 4:.1f}" text-anchor="end" fill="#555">{t:.2f}</text>')
    s.append(f'<line x1="{M["l"]}" x2="{W - M["r"]}" y1="{H - M["b"]}" y2="{H - M["b"]}" stroke="#555"/>')
    s.append(f'<line x1="{M["l"]}" x2="{M["l"]}" y1="{M["t"]}" y2="{H - M["b"]}" stroke="#555"/>')
    s.append(f'<text x="{(M["l"] + W - M["r"]) / 2}" y="{H - M["b"] + 38}" text-anchor="middle">'
             'q = preferred close / $100 notional (STRC for Strategy, BMNP for BitMine)</text>')
    s.append(f'<text transform="translate(16 {(M["t"] + H - M["b"]) / 2}) rotate(-90)" text-anchor="middle">m = net mNAV</text>')
    s.append(f'<line x1="{X(lo):.1f}" y1="{Y(lo):.1f}" x2="{X(hi):.1f}" y2="{Y(hi):.1f}" stroke="#222" stroke-dasharray="6 4"/>')
    s.append(f'<text x="{X(hi) - 40:.1f}" y="{Y(hi) + 6:.1f}" text-anchor="end">m = q</text>')  # above-left, clear of the diagonal
    s.append(f'<text x="{M["l"] + 10}" y="{M["t"] + 20}" font-weight="bold">Strategy\'s rotation adds here (m &gt; q)</text>')
    s.append(f'<text x="{W - M["r"] - 10}" y="{H - M["b"] - 12}" text-anchor="end" font-weight="bold">'
             'BitMine\'s rotation adds here (m &lt; q)</text>')
    for w in sorted(pts, key=lambda w: -(w['dollars_moved'] or 0)):  # small marks on top
        c = COLOR[w['firm']]
        s.append(mark(w['firm'], X(w['q']), Y(w['m']), rad(w), f'fill:{c};fill-opacity:0.45;stroke:{c};stroke-width:1.5'))
    y, x = H - 16, M['l']
    for firm in ('MSTR', 'BMNR'):
        c = COLOR[firm]
        s.append(mark(firm, x + 7, y - 4, 6, f'fill:{c};fill-opacity:0.45;stroke:{c}'))
        s.append(f'<text x="{x + 18}" y="{y}">{FIRMS[firm]["name"]}</text>')
        x += 100
    s.append(f'<line x1="{x}" y1="{y + 2}" x2="{x + 14}" y2="{y - 10}" stroke="#222" stroke-dasharray="3 2"/>')
    s.append(f'<text x="{x + 20}" y="{y}">m = q</text>')
    s.append(f'<text x="{x + 80}" y="{y}" fill="#555">Mark area: dollars moved that week (filed actions only)</text>')
    return '\n'.join(s + ['</svg>']) + '\n'


def paragraphs(d):
    h = {x['firm']: x for x in d['headline']}
    ruler = ("The ruler is Strategy's own net coins per share definition, applied to both firms, from the glossary in "
             f"Strategy's 2026-08-24 FWP. Net coins N are coins held plus USD assets, less out-of-the-money convertible "
             "debt and preferred notional, converted to coins at the coin price. n is N per fully diluted share. m is net "
             "mNAV, the common share price over the net coin value per share: m = s / (p·n). q is the preferred's close "
             "over its $100 notional.")
    line = ("Issuing common adds to n while m is above 1; retiring preferred adds while q is below 1. Strategy's rotation "
            "sells common and retires STRC, so it adds while m > q: it stops adding when STRC trades above $100 × m. "
            "BitMine's rotation sells BMNP and buys back common, so it adds while m < q: it stops adding when BMNP trades "
            "below $100 × m. The line m = q is where both rotations add nothing.")
    where = ' '.join(f"{h[f]['sentence']} {h[f]['close_sentence']}" for f in ('MSTR', 'BMNR'))
    return ruler, line, where


def footnote(c, weekly, biases):
    (_, n, m0, m1), (_, k, b0, b1) = c['MSTR'], c['BMNR']
    return [closest(weekly, biases),
        f"Period: Strategy weeks ending {m0} to {m1} ({n} filed dates, including the 2026-06-30 quarter-end holdings "
        f"row); BitMine weeks ending {b0} to {b1} ({k} weeks with a BMNP price; BMNP was issued 2026-06-10).",
        "Sources: Strategy weekly 8-Ks and Q2 10-Q (EDGAR CIK 1050446); BitMine weekly 8-K releases and 10-Q (EDGAR CIK "
        "1829311); Yahoo Finance daily closes for MSTR, STRC, STRK, STRF, STRD, BMNR and BMNP; CoinGecko BTC and ETH "
        "closes. Each week uses closes from the last US trading day on or before the week's end.",
        "Labeled estimates: BitMine S is estimated between filings, anchored to the 10-Q share counts for 2026-05-31 "
        "and 2026-07-09, with unreported issuance estimated as the week's unexplained change in cash divided by the "
        "BMNR close. BitMine R is its stated cash and marketable securities, so it includes securities. The USD of each "
        "BitMine ETH purchase is units × that week's ETH close.",
    ]


def md(t, paras, notes):
    return '\n\n'.join([f'# {t}', *paras, '![Break-even map: m against q, one mark per firm-week](map.svg)',
                        '---', *(f'<sub>{x}</sub>' for x in notes),
                        f'<sub>Page: {PAGE}. Method: {REPO}/blob/main/docs/methodology.md. '
                        f'Code and data: {REPO}. Definition source: {FWP}.</sub>']) + '\n'


CSS = """@page { size: Letter; margin: 0.6in; }
body { font: 10pt/1.38 Helvetica, Arial, sans-serif; color: #222; max-width: 7.3in; margin: 0 auto; }
h1 { font-size: 14.5pt; line-height: 1.25; margin: 0 0 0.12in; }
p { margin: 0 0 0.09in; }
figure { margin: 0.04in 0 0.06in; text-align: center; }
figure svg { width: 6.3in; height: auto; }
.note { font-size: 7.6pt; line-height: 1.3; color: #444; margin: 0 0 0.04in; }
a { color: #1a5aa6; }
@media screen { body { margin: 0.6in auto; } }"""


def page(t, paras, notes, svg):
    e = html.escape
    links = (f'Page: <a href="{PAGE}">{PAGE}</a>. Method: <a href="{REPO}/blob/main/docs/methodology.md">'
             f'docs/methodology.md</a>. Code and data: <a href="{REPO}">{REPO}</a>. '
             f'Definition source: <a href="{FWP}">Strategy FWP, 2026-08-24</a>.')
    body = [f'<h1>{e(t)}</h1>', *(f'<p>{e(p)}</p>' for p in paras), f'<figure>{svg}</figure>',
            *(f'<p class="note">{e(x)}</p>' for x in notes), f'<p class="note">{links}</p>']
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<title>{e(t)}</title>\n<style>\n{CSS}\n</style></head>\n<body>\n' + '\n'.join(body) + '\n</body></html>\n')


def main(data_dir='data', out='docs'):
    d = build(data_dir, online=False)
    weekly = read(os.path.join(data_dir, 'weekly.csv'))
    c = counts(weekly)
    t, paras, notes, svg = title(c), paragraphs(d), footnote(c, weekly, week_biases(data_dir, weekly)), map_svg(d['weeks'])
    files = {'map.svg': svg, 'memo.md': md(t, paras, notes), 'memo.html': page(t, paras, notes, svg)}
    for name, text in files.items():
        with open(os.path.join(out, name), 'w') as f:
            f.write(text)
    print(t)
    print('wrote ' + ', '.join(os.path.join(out, n) for n in files))
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
