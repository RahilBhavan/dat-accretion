#!/usr/bin/env python3
"""Sats per Share #16 card: 1080x1080 PNG from Rahil Design tokens and fonts (Firefox render).

    uv run --with playwright==1.63.0 python build_card.py RAHIL_DESIGN_DIR OUT_DIR PLEX_BOLD_TTF

RAHIL_DESIGN_DIR is the rahil-design skill folder (assets/tokens.json, assets/fonts/). PLEX_BOLD_TTF is IBMPlexSans-Bold.ttf
(sha256 9e6c74a8...afb2f), from https://github.com/IBM/plex packages/plex-sans/fonts/complete/ttf/, the repo the design
system's Plex files come from; the design folder has no Bold. It sets only the hero minus. Writes card.html and card.png.
Illustration only: every number is made up (coins x1.10, shares x1.25, so coins per share x0.88).
"""
import base64, hashlib, html, json, sys
from pathlib import Path

MINUS = '\N{MINUS SIGN}'
COINS, SHARES = 1.10, 1.25
CHANGE = lambda ratio: round((ratio - 1) * 100)
assert (CHANGE(COINS), CHANGE(SHARES), CHANGE(COINS / SHARES)) == (10, 25, -12) and f'{COINS / SHARES:.2f}' == '0.88'

TITLE_LINES = ('More coins,', 'less for you')
HERO_NUMBER = '12%'
PLEX_BOLD_SHA256 = '9e6c74a889a700d707613d24548fe4ffa6bc59559a0689d2cf9e133bdcdafb2f'
NUM_PX = 350
# Hero minus: U+2212 in IBM Plex Sans Bold, sized so its cap height equals Anton's digit height, with its bar lifted to
# the digits' vertical centre. Metrics from the font tables (units per em): Anton digit 1761/2048, Plex cap 698/1000,
# Plex minus bar centre 306/1000 above baseline, minus left bearing 67/1000.
ANTON_DIGIT_EM, PLEX_CAP_EM, PLEX_MINUS_MID_EM, PLEX_MINUS_LSB_EM = 1761 / 2048, 0.698, 0.306, 0.067
MINUS_PX = NUM_PX * ANTON_DIGIT_EM / PLEX_CAP_EM
MINUS_LIFT_PX = NUM_PX * ANTON_DIGIT_EM / 2 - MINUS_PX * PLEX_MINUS_MID_EM
MINUS_LSB_PX = MINUS_PX * PLEX_MINUS_LSB_EM
HERO_LABEL = 'coins per share'
SUPPORT = ('+10% coins', '+25% shares')
FOOT_LINES = ('Illustration, hypothetical', 'numbers · Oct 27')


def build(design, plex_bold):
    tokens = json.loads((design / 'assets/tokens.json').read_text())
    c = {k: v['$value'] for k, v in tokens['color'].items()}
    font = lambda n: base64.b64encode((design / 'assets/fonts' / n).read_bytes()).decode()
    bold = plex_bold.read_bytes()
    assert hashlib.sha256(bold).hexdigest() == PLEX_BOLD_SHA256, 'not the IBM Plex Sans Bold from the IBM Plex repo'
    esc = html.escape
    support = ''.join(f'<li>{esc(s)}</li>' for s in SUPPORT)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
@font-face{{font-family:'Rahil Display';src:url(data:font/ttf;base64,{font('Anton-Regular.ttf')})}}
@font-face{{font-family:'Rahil Plex';font-weight:400;src:url(data:font/ttf;base64,{font('IBMPlexSans-Regular.ttf')})}}
@font-face{{font-family:'Rahil Plex';font-weight:600;src:url(data:font/ttf;base64,{font('IBMPlexSans-SemiBold.ttf')})}}
@font-face{{font-family:'Rahil Plex';font-weight:700;src:url(data:font/ttf;base64,{base64.b64encode(bold).decode()})}}
*{{box-sizing:border-box}}html,body{{margin:0}}
body{{width:1080px;height:1080px;background:{c['canvas']};color:{c['ink']};font-family:'Rahil Plex';overflow:hidden}}
article{{width:1080px;height:1080px;padding:56px;display:flex;flex-direction:column}}
h1{{font:400 104px/1.04 'Rahil Display';margin:0;text-transform:uppercase}}
.hero{{margin:auto 0 44px;display:flex;flex-direction:column;gap:0}}
.num{{font:400 {NUM_PX}px/1 'Rahil Display';color:{c['accent']};margin:0;letter-spacing:0}}
.minus{{font:700 {MINUS_PX:.1f}px/0 'Rahil Plex';position:relative;top:{-MINUS_LIFT_PX:.1f}px;margin-left:{-MINUS_LSB_PX:.1f}px}}
.label{{font:600 68px/1.1 'Rahil Plex';margin:0}}
ul{{list-style:none;margin:0 0 44px;padding:0;display:flex;justify-content:space-between;font:600 68px/1.1 'Rahil Plex'}}
.foot{{font:400 60px/1.2 'Rahil Plex';color:{c['secondary']};margin:0}}
</style></head><body><article><h1>{'<br>'.join(esc(t) for t in TITLE_LINES)}</h1>
<section class="hero" aria-label="Illustration"><p class="num"><span class="minus">{MINUS}</span>{esc(HERO_NUMBER)}</p><p class="label">{esc(HERO_LABEL)}</p></section>
<ul>{support}</ul>
<p class="foot">{'<br>'.join(esc(t) for t in FOOT_LINES)}</p></article></body></html>"""


def main(design, out, plex_bold):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    (out / 'card.html').write_text(build(design, plex_bold), encoding='utf-8')
    firefox = Path.home() / '.cache/ms-playwright/firefox-1555/firefox/firefox'
    with sync_playwright() as p:
        browser = p.firefox.launch(executable_path=str(firefox))
        page = browser.new_page(viewport={'width': 1080, 'height': 1080}, device_scale_factor=1)
        page.goto((out / 'card.html').resolve().as_uri())
        page.evaluate('document.fonts.ready')
        page.wait_for_timeout(300)
        report = page.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect();
          const px = s => parseFloat(getComputedStyle(document.querySelector(s)).fontSize);
          return {fonts: [...document.fonts].map(f => f.family + ':' + f.status),
          h1: [r('h1').top, r('h1').bottom], hero: [r('.num').top, r('.num').bottom, r('.label').bottom],
          support: [r('ul').top, r('ul').bottom], foot: [r('.foot').top, r('.foot').bottom, r('.foot').right],
          foot_px: px('.foot'), label_px: px('.label'), num_px: px('.num'), hero_text: document.querySelector('.num').textContent.codePointAt(0).toString(16),
          overflow: [...document.querySelectorAll('article *')].filter(e => getComputedStyle(e).display !== 'inline' && e.scrollWidth > e.clientWidth + 1).map(e => e.className || e.tagName)}; }""")
        print(json.dumps(report))
        page.screenshot(path=str(out / 'card.png'))
        browser.close()


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
