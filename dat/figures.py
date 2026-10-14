"""`python -m dat.figures`: static course figures -> docs/course/figures/<name>-{light,dark}.svg. stdlib only.

Each figure stands in for a `widget` block that GitHub shows as plain text. Graphics follow framing.md (Tufte):
bars from zero on one scale per figure, one accent for the lesson's subject, grays for context, labels on the data,
toy numbers labeled as an illustration. Colors are the site's tokens (site/style.css), so the course matches the page.
"""
import html, math, os, sys
from dat.balances import read

THEMES = {
    'light': {'fg': '#15171b', 'muted': '#5d6470', 'axis': '#9aa1ab', 'accent': '#1f6fd1', 'ink2': '#3b4250',
              'gray1': '#9aa3ae', 'gray2': '#cdd3da'},
    'dark': {'fg': '#eef1f4', 'muted': '#a3acb8', 'axis': '#67717e', 'accent': '#5c9ef0', 'ink2': '#c9d0d9',
             'gray1': '#7b8592', 'gray2': '#3f4855'},
}
FONT = '-apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Helvetica, Arial, sans-serif'
MINUS = '−'
e = html.escape


def svg(W, H, label, body, t):
    """Transparent background so the figure sits on GitHub's light or dark page."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'aria-label="{e(label)}" font-family="{FONT}" font-size="13" fill="{t["fg"]}" '
            f'style="font-variant-numeric: tabular-nums">\n'
            f'<defs><pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<line x1="0" y1="0" x2="0" y2="5" stroke="{t["gray1"]}" stroke-width="2"/></pattern></defs>\n'
            + '\n'.join(body) + '\n</svg>\n')


def sign(x, fmt):
    if fmt(abs(x)) in ('0', '0.0'):
        return '0'
    return (MINUS if x < 0 else '+') + fmt(abs(x))


def usd(x):
    a = abs(x)
    if a < 500:
        return '$0'
    body = f'${a / 1e9:.2f}B' if a >= 1e9 else f'${a / 1e6:.1f}M' if a >= 1e5 else f'${a / 1e3:.0f}k'
    return (MINUS if x < 0 else '+') + body


# 1. the ruler: net coins N built from C, R, D and F (lesson 00-03)

def ruler(data_dir, firm, week, t):
    b = next(r for r in read(os.path.join(data_dir, 'balances.csv')) if r['firm'] == firm and r['date'] == week)
    w = next(r for r in read(os.path.join(data_dir, 'weekly.csv')) if r['firm'] == firm and r['week_end'] == week)
    p, S = float(w['p']), int(b['shares_diluted'])
    C, R, D, F = float(b['coins']), float(b['usd_reserve']), float(b['debt']), float(b['pref_notional'])
    N = C + (R - D - F) / p
    n = N / S
    assert abs(n / float(w['n']) - 1) < 1e-6, (n, w['n'])  # same N as the engine's weekly.csv
    steps = [('Coins held, C', '', C), ('+ USD assets, R ÷ p', f'${R / 1e9:.2f}B ÷ ${p:,.0f}', R / p),
             ('− Debt, D ÷ p', f'${D / 1e9:.2f}B ÷ ${p:,.0f}', -D / p),
             ('− Preferred notional, F ÷ p', f'${F / 1e9:.2f}B ÷ ${p:,.0f}', -F / p)]
    W, L, X0, X1, rh, top = 800, 210, 220, 520, 34, 46
    hi = max(C, C + R / p)
    X = lambda v: X0 + v / hi * (X1 - X0)
    s = [f'<text x="0" y="16" font-weight="600">Strategy, week ending {week}: net coins N, in BTC</text>',
         f'<text x="0" y="34" fill="{t["muted"]}">Each bar starts where the last one ended; N is drawn from zero.</text>']
    run = 0.0
    for k, (name, how, v) in enumerate(steps):
        y = top + k * rh
        a, b2 = sorted((run, run + v))
        s.append(f'<text x="{L}" y="{y + 17}" text-anchor="end">{e(name)}</text>')
        s.append(f'<rect x="{X(a):.1f}" y="{y + 5}" width="{X(b2) - X(a):.1f}" height="16" fill="{t["gray1"] if k else t["ink2"]}"/>')
        val = f'{v:,.0f}' if k == 0 else sign(v, lambda x: f'{x:,.0f}')
        s.append(f'<text x="{X1 + 10}" y="{y + 17}">{val}<tspan fill="{t["muted"]}" dx="8">{e(how)}</tspan></text>')
        run += v
    y = top + len(steps) * rh + 6
    s.append(f'<line x1="{X0}" x2="{W}" y1="{y - 3}" y2="{y - 3}" stroke="{t["axis"]}"/>')
    s.append(f'<text x="{L}" y="{y + 19}" text-anchor="end" font-weight="600">= Net coins, N</text>')
    s.append(f'<rect x="{X(0):.1f}" y="{y + 7}" width="{X(N) - X(0):.1f}" height="16" fill="{t["accent"]}"/>')
    s.append(f'<text x="{X1 + 10}" y="{y + 19}" font-weight="600">{N:,.0f}</text>')
    s.append(f'<line x1="{X0}" x2="{X0}" y1="{top}" y2="{y + 28}" stroke="{t["axis"]}"/>')
    y += 58
    s.append(f'<text x="0" y="{y}">n = N ÷ S = {N:,.0f} ÷ {S:,} shares = <tspan font-weight="600">{n * 1e8:,.0f} sats per share</tspan></text>')
    s.append(f'<text x="0" y="{y + 20}" fill="{t["muted"]}">m = s ÷ (p · n) = ${float(w["s"]):.2f} ÷ (${p:,.2f} × {n:.7f}) = '
             f'{float(w["s"]) / (p * n):.3f}. Source: balances.csv and weekly.csv.</text>')
    return svg(W, y + 30, f'Net coins for {firm} on {week}: {C:,.0f} BTC held, plus USD assets, less debt and preferred, '
               f'gives N = {N:,.0f} BTC and {n * 1e8:,.0f} sats per share', s, t)


# 2. one week's parts, in basis points of n (lessons 01-05, 02-01, 02-02)

LABEL = {'price': 'Coin price', 'itm_flip': 'In-the-money flips', 'carry': 'Carry', 'est_issuance': 'Estimated issuance',
         'residual': 'Residual (unexplained)'}
ACT = {'issue_common': 'Issue common', 'buyback_common': 'Buy back common', 'issue_pref': 'Issue', 'retire_pref': 'Retire',
       'buy_coin': 'Buy', 'sell_coin': 'Sell'}


def row_label(a):
    if a['action'] in ACT:
        what = ACT[a['action']] + ('' if 'common' in a['action'] else ' ' + a['ticker'])
        at = f" at m {float(a['m']):.3f}" if a['m'] and 'common' in a['action'] else f" at q {float(a['q']):.3f}" if a['q'] else ''
        return f"{what} ${float(a['usd']) / 1e6:,.1f}M{at}"
    if a['action'] == 'carry':
        return {'DIV_INT': 'Carry: dividends and interest', 'DIV': 'Carry: BMNP dividends', 'STAKE': 'Carry: staking'}.get(a['ticker'], 'Carry')
    return LABEL[a['action']]


def weekparts(data_dir, firm, week, focus, t):
    """Waterfall of a week's attribution rows. focus: the action whose bar takes the accent."""
    rows = [a for a in read(os.path.join(data_dir, 'attribution.csv')) if a['firm'] == firm and a['week_end'] == week]
    wk = sorted((r for r in read(os.path.join(data_dir, 'weekly.csv')) if r['firm'] == firm), key=lambda r: r['week_end'])
    i = [r['week_end'] for r in wk].index(week)
    cur, prev = wk[i], wk[i - 1]
    n, p = float(cur['n']), float(cur['p'])
    bal = next(b for b in read(os.path.join(data_dir, 'balances.csv')) if b['firm'] == firm and b['date'] == week)
    S = int(bal['shares_diluted'])
    obs = n - float(prev['n'])
    assert abs(math.fsum(float(a['dn_exact']) for a in rows) - obs) < 1e-12, (firm, week)  # parts sum to observed
    bp = lambda dn: dn / n * 1e4
    parts = [(row_label(a), bp(float(a['dn_exact'])), float(a['dn_exact']) * S * p, a['action']) for a in rows
             if not (a['action'] == 'itm_flip' and float(a['dn_exact']) == 0)]
    run, lo, hi = 0.0, 0.0, 0.0
    for _, v, _, _ in parts:
        run += v
        lo, hi = min(lo, run), max(hi, run)
    W, L, X0, X1, rh, top = 860, 250, 262, 580, 30, 50
    X = lambda v: X0 + (v - lo) / (hi - lo) * (X1 - X0)
    coin = 'BTC' if firm == 'MSTR' else 'ETH'
    name = {'MSTR': 'Strategy', 'BMNR': 'BitMine', 'SBET': 'SharpLink'}[firm]
    s = [f'<text x="0" y="16" font-weight="600">{name}, week ending {week}: change in net {coin} per share, by part</text>',
         f'<text x="0" y="34" fill="{t["muted"]}">Basis points of this week\'s n (1 bp = 0.01%), in the engine\'s order. '
         f'Dollars are value to common, Δn × S × p.</text>']
    run = 0.0
    for k, (label, v, dollars, action) in enumerate(parts):
        y = top + k * rh
        a, b = sorted((run, run + v))
        fill = (t['accent'] if action == focus else 'url(#hatch)' if action in ('residual', 'est_issuance') else t['gray1'])
        s.append(f'<text x="{L}" y="{y + 16}" text-anchor="end"{" font-weight=\"600\"" if action == focus else ""}>{e(label)}</text>')
        s.append(f'<rect x="{X(a):.1f}" y="{y + 5}" width="{max(X(b) - X(a), 1):.1f}" height="14" fill="{fill}"/>')
        small = action == focus and X(b) - X(a) < 4  # true scale: say so instead of inflating the bar
        s.append(f'<text x="{X1 + 12}" y="{y + 16}">{sign(v, lambda x: f"{x:,.1f}")} bp'
                 f'<tspan fill="{t["muted"]}" dx="8">{usd(dollars)}{", too small to see at true scale" if small else ""}</tspan></text>')
        run += v
    y = top + len(parts) * rh + 6
    s.append(f'<line x1="{X0}" x2="{X1 + 160}" y1="{y - 3}" y2="{y - 3}" stroke="{t["axis"]}"/>')
    s.append(f'<text x="{L}" y="{y + 17}" text-anchor="end" font-weight="600">Observed change</text>')
    a, b = sorted((0, bp(obs)))
    s.append(f'<rect x="{X(a):.1f}" y="{y + 5}" width="{max(X(b) - X(a), 1):.1f}" height="14" fill="{t["ink2"]}"/>')
    s.append(f'<text x="{X1 + 12}" y="{y + 17}" font-weight="600">{sign(bp(obs), lambda x: f"{x:,.1f}")} bp'
             f'<tspan fill="{t["muted"]}" font-weight="400" dx="8">{usd(obs * S * p)}</tspan></text>')
    s.append(f'<line x1="{X(0):.1f}" x2="{X(0):.1f}" y1="{top}" y2="{y + 24}" stroke="{t["fg"]}"/>')
    s.append(f'<text x="{X(0):.1f}" y="{y + 40}" text-anchor="middle" fill="{t["muted"]}">0</text>')
    return svg(W, y + 50, f'{name} week ending {week}: ' + '; '.join(f'{l} {v:+.1f} bp' for l, v, _, _ in parts)
               + f'; observed {bp(obs):+.1f} bp', s, t)


