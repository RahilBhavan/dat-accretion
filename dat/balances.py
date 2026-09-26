"""Strategy's net definition: net coins N, per share n, mNAV, amplification. stdlib only.

Source: glossary in the 2026-08-24 FWP,
https://www.sec.gov/Archives/edgar/data/1050446/000119312526363557/d431748dfwp.htm
In-the-money (s > conversion price) converts and prefs leave D/F and add their shares to S.
Other debt (the secured term loan) is not deducted.

Step 2 (`python -m dat.balances`): per stated 8-K week, C and R as stated, D/F/S from Q2 10-Q anchors
rolled by actions.csv -> data/balances.csv and data/weekly.csv; prints the R check (method.md).
"""
import csv, os, sys
from decimal import Decimal


def net(coins, usd_assets, converts, prefs, basic_shares, awards, p, s):
    """converts: list of (face_usd, conv_price). prefs: list of (notional_usd, conv_price_or_None, shares_if_converted_or_0).
    Returns dict: D, F, S, N (net coins), n (net coins per share), net_sats_per_share (n*1e8),
    net_reserve_usd (N*p), amplification (coins*p / (N*p)), mnav (s / (N*p/S))."""
    D, F, S = 0.0, 0.0, basic_shares + awards
    for face, cp in converts:
        if s > cp:
            S += face / cp
        else:
            D += face
    for notional, cp, shares in prefs:
        if cp is not None and s > cp:
            S += shares
        else:
            F += notional
    N = coins + (usd_assets - D - F) / p
    n = N / S
    return {'D': D, 'F': F, 'S': S, 'N': N, 'n': n, 'net_sats_per_share': n * 1e8,
            'net_reserve_usd': N * p, 'amplification': coins / N, 'mnav': s / (N * p / S)}


# ---- Step 2: weekly state for Strategy (MSTR) -> data/balances.csv, data/weekly.csv ----
Q2_10Q = 'https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm'
# converts (face, conv price), Q2 10-Q above
CONVERTS = [
    (1_010.0e6, 183.19),  # 2028
    (1_500.0e6, 672.40),  # 2029
    (800.0e6, 149.77),  # 2030A
    (2_000.0e6, 433.43),  # 2030B
    (603.659e6, 232.72),  # 2031
    (800.0e6, 204.33),  # 2032
]
EURUSD = 1.147  # STRE: API-implied rate; Friday 12:30 NY fixing unpublished
PREF_ANCHOR_DATE = '2026-06-30'  # Q2 10-Q notional per preferred, USD
PREF_ANCHOR = {'STRF': 1_283_969_000, 'STRC': 104_894_705 * 100, 'STRK': 1_402_074_000,
               'STRD': 1_402_422_000, 'STRE': 775_000_000 * EURUSD}
STRK_CONV = 1000.0  # STRK: $100 liquidation preference converts to 0.1 MSTR share
# Class A as of 2026-07-24 (10-Q cover); the 7/20-7/26 week's ATM sales are taken as included.
CLASS_A, CLASS_A_WEEK = 364_585_501, '2026-07-26'
CLASS_B = 19_640_250  # 10-Q 6/30, constant
AWARDS = 3_950_554  # options + RSU + PSU, 10-Q 6/30, constant
CHECK_FROM = '2026-08-02'
STRC_CHECK = ('2026-09-20', 9_316_191_300)  # 93,161,913 sh x $100 (Step 0)
BAL_FIELDS = ['firm', 'date', 'coins', 'usd_reserve', 'debt', 'pref_notional', 'shares_diluted', 'source']
WEEK_FIELDS = ['firm', 'week_end', 'price_date', 'p', 's', 'q', 'm', 'n']
SIGN = {'issue_common': 1, 'issue_pref': 1, 'sell_coin': 1, 'buy_coin': -1, 'retire_pref': -1,
        'buyback_common': -1, 'carry': 1}


def rolled(anchor, anchor_week, deltas, week):
    """Level at week from anchor at anchor_week; deltas [(week_end, change)]. Changes dated after the
    anchor and on or before week are added; changes after week up to the anchor are backed out."""
    return (anchor + sum(v for w, v in deltas if anchor_week < w <= week)
            - sum(v for w, v in deltas if week < w <= anchor_week))


