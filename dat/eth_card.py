"""`python -m dat.eth_card [data_dir]`: BitMine's weekly net ETH per 1,000 shares -> data/eth_per_share.csv, and the
1080x1080 card drawn from it -> docs/social/eth-per-share-<last week>/.

Series (stdlib only). For each BMNR week in weekly.csv, ETH held, cash & marketable securities, ETH bought, staked ETH
and the week's buyback come from that week's 8-K ex99-1 (re-read through parse_bmnr.parse, cached in data/raw), not from
a derived file. The model adds the BMNP notional F and the estimated diluted shares S (balances.csv, method.md "BitMine
S") and the ETH close p (weekly.csv). Then, with D = 0 (method.md):

    N = C + (R - F) / p        net_eth_per_1000_shares = 1000 * N / S

The CSV carries every input, so each number recomputes by hand; the result is checked against weekly.csv's n.

Card (needs the rahil-design bundle, Firefox and `uv run --with playwright==1.63.0 --with fonttools`): drawn 360px
wide at 3x so the PNG is exactly 1080x1080. The week's 8-K figures and the basis for "within error" are fine print at
15px, which misses the bundle's 18px phone-feed label floor (and the 41px title misses its 40px point floor); the
brief records the measured sizes, and that overflow was also checked with a 390px viewport. Colours and fonts
come from the bundle's tokens, never typed here. `--card` redraws from the saved CSV without reading the filings. Writes card.html, card.png, brief.json and alt.txt. The card is a
draft: it carries no design-review pass until a named reviewer records one for its bytes.
"""
import base64, csv, hashlib, html, json, os, sys
from dat.balances import read

CARD_WEEKS = 5      # the last five weeks: the most dated labels 20px type holds in a 300px plot
BUNDLE = os.environ.get('RAHIL_DESIGN', os.path.expanduser('~/.t3/projects/main/.agents/skills/rahil-design'))
SIZE, SCALE, FINE, PHONE = 360, 3, 15, 390  # FINE: px of the fine print (the 20px feed floor leaves no room for the week's figures)
FIELDS = ['week_end', 'filed', 'filing_url', 'eth_held', 'cash_securities_usd', 'bmnp_notional_usd', 'eth_close_usd',
          'net_eth', 'shares_diluted_est', 'net_eth_per_1000_shares', 'change_pct', 'eth_added', 'eth_staked',
          'buyback_shares', 'buyback_avg_usd', 's_bias_pct_of_s', 'on_card']
TITLE = 'Bought back 2.04M shares. ETH/share within error.'
LABEL = 'Estimated net ETH per 1,000 diluted shares (ETH plus net cash in ETH)'
AXIS = 'ETH per 1,000 shares'
FOOT = 'Source: BitMine 8-K ex99-1 plus dat-accretion model, as of Oct 25, 2026, 2:00 PM ET'


def net_per_1000(eth, cash, notional, eth_close, shares):
    """Net ETH per 1,000 diluted shares: 1000 * (C + (R - F) / p) / S, with D = 0."""
    return 1000 * (eth + (cash - notional) / eth_close) / shares


