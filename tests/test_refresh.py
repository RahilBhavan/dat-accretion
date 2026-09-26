import check
from dat import refresh
from dat.balances import bmnr_s_bias


def test_steps_order():
    # prices before parse_bmnr (it prices ETH buys); both parsers before balances; memo reads the engine's output
    assert refresh.STEPS == ['dat.parse_mstr', 'dat.prices', 'dat.parse_bmnr', 'dat.balances', 'dat.engine',
                             'dat.memo', 'dat.build_site']


def test_reanchor_filter_keeps_only_periods_after_the_anchor():
    fs = [{'form': '10-Q', 'period': '2026-06-30', 'url': 'q2'}, {'form': '10-Q', 'period': '2026-09-30', 'url': 'q3'}]
    assert refresh.newer(fs, '2026-06-30') == [fs[1]]


def test_bmnr_s_bias_pin():
    # method.md "BitMine S": about +0.43% of S by 2026-09-20; the memo prints it to 2 dp
    b, week = bmnr_s_bias('data', '2026-09-20')
    assert week == '2026-09-20' and f'{b:.2%}' == '0.43%'


def test_newer_8k_text():
    fs = [{'filed': '2026-09-21'}, {'filed': '2026-09-25', 'skip': 1}, {'filed': '2026-09-28'}]
    holdings = lambda f: 'skip' not in f
    assert (check.newer_8k('2026-09-20', '2026-09-21', fs, holdings)
            == '; repo at week 2026-09-20; newer 8-K filed 2026-09-28 not yet parsed')
    assert check.newer_8k('2026-09-20', '2026-09-21', fs[:2], holdings) == ''
