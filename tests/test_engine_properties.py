"""Seeded randomized properties of dat.engine.dn_first_order against the exact recompute through balances.net().

stdlib sampling only (random.Random(seed)); pytest just runs it. The exact side is the one attribute() uses:
state_net(apply(state, row))['n'] - state_net(state)['n'], and state_net calls balances.net().

Closed forms the tests are checked against (S is pre-trade diluted shares, P the action price, eps = x/(P·S)):
  issue_common     exact = first_order / (1 + eps)   (S grows by x/P)
  buyback_common   exact = first_order / (1 - eps)
  issue_pref, retire_pref   exact = first_order      (S unchanged, N linear in x)
So the common-stock gap is O(x^2) (log-log slope 2) and the preferred gap is rounding only.
"""
import math
import random
import pytest
from dat.engine import dn_first_order, state_net, apply

SEEDS = range(8)
STATES_PER_SEED = 25
EPS = [1e-2, 3e-3, 1e-3, 3e-4, 1e-4]  # trade size as a fraction of pre-trade market cap at the action price
MIN_GAP = 0.05  # keep |m - 1| and |q - 1| away from the sign boundary so a sign flip is not rounding noise


def sample_state(rng):
    """Random out-of-the-money state: coins, reserve, converts, one preferred, shares, prices. -> state dict.
    Algebraic only: no cash sufficiency constraint on R."""
    p = math.exp(rng.uniform(math.log(1e3), math.log(2e5)))
    C = rng.uniform(1e4, 1e6)
    cap = C * p
    s = math.exp(rng.uniform(math.log(5), math.log(500)))
    converts = [(rng.uniform(0.02, 0.1) * cap, s * rng.uniform(1.2, 3)) for _ in range(rng.randint(0, 3))]  # s < cp
    basic = rng.uniform(1e7, 5e8)
    return {'C': C, 'R': rng.uniform(0, 0.3) * cap, 'converts': converts, 'conv': {},
            'prefs': {'P': rng.uniform(0.05, 0.3) * cap}, 'basic': basic, 'awards': rng.uniform(0, 0.05) * basic,
            'options': [], 'p': p, 's': s}


def ratio_off_one(rng, lo=0.3, hi=3.0):
    """Log-uniform in [lo, hi], at least MIN_GAP away from 1, either side."""
    while True:
        r = math.exp(rng.uniform(math.log(lo), math.log(hi)))
        if abs(r - 1) >= MIN_GAP:
            return r


def common_case(st, m, eps, action):
    """-> (row, price, x) for a common action at mNAV m and size eps of market cap at that price."""
    n, S = state_net(st)['n'], state_net(st)['S']
    price = m * st['p'] * n
    x = eps * price * S
    return {'action': action, 'ticker': 'X', 'usd': x, 'units': x / price, 'avg_price': price}, x


def pref_case(st, q, f, action):
    """-> (row, x) for a preferred action at price q (fraction of notional); f is the share of the pref retired
    or issued, so x = q·f·F."""
    notional = f * st['prefs']['P']
    x = q * notional
    return {'action': action, 'ticker': 'P', 'usd': x, 'units': notional, 'avg_price': 100 * q}, x


def exact_dn(st, row):
    return state_net(apply(st, row))['n'] - state_net(st)['n']


def first_order(st, row, m=None, q=None):
    return dn_first_order(row['action'], float(row['usd']), st['p'], state_net(st)['S'], m, q)


def common_gap(st, m, eps, action):
    row, x = common_case(st, m, eps, action)
    fo, ex = first_order(st, row, m=m), exact_dn(st, row)
    return x, fo, ex


def slope(xs, ys):
    """Least-squares slope of log(y) against log(x)."""
    lx, ly = [math.log(v) for v in xs], [math.log(v) for v in ys]
    mx, my = math.fsum(lx) / len(lx), math.fsum(ly) / len(ly)
    return math.fsum((a - mx) * (b - my) for a, b in zip(lx, ly)) / math.fsum((a - mx) ** 2 for a in lx)


