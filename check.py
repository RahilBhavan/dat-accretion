"""Done check (`python check.py [data_dir]`): exit 0 iff every assertion passes. stdlib only.

1-2. Live Strategy KPI API netSatsPerShare and amplification vs the rebuild (latest MSTR state from
     dat.engine.states, revalued at the API's latestPrice and the live MSTR price), within 0.5%.
3.   BitMine rolled ETH vs strategicethreserve.xyz at its snapshot week (dat.parse_bmnr.check).
4.   Residual test for every in-scope week (dat.engine.residual_test; MSTR from 2026-08-02).
5.   Every unique actions.csv filing_url fetches from EDGAR (dat.edgar client: UA, 0.6s throttle; not cached).
Network failures are failures. Writes <data_dir>/check.json {status, run_at, checks: [{name, compared, ok}]}.
"""
import contextlib, datetime as dt, io, json, os, signal, sys
from decimal import Decimal
from dat.balances import read

TOL = 0.005


def load(data_dir, firm):
    pick = lambda f: [r for r in read(os.path.join(data_dir, f)) if r['firm'] == firm]
    bal = sorted(pick('balances.csv'), key=lambda b: b['date'])
    weekly = {r['week_end']: {**r, 'p': float(r['p']), 's': float(r['s'])} for r in pick('weekly.csv')}
    return bal, weekly, sorted(pick('stated.csv'), key=lambda r: r['week_end']), pick('actions.csv')


def result(name, compared, ok):
    return {'name': name, 'compared': compared, 'ok': bool(ok)}


def kpi(data_dir):
    """#1 netSatsPerShare and #2 amplification vs the live API."""
    from dat.engine import states, state_net
    from dat.snapshot_kpi import get_json, positive, KPI_URL, CHART_URL
    api = get_json(KPI_URL)['results']
    p = positive('latestPrice', api.get('latestPrice'))
    s = positive('regularMarketPrice', get_json(CHART_URL)['chart']['result'][0]['meta'].get('regularMarketPrice'))
    bal, weekly, stated, actions = load(data_dir, 'MSTR')
    w = bal[-1]['date']
    x = state_net({**states('MSTR', bal, weekly, stated, actions)[w], 'p': p, 's': s})
    src = f"state from 8-K for week {w} ({stated[-1]['filing_url']}; the API may reflect a newer 8-K), BTC ${p:,.2f} " \
          f"(API latestPrice), MSTR ${s:,.2f} (Yahoo)"
    out = []
    for name, ours, key in (('netSatsPerShare', x['net_sats_per_share'], 'netSatsPerShare'),
                            ('amplification', x['amplification'], 'amplification')):
        theirs = positive(key, api.get(key))
        d = ours / theirs - 1
        out.append(result(f'{name} vs API', f'rebuilt {ours:,.4f} vs API {theirs:,.4f}: {d:+.3%} '
                                             f'(tolerance {TOL:.1%}); {src}', abs(d) <= TOL))
    return out


def bmnr_eth(data_dir):
    """#3 rolled ETH (first stated + cumulative buy_coin units, as parse_bmnr rolls it) vs strategicethreserve.xyz."""
    from dat.parse_bmnr import check
    _, _, stated, actions = load(data_dir, 'BMNR')
    acq = {}
    for a in actions:
        if a['action'] == 'buy_coin':
            acq[a['week_end']] = acq.get(a['week_end'], 0) + Decimal(a['units'])
    parsed = [{'week_end': r['week_end'], 'coins': Decimal(r['coins']), 'acquired': acq.get(r['week_end'])}
              for r in stated]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = check(parsed, {})
    return [result('BitMine ETH vs strategicethreserve.xyz', buf.getvalue().strip().splitlines()[-1], code == 0)]


def residuals(data_dir):
    """#4 method.md item 5, per in-scope week."""
    from dat.engine import states, state_net, week_rows, attribute, residual_test, CHECK_FROM
    from dat.balances import reserve_checks
    out = []
    for firm, start in CHECK_FROM.items():
        bal, weekly, stated, actions = load(data_dir, firm)
        tol = {c[0]: float(c[4]) for c in reserve_checks(stated, actions, start) if c[4] is not None}
        sts, weeks = states(firm, bal, weekly, stated, actions), [b['date'] for b in bal]
        for prev_w, w in zip(weeks, weeks[1:]):
            if w < start:
                continue
            prev, cur = sts[prev_w], sts[w]
            rows, obs = attribute(prev, cur, week_rows(firm, prev_w, w, prev, cur, actions))
            res, usd = rows[-1]['dn_exact'], state_net(cur)['S'] * cur['p']
            ok, which = residual_test(res, obs, tol[w] / usd)
            out.append(result(f'residual {firm} {w}', f'|residual| ${abs(res) * usd / 1e6:,.1f}M vs 5% of |observed| '
                                                        f'${abs(obs) * usd / 1e6:,.1f}M = ${0.05 * abs(obs) * usd / 1e6:,.1f}M '
                                                        f'or R rounding ±${tol[w] / 1e6:,.1f}M: {which}', ok))
    return out


def filing_urls(data_dir):
    """#5 GET each unique filing_url (EDGAR may reject HEAD); urllib raises on a non-2xx status. Body discarded."""
    from dat.edgar import client
    urls = sorted({r['filing_url'] for r in read(os.path.join(data_dir, 'actions.csv')) if r['filing_url']})
    bad = []
    for i, u in enumerate(urls, 1):
        try:
            client.get(u)
        except Exception as e:
            bad.append(u)
            print(f'  FAIL {u}: {e}', flush=True)
        if i % 10 == 0 or i == len(urls):
            print(f'  fetched {i}/{len(urls)}, {len(bad)} failed', flush=True)
    return [result('actions.csv filing_url fetch', f'{len(urls) - len(bad)} of {len(urls)} unique URLs returned 200'
                                                   + (f'; failed: {", ".join(bad)}' if bad else ''), urls and not bad)]


CHECKS = [kpi, bmnr_eth, residuals, filing_urls]


def run(data_dir='data', checks=CHECKS):
    """Run every check; an exception (network included) is a failed check, never a skip."""
    out = []
    for fn in checks:
        try:
            rs = fn(data_dir)
        except Exception as e:
            rs = [result(fn.__name__, f'error: {type(e).__name__}: {e}', False)]
        for r in rs:
            print(f"{'PASS' if r['ok'] else 'FAIL'} {r['name']}: {r['compared']}")
        out += rs
    ok = bool(out) and all(r['ok'] for r in out)
    return {'status': 'pass' if ok else 'fail',
            'run_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'checks': out}


def main(data_dir='data', checks=CHECKS):
    d = {'status': 'fail', 'run_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
         'checks': [result('check.py', 'did not finish (crash or signal)', False)]}
    try:
        d = run(data_dir, checks)
    finally:  # an unexpected exception or SIGTERM still leaves a fail record
        with open(os.path.join(data_dir, 'check.json'), 'w') as f:
            json.dump(d, f, indent=1)
            f.write('\n')
    print(f"{d['status'].upper()}: {sum(r['ok'] for r in d['checks'])}/{len(d['checks'])} checks pass")
    return 0 if d['status'] == 'pass' else 1


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))  # run finally blocks on a step timeout
    sys.exit(main(*sys.argv[1:]))
