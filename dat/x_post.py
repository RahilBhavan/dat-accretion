"""`python -m dat.x_post`: figures for the Sats per Share #15 "Q3 preview" X post, each traced to filed rows.

Reads data/actions.csv and data/attribution.csv, sums Strategy's Q3 2026 (Jul 1 to Sep 30) actions, and writes
posts/sats-per-share-15/sources.csv: one line per underlying row with the 8-K accession number. It then checks that
every number in the card, thread and alt text is one of those figures. `--card OUT_DIR` also writes the card HTML
(fonts embedded from --fonts); render it to 1080x1080 with the design skill's Firefox renderer (see README.md there).
stdlib only. The post text lives in posts/sats-per-share-15/; framing.md governs it.
"""
import argparse, base64, csv, html, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POST = ROOT / 'posts' / 'sats-per-share-15'
START, END = '2026-06-30', '2026-09-30'  # week_end after START through END: Strategy's Q3
SATS = 1e8
MINUS = '−'
FOOTER = 'Source: Strategy 8-Ks, Jul–Sep 2026 · Oct 27'


def accession(url):
    """EDGAR folder 000119312526295586 is accession 0001193125-26-295586."""
    folder = url.split('/')[-2]
    return f'{folder[:10]}-{folder[10:12]}-{folder[12:]}'


def read(name):
    with open(ROOT / 'data' / name, newline='') as f:
        return list(csv.DictReader(f))


def in_q3(row):
    return row['firm'] == 'MSTR' and START < row['week_end'] <= END


def sats(x):
    return round(x * SATS)


def signed(n):
    return (MINUS if n < 0 else '+') + f'{abs(n):,}'


def figures():
    """Returns (figures, sources): figure name -> display text, and one dict per underlying row."""
    attribution, actions = read('attribution.csv'), read('actions.csv')
    groups = {  # figure -> (attribution actions summed)
        'atm_sats': ('issue_common',), 'strc_sats': ('retire_pref',),
        'btc_trade_sats': ('buy_coin', 'sell_coin'), 'carry_sats': ('carry',)}
    sources, totals = [], {}
    for key, kinds in groups.items():
        rows = [r for r in attribution if in_q3(r) and r['action'] in kinds]
        total = sum(float(r['dn_exact']) for r in rows)
        totals[key] = total
        for r in rows:
            sources.append({'figure': key, 'week_end': r['week_end'], 'action': r['action'], 'ticker': r['ticker'],
                            'usd': r['usd'], 'units': '', 'dn_exact_sats': f"{float(r['dn_exact']) * SATS:.2f}",
                            'accession': accession(r['filing_url']), 'filing_url': r['filing_url'],
                            'data_file': 'data/attribution.csv'})
    strc = [r for r in actions if in_q3(r) and r['action'] == 'retire_pref']
    buys = [r for r in actions if in_q3(r) and r['action'] == 'buy_coin']
    sells = [r for r in actions if in_q3(r) and r['action'] == 'sell_coin']
    for key, rows in (('strc_usd', strc), ('btc_bought', buys), ('btc_sold', sells)):
        for r in rows:
            sources.append({'figure': key, 'week_end': r['week_end'], 'action': r['action'], 'ticker': r['ticker'],
                            'usd': r['usd'], 'units': r['units'] if key != 'strc_usd' else '', 'dn_exact_sats': '',
                            'accession': accession(r['filing_url']), 'filing_url': r['filing_url'],
                            'data_file': 'data/actions.csv'})
    usd = lambda rows: sum(float(r['usd']) for r in rows) / 1e6
    btc = lambda rows: sum(int(float(r['units'])) for r in rows)
    figs = {
        'atm_sats': signed(sats(totals['atm_sats'])), 'strc_sats': signed(sats(totals['strc_sats'])),
        'btc_trade_sats': signed(sats(totals['btc_trade_sats'])), 'carry_sats': signed(sats(totals['carry_sats'])),
        'strc_usd': f'${usd(strc):,.1f}M', 'btc_bought': f'{btc(buys):,} BTC / ${usd(buys):,.1f}M',
        'btc_sold': f'{btc(sells):,} BTC / ${usd(sells):,.1f}M'}
    figs['returned_sats'] = signed(sats(totals['atm_sats']) + sats(totals['strc_sats']))  # +332 and +179, as shown
    figs['_values'] = {k: totals[k] * SATS for k in totals}
    return figs, sources


def write_sources(sources):
    POST.mkdir(parents=True, exist_ok=True)
    with open(POST / 'sources.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(sources[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(sources)


MONTH_DAY = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2}(?:, 20\d\d)?'
BANNED = re.compile(r'\b(buy|sell|undervalued|opportunity|cheap|expensive|smart|costly|target|forecast)\b', re.I)
CAVEAT = "BTC's price move is excluded"  # the one sentence that qualifies the figures; exactly one thread post


def magnitudes(text):
    """Figure-like tokens with sign stripped: 332, $1,379.1M, 7,218. Dates, Q3, #15 and part counters are removed."""
    text = re.sub(MONTH_DAY + r'|(?m:^\d/)|Q\d|#\d+|Jul.Sep 2026|dat-accretion|8-Ks?', '', text.replace(MINUS, '-'))
    return {t.lstrip('+-') for t in re.findall(r'[+-]?\$?\d+(?:,\d{3})*(?:\.\d+)?M?', text)}