def test_sampler_hits_requested_m():
    rng = random.Random(0)
    for _ in range(50):
        st, m = sample_state(rng), ratio_off_one(rng)
        row, _ = common_case(st, m, 1e-3, 'issue_common')
        n = state_net(st)['n']
        assert float(row['avg_price']) / (st['p'] * n) == pytest.approx(m, rel=1e-12)
        assert state_net(st)['N'] > 0
        assert all(st['s'] < cp for _, cp in st['converts'])  # no ITM flip inside the trade


# ---- sign checks (iff, both sides) ----

@pytest.mark.parametrize('seed', SEEDS)
def test_issue_common_accretive_iff_m_above_one(seed):
    rng = random.Random(seed)
    for _ in range(STATES_PER_SEED):
        st, m = sample_state(rng), ratio_off_one(rng)
        for eps in EPS:
            _, fo, ex = common_gap(st, m, eps, 'issue_common')
            assert (fo > 0) == (m > 1) and (ex > 0) == (m > 1), (seed, m, eps, fo, ex)


@pytest.mark.parametrize('seed', SEEDS)
def test_buyback_common_accretive_iff_m_below_one(seed):
    rng = random.Random(seed)
    for _ in range(STATES_PER_SEED):
        st, m = sample_state(rng), ratio_off_one(rng)
        for eps in EPS:
            _, fo, ex = common_gap(st, m, eps, 'buyback_common')
            assert (fo > 0) == (m < 1) and (ex > 0) == (m < 1), (seed, m, eps, fo, ex)


@pytest.mark.parametrize('seed', SEEDS)
def test_retire_pref_accretive_iff_q_below_one(seed):
    """method.md: retire_pref = k·(1/q − 1) adds while q < 1 (STRC at $86.52 is the anchor).
    The request text said q > 1; the exact recompute below shows that sign is dilutive."""
    rng = random.Random(seed)
    for _ in range(STATES_PER_SEED):
        st, q = sample_state(rng), ratio_off_one(rng, 0.5, 1.5)
        for f in EPS:
            row, _ = pref_case(st, q, f, 'retire_pref')
            fo, ex = first_order(st, row, q=q), exact_dn(st, row)
            assert (fo > 0) == (q < 1) and (ex > 0) == (q < 1), (seed, q, f, fo, ex)


@pytest.mark.parametrize('seed', SEEDS)
def test_issue_pref_accretive_iff_q_above_one(seed):
    rng = random.Random(seed)
    for _ in range(STATES_PER_SEED):
        st, q = sample_state(rng), ratio_off_one(rng, 0.5, 1.5)
        for f in EPS:
            row, _ = pref_case(st, q, f, 'issue_pref')
            fo, ex = first_order(st, row, q=q), exact_dn(st, row)
            assert (fo > 0) == (q > 1) and (ex > 0) == (q > 1), (seed, q, f, fo, ex)


def test_exact_zero_at_par():
    rng = random.Random(1)
    for _ in range(STATES_PER_SEED):
        st = sample_state(rng)
        n = state_net(st)['n']
        for action in ('issue_common', 'buyback_common'):
            row, _ = common_case(st, 1.0, 1e-3, action)
            assert exact_dn(st, row) == pytest.approx(0, abs=1e-9 * n)
        for action in ('issue_pref', 'retire_pref'):
            row, _ = pref_case(st, 1.0, 1e-3, action)
            assert exact_dn(st, row) == pytest.approx(0, abs=1e-9 * n)


# ---- antisymmetry ----

@pytest.mark.parametrize('seed', SEEDS)
def test_first_order_pairs_are_exact_negatives(seed):
    """Float subtraction is antisymmetric, so (1 − 1/m) and (1/m − 1) negate bit for bit."""
    rng = random.Random(seed)
    for _ in range(200):
        x, p, S = math.exp(rng.uniform(10, 24)), math.exp(rng.uniform(7, 12)), math.exp(rng.uniform(15, 20))
        m, q = ratio_off_one(rng), ratio_off_one(rng, 0.5, 1.5)
        assert dn_first_order('issue_common', x, p, S, m=m) == -dn_first_order('buyback_common', x, p, S, m=m)
        assert dn_first_order('issue_pref', x, p, S, q=q) == -dn_first_order('retire_pref', x, p, S, q=q)


