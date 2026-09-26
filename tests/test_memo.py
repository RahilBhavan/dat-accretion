import pytest
from dat import memo
from dat.balances import read


def test_main_writes_memo_with_computed_counts(tmp_path):
    assert memo.main('data', str(tmp_path)) == 0
    c = memo.counts(read('data/weekly.csv'))
    text = (tmp_path / 'memo.md').read_text()
    for a, n, _, _ in c.values():
        assert f'{a} of {n}' in text.splitlines()[0]
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
    assert 'up to 0.90% of S by 2026-10-11' in text
    with pytest.raises(ValueError, match='rewrite the footnote'):
        memo.closest(rows, {'2026-08-23': 0.006, '2026-10-11': 0.009})


def test_bias_that_flips_a_week_fails():
    rows = read('data/weekly.csv')
    with pytest.raises(ValueError, match='rewrite the footnote'):
        memo.closest(rows, {w: 0.02 for w in memo.week_biases('data', rows)})
