import pytest
from dat.balances import net

# 8-K filed 2026-09-21 (acc 0001193125-26-396093; file named mstr-20260914.htm)
COINS = 846_000  # https://www.sec.gov/Archives/edgar/data/1050446/000119312526396093/mstr-20260914.htm
USD_ASSETS = 5.04e9 + 1.05e9  # USD Reserve + USD Cash, same 8-K
# converts (face, conv price), Q2 10-Q https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm
CONVERTS = [
    (1_010.0e6, 183.19),  # 2028
    (1_500.0e6, 672.40),  # 2029
    (800.0e6, 149.77),  # 2030A
    (2_000.0e6, 433.43),  # 2030B
    (603.659e6, 232.72),  # 2031
    (800.0e6, 204.33),  # 2032
]
# prefs (notional, conv price or None, shares if converted), Q2 10-Q above
PREFS = [
    (1_283.97e6, None, 0),  # STRF
    (9_316.19e6, None, 0),  # STRC: 104,894,705 at 6/30 (10-Q) − 11,732,792 repurchased per weekly 8-Ks 2026-07-27 through 2026-09-21 = 93,161,913 sh
    (1_402.07e6, 1000.0, 1_402_074),  # STRK
    (1_402.42e6, None, 0),  # STRD
    (775e6 * 1.147, None, 0),  # STRE, EUR->USD rate implied by API; Friday 12:30 NY fixing unpublished
]
# class A 364,585,501 as of 2026-07-24 (Q2 10-Q cover) + ATM MSTR shares from weekly 8-Ks for weeks
# 7/27-8/2 (3,011,361), 8/3-8/9 (6,585,682), 8/10-8/16 (3,458,866), 8/17-8/23 (18,261,118),
# 8/24-8/30 (4,531,421) = 400,433,949; + class B 19,640,250.
# API implies FDSO ~429.84M vs 429.37M here; ~0.47M gap unexplained (likely award vesting after 6/30).
BASIC = 420_074_199
AWARDS = 3_950_554  # options 3,176,105 + RSU 659,370 + PSU 115,079 (10-Q above)
P, S = 84015, 158.93  # data branch, data/kpi_snapshots.csv, 2026-09-25T16:19:32Z
API = {'net_sats_per_share': 157730.9538, 'net_reserve_usd': 56961379020,
       'amplification': 1.2478, 'mnav': 1.1994}


def run(s=S):
    return net(COINS, USD_ASSETS, CONVERTS, PREFS, BASIC, AWARDS, P, s)


@pytest.mark.parametrize('k', list(API))
def test_matches_api(k):
    got = run()[k]
    assert abs(got / API[k] - 1) < 0.005, f'{k}: rebuilt {got} vs API {API[k]}'


def test_only_2030a_itm():
    assert run()['D'] == pytest.approx(sum(f for f, cp in CONVERTS if cp != 149.77))


def test_2028_flips_at_190():
    a, b = run(), run(190)
    assert a['D'] - b['D'] == pytest.approx(1_010e6)
    assert b['S'] - a['S'] == pytest.approx(1_010e6 / 183.19)