def series(data_dir='data'):
    from dat import edgar, filings
    from dat.parse_bmnr import parse
    from dat.prices import load, close_on_or_before
    path = lambda n: os.path.join(data_dir, n)
    weekly = {r['week_end']: r for r in read(path('weekly.csv')) if r['firm'] == 'BMNR'}
    stated = {r['week_end']: r for r in read(path('stated.csv')) if r['firm'] == 'BMNR'}
    bal = {r['date']: r for r in read(path('balances.csv')) if r['firm'] == 'BMNR'}
    stake = {r['week_end']: float(r['eth_est']) for r in read(path('staking.csv'))}
    prices, rows, prev = load(path('prices.csv')), [], None
    for week in sorted(weekly):
        w, st, b = weekly[week], stated[week], bal[week]
        url = st['filing_url']
        r = parse(edgar.fetch(url), {'accession': filings.dashed(filings.accession(url)), 'filed': st['filed']}, url)
        eth, cash, F, S, p = int(r['coins']), int(r['cash']), float(b['pref_notional']), float(b['shares_diluted']), float(w['p'])
        if r['week_end'] != week or eth != int(st['coins']) or cash != int(st['usd_reserve']):
            raise ValueError(f'BMNR {week}: 8-K ({r["week_end"]}, {eth}, {cash}) disagrees with stated.csv {st}')
        n = net_per_1000(eth, cash, F, p, S)
        if abs(n - 1000 * float(w['n'])) > 1e-6:
            raise ValueError(f'BMNR {week}: recomputed {n:.6f} per 1,000 shares, weekly.csv has {1000 * float(w["n"]):.6f}')
        d, s = close_on_or_before(prices, 'BMNR', week)
        bias = stake.get(week, 0) * p / s / S * 100  # staking costed as a purchase adds this share of S (data.md)
        rows.append({'week_end': week, 'filed': st['filed'], 'filing_url': url, 'eth_held': eth,
                     'cash_securities_usd': cash, 'bmnp_notional_usd': f'{F:.0f}', 'eth_close_usd': f'{p:.2f}',
                     'net_eth': f'{eth + (cash - F) / p:.1f}', 'shares_diluted_est': f'{S:.0f}',
                     'net_eth_per_1000_shares': f'{n:.4f}',
                     'change_pct': '' if prev is None else f'{(n / prev - 1) * 100:+.3f}',
                     'eth_added': r['acquired'] or '', 'eth_staked': r['staked'] or '',
                     'buyback_shares': int(r['buyback'][0]) if r['buyback'] else '',
                     'buyback_avg_usd': r['buyback'][1] if r['buyback'] else '',
                     's_bias_pct_of_s': f'{bias:.3f}', 'on_card': 'no'})
        prev = n
    for row in rows[-CARD_WEEKS:]:
        row['on_card'] = 'yes'
    return rows


def write_series(rows, path):
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, FIELDS, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def md(iso):
    return f'{int(iso[5:7])}/{int(iso[8:])}'


def pct2(row):
    return f'{float(row["change_pct"]):+.2f}%'


def alt_text(card):
    """Describes the chart as drawn: all five weeks are dated on the axis, only the last two carry a value label."""
    last, prev = card[-1], card[-2]
    return (f'Line chart, {LABEL}, vertical axis {AXIS}, at BitMine for five weeks ending {md(card[0]["week_end"])} to '
            f'{md(last["week_end"])}. Value labels on the chart: {md(prev["week_end"])} {prev["net_eth_per_1000_shares"]} and '
            f'{md(last["week_end"])} {last["net_eth_per_1000_shares"]}, up {pct2(last).lstrip("+")} in the last week. '
            f'Week ending Oct 25: {int(last["eth_held"]):,} ETH held, '
            f'{int(last["eth_staked"]):,} staked, {int(last["eth_added"]):,} ETH added; {int(last["buyback_shares"]) / 1e6:.2f} '
            f'million shares bought back at ${last["buyback_avg_usd"]}. Share count is estimated, and its staking bias of '
            f'{last["s_bias_pct_of_s"]}% a week is larger than the change. The vertical axis spans only the five values. '
            + FOOT + '.')


def facts(card):
    """Fine print under the plot: the week's 8-K figures and the basis for 'within error'."""
    r = card[-1]
    return (f'{LABEL}. {int(r["eth_held"]):,} ETH held, {int(r["eth_staked"]):,} staked, '
            f'+{int(r["eth_added"]):,}; {int(r["buyback_shares"]) / 1e6:.2f}M shares at ${r["buyback_avg_usd"]}. '
            f'Staking biases shares {float(r["s_bias_pct_of_s"]):.3f}% a week, above the {pct2(r)} change.')