def pref_notional(actions, week):
    """{ticker: notional USD at week}, anchored at the 6/30 10-Q, rolled by issue_pref/retire_pref units."""
    return {t: rolled(a, PREF_ANCHOR_DATE, [(r['week_end'], SIGN[r['action']] * float(r['units'])) for r in actions
                                           if r['ticker'] == t and r['action'] in ('issue_pref', 'retire_pref')], week)
            for t, a in PREF_ANCHOR.items()}


def class_a(actions, week):
    return rolled(CLASS_A, CLASS_A_WEEK, [(r['week_end'], SIGN[r['action']] * float(r['units'])) for r in actions
                                          if r['action'] in ('issue_common', 'buyback_common')], week)


def dec(x):
    return Decimal(x) if x else Decimal(0)


def reserve_checks(stated, actions, check_from=CHECK_FROM):
    """-> [(week, kind, dR, flow, tol, ok)] per stated week after the first with a stated USD Reserve.
    kind 'R': reserve+cash change vs actions.csv cash flows (both weeks disclose USD Cash).
    kind 'reserve': USD Reserve change vs itemized reserve_in - reserve_out (either week lacks USD Cash).
    Before check_from, kind is 'none', flow is the actions.csv cash flow, tol and ok are None.
    tol = half the last-digit unit of each stated figure compared, summed."""
    rows = sorted((s for s in stated if s['usd_reserve']), key=lambda s: s['week_end'])
    out = []
    for prev, cur in zip(rows, rows[1:]):
        week = cur['week_end']
        acts = sum(SIGN[a['action']] * dec(a['usd']) for a in actions if prev['week_end'] < a['week_end'] <= week)
        if prev['usd_cash'] and cur['usd_cash']:
            kind, flow, figs = 'R', acts, ('usd_reserve', 'usd_cash')
        else:
            kind, flow, figs = 'reserve', dec(cur['reserve_in']) - dec(cur['reserve_out']), ('usd_reserve',)
        d = sum(dec(cur[f]) - dec(prev[f]) for f in figs)
        tol = sum(dec(r[f + '_prec']) for r in (prev, cur) for f in figs) / 2
        if week < check_from:
            out.append((week, 'none', dec(cur['usd_reserve']) + dec(cur['usd_cash'])
                        - dec(prev['usd_reserve']) - dec(prev['usd_cash']), acts, None, None))
        else:
            out.append((week, kind, d, flow, tol, abs(d - flow) <= tol))
    return out


def accession(url):
    return url.rstrip('/').split('/')[-2]


def build(stated, actions, prices):
    """-> (balances rows, weekly rows, notes) for every stated week."""
    from dat.prices import close_on_or_before
    bal, weekly, notes, last_r = [], [], [], None
    for st in sorted(stated, key=lambda s: s['week_end']):
        week = st['week_end']
        src = f"8-K {accession(st['filing_url'])}; 10-Q 6/30 roll"
        if st['usd_reserve']:
            R = float(st['usd_reserve']) + float(st['usd_cash'] or 0)
            last_r = (R, accession(st['filing_url']))
            if not st['usd_cash']:
                src += '; R = USD Reserve only (USD Cash not disclosed)'
        else:
            R = last_r[0]
            src += f'; R not stated, carried from 8-K {last_r[1]}'
        price_date, s = close_on_or_before(prices, 'MSTR', week)
        closes = {}
        for t in ('STRC', 'BTC'):
            d, closes[t] = close_on_or_before(prices, t, price_date)
            if d != price_date:
                raise LookupError(f'{t}: no close on {price_date} (MSTR price date for week {week})')
        pn = pref_notional(actions, week)
        prefs = [(v, STRK_CONV, v / STRK_CONV) if t == 'STRK' else (v, None, 0) for t, v in pn.items()]
        x = net(float(st['coins']), R, CONVERTS, prefs, class_a(actions, week) + CLASS_B, AWARDS, closes['BTC'], s)
        bal.append({'firm': 'MSTR', 'date': week, 'coins': st['coins'], 'usd_reserve': round(R), 'debt': round(x['D']),
                    'pref_notional': round(x['F']), 'shares_diluted': round(x['S']), 'source': src})
        weekly.append({'firm': 'MSTR', 'week_end': week, 'price_date': price_date, 'p': closes['BTC'], 's': s,
                       'q': closes['STRC'] / 100, 'm': f"{x['mnav']:.6f}", 'n': f"{x['n']:.10g}"})
        notes.append((week, pn['STRC']))
    return bal, weekly, notes