@pytest.mark.parametrize('seed', SEEDS)
def test_exact_pref_pair_negates(seed):
    """S is unchanged, so issuing then retiring the same notional at the same q is exact up to rounding."""
    rng = random.Random(seed)
    for _ in range(STATES_PER_SEED):
        st, q = sample_state(rng), ratio_off_one(rng, 0.5, 1.5)
        for f in EPS:
            issue, _ = pref_case(st, q, f, 'issue_pref')
            retire, _ = pref_case(st, q, f, 'retire_pref')
            a, b = exact_dn(st, issue), exact_dn(st, retire)
            assert a + b == pytest.approx(0, abs=1e-8 * abs(a)), (seed, q, f, a, b)


@pytest.mark.parametrize('seed', SEEDS)
def test_exact_common_pair_negates_to_second_order(seed):
    """issue = fo/(1+eps), buyback = −fo/(1−eps): the sum is −2·eps·fo/(1−eps²), relative size 2·eps."""
    rng = random.Random(seed)
    for _ in range(STATES_PER_SEED):
        st, m = sample_state(rng), ratio_off_one(rng)
        rel = []
        for eps in EPS:
            _, fo, a = common_gap(st, m, eps, 'issue_common')
            _, _, b = common_gap(st, m, eps, 'buyback_common')
            rel.append(abs(a + b) / abs(fo))
            assert rel[-1] == pytest.approx(2 * eps / (1 - eps * eps), rel=1e-6), (seed, m, eps)
        assert rel == sorted(rel, reverse=True)  # shrinks with size


# ---- convergence ----

@pytest.mark.parametrize('action', ['issue_common', 'buyback_common'])
@pytest.mark.parametrize('seed', SEEDS)
def test_common_gap_matches_closed_form(seed, action):
    rng = random.Random(seed)
    sign = 1 if action == 'issue_common' else -1
    for _ in range(STATES_PER_SEED):
        st, m = sample_state(rng), ratio_off_one(rng)
        for eps in EPS:
            _, fo, ex = common_gap(st, m, eps, action)
            assert ex == pytest.approx(fo / (1 + sign * eps), rel=1e-6), (seed, m, eps, fo, ex)


@pytest.mark.parametrize('action', ['issue_common', 'buyback_common'])
@pytest.mark.parametrize('seed', SEEDS)
def test_common_gap_shrinks_faster_than_size(seed, action):
    """gap/x falls as x falls, and the log-log slope of gap against x is 2, not 1."""
    rng = random.Random(seed)
    for _ in range(STATES_PER_SEED):
        st, m = sample_state(rng), ratio_off_one(rng)
        xs, gaps = [], []
        for eps in EPS:
            x, fo, ex = common_gap(st, m, eps, action)
            xs.append(x); gaps.append(abs(fo - ex))
        per_size = [g / x for g, x in zip(gaps, xs)]
        assert per_size == sorted(per_size, reverse=True), (seed, m, per_size)
        assert 1.9 < slope(xs, gaps) < 2.1, (seed, m, slope(xs, gaps))


@pytest.mark.parametrize('action', ['issue_pref', 'retire_pref'])
@pytest.mark.parametrize('seed', SEEDS)
def test_pref_first_order_is_exact(seed, action):
    rng = random.Random(seed)
    for _ in range(STATES_PER_SEED):
        st, q = sample_state(rng), ratio_off_one(rng, 0.5, 1.5)
        for f in EPS:
            row, _ = pref_case(st, q, f, action)
            fo, ex = first_order(st, row, q=q), exact_dn(st, row)
            assert ex == pytest.approx(fo, rel=1e-8), (seed, q, f, fo, ex)


def test_coin_trades_are_zero_first_order():
    rng = random.Random(3)
    for _ in range(STATES_PER_SEED):
        st = sample_state(rng)
        pre = state_net(st)['n']
        usd = 1e-3 * st['p'] * st['C']
        for action, units in (('buy_coin', usd / st['p']), ('sell_coin', usd / st['p'])):
            row = {'action': action, 'ticker': 'BTC', 'usd': usd, 'units': units, 'avg_price': st['p']}
            assert dn_first_order(action, usd, st['p'], state_net(st)['S']) == 0
            assert exact_dn(st, row) == pytest.approx(0, abs=1e-9 * pre)  # bought at p: N and n unchanged
