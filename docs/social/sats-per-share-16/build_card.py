#!/usr/bin/env python3
"""Sats per Share #16 card: 1080x1080 PNG from Rahil Design tokens and fonts (Firefox render).

    uv run --with playwright==1.63.0 python build_card.py RAHIL_DESIGN_DIR OUT_DIR

RAHIL_DESIGN_DIR is the rahil-design skill folder (assets/tokens.json, assets/fonts/). Writes card.html and card.png.
Illustration only: every number is made up (100 coins and 100 shares become 110 and 125).
"""
import base64, html, json, sys
from pathlib import Path

MINUS = '\N{MINUS SIGN}'
COINS, SHARES = (100, 110), (100, 125)
PER = (COINS[0] / SHARES[0], COINS[1] / SHARES[1])
CHANGE = lambda a, b: round((b / a - 1) * 100)
assert (CHANGE(*COINS), CHANGE(*SHARES), CHANGE(*PER)) == (10, 25, -12) and f'{PER[1]:.2f}' == '0.88'

TITLE_LINES = ('Coins +10%.', f'Per share {MINUS}12%.')
CONTEXT = 'Illustration · before → after'
ROWS = [('Coins', '100 → 110', None), ('Shares', '100 → 125', None), ('Per share', '1.00 → ', '0.88')]
NOTE = '110 \u00f7 125 = 0.88'
FOOT = 'Illustration, made-up numbers · definition: Strategy Net BTC per Share (SEC FWP)'


def build(design):
    tokens = json.loads((design / 'assets/tokens.json').read_text())
    c = {k: v['$value'] for k, v in tokens['color'].items()}
    font = lambda n: base64.b64encode((design / 'assets/fonts' / n).read_bytes()).decode()
    rows = ''.join('<tr><th scope="row">%s</th><td>%s%s</td></tr>' % (
        html.escape(label), html.escape(value),
        f'<span class="focus">{html.escape(hi)}</span>' if hi else '') for label, value, hi in ROWS)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
@font-face{{font-family:'Rahil Display';src:url(data:font/ttf;base64,{font('Anton-Regular.ttf')})}}
@font-face{{font-family:'Rahil Plex';src:url(data:font/ttf;base64,{font('IBMPlexSans-Regular.ttf')})}}
*{{box-sizing:border-box}}html,body{{margin:0}}
body{{width:1080px;height:1080px;background:{c['canvas']};color:{c['ink']};font-family:'Rahil Plex';overflow:hidden}}
article{{width:1080px;height:1080px;padding:56px;display:flex;flex-direction:column;gap:32px}}
h1{{font:136px/1.02 'Rahil Display';margin:0;text-transform:uppercase}}
.figure{{background:{c['figure-surface']};color:{c['figure-ink']};padding:32px 44px 34px;display:flex;flex-direction:column;gap:16px}}
.context{{font-size:54px;line-height:1.2;margin:0;color:{c['figure-secondary']}}}
table{{width:100%;border-collapse:collapse;font-size:68px;line-height:1.15;font-variant-numeric:tabular-nums}}
th,td{{padding:5px 0;font-weight:400;vertical-align:middle}}th{{text-align:left}}td{{text-align:right;white-space:nowrap}}
.focus{{display:inline-block;background:{c['accent']};color:{c['figure-ink']};outline:3px solid {c['figure-ink']};padding:0 14px}}
.note{{font-size:60px;line-height:1.2;margin:0;color:{c['figure-secondary']}}}
.foot{{font-size:44px;line-height:1.25;color:{c['secondary']};margin:0;text-wrap:balance}}
</style></head><body><article><h1>{'<br>'.join(html.escape(t) for t in TITLE_LINES)}</h1>
<section class="figure" aria-label="{html.escape(CONTEXT)}"><p class="context">{html.escape(CONTEXT)}</p><table>{rows}</table><p class="note">{html.escape(NOTE)}</p></section>
<p class="foot">{html.escape(FOOT)}</p></article></body></html>"""


def main(design, out):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    (out / 'card.html').write_text(build(design), encoding='utf-8')
    firefox = Path.home() / '.cache/ms-playwright/firefox-1555/firefox/firefox'
    with sync_playwright() as p:
        browser = p.firefox.launch(executable_path=str(firefox))
        page = browser.new_page(viewport={'width': 1080, 'height': 1080}, device_scale_factor=1)
        page.goto((out / 'card.html').resolve().as_uri())
        page.evaluate('document.fonts.ready')
        page.wait_for_timeout(300)
        report = page.evaluate("""() => { const a = document.querySelector('article').getBoundingClientRect();
          return {fonts: [...document.fonts].map(f => f.family + ':' + f.status), foot_bottom: document.querySelector('.foot').getBoundingClientRect().bottom,
          h1_lines: Math.round(document.querySelector('h1').getBoundingClientRect().height / 139), h1_right: Math.max(...[...document.querySelector('h1').getClientRects()].map(r => r.right)),
          overflow: [...document.querySelectorAll('article *')].filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.className || e.tagName)}; }""")
        print(json.dumps(report))
        page.screenshot(path=str(out / 'card.png'))
        browser.close()


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))