# ---- Step 3: weekly state for BitMine (BMNR), method.md "BitMine mapping" and "BitMine S" ----
BMNR_10Q = 'https://www.sec.gov/Archives/edgar/data/1829311/000162828026048157/bmnr-20260531.htm'
BMNR_A0 = ('2026-05-31', 579_652_432)  # common outstanding, 10-Q balance sheet
BMNR_A1 = ('2026-07-09', 603_226_394)  # common outstanding, 10-Q cover
BMNR_RSU = 1_097_346  # unvested time-based RSUs at 5/31 (10-Q); no strike, always in S
# (shares, strike) from the 10-Q; in S only while the BMNR close is above the strike.
BMNR_DILUTIVE = [(359_124, 21.10),  # options: weighted-average exercise price (per-grant strikes not disclosed)
                 (2_820_774, 5.40),  # strategic advisor warrants
                 (50_875, 0.0),  # representative warrants: strike not disclosed; 10-Q counts them in the money
                 (10_435_430, 87.50)]  # CVI warrants, expire 2027-03-22
# Excluded: 4,500,000 performance RSUs (conditions unmet at 5/31); 1,280 C-3 warrants (strike not disclosed,
# out of the money per the 10-Q). D = 0: the 10-Q states no debt at 5/31.


def bmnr_flows(stated, actions):
    """{week: (dR, disclosed cash flows, unexplained)} for each stated week after the first.
    Flows: BMNP net proceeds, estimated ETH cost, buybacks, dividends (actions.csv usd, signed)."""
    rows = sorted(stated, key=lambda s: s['week_end'])
    out = {}
    for prev, cur in zip(rows, rows[1:]):
        w = cur['week_end']
        flow = sum(SIGN[a['action']] * dec(a['usd']) for a in actions if prev['week_end'] < a['week_end'] <= w)
        d = dec(cur['usd_reserve']) - dec(prev['usd_reserve'])
        out[w] = (d, flow, d - flow)
    return out


def bmnr_basic(weeks, flows, closes, actions):
    """{week: (basic shares, estimated shares added that week, label)}. Estimate = max(unexplained dR, 0) / BMNR close.
    Weeks up to the one holding the 7/09 anchor: estimates scaled so A0 + issuance - buybacks = A1 there.
    Later weeks: A1 + unscaled estimates - buybacks."""
    bb = {}
    for a in actions:
        if a['action'] == 'buyback_common':
            bb[a['week_end']] = bb.get(a['week_end'], 0) + float(a['units'])
    est = {w: max(float(flows[w][2]), 0) / closes[w] if w in flows else 0.0 for w in weeks}
    a1_week = min(w for w in weeks if w >= BMNR_A1[0])
    between = [w for w in weeks if BMNR_A0[0] < w <= a1_week]
    if bb.get(a1_week):
        raise ValueError(f'buyback in week {a1_week}, which holds the {BMNR_A1[0]} anchor: cannot tell if it is before or '
                         'after the cover count; split the week by trade date before rolling')
    scale = (BMNR_A1[1] - BMNR_A0[1] + sum(bb.get(w, 0) for w in between)) / sum(est[w] for w in between)
    out, level = {}, float(BMNR_A0[1])
    for w in weeks:
        if w <= BMNR_A0[0]:
            out[w] = (float(BMNR_A0[1]), 0.0, 'S anchored 10-Q 5/31 balance sheet')
            continue
        add = est[w] * (scale if w <= a1_week else 1)
        level += add - bb.get(w, 0)
        if w == a1_week:
            level = float(BMNR_A1[1]) - sum(bb.get(x, 0) for x in weeks if BMNR_A1[0] < x <= w)
            label = f'S anchored 10-Q cover {BMNR_A1[0]} (week holding it)'
        elif w < a1_week:
            label = f'S estimated: 5/31 anchor + unexplained dR / BMNR close x {scale:.4f} (scaled to 7/09 anchor)'
        else:
            label = 'S estimated: 7/09 anchor + unexplained dR / BMNR close (unscaled) - buybacks'
        out[w] = (level, add, label)
    return out, scale, between