def card_html(card, T, fonts):
    """The card markup. T: bundle colour tokens; fonts: {file name: base64}."""
    ink, canvas, surf, fink, fsec = T['ink'], T['canvas'], T['figure-surface'], T['figure-ink'], T['figure-secondary']
    hi = T['chart-highlight']
    W, X0, DX = 300, 28, 61       # plot width; first point x; spacing between weeks (a 56px label fits in 61px)
    vals = [float(r['net_eth_per_1000_shares']) for r in card]
    lo, hi_v = min(vals), max(vals)
    top, bot = 28, 38             # plot rows (px in the svg): highest and lowest value
    xs = [X0 + DX * i for i in range(len(card))]
    ys = [bot - (v - lo) / (hi_v - lo) * (bot - top) for v in vals]
    line = ' '.join(f'{x},{y:.1f}' for x, y in zip(xs, ys))
    dots = ''.join(f'<circle cx="{x}" cy="{y:.1f}" r="3.5" fill="{T["chart-series-1"]}"/>' for x, y in zip(xs[:-1], ys[:-1]))
    last = f'<circle cx="{xs[-1]}" cy="{ys[-1]:.1f}" r="6" fill="{hi}" stroke="{T["chart-series-1"]}" stroke-width="2"/>'
    labels = ''.join(f'<text x="{x}" y="55" text-anchor="middle" class="tick">{md(r["week_end"])}</text>'
                     for x, r in zip(xs, card))
    value = lambda x, y, r, anchor, cls: (f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}">'
                                          f'{r["net_eth_per_1000_shares"]}</text>')
    chip = (f'<rect x="1" y="1" width="82" height="23" fill="{hi}" stroke="{T["chart-series-1"]}" stroke-width="2"/>'
            f'<text x="42" y="20" text-anchor="middle" class="val b">{pct2(card[-1])}</text>')
    values = chip + value(228, 19, card[-2], 'end', 'val prior') + value(W, 19, card[-1], 'end', 'val b')
    font = lambda n: base64.b64encode(open(os.path.join(BUNDLE, 'assets/fonts', n), 'rb').read()).decode()
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(TITLE)}</title><style>
@font-face{{font-family:'Rahil Display';src:url(data:font/ttf;base64,{fonts['Anton-Regular.ttf']})}}
@font-face{{font-family:'Rahil Plex';src:url(data:font/ttf;base64,{fonts['IBMPlexSans-Regular.ttf']})}}
@font-face{{font-family:'Rahil Plex';font-weight:600;src:url(data:font/ttf;base64,{fonts['IBMPlexSans-SemiBold.ttf']})}}
*{{box-sizing:border-box}}html,body{{margin:0}}
body{{width:{SIZE}px;height:{SIZE}px;background:{canvas};color:{ink};font-family:'Rahil Plex',sans-serif}}
article{{width:{SIZE}px;height:{SIZE}px;padding:20px;display:grid;grid-template-rows:auto minmax(0,1fr) auto auto;gap:3px}}
h1{{font:41px/0.9 'Rahil Display',sans-serif;margin:0;text-transform:uppercase}}
.figure{{background:{surf};color:{fink};border-radius:12px;padding:4px 10px 0;font-size:20px;line-height:1.15;
font-variant-numeric:tabular-nums}}
svg{{display:block;width:{W}px;height:62px}}
.axis{{font:18px/1 'Rahil Plex',sans-serif;color:{fsec};margin:0 0 2px}}
.tick{{font:20px 'Rahil Plex',sans-serif;fill:currentColor;color:{fsec}}}
.val{{font:20px 'Rahil Plex',sans-serif;fill:currentColor;color:{fink}}}.prior{{color:{fsec}}}.b{{font-weight:600}}
.fine{{font-size:{FINE}px;line-height:1.08;color:{ink};margin:0}}
.source{{font-size:{FINE}px;line-height:1.08;color:{ink};margin:0}}
</style></head><body><article><h1>{html.escape(TITLE)}</h1>
<div class="figure"><div class="axis">{html.escape(AXIS)}</div>
<svg viewBox="0 0 {W} 62" role="img" aria-label="{html.escape(alt_text(card))}"><polyline points="{line}" fill="none"
stroke="{T['chart-series-1']}" stroke-width="2.5" stroke-linejoin="round"/>{dots}{last}{values}{labels}</svg></div>
<p class="fine">{html.escape(facts(card))}</p><p class="source">{html.escape(FOOT)}</p></article></body></html>"""


def overflow_at(sb, html_path, size):
    """The card's overflow list with the browser viewport at size x size (a 390px phone), PNG not rewritten."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True, executable_path=str(sb.FIREFOX))
        page = browser.new_page(viewport={'width': size, 'height': size}, device_scale_factor=SCALE)
        page.goto('file://' + os.path.abspath(html_path))
        page.evaluate('document.fonts.ready')
        page.wait_for_timeout(300)
        found = page.evaluate(sb.MEASURE)['overflow']
        browser.close()
    return found


