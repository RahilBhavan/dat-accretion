#!/usr/bin/env python3
"""Sats per Share #16 bar card ("More coins, less per share."): 1080x1080 PNG from Rahil Design tokens and fonts.

    uv run --with playwright==1.63.0 python build_card.py RAHIL_DESIGN_DIR OUT_DIR

RAHIL_DESIGN_DIR is the rahil-design skill folder (assets/tokens.json, assets/fonts/). Writes card.html, card.png,
alt.txt and manifest.json (sha256 of each). Illustration only: every number is made up.
The hub's social_bars.py builds this card at 390 px with a 22 px floor; the required label and footer overflow it
(28 words outside the title, the label wraps), so this script lays the same card out at 1080 px.
"""
import base64, hashlib, html, json, sys
from pathlib import Path

MINUS = '\N{MINUS SIGN}'
COINS, SHARES, BEFORE = 110, 125, 100
PER = round(COINS / SHARES * 100)
CHANGE = round((COINS / SHARES - 1) * 100)
assert (PER, CHANGE) == (88, -12)

TITLE = 'More coins, less per share.'
LABEL = 'Illustration, made-up numbers · index, before = 100 (gross coins)'
FOOT = 'Net definition: Strategy FWP (SEC), Aug 24, 2026'
SCALE_MAX = 130
BAR_AT_MAX = 400
ROWS = [('Before', BEFORE, 'hollow', None), ('Coins', COINS, 'bar', None), ('Shares', SHARES, 'bar', None),
        ('Per share', PER, 'hi', f'{MINUS}{abs(CHANGE)}%')]
ALT = (f'More coins, less per share. {LABEL}. Before = 100. Coins {COINS}, shares {SHARES}, per share {PER}, '
       f'{MINUS}{abs(CHANGE)}% (110 ÷ 125). Strategy’s net bitcoin per share also nets out USD assets, '
       f'debt and preferred claims; this example does not. Not a filing. {FOOT}')


def build(design):
    tokens = json.loads((design / 'assets/tokens.json').read_text())
    c = {k: v['$value'] for k, v in tokens['color'].items()}
    ch = {k: v['$value'] for k, v in tokens['chart'].items()}
    font = lambda n: base64.b64encode((design / 'assets/fonts' / n).read_bytes()).decode()
    rows = ''
    for label, value, kind, delta in ROWS:
        width = round(BAR_AT_MAX * value / SCALE_MAX)
        extra = f'<span class="delta">{html.escape(delta)}</span>' if delta else ''
        rows += (f'<div class="row"><span class="label">{html.escape(label)}</span><span class="trk">'
                 f'<span class="{kind}" style="width:{width}px"></span><span class="value">{value}</span>{extra}</span></div>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
@font-face{{font-family:'Rahil Display';src:url(data:font/ttf;base64,{font('Anton-Regular.ttf')})}}
@font-face{{font-family:'Rahil Plex';src:url(data:font/ttf;base64,{font('IBMPlexSans-Regular.ttf')})}}
@font-face{{font-family:'Rahil Plex';font-weight:600;src:url(data:font/ttf;base64,{font('IBMPlexSans-SemiBold.ttf')})}}
*{{box-sizing:border-box}}html,body{{margin:0}}
body{{width:1080px;height:1080px;background:{c['canvas']};color:{c['ink']};font-family:'Rahil Plex',sans-serif;overflow:hidden}}
article{{width:1080px;height:1080px;padding:56px;display:flex;flex-direction:column;gap:32px}}
h1{{font:136px/1.0 'Rahil Display',sans-serif;margin:0;text-transform:uppercase}}
.figure{{background:{c['figure-surface']};color:{c['figure-ink']};border-radius:{tokens['radius']['panel']['$value']['value']}px;padding:36px 44px 40px;display:flex;flex-direction:column;gap:22px;font-variant-numeric:tabular-nums}}
.ph{{font-size:40px;line-height:1.2;color:{c['figure-secondary']};margin:0;text-wrap:balance}}
.row{{display:grid;grid-template-columns:240px 1fr;align-items:center;gap:24px;font-size:56px;line-height:1.1}}
.label{{text-align:right;white-space:nowrap}}.trk{{display:flex;align-items:center;gap:18px;white-space:nowrap}}
.bar,.hi,.hollow{{display:block;height:50px;flex:none}}
.bar{{background:{ch['series-3']}}}.hollow{{background:{c['figure-surface']};border:5px solid {ch['series-1']}}}
.hi{{background:{ch['highlight']};outline:5px solid {ch['series-1']};outline-offset:-5px}}
.delta{{font-weight:600;margin-left:6px}}
.foot{{font-size:46px;line-height:1.25;color:{c['ink']};margin:0;text-wrap:balance}}
</style></head><body><article><h1>{html.escape(TITLE)}</h1>
<section class="figure"><p class="ph">{html.escape(LABEL)}</p>{rows}</section>
<p class="foot">{html.escape(FOOT)}</p></article></body></html>"""


def main(design, out):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    (out / 'card.html').write_text(build(design), encoding='utf-8')
    (out / 'alt.txt').write_text(ALT + '\n', encoding='utf-8')
    firefox = Path.home() / '.cache/ms-playwright/firefox-1555/firefox/firefox'
    with sync_playwright() as p:
        browser = p.firefox.launch(executable_path=str(firefox))
        page = browser.new_page(viewport={'width': 1080, 'height': 1080}, device_scale_factor=1)
        page.goto((out / 'card.html').resolve().as_uri())
        page.evaluate('document.fonts.ready')
        page.wait_for_timeout(300)
        report = page.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect();
          return {fonts: [...document.fonts].map(f => f.family + ':' + f.status), foot_bottom: r('.foot').bottom,
          h1_lines: Math.round(r('h1').height / 136), foot_lines: Math.round(r('.foot').height / 57.5),
          foot_color: getComputedStyle(document.querySelector('.foot')).color,
          delta: document.querySelector('.delta').textContent, ph_lines: Math.round(r('.ph').height / 48),
          delta_right: r('.delta').right, figure_right: r('.figure').right, figure_bottom: r('.figure').bottom,
          overflow: [...document.querySelectorAll('article *')].filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.className || e.tagName)}; }""")
        print(json.dumps(report, ensure_ascii=False))
        page.screenshot(path=str(out / 'card.png'))
        browser.close()
    manifest = {n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in ('card.png', 'card.html', 'alt.txt')}
    (out / 'manifest.json').write_text(json.dumps({'id': 'tue27-pm-per-share', 'size': '1080x1080', 'sha256': manifest}, indent=2) + '\n')


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))