# 3. the toy balance sheet (lesson 00-04), same numbers as the page's figure

TOY = {'coins': 1000, 'cash': 90, 'pref': 300, 'retired': 100}


def sheet(t):
    T = TOY
    unit, colW, top, base = 190 / (T['coins'] + T['cash']), 56, 52, 52 + 190
    s = [f'<text x="0" y="14" font-size="11" letter-spacing="0.08em" fill="{t["muted"]}">ILLUSTRATION, NOT FILED FIGURES</text>']
    for k, after in enumerate((False, True)):
        ox = k * 360
        assets = [('Coins', T['coins'])] if after else [('Cash', T['cash']), ('Coins', T['coins'])]
        pref = T['pref'] - T['retired'] if after else T['pref']
        total = sum(v for _, v in assets)
        claims = [('Preferred', pref), ('Common', total - pref)]
        s.append(f'<text x="{ox}" y="38" font-weight="600">{"After: retire a $100 claim for $90" if after else "Before"}</text>')
        for c, (segs, title) in enumerate(((assets, 'Assets'), (claims, 'Claims'))):
            x = ox + 8 + c * 150
            y = top + (T['coins'] + T['cash'] - total) * unit
            if after and c == 0:
                s.append(f'<rect x="{x}" y="{top}" width="{colW}" height="{T["cash"] * unit:.1f}" fill="none" '
                         f'stroke="{t["gray1"]}" stroke-dasharray="3 3"/>')
                s.append(f'<text x="{x + colW + 6}" y="{top + T["cash"] * unit / 2 + 4:.1f}" fill="{t["muted"]}">cash −90</text>')
            for name, v in segs:
                h, common = v * unit, name == 'Common'
                note = ' +10' if after and common else ' −100' if after and name == 'Preferred' else ''
                s.append(f'<rect x="{x}" y="{y:.1f}" width="{colW}" height="{h:.1f}" fill="{t["accent"] if common else t["gray2"]}" '
                         f'stroke="{"none" if common else t["gray1"]}" stroke-width="0.5"/>')
                s.append(f'<text x="{x + colW + 6}" y="{y + h / 2 + 4:.1f}"{" font-weight=\"600\"" if common else ""}>'
                         f'{name} {v:,}{note}</text>')
                y += h
            s.append(f'<text x="{x + colW / 2}" y="{base + 18}" text-anchor="middle" fill="{t["muted"]}">{title}</text>')
        s.append(f'<line x1="{ox}" x2="{ox + 320}" y1="{base}" y2="{base}" stroke="{t["axis"]}"/>')
    s.append(f'<text x="0" y="{base + 44}" fill="{t["muted"]}">Assets equal claims on both sides, on one scale. '
             'Paying $90 removes a $100 claim, so the common block grows by $10.</text>')
    return svg(700, base + 56, 'Illustration: before, cash 90 and coins 1,000 against preferred 300 and common 790; after paying '
               '$90 to retire a $100 preferred claim, coins 1,000 against preferred 200 and common 800', s, t)


FIGURES = {
    'ruler-MSTR-2026-09-20': lambda d, t: ruler(d, 'MSTR', '2026-09-20', t),
    'weekparts-MSTR-2026-09-20': lambda d, t: weekparts(d, 'MSTR', '2026-09-20', 'retire_pref', t),
    'weekparts-MSTR-2026-08-23': lambda d, t: weekparts(d, 'MSTR', '2026-08-23', 'residual', t),
    'weekparts-BMNR-2026-08-23': lambda d, t: weekparts(d, 'BMNR', '2026-08-23', 'est_issuance', t),
    'balance-sheet-toy': lambda d, t: sheet(t),
}


def main(data_dir='data', out='docs/course/figures'):
    os.makedirs(out, exist_ok=True)
    for name, make in FIGURES.items():
        for mode, t in THEMES.items():
            path = os.path.join(out, f'{name}-{mode}.svg')
            with open(path, 'w') as fh:
                fh.write(make(data_dir, t))
            print(path)
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
