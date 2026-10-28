"""Render the Oct 26 week's X cards (Rahil Design social-table template) and run their checks.

    uv run --with playwright==1.63.0 --with pillow --with numpy --with fonttools python social/2026-10-26/build_cards.py

Reads cards.json next to this file. Writes under cards/ (square 1080, phone 390, feed 360/390 composites) and checks/ (render, palette, pixel
audit, lint, hashes). The card HTML goes to ~/scratch/dat-accretion/cards-html (large, fonts embedded, rebuildable).
The pixel audit covers the card images; the feed composites add a mock X frame (black, white text) and are for inspection only.
Needs the hub checkout for Rahil Design's renderer and fonts (HUB env var overrides the default path).
Nothing here posts, uploads or publishes.
"""
import base64, hashlib, html, importlib.util, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HUB = Path(os.environ.get('HUB', '/home/rahil/.t3/projects/main'))
SKILL = HUB / '.agents/skills/rahil-design'
SCRATCH = Path.home() / 'scratch/dat-accretion/cards-html'
FIREFOX = Path.home() / '.cache/ms-playwright/firefox-1555/firefox/firefox'
sys.path.insert(0, str(SKILL / 'scripts'))
from playwright.sync_api import sync_playwright  # noqa: E402
from social_table import card_html  # noqa: E402
from social_table_checks import CHECK_JS  # noqa: E402

spec = importlib.util.spec_from_file_location('inspect_render', HUB / '.agents/skills/present-data/scripts/inspect_render.py')
inspect_render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspect_render)

CARDS = json.loads((HERE / 'cards.json').read_text())
DRAFTS = {d['id']: d for d in json.loads((HERE / 'final-drafts.json').read_text())}
TOKENS = json.loads((SKILL / 'assets/tokens.json').read_text())
OUT, CHECKS = HERE / 'cards', HERE / 'checks'
FLOOR = {k: v['$value']['value'] for k, v in TOKENS['feed'].items()}


