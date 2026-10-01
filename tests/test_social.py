import re
from dat import social
from dat.balances import read
from dat.build_site import build, counts

BANNED = re.compile(r'\b(buy|sell|undervalued|opportunity|cheap|expensive|smart|costly)\b', re.I)


def test_main_writes_cards_and_posts(tmp_path):
    assert social.main('data', str(tmp_path)) == 0
    d = build('data')
    (out,) = tmp_path.iterdir()
    assert out.name == max(w['week_end'] for w in d['weeks'] if w['firm'] == 'MSTR')

    for f in ('MSTR', 'BMNR', 'SBET'):  # split end values equal totals
        _, obs, ex = social.split_series(d['weeks'], f)
        t = d['totals'][f]
        assert abs(obs[-1] - t['observed']) < 1 and abs(ex[-1] - (t['observed'] - t['price'])) < 1
        assert social.usd(t['observed'], True) in (out / f'split-{f}.svg').read_text()

    c = counts(read('data/weekly.csv'))  # MSTR adds below break-even; BitMine adds above it
    below_m, n_m = social.gap_counts(social.gap_rows(d['weeks'], 'MSTR'))
    below_b, n_b = social.gap_counts(social.gap_rows(d['weeks'], 'BMNR'))
    assert (below_m, n_m) == c['MSTR'][:2] and (n_b - below_b, n_b) == c['BMNR'][:2]
    assert f'Below in {below_m} of {n_m} filed weeks' in (out / 'gap-MSTR.svg').read_text()
    assert f'Below in {below_b} of {n_b} weeks' in (out / 'gap-BMNR.svg').read_text()

    top = social.receipt_rows('data', d['weeks'])[:social.TOP_N]  # receipts card shows the top rows by |value|
    card = social.text_out((out / 'receipts-top.svg').read_text())
    assert all(social.usd(r['value'], True) in card for r in top)

    frames = sorted((out / 'replay').glob('frame-*.svg'))
    dates = {w['week_end'] for w in d['weeks'] if w['firm'] in ('MSTR', 'BMNR') and w['m'] is not None and w['q'] is not None}
    assert len(frames) == social.FRAMES * (len(dates) - 1) + 1 + social.HOLD_END + social.HOLD_NEAR

    svgs = sorted(out.glob('*.svg'))
    assert 'receipts-top.svg' in {p.name for p in svgs}
    texts = [social.text_out(p.read_text()) for p in [*svgs, *frames]]
    texts += [(out / n).read_text() for n in ('posts.md', 'receipts.md')]
    for t in texts:
        assert '—' not in t
        assert not BANNED.search(t), BANNED.search(t)


def test_usd_format():
    assert social.usd(1810220777, True) == '+$1.81B'
    assert social.usd(-344011738) == '−$344M'
    assert social.usd(999_700_000) == '$1.00B' and social.usd(0, True) == '$0'
    assert social.tick_usd(-4e9, 4e9) == '\u2212$4B' and social.tick_usd(0, 4e9) == '$0' and social.tick_usd(-5, 1) == '\u2212$5'
