import math
import pytest
from dat.balances import CONVERTS, STRK_CONV, AWARDS
from dat.engine import dn_first_order, strategy_rotation, bitmine_rotation, state_net, apply, attribute, residual_test

P, S = 64_092.65, 388_176_305  # MSTR 7/26 week: weekly.csv p, balances.csv shares_diluted


def test_strc_anchor():
    # Bitcoin Magazine STRC week: $24,998,000 retires $28,893,000 notional.
    x, notional = 24_998_000, 28_893_000
    q = x / notional
    assert round(q, 4) == 0.8652  # 0.865192...; method.md "q = 0.8652"
    # value to common = dn·p·S = (1/q − 1)·x = notional − x = 28,893,000 − 24,998,000 = 3,895,000
    assert round(dn_first_order('retire_pref', x, P, S, q=q) * P * S) == 3_895_000


@pytest.mark.parametrize('action', ['issue_common', 'buyback_common', 'issue_pref', 'retire_pref', 'buy_coin', 'sell_coin'])
def test_zero_at_par(action):
    assert dn_first_order(action, 1e8, P, S, m=1.0, q=1.0) == 0


@pytest.mark.parametrize('mq', [0.6, 0.87, 1.0, 1.4, 2.5])
def test_rotations_zero_at_m_eq_q(mq):
    assert strategy_rotation(1e8, P, S, mq, mq) == pytest.approx(0, abs=1e-20)
    assert bitmine_rotation(1e8, P, S, mq, mq) == pytest.approx(0, abs=1e-20)
    assert strategy_rotation(1e8, P, S, mq * 1.1, mq) > 0 > bitmine_rotation(1e8, P, S, mq * 1.1, mq)


def mstr_state():
    """Strategy at 2026-09-20: 846,000 BTC, R $6.09B, Q2 converts, prefs rolled to 9/20 (balances.py)."""
    return {'C': 846_000.0, 'R': 6.09e9, 'converts': CONVERTS, 'conv': {'STRK': STRK_CONV},
            'prefs': {'STRF': 1_283_969_000.0, 'STRC': 9_316_191_300.0, 'STRK': 1_402_074_000.0,
                      'STRD': 1_402_422_000.0, 'STRE': 775e6 * 1.147},
            'basic': 400_433_949.0 + 19_640_250, 'awards': AWARDS, 'options': [], 'p': 80_873.58, 's': 153.92}


@pytest.mark.parametrize('row', [
    {'action': 'issue_common', 'ticker': 'MSTR', 'usd': '300000000', 'units': '2000000', 'avg_price': '150'},
    {'action': 'retire_pref', 'ticker': 'STRC', 'usd': '174000000', 'units': '177123800', 'avg_price': '98.236375'}])
def test_first_order_matches_exact(row):
    st = mstr_state()
    pre = state_net(st)
    assert float(row['usd']) < 0.01 * st['s'] * pre['S']  # under 1% of market cap
    m = float(row['avg_price']) / (st['p'] * pre['n']) if row['action'] == 'issue_common' else None
    q = float(row['avg_price']) / 100 if row['action'] == 'retire_pref' else None
    fo = dn_first_order(row['action'], float(row['usd']), st['p'], pre['S'], m, q)
    exact = state_net(apply(st, row))['n'] - pre['n']
    assert fo == pytest.approx(exact, rel=0.01)


def test_identity_two_weeks():
    prev = {'C': 1000.0, 'R': 5e6, 'converts': [(20e6, 12.0)], 'prefs': {'P': 30e6}, 'conv': {}, 'basic': 1e6,
            'awards': 1e4, 'options': [(5e4, 11.0)], 'p': 50_000.0, 's': 10.0}
    acts = [{'action': 'issue_common', 'ticker': 'X', 'usd': '2000000', 'units': '150000', 'avg_price': '13.3333'},
            {'action': 'buy_coin', 'ticker': 'BTC', 'usd': '1500000', 'units': '29', 'avg_price': '51724'},
            {'action': 'retire_pref', 'ticker': 'P', 'usd': '900000', 'units': '1000000', 'avg_price': '90'},
            {'action': 'carry', 'ticker': 'DIV', 'usd': '-200000', 'units': '0', 'avg_price': ''}]
    cur = dict(prev, C=1033.0, R=4.5e6, prefs={'P': 29e6}, basic=1.15e6, p=52_000.0, s=13.0)  # s crosses 11 and 12
    rows, obs = attribute(prev, cur, acts)
    assert [r['action'] for r in rows] == ['price', 'itm_flip', 'issue_common', 'buy_coin', 'retire_pref', 'carry', 'residual']
    assert rows[1]['dn_exact'] != 0  # convert (D -> S) and options cross at s = 13
    assert math.fsum(r['dn_exact'] for r in rows) == pytest.approx(obs, rel=1e-12)
    assert obs == pytest.approx(state_net(cur)['n'] - state_net(prev)['n'], rel=1e-15)


def test_residual_test():
    # 8/30-like week: -$10.6M residual on a -$106.9M week (9.9%), R rounding ±$20M; value = dn·p·S
    to_dn = 1 / (77_820.76 * 424_024_753)
    obs, tol = -106.9e6 * to_dn, 20e6 * to_dn
    assert residual_test(-3e6 * to_dn, obs, tol) == (True, '<5%')
    assert residual_test(-10.6e6 * to_dn, obs, tol) == (True, 'rounding')
    assert residual_test(-25e6 * to_dn, obs, tol) == (False, 'FAIL')
