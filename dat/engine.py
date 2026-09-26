"""Step 4 (`python -m dat.engine`): weekly attribution of Δn -> data/attribution.csv. stdlib only.

method.md "Actions" (five first-order formulas) and "Attribution (Step 4)": each week's observed Δn is
split into price, itm_flip, each action (actions.csv order), carry, est_issuance (BMNR, S estimated),
and residual. Every step is an exact recompute through net().
"""
import math, os, sys
from dat.balances import (net, read, write, CONVERTS, STRK_CONV, CLASS_B, AWARDS, pref_notional, class_a,
                          bmnr_flows, bmnr_basic, BMNR_RSU, BMNR_DILUTIVE, reserve_checks, sbet_basic, sbet_awards,
                          sbet_options)

FIELDS = ['firm', 'week_end', 'action', 'ticker', 'usd', 'm', 'q', 'dn_first_order', 'dn_exact', 'dn_per_dollar',
          'filing_url']
COMMON, PREF = ('issue_common', 'buyback_common'), ('issue_pref', 'retire_pref')
CHECK_FROM = {'MSTR': '2026-08-02'}  # 5% residual scope (method.md); BMNR and SBET: report only
LIMIT = 0.05


def dn_first_order(action, x, p, S, m=None, q=None):
    """method.md table: k = x/(p·S), x dollars. Coin trades are 0 on day one."""
    k = x / (p * S)
    return {'issue_common': lambda: k * (1 - 1 / m), 'buyback_common': lambda: k * (1 / m - 1),
            'issue_pref': lambda: k * (1 - 1 / q), 'retire_pref': lambda: k * (1 / q - 1),
            'buy_coin': lambda: 0.0, 'sell_coin': lambda: 0.0}[action]()


def residual_test(res, obs, tol_dn):
    """method.md item 5: pass if |res| < 5% of |obs| or |res| <= the week's R rounding tolerance in Δn.
    -> (ok, which): '<5%', 'rounding', or 'FAIL'."""
    if abs(res) < LIMIT * abs(obs):
        return True, '<5%'
    return (True, 'rounding') if abs(res) <= tol_dn else (False, 'FAIL')


def strategy_rotation(x, p, S, m, q):
    """Issue common (1) and retire preferred (4) with the same x: k·(1/q − 1/m), adds while m > q."""
    return dn_first_order('issue_common', x, p, S, m=m) + dn_first_order('retire_pref', x, p, S, q=q)


def bitmine_rotation(x, p, S, m, q):
    """Issue preferred (3) and buy back common (2) with the same x: k·(1/m − 1/q), adds while m < q."""
    return dn_first_order('issue_pref', x, p, S, q=q) + dn_first_order('buyback_common', x, p, S, m=m)


def state_net(st):
    """State dict: C, R, converts [(face, cp)], prefs {ticker: notional}, conv {ticker: cp}, basic, awards,
    options [(shares, strike)] (in S only while s > strike), p, s. -> net() dict."""
    prefs = [(v, st['conv'].get(t), v / st['conv'][t] if t in st['conv'] else 0) for t, v in st['prefs'].items()]
    prefs += [(0.0, k, sh) for sh, k in st['options']]
    return net(st['C'], st['R'], st['converts'], prefs, st['basic'], st['awards'], st['p'], st['s'])


def apply(st, a):
    """New state after one actions.csv-style row (usd, units positive magnitudes; carry signed)."""
    st = {**st, 'prefs': dict(st['prefs'])}
    act, usd, u = a['action'], float(a['usd']), float(a['units'] or 0)
    if act == 'issue_common':
        st['R'] += usd; st['basic'] += u
    elif act == 'buyback_common':
        st['R'] -= usd; st['basic'] -= u
    elif act == 'issue_pref':
        st['R'] += usd; st['prefs'][a['ticker']] = st['prefs'].get(a['ticker'], 0.0) + u
    elif act == 'retire_pref':
        st['R'] -= usd; st['prefs'][a['ticker']] -= u
    elif act == 'buy_coin':
        st['C'] += u; st['R'] -= usd
    elif act == 'sell_coin':
        st['C'] -= u; st['R'] += usd
    elif act == 'carry':
        st['R'] += usd; st['C'] += u
    else:
        raise ValueError(f'unknown action {act}')
    return st


