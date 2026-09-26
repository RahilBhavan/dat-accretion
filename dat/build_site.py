"""Step 5 (`python -m dat.build_site`): data/*.csv -> site/data.json for the static page. stdlib only.

Per firm-week: m, q, n, p, s, S, dollars moved, filing links, and each attribution row's value to common
(dn_exact × S × p at this week's S and p, method.md "Attribution") grouped into the page's bar categories.
Observed value to common is recomputed through the engine's states, so the bars can be checked against it.
"""
import datetime as dt, json, math, os, sys
from dat.balances import read
from dat.engine import states, state_net
from dat.parse_bmnr import excluded_holdings

CATEGORIES = ['issue_common', 'buyback_common', 'issue_pref', 'retire_pref', 'coins', 'carry', 'residual']
GROUP = {'est_issuance': 'issue_common', 'buy_coin': 'coins', 'sell_coin': 'coins'}  # attribution action -> bar
SEPARATE = ('price', 'itm_flip')  # not stacked: tooltip and table only
FIRMS = {'MSTR': {'name': 'Strategy', 'coin': 'BTC', 'unit': 'sats', 'pref': 'STRC', 'side': 'below'},
         'BMNR': {'name': 'BitMine', 'coin': 'ETH', 'unit': 'ETH', 'pref': 'BMNP', 'side': 'above'},
         'SBET': {'name': 'SharpLink', 'coin': 'ETH', 'unit': 'ETH', 'pref': None, 'side': None}}
LIQ_PREF = 100  # STRC stated amount and BMNP liquidation preference, USD (method.md)
BMNR_R_NOTE = ('BitMine R is its stated "total cash & marketable securities", so it includes marketable securities. '
               'BitMine\'s BTC holdings and equity stakes are excluded, as Strategy\'s definition counts only the coin '
               'reserve and USD assets.')
NOTES = [
    'BitMine S is estimated between filings. It is anchored to the 10-Q share counts for 2026-05-31 and 2026-07-09 '
    'and rolled by disclosed buybacks. Unreported issuance each week is estimated as the week\'s unexplained change '
    'in R divided by that week\'s BMNR close; the bars show it hatched as estimated issuance. ETH counted as bought '
    'includes staking, which raises the S estimate by about 0.43% by 2026-09-20; the next 10-K count resets it.',
    'BitMine releases give ETH bought in coins only. The USD of each BitMine ETH purchase is estimated as units × that '
    'week\'s ETH close. Coin trades are neutral on day one, so the estimate does not move the bars. The releases do '
    'not separate staking rewards from purchases.',
    'Strategy R is taken as stated in each 8-K. The roll-forward check on R runs from 2026-08-02; before that date R '
    'is unchecked and any unexplained change lands in the residual. Before 2026-08-23 R is the USD Reserve alone '
    '(USD Cash was established that week, funded by that week\'s MSTR sale proceeds). The 2026-06-30 quarter-end row carries R from the prior 8-K.',
    'Residuals are report-only for Strategy weeks before 2026-08-02 and for every BitMine week. The residual test '
    '(under 5% of the week\'s change, or within R rounding) applies to Strategy from 2026-08-02.',
    'STRE is in EUR; it converts at 1.147 USD per EUR, the rate implied by Strategy\'s API. The Friday 12:30 PM New '
    'York fixing Strategy uses is not published.',
    'Break-even prices use a $100 stated amount for STRC and a $100 liquidation preference for BMNP. After BitMine\'s '
    'first follow-on BMNP sale the BMNP preference floats to max($100, last sale price, 10-day average).',
    'Each firm\'s first week, 2026-05-31, is the anchor: it has no attribution, since the change in n needs a prior '
    'week. It is not in the bars.',
    'BitMine weeks before BMNP was issued (2026-05-31 and 2026-06-07) have no q, so they are not on the map.',
]