def build_card(rows, out):
    sys.path.insert(0, os.path.join(BUNDLE, 'scripts'))
    import social_bars as sb
    from chart_theme import T, VERSION
    sb.SIZE = SIZE
    card = rows[-CARD_WEEKS:]
    fonts = {n: base64.b64encode(open(os.path.join(BUNDLE, 'assets/fonts', n), 'rb').read()).decode()
             for n in ('Anton-Regular.ttf', 'IBMPlexSans-Regular.ttf', 'IBMPlexSans-SemiBold.ttf')}
    os.makedirs(out, exist_ok=True)
    markup = card_html(card, T, fonts)
    open(os.path.join(out, 'card.html'), 'w').write(markup)
    m = sb.render(os.path.join(out, 'card.html'), os.path.join(out, 'card.png'))
    sizes = [px for _, px in m['sizes']]
    m['overflow'] += [f'at {PHONE}px: {o}' for o in overflow_at(sb, os.path.join(out, 'card.html'), PHONE)]
    errors = [f'overflow: {o}' for o in m['overflow']] + [f'font {f!r} is not a token font' for f in set(m['fonts'])]
    errors += [f'no glyph for {g}; spell it out' for g in sb.missing_glyphs(m['glyphs'])] + sb.face_errors(m['faces'])
    brief = {'id': os.path.basename(out), 'title': TITLE, 'system_version': VERSION, 'accents': 1,
             'accent_meaning': 'latest week', 'encodings': [{'mark': 'line', 'baseline': 'five plotted values'}],
             'sizes_checked': [f'{SIZE}x{SIZE}', f'{PHONE}x{PHONE}'], 'measurement_basis': 'canvas', 'measured_by': 'dat.eth_card/firefox',
             'min_label_px': min(sizes), 'point_px': max(sizes), 'overflow': m['overflow'],
             'source': FOOT, 'alt': alt_text(card), 'review_status': 'design review pending',
             'artifacts': {n: hashlib.sha256(open(os.path.join(out, n), 'rb').read()).hexdigest() for n in ('card.html', 'card.png')}}
    open(os.path.join(out, 'brief.json'), 'w').write(json.dumps(brief, indent=2) + '\n')
    open(os.path.join(out, 'alt.txt'), 'w').write(brief['alt'] + '\n')
    print(f'{out}/card.png: labels {min(sizes)}px, largest text {max(sizes)}px; '
          + ('; '.join(errors) or 'ok'))
    return 1 if errors else 0


def main(data_dir='data', *flags):
    if '--card' in flags:  # redraw the card from the saved series, without re-reading the filings
        rows = read(os.path.join(data_dir, 'eth_per_share.csv'))
    else:
        rows = series(data_dir)
    out_csv = os.path.join(data_dir, 'eth_per_share.csv')
    if '--card' not in flags:
        write_series(rows, out_csv)
    print(f'{len(rows)} weeks in {out_csv}: ' + ', '.join(f'{md(r["week_end"])} {r["net_eth_per_1000_shares"]}' for r in rows[-CARD_WEEKS:]))
    return build_card(rows, os.path.join('docs', 'social', f'eth-per-share-{rows[-1]["week_end"]}'))


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
