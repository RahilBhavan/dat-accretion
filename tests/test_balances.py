import pytest
from decimal import Decimal
from dat.balances import net, CONVERTS, pref_notional, class_a, reserve_checks, PREF_ANCHOR, bmnr_flows, bmnr_basic, BMNR_A0, BMNR_A1

# 8-K filed 2026-09-21 (acc 0001193125-26-396093; file named mstr-20260914.htm)
COINS = 846_000  # https://www.sec.gov/Archives/edgar/data/1050446/000119312526396093/mstr-20260914.htm
USD_ASSETS = 5.04e9 + 1.05e9  # USD Reserve + USD Cash, same 8-K
# converts (face, conv price): dat.balances.CONVERTS, from the Q2 10-Q
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


def act(week, action, ticker, usd='0', units='0'):
    return {'week_end': week, 'action': action, 'ticker': ticker, 'usd': usd, 'units': units}


def test_pref_roll_both_directions():
    acts = [act('2026-06-28', 'issue_pref', 'STRC', units='5000000'),  # before the 6/30 anchor: backed out
            act('2026-07-26', 'retire_pref', 'STRC', units='28893000'),
            act('2026-08-02', 'issue_pref', 'STRF', units='1000000')]
    at = lambda w, t: pref_notional(acts, w)[t]
    assert at('2026-06-30', 'STRC') == PREF_ANCHOR['STRC']
    assert at('2026-06-21', 'STRC') == PREF_ANCHOR['STRC'] - 5_000_000
    assert at('2026-06-28', 'STRC') == PREF_ANCHOR['STRC']
    assert at('2026-07-26', 'STRC') == PREF_ANCHOR['STRC'] - 28_893_000
    assert at('2026-08-02', 'STRF') == PREF_ANCHOR['STRF'] + 1_000_000
    assert at('2026-07-26', 'STRF') == PREF_ANCHOR['STRF']


def test_class_a_roll_direction():
    acts = [act('2026-07-19', 'issue_common', 'MSTR', units='100'), act('2026-07-26', 'issue_common', 'MSTR', units='10'),
            act('2026-08-02', 'issue_common', 'MSTR', units='1'), act('2026-08-09', 'buyback_common', 'MSTR', units='3')]
    base = 364_585_501
    assert class_a(acts, '2026-07-26') == base  # the 7/20-7/26 week is in the 7/24 anchor
    assert class_a(acts, '2026-07-19') == base - 10
    assert class_a(acts, '2026-07-12') == base - 110
    assert class_a(acts, '2026-08-02') == base + 1
    assert class_a(acts, '2026-08-09') == base - 2


def st(week, reserve, rprec, cash='', cprec='', r_in='', r_out=''):
    return {'week_end': week, 'usd_reserve': reserve, 'usd_reserve_prec': rprec, 'usd_cash': cash,
            'usd_cash_prec': cprec, 'reserve_in': r_in, 'reserve_out': r_out}


def test_reserve_check_pass_fail_and_kinds():
    stated = [st('2026-07-26', '3750000000', '10000000'),
              st('2026-08-02', '4000000000', '100000000', r_in='250000000'),  # tol 5M + 50M
              st('2026-08-09', '4040000000', '10000000', r_in='200000000', r_out='40000000'),
              st('2026-08-16', '5100000000', '10000000', '1590000000', '10000000'),  # prior lacks cash: reserve kind
              st('2026-08-23', '5100000000', '10000000', '1610000000', '10000000'),
              st('2026-08-30', '5100000000', '10000000', '1440000000', '10000000')]
    acts = [act('2026-08-23', 'issue_common', 'MSTR', '602800000'), act('2026-08-23', 'buy_coin', 'BTC', '369700000'),
            act('2026-08-23', 'retire_pref', 'STRC', '151800000'), act('2026-08-23', 'carry', 'DIV_INT', '-50700000'),
            act('2026-08-30', 'retire_pref', 'STRC', '196300000')]
    got = {w: (k, d, f, t, ok) for w, k, d, f, t, ok in reserve_checks(stated, acts, check_from='2026-08-02')}
    assert got['2026-08-02'] == ('reserve', 250_000_000, 250_000_000, 55_000_000, True)
    assert got['2026-08-09'][:3] == ('reserve', 40_000_000, 160_000_000) and got['2026-08-09'][4] is False  # off 120M > 55M
    assert got['2026-08-16'][0] == 'reserve' and got['2026-08-16'][4] is False  # +1.06B, nothing itemized
    assert got['2026-08-23'] == ('R', 20_000_000, 30_600_000, 20_000_000, True)  # off 10.6M within 4 x 5M
    assert got['2026-08-30'][:3] == ('R', -170_000_000, -196_300_000) and got['2026-08-30'][4] is False  # off 26.3M
    early = reserve_checks(stated[:2], acts, check_from='2026-08-09')
    assert early == [('2026-08-02', 'none', Decimal(250_000_000), Decimal(0), None, None)]


def bst(week, r):
    return {'week_end': week, 'usd_reserve': str(r)}


def test_bmnr_flows_unexplained():
    stated = [bst('2026-06-07', 200_000_000), bst('2026-06-14', 455_000_000)]
    acts = [act('2026-06-14', 'issue_pref', 'BMNP', '273800000', '350000000'),
            act('2026-06-14', 'buy_coin', 'ETH', '128000000', '76881'), act('2026-06-14', 'carry', 'DIV', '-800000')]
    d, flow, un = bmnr_flows(stated, acts)['2026-06-14']
    assert (d, flow, un) == (255_000_000, 145_000_000, 110_000_000)


def test_bmnr_basic_scales_to_anchor_then_accumulates():
    weeks = ['2026-05-31', '2026-06-07', '2026-07-12', '2026-07-19', '2026-07-26']
    gap = BMNR_A1[1] - BMNR_A0[1]
    # unexplained dR: $100 then $300 before the anchor (close $10 -> 10 and 30 shares, scaled to the gap);
    # -$50 (no issuance) and $200 after it (close $20 -> 10 shares); 5 shares bought back in 7/19.
    flows = {'2026-06-07': (0, 0, 100), '2026-07-12': (0, 0, 300), '2026-07-19': (0, 0, -50), '2026-07-26': (0, 0, 200)}
    closes = dict.fromkeys(weeks, 10.0) | {'2026-07-26': 20.0}
    acts = [act('2026-07-19', 'buyback_common', 'BMNR', units='5')]
    out, scale, between = bmnr_basic(weeks, flows, closes, acts)
    assert out['2026-05-31'][0] == BMNR_A0[1]
    assert scale == pytest.approx(gap / 40)
    assert out['2026-06-07'][0] == pytest.approx(BMNR_A0[1] + gap / 4)
    assert out['2026-07-12'][0] == BMNR_A1[1] and 'anchored' in out['2026-07-12'][2]
    assert out['2026-07-19'][0] == BMNR_A1[1] - 5 and out['2026-07-19'][1] == 0
    assert out['2026-07-26'][0] == BMNR_A1[1] - 5 + 10 and 'estimated' in out['2026-07-26'][2]


def test_bmnr_buyback_in_anchor_week_raises():
    weeks = ['2026-05-31', '2026-07-12']
    with pytest.raises(ValueError, match='holds the 2026-07-09 anchor'):
        bmnr_basic(weeks, {'2026-07-12': (0, 0, 100)}, dict.fromkeys(weeks, 10.0),
                   [act('2026-07-12', 'buyback_common', 'BMNR', units='5')])