def sbet_notes(dates, last_filed):
    listed = ', '.join(dates[:-1]) + ' and ' + dates[-1]
    return [
        f'SharpLink states ETH holdings in its filings only on {listed}, and its last 8-K was filed {last_filed}. Its '
        'marks and bars are per filed date, not per week; nothing is carried forward between them. Its first filed '
        f'date, {dates[0]}, is its anchor.',
        'SharpLink has no preferred, so it has no q and no rotation line. Its marks sit at q = 1 on the map, where the '
        'line m = q is m = 1: the break-even for issuing or buying back common.',
        'SharpLink C is its stated Total ETH Holdings: native ETH plus LsETH and weETH at the stated as-if-redeemed ETH '
        'equivalence. The stated ETH change not explained by stated purchases is booked as carry, labeled inferred '
        'staking and LST accrual. BitMine has no such row, because its "acquired" figure already includes staking.',
        'SharpLink R is balance-sheet cash, stated only at quarter ends (2026-06-30 in this period). Other dates roll '
        'it by filed cash flows, so operating costs and staking revenue are not in it. SharpLink S uses the 10-Q counts '
        'for 2026-06-30 and 2026-08-03, rolled by filed issuance and buybacks. SharpLink residuals are report only.',
        'SharpLink\'s residuals come from shares added to S that no filing ties to an action: 49,265 performance '
        'RSUs on 2026-06-30, and on 2026-08-03 the July RSU and performance RSU grants and award shares.',
    ]


def fnum(x):
    return None if x in ('', None) else float(x)


def cents(x):
    return None if x is None else round(x, 2)


def excluded_sentence(x):
    names = [f"a ${usd / 1e6:,.0f} million stake in {name}" for name, usd in x['stakes']]
    items = ([f"{x['btc']:,} BTC"] if x['btc'] else []) + names
    listed = items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]
    return f"BitMine's {x['week_end']} release lists {listed}; these are excluded."


def release_text(url, online):
    """The release from edgar's cache; fetched from EDGAR only when online and not cached."""
    from dat import edgar
    if os.path.exists(edgar.cache_path(url)):
        return edgar.fetch(url)  # cache hit: no request
    return edgar.fetch(url) if online else None


def bmnr_r_note(url, online):
    """The BitMine R caveat, plus the excluded BTC and stakes from the latest release when its holdings sentence
    parses; otherwise the sentence is left out with a warning (never fails the build)."""
    try:
        html = release_text(url, online)
        x = excluded_holdings(html) if html else None
    except Exception as e:  # network or parse trouble must not block the page
        html, x = None, None
        print(f'warning: BitMine release {url}: {e}', file=sys.stderr)
    if not x:
        print(f'warning: excluded BitMine holdings not found in {url}; note omits them', file=sys.stderr)
        return {'text': BMNR_R_NOTE, 'url': None}
    return {'text': BMNR_R_NOTE + ' ' + excluded_sentence(x), 'url': url}


def sentence(h):
    f = FIRMS[h['firm']]
    if h['firm'] == 'SBET':
        return (f"At a net mNAV of {h['m']:.3f} (filed date {h['week_end']}), SharpLink has no preferred, so no rotation "
                "line applies: issuing common adds net ETH per share while m is above 1 and buying back common adds "
                "while m is below 1.")
    return (f"At a net mNAV of {h['m']:.3f} (week ending {h['week_end']}), {f['name']}'s {f['pref']} rotation adds "
            f"net {f['unit']} per share while {f['pref']} trades {f['side']} ${h['break_even']:.2f}.")


def close_sentence(h):
    if h['firm'] == 'SBET':
        return (f"SBET closed at ${h['s']:.2f} on {h['price_date']}. SharpLink's filings state ETH holdings only on "
                f"{', '.join(h['dates'])}.")
    return f"{h['pref']} closed at ${h['pref_close']:.2f} on {h['price_date']} (q = {h['q']:.4f})."


def load_check(path):
    """check.json, or {'status': 'not yet run'} when absent, empty or not a JSON object (warning on stderr)."""
    if not os.path.exists(path):
        return {'status': 'not yet run'}
    try:
        with open(path) as f:
            d = json.load(f)
        if isinstance(d, dict):
            return d
    except ValueError:
        pass
    print(f'warning: {path} is empty or invalid; check shown as not yet run', file=sys.stderr)
    return {'status': 'not yet run'}