def attribute(prev, cur, rows):
    """-> (out rows, observed Δn). rows are applied in the given order after price and itm_flip; a row's
    'label' (default: its action) names it in the output. Residual = observed − sum of the rest."""
    out, st = [], prev

    def step(label, new, **kw):
        nonlocal st
        out.append({'action': label, 'dn_exact': state_net(new)['n'] - state_net(st)['n'], **kw})
        st = new

    step('price', {**st, 'p': cur['p']})
    step('itm_flip', {**st, 's': cur['s']})
    for a in rows:
        act, x, pre = a['action'], float(a['usd']), state_net(st)
        m = float(a['avg_price']) / (st['p'] * pre['n']) if act in COMMON else None
        q = float(a['avg_price']) / 100 if act in PREF else None
        new = apply(st, a)
        dn = state_net(new)['n'] - pre['n']
        is_act = act != 'carry'
        step(a.get('label', act), new, ticker=a['ticker'], usd=x, m=m, q=q,
             dn_first_order=dn_first_order(act, x, st['p'], pre['S'], m, q) if is_act else None,
             dn_per_dollar=dn / x if is_act else None, filing_url=a.get('filing_url', ''))
    obs = state_net(cur)['n'] - state_net(prev)['n']
    out.append({'action': 'residual', 'dn_exact': obs - math.fsum(r['dn_exact'] for r in out)})
    return out, obs


def states(firm, bal, weekly, stated, actions):
    """{week: state} from balances.csv C, R (BMNR F), weekly.csv p, s; per-ticker prefs and basic shares
    rebuilt with dat.balances helpers."""
    out = {}
    if firm == 'BMNR':
        weeks = [b['date'] for b in bal]
        basic, _, _ = bmnr_basic(weeks, bmnr_flows(stated, actions), {w: weekly[w]['s'] for w in weeks}, actions)
    for b in bal:
        w = b['date']
        st = {'C': float(b['coins']), 'R': float(b['usd_reserve']), 'p': weekly[w]['p'], 's': weekly[w]['s']}
        if firm == 'MSTR':
            st.update(converts=CONVERTS, prefs=pref_notional(actions, w), conv={'STRK': STRK_CONV},
                      basic=class_a(actions, w) + CLASS_B, awards=AWARDS, options=[])
        elif firm == 'BMNR':
            st.update(converts=[], prefs={'BMNP': float(b['pref_notional'])}, conv={}, basic=basic[w][0],
                      awards=BMNR_RSU, options=BMNR_DILUTIVE)
        else:  # SBET: no converts or preferred; rows per filed holdings date
            st.update(converts=[], prefs={}, conv={}, basic=sbet_basic(actions, w)[0], awards=sbet_awards(w),
                      options=sbet_options(w))
        out[w] = st
    return out


def week_rows(firm, prev_w, w, prev, cur, actions):
    """Rows to apply for week w, in method.md order: actions, carry, est_issuance."""
    acts = [a for a in actions if prev_w < a['week_end'] <= w]
    rows = [a for a in acts if a['action'] != 'carry'] + [a for a in acts if a['action'] == 'carry']
    if firm == 'BMNR':  # basic-share change not explained by buybacks: the S estimate (balances.csv source)
        u = cur['basic'] - prev['basic'] + sum(float(a['units']) for a in acts if a['action'] == 'buyback_common')
        if abs(u) > 0.5:
            rows.append({'action': 'issue_common', 'label': 'est_issuance', 'ticker': 'BMNR', 'usd': u * cur['s'],
                         'units': u, 'avg_price': cur['s'], 'filing_url': ''})
    return rows


def fmt(v, spec=None):
    return '' if v is None or v == '' else (format(v, spec) if spec else repr(float(v)))