def check_text(figs):
    """Every number in thread.md and alt.txt is one of the sourced figures; no banned investment or verdict words."""
    sourced = {t for k, v in figs.items() if k != '_values' for t in magnitudes(v)}
    problems = []
    for name, body in (('thread.md', '\n'.join(thread_parts())), ('alt.txt', (POST / 'alt.txt').read_text())):
        problems += [f'{name}: {n} is not a sourced figure' for n in sorted(magnitudes(body) - sourced)]
        problems += [f'{name}: banned word {m.group(0)!r}' for m in BANNED.finditer(body)]
        problems += [f'{name}: em dash' for _ in '\u2014' if '\u2014' in body]
    return problems


def thread_parts():
    return [p.strip() for p in re.split(r'^(?=\d/ )', (POST / 'thread.md').read_text(), flags=re.M) if p.strip()]


def check_thread():
    parts = thread_parts()
    problems = [] if len(parts) == 3 else [f'thread.md has {len(parts)} posts, not 3']
    problems += [f'post {i} has {len(p)} characters (limit 279)' for i, p in enumerate(parts, 1) if len(p) > 279]
    hits = [i for i, p in enumerate(parts, 1) if CAVEAT in p]
    problems += [] if len(hits) == 1 else [f'caveat {CAVEAT!r} appears in posts {hits}, not exactly one']
    return problems


def hero(text):
    """The hero minus is its own span so CSS can set it in Plex Sans Bold; Anton's minus is its hyphen glyph, set low."""
    return f'<span class="minus">{MINUS}</span>{text[1:]}' if text.startswith(MINUS) else text


def card_html(figs, fonts):
    """Authored at 360x360 CSS px; rendered at 3x it is exactly 1080x1080. Colors and fonts are Rahil Design tokens.

    Hero: the dividends and interest figure. Two bars share one scale and one zero line: +511 to the right, the
    hero's figure to the left, each length exactly proportional to its sats.
    """
    font = lambda n: base64.b64encode((fonts / n).read_bytes()).decode()
    gain, loss = (int(figs[k].replace(MINUS, '-')) for k in ('returned_sats', 'carry_sats'))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
@font-face{{font-family:'Rahil Display';src:url(data:font/ttf;base64,{font('Anton-Regular.ttf')})}}
@font-face{{font-family:'Rahil Plex';src:url(data:font/ttf;base64,{font('IBMPlexSans-Regular.ttf')})}}
@font-face{{font-family:'Rahil Plex';font-weight:600;src:url(data:font/ttf;base64,{font('IBMPlexSans-SemiBold.ttf')})}}
@font-face{{font-family:'Rahil Plex';font-weight:700;src:url(data:font/ttf;base64,{font('IBMPlexSans-Bold.ttf')})}}
{CSS.replace('LOSS', str(-loss)).replace('GAIN', str(gain))}</style></head><body><article>
<h1>DIVIDENDS ATE THE BUYBACKS</h1>
<div class="hero"><span class="num">{hero(figs['carry_sats'])}</span><span class="what">sats per share, Q3 dividends + interest</span></div>
<div class="figure">
<div class="name">Buybacks + stock sales</div>
<div class="bars"><div class="neg"></div><div class="pos"><span class="bar gain">{figs['returned_sats']}</span></div></div>
<div class="name">Dividends + interest</div>
<div class="bars"><div class="neg"><span class="bar loss">{figs['carry_sats']}</span></div><div class="pos"></div></div>
</div>
<p class="source">{html.escape(FOOTER)}</p></article></body></html>"""


CSS = """*{box-sizing:border-box}html,body{margin:0}
body{width:360px;height:360px;background:#111214;color:#F5F5EF;font-family:'Rahil Plex',sans-serif}
article{width:360px;height:360px;padding:19px 20px;display:flex;flex-direction:column;gap:6px}
h1{font:45px/.95 'Rahil Display',sans-serif;margin:0}
.hero{display:flex;align-items:center;gap:12px}
.num{font:84px/.9 'Rahil Display',sans-serif;color:#FFE500}
.minus{font:700 103.5px/0 'Rahil Plex',sans-serif;position:relative;top:-4.5px;margin:0 -4.4px}
.what{font-size:20px;line-height:1.15;text-wrap:balance}
.figure{background:#F5F5EF;color:#111214;border-radius:12px;padding:5px 8px;font-size:20px;line-height:21px;
font-variant-numeric:tabular-nums}
.name{height:21px}
.bars{display:grid;grid-template-columns:LOSSfr GAINfr;height:24px}
.pos{border-left:2px solid #111214}
.neg{display:flex;justify-content:flex-end}
.bar{display:block;height:24px;line-height:24px;font-weight:600;padding:0 6px;white-space:nowrap}
.gain{width:100%;background:#45474C;color:#F5F5EF;text-align:right}
.loss{width:100%;background:#FFE500;outline:2px solid #111214;outline-offset:-2px;text-align:left}
.source{font-size:20px;line-height:1.05;color:#B7B8B1;margin:0;text-wrap:balance}"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--card', type=Path, help='write card.html here')
    ap.add_argument('--fonts', type=Path, help='directory with Anton-Regular.ttf and IBMPlexSans-{Regular,SemiBold,Bold}.ttf')
    args = ap.parse_args()
    figs, sources = figures()
    write_sources(sources)
    print(f'{len(sources)} source rows -> {POST / "sources.csv"}')
    for k, val in figs.items():
        if k != '_values':
            print(f'  {k}: {val}')
    if args.card:
        args.card.mkdir(parents=True, exist_ok=True)
        (args.card / 'card.html').write_text(card_html(figs, args.fonts))
    problems = check_thread() + check_text(figs) if (POST / 'thread.md').exists() else []
    for p in problems:
        print('FAIL', p)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
