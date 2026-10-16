import os, re
import pytest
from dat import memo
from dat.balances import read


def test_main_writes_memo_with_computed_counts(tmp_path):
    assert memo.main('data', str(tmp_path)) == 0
    c = memo.counts(read('data/weekly.csv'))
    text = (tmp_path / 'memo.md').read_text()
    first = text.splitlines()[0]
    assert '$' in first and 'break-even' not in first  # figure-only title: break-even prices, no counts
    (a, n, _, _), (b, k, _, _), (x, y, _, _) = c['MSTR'], c['BMNR'], c['SBET']
    for s in (f'{a} of {n}', f'{k - b} of {k}', f'{x} of {y}'):
        assert s in text
    assert (tmp_path / 'map.svg').read_text().startswith('<svg') and '<svg' in (tmp_path / 'memo.html').read_text()


def test_stale_bias_fails():
    rows = read('data/weekly.csv') + [{'firm': 'BMNR', 'week_end': '2099-12-27', 'm': '1.03', 'q': '0.98'}]
    with pytest.raises(ValueError, match='rerun'):
        memo.closest(rows, memo.week_biases('data', read('data/weekly.csv')))


MSTR = {'firm': 'MSTR', 'week_end': '2026-09-20', 'm': '1.2', 'q': '0.98'}


def test_each_week_uses_its_own_bias():
    # 8/23 sits 0.5% above q; the latest bias (0.9%) exceeds that, its own (0.3%) does not: passes
    rows = [MSTR, {'firm': 'BMNR', 'week_end': '2026-08-23', 'm': '1.005', 'q': '1.0'},
            {'firm': 'BMNR', 'week_end': '2026-10-11', 'm': '1.05', 'q': '1.0'}]
    text = memo.closest(rows, {'2026-08-23': 0.003, '2026-10-11': 0.009})
    assert 'up to 0.90% of S by 2026-10-11' in text and 'leaves m above q in every BitMine week' in text
    text = memo.closest(rows, {'2026-08-23': 0.006, '2026-10-11': 0.009})  # its own bias now flips 8/23
    assert 'at or below q in 1 of 2 BitMine weeks (2026-08-23)' in text


def test_bias_that_flips_weeks_is_stated():
    rows = read('data/weekly.csv')
    text = memo.closest(rows, {w: 0.5 for w in memo.week_biases('data', rows)})  # a bias that flips every week
    n = sum(r['firm'] == 'BMNR' and bool(r['m']) and bool(r['q']) for r in rows)
    assert f'at or below q in {n} of {n} BitMine weeks' in text


def test_memo_leads_with_break_even_table(tmp_path):
    memo.main('data', str(tmp_path))
    lines = (tmp_path / 'memo.md').read_text().splitlines()
    assert lines[2].startswith('| Firm |') and 'Break-even' in lines[2]  # answer first: table right under the title
    assert '<table class="be">' in (tmp_path / 'memo.html').read_text()


def test_bitmine_row_marked_when_its_week_flips_on_the_bias():
    d = memo.build('data', online=False)
    week = {x['firm']: x for x in d['headline']}['BMNR']['week_end']
    _, rows, caption = memo.table(d, flips=[week])
    assert rows[1][-1].endswith('*') and 'within the S-estimate bias' in caption
    _, rows, caption = memo.table(d, flips=[])
    assert not rows[1][-1].endswith('*') and 'bias' not in caption
    assert rows[2][-1] == 'issue if m > 1; buy back if m < 1'


def test_map_has_equal_units_and_a_45_degree_diagonal():
    svg = memo.map_svg(memo.build('data', online=False)['weeks'])
    x1, y1, x2, y2 = map(float, re.search(
        r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" stroke="#222"', svg).groups())
    assert abs(abs(x2 - x1) - abs(y2 - y1)) < 0.2  # m = q rises one unit of m per unit of q: 45 degrees
    assert 'font-size="10"' in svg and memo.FONTS + 'ibm-plex-mono-400.woff2' in svg


def test_memo_font_path_resolves_from_docs():
    for f in ('source-serif-4.woff2', 'ibm-plex-mono-400.woff2', 'ibm-plex-mono-500.woff2'):
        assert os.path.exists(os.path.join('docs', memo.FONTS, f))


def test_causes_match_site_totals_and_sum_to_observed():
    d = memo.build('data', online=False)
    header, rows, _ = memo.causes(d)
    for f in ('MSTR', 'BMNR', 'SBET'):
        t = d['totals'][f]
        parts = ('price', 'itm_flip', 'actions', 'est_issuance', 'carry', 'residual')
        assert abs(sum(t[k] for k in parts) - t['observed']) < 1  # dollars
        col = header.index(memo.FIRMS[f]['name'])
        assert {r[0]: r[col] for r in rows}['Observed'] == memo.usd_m(t['observed'])


def test_memo_text_has_one_bias_wording_and_no_em_dash(tmp_path):
    memo.main('data', str(tmp_path))
    text = (tmp_path / 'memo.md').read_text()
    b, week = memo.bmnr_s_bias('data')
    assert memo.s_bias_text(b, week) in text and 'known upward' not in text and '—' not in text
    assert "Strategy's rotation adds while STRC is below" not in text  # the rule is not repeated after the counts