def feed_html(draft, alt, image, width):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;width:'
            + str(width) + 'px;padding:16px;background:#000;color:#eee;font:18px/1.4 Arial}.profile{font-weight:bold;margin:0 0 12px}'
            '.profile span{font-weight:normal;color:#aaa}.copy{white-space:pre-wrap;margin:0 0 16px}'
            'img{display:block;width:100%;height:auto;border:1px solid #444;border-radius:10px}</style></head><body>'
            '<p class="profile">Rahil Bhavan <span>@Bhavanzim</span></p><p class="copy">' + html.escape(draft['copy'])
            + '</p><img alt="' + html.escape(alt, quote=True) + '" src="data:image/png;base64,'
            + base64.b64encode(image.read_bytes()).decode() + '"></body></html>')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def luminance(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def palette_report(paths):
    colors = {k: v['$value'].upper() for k, v in TOKENS['color'].items()}
    allowed = {colors[k] for k in ('canvas', 'ink', 'secondary', 'accent', 'figure-surface', 'figure-ink', 'figure-secondary')}
    pairs = [('ink', 'canvas'), ('figure-ink', 'figure-surface'), ('figure-secondary', 'figure-surface'),
             ('secondary', 'canvas'), ('figure-ink', 'accent')]
    report = {'scope': 'solid-colour Rahil role matrix on the HTML source; pixel_audit.py covers the PNGs',
              'pairs': [{'foreground': f, 'background': b, 'ratio': round(contrast(colors[f], colors[b]), 2),
                         'min': 4.5, 'ok': contrast(colors[f], colors[b]) >= 4.5} for f, b in pairs], 'cards': [], 'errors': []}
    import re
    for path in paths:
        found = sorted({c.upper() for c in re.findall(r'#[0-9a-fA-F]{6}\b', Path(path).read_text(errors='ignore').split('</style>')[0]
                        .replace(re.search(r'base64,[A-Za-z0-9+/=]+', Path(path).read_text()).group(0), ''))})
        off = [c for c in found if c not in allowed]
        report['cards'].append({'path': Path(path).name, 'colors': found, 'off_palette': off})
        report['errors'] += [f'{Path(path).name}: {c}' for c in off]
    report['errors'] += [f"{p['foreground']} on {p['background']} {p['ratio']}" for p in report['pairs'] if not p['ok']]
    report['passed'] = not report['errors']
    return report


def main():
    OUT.mkdir(exist_ok=True), CHECKS.mkdir(exist_ok=True), SCRATCH.mkdir(parents=True, exist_ok=True)
    measure, htmls = [], []
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True, executable_path=str(FIREFOX))
        for card in CARDS:
            key = card['id']
            page_path = SCRATCH / (key + '.html')
            page_path.write_text(card_html(card, TOKENS, SKILL / 'assets/fonts'))
            htmls.append(page_path)
            pg = browser.new_page(viewport={'width': 390, 'height': 390}, device_scale_factor=1080 / 390)
            pg.goto(page_path.as_uri()); pg.evaluate('document.fonts.ready')
            r = pg.evaluate(inspect_render.JS); extra = pg.evaluate(CHECK_JS); r.update(id=key, extra=extra)
            pg.screenshot(path=str(OUT / (key + '-square.png')), timeout=20000); pg.close()
            pg = browser.new_page(viewport={'width': 390, 'height': 390})
            pg.goto(page_path.as_uri()); pg.evaluate('document.fonts.ready')
            pg.screenshot(path=str(OUT / (key + '-phone.png')), timeout=20000); pg.close()
            feeds = []
            for width in (360, 390):
                f = SCRATCH / (key + f'-feed-{width}.html')
                f.write_text(feed_html(DRAFTS[key], card['alt'], OUT / (key + '-square.png'), width))
                pg = browser.new_page(viewport={'width': width, 'height': 700})
                pg.goto(f.as_uri()); pg.wait_for_function('document.querySelector("img").complete')
                pg.screenshot(path=str(OUT / (key + f'-feed-{width}.png')), full_page=True, timeout=20000)
                w = pg.locator('img').evaluate('(e)=>e.clientWidth'); scale = w / 390
                feeds.append({'viewport': width, 'image_content_width': w, 'min_label_px': round(r['min_label_px'] * scale, 2),
                              'point_px': round(r['point_px'] * scale, 2), 'overflow': pg.evaluate('document.documentElement.scrollWidth>innerWidth')})
                pg.close()
            r['feeds'] = feeds; measure.append(r)
            print(key, 'issues', len(r['issues']) + len(extra['issues']), [f['min_label_px'] for f in feeds], flush=True)
        browser.close()
    (CHECKS / 'render-checks.json').write_text(json.dumps(measure, indent=2))
    palette = palette_report(htmls)
    (CHECKS / 'palette-check.json').write_text(json.dumps(palette, indent=2))
    py = sys.executable
    audit = subprocess.run([py, str(SKILL / 'scripts/pixel_audit.py')] + [str(p) for p in sorted(OUT.glob('*-square.png')) + sorted(OUT.glob('*-phone.png'))], capture_output=True, text=True)
    lint = subprocess.run([py, str(SKILL / 'scripts/design_check.py'), 'lint'] + [str(p) for p in htmls], capture_output=True, text=True)
    (CHECKS / 'pixel-audit.txt').write_text(audit.stdout + audit.stderr + f'\nexit {audit.returncode}\n')
    (CHECKS / 'design-lint.txt').write_text((lint.stdout + lint.stderr) + f'\nexit {lint.returncode}\n')
    hashes = {p.name: sha(p) for p in sorted(OUT.glob('*.png'))}
    (CHECKS / 'sha256.json').write_text(json.dumps(hashes, indent=2))
    bad = [r['id'] for r in measure if r['issues'] or r['extra']['issues'] or not r['extra']['font_loaded']
           or any(f['min_label_px'] < FLOOR['label-floor'] or f['point_px'] < FLOOR['point-floor'] or f['overflow'] for f in r['feeds'])]
    print('palette passed' if palette['passed'] else 'PALETTE FAIL', '| pixel_audit exit', audit.returncode, '| lint exit', lint.returncode)
    if bad or not palette['passed'] or audit.returncode or lint.returncode:
        raise SystemExit('CHECK FAIL: ' + ', '.join(bad) + f' palette={palette["passed"]} audit={audit.returncode} lint={lint.returncode}')
    print('ALL CHECKS PASS for', ', '.join(c['id'] for c in CARDS))


if __name__ == '__main__':
    main()
