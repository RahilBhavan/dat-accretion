import pytest
from dat import memo
from dat.balances import read, bmnr_s_bias


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
        memo.closest(rows, (0.0043, '2026-09-20'))


def test_bias_that_flips_a_week_fails():
    with pytest.raises(ValueError, match='rewrite the footnote'):
        memo.closest(read('data/weekly.csv'), (0.02, bmnr_s_bias('data')[1]))
