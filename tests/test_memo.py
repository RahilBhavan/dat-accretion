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
    assert '<table>' in (tmp_path / 'memo.html').read_text()