def main(data_dir='data'):
    path = lambda f: os.path.join(data_dir, f)
    all_bal, all_weekly, all_stated, all_actions = (read(path(f)) for f in
                                                    ('balances.csv', 'weekly.csv', 'stated.csv', 'actions.csv'))
    out, bad_id, bad_n, scope = [], [], [], []
    for firm in ('BMNR', 'MSTR', 'SBET'):
        pick = lambda rows: [r for r in rows if r['firm'] == firm]
        bal = sorted(pick(all_bal), key=lambda b: b['date'])
        weekly = {r['week_end']: {**r, 'p': float(r['p']), 's': float(r['s'])} for r in pick(all_weekly)}
        actions, st_rows = pick(all_actions), sorted(pick(all_stated), key=lambda r: r['week_end'])
        tol = {c[0]: float(c[4]) for c in reserve_checks(st_rows, actions, CHECK_FROM[firm])
               if c[4] is not None} if firm in CHECK_FROM else {}
        sts = states(firm, bal, weekly, st_rows, actions)
        weeks = [b['date'] for b in bal]
        for w in weeks:  # rebuilt n must be weekly.csv's n (10 significant digits there)
            if abs(state_net(sts[w])['n'] / float(weekly[w]['n']) - 1) > 1e-9:
                bad_n.append((firm, w))
        print(f'{firm} {weeks[0]} anchor week: no attribution')
        for prev_w, w in zip(weeks, weeks[1:]):
            prev, cur = sts[prev_w], sts[w]
            rows, obs = attribute(prev, cur, week_rows(firm, prev_w, w, prev, cur, actions))
            total = math.fsum(r['dn_exact'] for r in rows)
            if abs(total - obs) > 1e-12 * abs(obs):
                bad_id.append((firm, w))
            res = rows[-1]['dn_exact']
            in_scope = firm in CHECK_FROM and w >= CHECK_FROM[firm]
            to_usd = state_net(cur)['S'] * cur['p']
            verdict = 'report only'
            if in_scope:
                ok, which = residual_test(res, obs, tol[w] / to_usd)
                verdict = {'<5%': 'PASS <5%', 'rounding': f'PASS within rounding ±${tol[w] / 1e6:,.1f}M',
                           'FAIL': f'FAIL (rounding ±${tol[w] / 1e6:,.1f}M)'}[which]
                scope.append((firm, w, ok, abs(res / obs), res * to_usd, obs * to_usd, tol[w]))
            print(f'{firm} {w} obs dn={obs:+.4e} explained={obs - res:+.4e} residual={res:+.4e} '
                  f'(${res * to_usd / 1e6:+,.1f}M) res/|dn|={abs(res / obs):.2%} {verdict}')
            for r in rows:
                out.append({'firm': firm, 'week_end': w, 'action': r['action'], 'ticker': r.get('ticker', ''),
                            'usd': fmt(r.get('usd'), '.0f'), 'm': fmt(r.get('m'), '.6f'), 'q': fmt(r.get('q'), '.6f'),
                            'dn_first_order': fmt(r.get('dn_first_order')), 'dn_exact': fmt(r['dn_exact']),
                            'dn_per_dollar': fmt(r.get('dn_per_dollar')), 'filing_url': r.get('filing_url', '')})
    write(path('attribution.csv'), FIELDS, out)
    print(f'attribution.csv {len(out)} rows')
    fails = [s for s in scope if not s[2]]
    print(f'residual test (MSTR from {CHECK_FROM["MSTR"]}; <5% or within R rounding): {len(scope) - len(fails)}/'
          f'{len(scope)} in-scope weeks pass (reported here; check.py enforces)' + ('' if fails else '; no failures'))
    for firm, w, _, rel, res_usd, obs_usd, t in fails:
        print(f'  FAIL: {firm} {w} residual {rel:.1%} of |dn| = ${res_usd / 1e6:+,.1f}M on observed '
              f'${obs_usd / 1e6:+,.1f}M (value to common), rounding ±${t / 1e6:,.1f}M')
    if bad_n:
        print(f'rebuilt n differs from weekly.csv: {bad_n}')
    if bad_id:
        print(f'identity FAILED (sum of rows != observed dn): {bad_id}')
    else:
        print('identity OK: every week, rows incl. residual sum to observed dn within 1e-12 relative')
    return 1 if bad_id or bad_n else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