def bmnr_s_bias(data_dir='data', asof=None):
    """(bias, week): upward bias in BitMine S at week `asof` (default: its last balances.csv week), as a share of S (method.md "BitMine S").
    Staked ETH (data/staking.csv, parse_bmnr's estimate) is costed as a cash purchase, so each week after the one
    holding the 7/09 anchor adds eth_est x ETH close / BMNR close shares via unexplained dR. Upper bound: weeks
    whose unexplained dR is floored at 0 add fewer."""
    from dat.prices import load, close_on_or_before
    prices = load(os.path.join(data_dir, 'prices.csv'))
    stake = {r['week_end']: float(r['eth_est']) for r in read(os.path.join(data_dir, 'staking.csv'))}
    bal = sorted((r for r in read(os.path.join(data_dir, 'balances.csv')) if r['firm'] == 'BMNR'
                  and (asof is None or r['date'] <= asof)), key=lambda r: r['date'])
    weeks = [r['date'] for r in bal]
    a1_week = min(w for w in weeks if w >= BMNR_A1[0])
    shares = 0.0
    for w in weeks:
        if w <= a1_week:
            continue
        if w not in stake:
            raise LookupError(f'BMNR {w}: no staking estimate in staking.csv (release gives no staked ETH or yield); '
                              'the S bias cannot be computed')
        d, s = close_on_or_before(prices, 'BMNR', w)
        e = close_on_or_before(prices, 'ETH', d)
        if e[0] != d:
            raise LookupError(f'ETH: no close on {d} (BMNR price date for week {w})')
        shares += stake[w] * e[1] / s
    return shares / float(bal[-1]['shares_diluted']), weeks[-1]


def build_bmnr(stated, actions, prices):
    """-> (balances rows, weekly rows, per-week print lines) for BMNR."""
    from dat.prices import close_on_or_before
    stated = sorted(stated, key=lambda s: s['week_end'])
    weeks = [s['week_end'] for s in stated]
    pdate, closes = {}, {}
    for w in weeks:
        pdate[w], closes[w] = close_on_or_before(prices, 'BMNR', w)

    def close(t, w):
        d, c = close_on_or_before(prices, t, pdate[w])
        if d != pdate[w]:
            raise LookupError(f'{t}: no close on {pdate[w]} (BMNR price date for week {w})')
        return c

    issue = min(a['week_end'] for a in actions if a['action'] == 'issue_pref' and a['ticker'] == 'BMNP')
    flows = bmnr_flows(stated, actions)
    basic, scale, between = bmnr_basic(weeks, flows, closes, actions)
    bal, weekly, lines = [], [], []
    for st in stated:
        w, s = st['week_end'], closes[st['week_end']]
        F = sum(SIGN[a['action']] * float(a['units']) for a in actions
                if a['ticker'] == 'BMNP' and a['action'] in ('issue_pref', 'retire_pref') and a['week_end'] <= w)
        awards = BMNR_RSU + sum(n for n, k in BMNR_DILUTIVE if s > k)
        b, add, label = basic[w]
        p = close('ETH', w)
        x = net(float(st['coins']), float(st['usd_reserve']), [], [(F, None, 0)], b, awards, p, s)
        if w < issue:
            q, qlab = '', 'q blank (BMNP not issued)'
        elif w == issue:
            q, qlab = 0.80, 'q = 0.80 issue price / $100 (BMNP not yet trading)'
        else:
            q, qlab = close('BMNP', w) / 100, 'q = BMNP close / 100'
        bal.append({'firm': 'BMNR', 'date': w, 'coins': st['coins'], 'usd_reserve': round(float(st['usd_reserve'])),
                    'debt': 0, 'pref_notional': round(F), 'shares_diluted': round(x['S']),
                    'source': f"release {accession(st['filing_url'])}; R = cash & marketable securities (incl. securities); "
                              f"D = 0 (10-Q 5/31: no debt); {label}; awards/warrants in S at close {s:.2f}: "
                              f"{awards:,.0f}; {qlab}"})
        weekly.append({'firm': 'BMNR', 'week_end': w, 'price_date': pdate[w], 'p': p, 's': s, 'q': q,
                       'm': f"{x['mnav']:.6f}", 'n': f"{x['n']:.10g}"})
        un = f"unexplained dR={float(flows[w][2]) / 1e6:+,.1f}M" if w in flows else 'first week'
        lines.append(f"{w} {'anchored' if 'anchored' in label else 'estimated'} basic={b:,.0f} est_added={add:,.0f} "
                     f"({un}) S={x['S']:,.0f} m={x['mnav']:.4f} q={q if q == '' else f'{q:.4f}'}")
    lines.append(f'BMNR: issuance estimates {between[0][5:]}..{between[-1][5:]} scaled x{scale:.4f} to land on the 7/09 10-Q cover count')
    return bal, weekly, lines