def build(data_dir='data', online=False):
    path = lambda f: os.path.join(data_dir, f)
    all_w, all_a, all_act, all_bal, all_st = (read(path(f)) for f in
                                              ('weekly.csv', 'attribution.csv', 'actions.csv', 'balances.csv', 'stated.csv'))
    weeks, headline = [], []
    for firm in ('MSTR', 'BMNR', 'SBET'):
        pick = lambda rows: [r for r in rows if r['firm'] == firm]
        wk = sorted(pick(all_w), key=lambda r: r['week_end'])
        weekly = {r['week_end']: {**r, 'p': float(r['p']), 's': float(r['s'])} for r in wk}
        bal = sorted(pick(all_bal), key=lambda b: b['date'])
        st_rows = sorted(pick(all_st), key=lambda r: r['week_end'])
        sts = states(firm, bal, weekly, st_rows, pick(all_act))
        primary = {r['week_end']: r['filing_url'] for r in st_rows}
        prev = None
        for r in wk:
            w = r['week_end']
            cur = state_net(sts[w])
            S, p = cur['S'], float(r['p'])
            acts = [a for a in pick(all_act) if a['week_end'] == w and a['action'] != 'carry']
            attr = [a for a in pick(all_a) if a['week_end'] == w]
            urls = [primary[w]] + sorted({u['filing_url'] for u in acts + attr if u['filing_url']} - {primary[w]})
            row = {'firm': firm, 'week_end': w, 'price_date': r['price_date'], 'm': fnum(r['m']), 'q': fnum(r['q']),
                   'n': fnum(r['n']), 'p': p, 's': float(r['s']), 'S': round(S),
                   'dollars_moved': cents(math.fsum(abs(float(a['usd'])) for a in acts)), 'filing_urls': urls,
                   'value': None, 'est_issuance': None, 'price': None, 'itm_flip': None, 'actions_value': None,
                   'observed': None}
            if attr:  # the anchor week has none
                usd = lambda a: float(a['dn_exact']) * S * p
                val = {c: math.fsum(usd(a) for a in attr if GROUP.get(a['action'], a['action']) == c) for c in CATEGORIES}
                row.update(value={c: cents(v) for c, v in val.items()},
                           est_issuance=cents(math.fsum(usd(a) for a in attr if a['action'] == 'est_issuance')),
                           price=cents(math.fsum(usd(a) for a in attr if a['action'] == 'price')),
                           itm_flip=cents(math.fsum(usd(a) for a in attr if a['action'] == 'itm_flip')),
                           actions_value=cents(math.fsum(v for c, v in val.items() if c != 'residual')),
                           observed=cents((cur['n'] - prev['n']) * S * p))
            weeks.append(row)
            prev = cur
        last = wk[-1]
        if firm == 'SBET':
            h = {'firm': firm, 'name': FIRMS[firm]['name'], 'pref': None, 'week_end': last['week_end'],
                 'price_date': last['price_date'], 'm': float(last['m']), 'break_even': None, 'q': None,
                 'pref_close': None, 's': round(float(last['s']), 2), 'dates': [r['week_end'] for r in wk]}
            headline.append({**h, 'sentence': sentence(h), 'close_sentence': close_sentence(h)})
            continue
        m, q = float(last['m']), float(last['q'])
        h = {'firm': firm, 'name': FIRMS[firm]['name'], 'pref': FIRMS[firm]['pref'], 'week_end': last['week_end'],
             'price_date': last['price_date'], 'm': m, 'break_even': round(LIQ_PREF * m, 2), 'q': q,
             'pref_close': round(LIQ_PREF * q, 2)}
        headline.append({**h, 'sentence': sentence(h), 'close_sentence': close_sentence(h)})
    bmnr_url = max((r for r in all_st if r['firm'] == 'BMNR'), key=lambda r: r['week_end'])['filing_url']
    notes = [{'text': n, 'url': None} for n in NOTES]
    notes.insert(1, bmnr_r_note(bmnr_url, online))
    sbet = sorted(r['week_end'] for r in all_st if r['firm'] == 'SBET')
    last_8k = max(r['filed'] for r in all_st if r['firm'] == 'SBET')
    notes += [{'text': n, 'url': None} for n in sbet_notes(sbet, last_8k)]
    check = load_check(path('check.json'))
    return {'generated_at': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'categories': CATEGORIES, 'headline': headline, 'weeks': weeks, 'notes': notes, 'check': check}


def main(data_dir='data', out='site/data.json'):
    d = build(data_dir, online=True)
    with open(out, 'w') as f:
        json.dump(d, f, indent=1, sort_keys=True)
        f.write('\n')
    for h in d['headline']:
        print(h['sentence'])
        print(h['close_sentence'])
    print(f"{out}: {len(d['weeks'])} firm-weeks, check: {d['check'].get('status', 'present')}")
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