def read(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def write(path, fields, rows):
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def m_usd(x):
    return f'{float(x) / 1e6:+,.1f}M'


def main(data_dir='data'):
    from dat.prices import load
    all_stated, all_actions = read(os.path.join(data_dir, 'stated.csv')), read(os.path.join(data_dir, 'actions.csv'))
    firm = lambda rows, f: [r for r in rows if r['firm'] == f]
    stated, actions = firm(all_stated, 'MSTR'), firm(all_actions, 'MSTR')
    prices = load(os.path.join(data_dir, 'prices.csv'))
    bal, weekly, notes = build(stated, actions, prices)
    b_bal, b_weekly, b_lines = build_bmnr(firm(all_stated, 'BMNR'), firm(all_actions, 'BMNR'), prices)
    write(os.path.join(data_dir, 'balances.csv'), BAL_FIELDS, b_bal + bal)  # firms sorted, as in actions.csv
    write(os.path.join(data_dir, 'weekly.csv'), WEEK_FIELDS, b_weekly + weekly)
    print(f'balances.csv {len(bal)} MSTR + {len(b_bal)} BMNR rows, weekly.csv {len(weekly)} MSTR + {len(b_weekly)} BMNR rows')
    print('\n'.join(b_lines))
    print('BMNR: R not rolled; releases don\'t itemize flows')
    checks, bad = {c[0]: c[1:] for c in reserve_checks(stated, actions)}, []
    for st in sorted(stated, key=lambda s: s['week_end']):
        week = st['week_end']
        if week not in checks:
            print(f'{week} no R check: ' + ('first stated USD Reserve' if st['usd_reserve'] else 'USD Reserve not stated'))
            continue
        kind, d, flow, tol, ok = checks[week]
        if kind == 'none':
            print(f'{week} unexplained dR = ${float(d) / 1e6:,.1f}M (no itemized flows; unchecked); '
                  f'dR - actions.csv flows = {m_usd(d - flow)}')
            continue
        label = 'R (reserve+cash) vs actions.csv flows' if kind == 'R' else 'USD Reserve vs itemized reserve_in - reserve_out'
        print(f'{week} {label}: d={m_usd(d)} flows={m_usd(flow)} diff={m_usd(d - flow)} tol=±{float(tol) / 1e6:,.1f}M '
              f'{"OK" if ok else "FAIL"}')
        if not ok:
            bad.append(week)
    missing = [w['week_end'] for w in weekly if not (w['m'] and w['q'])]
    missing += [w['week_end'] for w in b_weekly if not w['m']]
    print(f'm and q (STRC) present for {len(weekly) - len(missing)}/{len(weekly)} weeks' + (f'; missing {missing}' if missing else ''))
    strc = dict(notes)[STRC_CHECK[0]]
    strc_ok = round(strc) == STRC_CHECK[1]
    print(f'STRC notional {STRC_CHECK[0]} = {strc:,.0f} (expect {STRC_CHECK[1]:,}) {"OK" if strc_ok else "FAIL"}')
    if bad:
        print(f'reserve check FAILED: {bad}')
    return 1 if bad or missing or not strc_ok else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
