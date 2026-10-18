"""Step 5 (`python -m dat.build_site`): data/*.csv -> site/data.json for the static page. stdlib only.

Per firm-week: m, q, n, p, s, S, dollars moved, filing links, and each attribution row's value to common
(dn_exact × S × p at this week's S and p, method.md "Attribution") grouped into the page's bar categories.
Observed value to common is recomputed through the engine's states, so the bars can be checked against it.
"""
import datetime as dt, json, math, os, sys
from dat.balances import read, bmnr_s_bias, bmnr_flows, BMNR_10Q, BMNR_A0, BMNR_A1, BMNR_RSU, BMNR_DILUTIVE
from dat.engine import states, state_net, CHECK_FROM
from dat.parse_bmnr import excluded_holdings
from dat.filings import page_name

CATEGORIES = ['issue_common', 'buyback_common', 'issue_pref', 'retire_pref', 'coins', 'carry', 'residual']
GROUP = {'est_issuance': 'issue_common', 'buy_coin': 'coins', 'sell_coin': 'coins'}  # attribution action -> bar
SEPARATE = ('price', 'itm_flip')  # not stacked: tooltip and table only
FIRMS = {'MSTR': {'name': 'Strategy', 'coin': 'BTC', 'unit': 'sats', 'pref': 'STRC', 'side': 'below'},
         'BMNR': {'name': 'BitMine', 'coin': 'ETH', 'unit': 'ETH', 'pref': 'BMNP', 'side': 'above'},
         'SBET': {'name': 'SharpLink', 'coin': 'ETH', 'unit': 'ETH', 'pref': None, 'side': None}}
ADDS = {'MSTR': lambda m, q: m > q, 'BMNR': lambda m, q: m < q}  # method.md: the rotation's adding side of m = q
LIQ_PREF = 100  # STRC stated amount and BMNP liquidation preference, USD (method.md)
BMNR_R_NOTE = ('BitMine R is its stated "total cash & marketable securities", so it includes marketable securities. '
               'BitMine\'s BTC holdings and equity stakes are excluded, as Strategy\'s definition counts only the coin '
               'reserve and USD assets.')
# The BitMine S bias, worded once for the page notes and the memo (dat.balances.bmnr_s_bias gives an upper bound).
S_BIAS = 'an upward bias of up to {bias} of S by {week}'


def s_bias_text(bias, week):
    return S_BIAS.format(bias=f'{bias:.2%}', week=week)


NOTES = [  # (group, text): estimate = an estimated figure; coverage = what is in or out; convention = a stated rule
    ('estimate', 'BitMine S is estimated between filings. It is anchored to the 10-Q share counts for 2026-05-31 and 2026-07-09 '
    'and rolled by disclosed buybacks. Unreported issuance each week is estimated as the week\'s unexplained change '
    'in R divided by that week\'s BMNR close; the bars show it hatched as estimated issuance. ETH counted as bought '
    'includes staking, which gives the S estimate {s_bias}; the next 10-K count resets it.'),
    ('estimate', 'BitMine releases give ETH bought in coins only. The USD of each BitMine ETH purchase is estimated as units × that '
    'week\'s ETH close. Coin trades are neutral on day one, so the estimate does not move the bars. The releases do '
    'not separate staking rewards from purchases.'),
    ('coverage', 'Strategy R is taken as stated in each 8-K. The roll-forward check on R runs from 2026-08-02; before that date R '
    'is unchecked and any unexplained change lands in the residual. Before 2026-08-23 R is the USD Reserve alone '
    '(USD Cash was established that week, funded by that week\'s MSTR sale proceeds). The 2026-06-30 quarter-end row carries R from the prior 8-K; the 2026-09-30 quarter-end row rolls R from the 9/27 8-K by filed cash flows.'),
    ('coverage', 'Residuals are report-only for Strategy weeks before 2026-08-02 and for every BitMine week. The residual test '
    '(under 5% of the week\'s change, or within R rounding) applies to Strategy from 2026-08-02.'),
    ('convention', 'STRE is in EUR; it converts at 1.147 USD per EUR, the rate implied by Strategy\'s API. The Friday 12:30 PM New '
    'York fixing Strategy uses is not published.'),
    ('convention', 'Break-even prices use a $100 stated amount for STRC and a $100 liquidation preference for BMNP. After BitMine\'s '
    'first follow-on BMNP sale the BMNP preference floats to max($100, last sale price, 10-day average).'),
    ('coverage', 'Each firm\'s first week, 2026-05-31, is the anchor: it has no attribution, since the change in n needs a prior '
    'week. It is not in the bars.'),
    ('coverage', 'BitMine weeks before BMNP was issued (2026-05-31 and 2026-06-07) have no q, so they are not on the map.'),
]


def sbet_notes(dates, last_filed):
    listed = ', '.join(dates[:-1]) + ' and ' + dates[-1]
    return [
        ('coverage', f'SharpLink states ETH holdings in its filings only on {listed}, and its last 8-K was filed {last_filed}. Its '
        'marks and bars are per filed date, not per week; nothing is carried forward between them. Its first filed '
        f'date, {dates[0]}, is its anchor.'),
        ('convention', 'SharpLink has no preferred, so it has no q and no rotation line. Its marks sit at q = 1 on the map, where the '
        'line m = q is m = 1: the break-even for issuing or buying back common.'),
        ('estimate', 'SharpLink C is its stated Total ETH Holdings: native ETH plus LsETH and weETH at the stated as-if-redeemed ETH '
        'equivalence. The stated ETH change not explained by stated purchases is booked as carry, labeled inferred '
        'staking and LST accrual. BitMine has no such row, because its "acquired" figure already includes staking.'),
        ('coverage', 'SharpLink R is balance-sheet cash, stated only at quarter ends (2026-06-30 in this period). Other dates roll '
        'it by filed cash flows, so operating costs and staking revenue are not in it. SharpLink S uses the 10-Q counts '
        'for 2026-06-30 and 2026-08-03, rolled by filed issuance and buybacks. SharpLink residuals are report only.'),
        ('coverage', 'SharpLink\'s residuals come from shares added to S that no filing ties to an action: 49,265 performance '
        'RSUs on 2026-06-30, and on 2026-08-03 the July RSU and performance RSU grants and award shares.'),
    ]


def counts(weekly):
    """{firm: (weeks on the adding side, weeks with m and q, first week, last week)} from weekly.csv rows.
    SBET (no preferred): (filed dates with m below 1, filed dates, first, last)."""
    out = {}
    for firm in ('MSTR', 'BMNR'):
        ws = sorted((r for r in weekly if r['firm'] == firm and r['m'] and r['q']), key=lambda r: r['week_end'])
        out[firm] = (sum(ADDS[firm](float(r['m']), float(r['q'])) for r in ws), len(ws), ws[0]['week_end'], ws[-1]['week_end'])
    ws = sorted((r for r in weekly if r['firm'] == 'SBET' and r['m']), key=lambda r: r['week_end'])
    out['SBET'] = (sum(float(r['m']) < 1 for r in ws), len(ws), ws[0]['week_end'], ws[-1]['week_end'])
    return out


def title(headline):
    """Page h1 and memo title: each rotation's break-even at the latest week, figures only (framing.md form)."""
    h = {x['firm']: x for x in headline}
    a, b = h['MSTR'], h['BMNR']
    when = (f"week ending {a['week_end']}" if a['week_end'] == b['week_end']
            else f"weeks ending {a['week_end']} and {b['week_end']}")
    return (f"At net mNAV {a['m']:.3f}, Strategy's STRC rotation adds net sats per share while STRC trades below "
            f"${a['break_even']:.2f}; at {b['m']:.3f}, BitMine's BMNP rotation adds net ETH per share while BMNP trades "
            f"above ${b['break_even']:.2f} ({when})")


def counts_sentence(c):
    """The weekly counts, stated the same way for both preferreds: weeks the close was below break-even ($100 × m)."""
    (a, n, _, _), (b, k, _, _), (x, y, _, _) = c['MSTR'], c['BMNR'], c['SBET']
    return (f"STRC closed below its break-even in {a} of {n} filed weeks, and BMNP closed below its break-even in "
            f"{k - b} of {k}. Strategy's rotation adds while STRC is below break-even; BitMine's adds while BMNP is above "
            f"it. SharpLink's m was below 1 on {x} of {y} filed dates.")


# The worked example on the page: Strategy's 7/26 STRC retirement (method.md test anchor 1, as filed: $25.0M).
EXAMPLE = ('MSTR', '2026-07-26', 'retire_pref', 'STRC')


def example(actions, attribution, balances):
    """One action, step by step, from the data rows. Raises if the row is missing, so the page never invents it."""
    firm, week, action, ticker = EXAMPLE
    key = lambda r: (r['firm'], r['week_end'], r['action'], r['ticker']) == EXAMPLE
    act = [r for r in actions if key(r)]
    att = [r for r in attribution if key(r)]
    bal = [r for r in balances if r['firm'] == firm and r['date'] == week]
    if len(act) != 1 or len(att) != 1 or len(bal) != 1:
        raise ValueError(f'worked example {EXAMPLE}: expected one actions, attribution and balances row')
    act, att, bal = act[0], att[0], bal[0]
    usd, notional = float(act['usd']), float(act['units'])
    dn = float(att['dn_exact'])
    return {'week_end': week, 'filing_url': act['filing_url'], 'usd': usd, 'notional': notional,
            'q': round(usd / notional, 4), 'avg_price': round(float(act['avg_price']), 2),
            'adds_usd': round(notional - usd), 'sats_per_share': round(dn * 1e8, 2), 'shares': int(float(bal['shares_diluted']))}


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
        return {'group': 'coverage', 'text': BMNR_R_NOTE, 'url': None}
    return {'group': 'coverage', 'text': BMNR_R_NOTE + ' ' + excluded_sentence(x), 'url': url}


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


# ---- BitMine gross ETH per 1,000 basic shares: weekly on the estimated count, the filed 10-Q counts as the check ----
BMNR_EDGAR = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1829311&type=8-K'


def bmnr_awards(close):
    """Awards and warrants in BitMine S at a BMNR close (dat.balances in-the-money rule): S minus these is basic."""
    return BMNR_RSU + sum(n for n, k in BMNR_DILUTIVE if close > k)


def eth_per_share(data_dir='data'):
    """BitMine's gross ETH held per 1,000 basic shares each stated week, on dat-accretion's estimated share count.
    Basic = balances.csv S minus awards in the money. Filed checks: the 5/31 10-Q balance sheet count (same date as
    the 5/31 holdings) and the 7/09 cover count, which falls between the 7/05 and 7/12 holdings (a range). Error: the
    7/09 count rebuilt from 5/31 by the unscaled issuance estimate, against the filed count (method.md "BitMine S")."""
    from dat.prices import load, close_on_or_before
    path = lambda f: os.path.join(data_dir, f)
    stated = sorted((r for r in read(path('stated.csv')) if r['firm'] == 'BMNR'), key=lambda r: r['week_end'])
    actions = [r for r in read(path('actions.csv')) if r['firm'] == 'BMNR']
    bal = {r['date']: r for r in read(path('balances.csv')) if r['firm'] == 'BMNR'}
    wk = {r['week_end']: r for r in read(path('weekly.csv')) if r['firm'] == 'BMNR'}
    weeks = [r['week_end'] for r in stated]
    a1_week = min(w for w in weeks if w >= BMNR_A1[0])
    rows = []
    for st in stated:
        w = st['week_end']
        b = bal[w]
        if int(b['coins']) != int(st['coins']):
            raise ValueError(f'BMNR {w}: balances.csv coins {b["coins"]} differ from stated {st["coins"]}')
        basic = int(b['shares_diluted']) - bmnr_awards(float(wk[w]['s']))
        rows.append({'week_end': w, 'eth': int(st['coins']), 'basic': basic, 'per_1000': round(1000 * int(st['coins']) / basic, 4),
                     'estimated': 'anchored' not in b['source'], 'filing_url': st['filing_url']})
    by = {r['week_end']: r for r in rows}
    # The 7/09 cover count sits between two stated weeks: the range spans ETH held on either side of it.
    before = max(w for w in weeks if w <= BMNR_A1[0])
    a0, lo, hi = by[BMNR_A0[0]], by[before], by[a1_week]
    filed = [{'date': BMNR_A0[0], 'shares': BMNR_A0[1], 'what': '10-Q balance sheet', 'share_url': BMNR_10Q,
              'eth_weeks': [a0['week_end']], 'eth_urls': [a0['filing_url']], 'per_1000': [round(1000 * a0['eth'] / BMNR_A0[1], 4)]},
             {'date': BMNR_A1[0], 'shares': BMNR_A1[1], 'what': '10-Q cover', 'share_url': BMNR_10Q,
              'eth_weeks': [before, a1_week], 'eth_urls': [lo['filing_url'], hi['filing_url']],
              'per_1000': [round(1000 * lo['eth'] / BMNR_A1[1], 4), round(1000 * hi['eth'] / BMNR_A1[1], 4)]}]
    # Out of sample: the same estimate, unscaled, from the 5/31 count to the week holding 7/09.
    flows, prices = bmnr_flows(stated, actions), load(path('prices.csv'))
    between = [w for w in weeks if BMNR_A0[0] < w <= a1_week]
    issued = math.fsum(max(float(flows[w][2]), 0) / close_on_or_before(prices, 'BMNR', w)[1] for w in between)
    bought = math.fsum(float(a['units']) for a in actions if a['action'] == 'buyback_common' and a['week_end'] in between)
    unscaled = BMNR_A0[1] + issued - bought
    err = unscaled - BMNR_A1[1]
    bias, bias_week = bmnr_s_bias(data_dir)
    check = {'from': BMNR_A0[0], 'to': BMNR_A1[0], 'estimate': round(unscaled), 'filed': BMNR_A1[1],
             'error': round(err), 'error_pct': round(100 * err / BMNR_A1[1], 3),
             'captured_pct': round(100 * (unscaled - BMNR_A0[1]) / (BMNR_A1[1] - BMNR_A0[1]), 1)}
    return {'weeks': rows, 'filed': filed, 'edgar_url': BMNR_EDGAR, 'check': check,
            'note': eth_note(check, s_bias_text(bias, bias_week)), 'bias_pct': round(100 * bias, 2), 'bias_week': bias_week}


def eth_note(c, s_bias):
    """The panel's printed caveat: how the share count is estimated, its error against a filed count, its bias."""
    side = 'under' if c['error'] < 0 else 'over'
    return (f"BitMine's weekly releases state ETH held but no share count, so the dashed line divides by an estimated "
            f"basic share count: the 10-Q count for {c['from']}, plus the week's unexplained change in cash divided by "
            f"the BMNR close, minus disclosed buybacks. Up to {c['to']} the estimate is scaled to land on the 10-Q cover "
            f"count, so the line meets the filed figures there by construction. Check: unscaled, the estimate gives "
            f"{c['estimate']:,} shares for {c['to']} against {c['filed']:,} filed, {abs(c['error']):,} "
            f"({abs(c['error_pct']):.2f}%) {side}. No share count has been filed since {c['to']}; the next 10-K cover "
            f"count is the next check. ETH counted as bought includes staking, which gives the estimate {s_bias}, so "
            f"the line after {c['to']} reads low by up to about as much. Gross: ETH held only; the page's net coins per "
            f"share (n) also counts cash and BMNP.")



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


def filing_pages(urls, site_dir='site'):
    """{SEC URL: relative path of its restyled copy}, for the copies dat.filings has written (the rest link to sec.gov)."""
    return {u: 'filings/' + page_name(u) for u in sorted(urls)
            if u and os.path.exists(os.path.join(site_dir, 'filings', page_name(u)))}


def build(data_dir='data', online=False, site_dir='site'):
    path = lambda f: os.path.join(data_dir, f)
    all_w, all_a, all_act, all_bal, all_st = (read(path(f)) for f in
                                              ('weekly.csv', 'attribution.csv', 'actions.csv', 'balances.csv', 'stated.csv'))
    weeks, headline = [], []
    now = dt.datetime.now(dt.timezone.utc)
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
        h['gap'] = round(h['pref_close'] - h['break_even'], 2)  # negative: preferred below break-even
        headline.append({**h, 'sentence': sentence(h), 'close_sentence': close_sentence(h)})
    bmnr_url = max((r for r in all_st if r['firm'] == 'BMNR'), key=lambda r: r['week_end'])['filing_url']
    bias, bias_week = bmnr_s_bias(data_dir)
    notes = [{'group': g, 'text': n.replace('{s_bias}', s_bias_text(bias, bias_week)), 'url': None}
             for g, n in NOTES]
    notes.insert(1, bmnr_r_note(bmnr_url, online))
    sbet = sorted(r['week_end'] for r in all_st if r['firm'] == 'SBET')
    last_8k = max(r['filed'] for r in all_st if r['firm'] == 'SBET')
    notes += [{'group': g, 'text': n, 'url': None} for g, n in sbet_notes(sbet, last_8k)]
    totals = {}
    for firm in FIRMS:  # actions = filed actions only: carry and estimated issuance are listed apart (method.md)
        ws = [w for w in weeks if w['firm'] == firm]
        att = [w for w in ws if w['value'] is not None]
        x = {k: math.fsum(f(w) for w in att) for k, f in (
            ('carry', lambda w: w['value']['carry']), ('est_issuance', lambda w: w['est_issuance']),
            ('residual', lambda w: w['value']['residual']), ('observed', lambda w: w['observed']),
            ('price', lambda w: w['price']), ('itm_flip', lambda w: w['itm_flip']))}
        x['actions'] = math.fsum(w['actions_value'] for w in att) - x['carry'] - x['est_issuance']
        # Residual split at the first R-checked week (method.md): before it, unexplained R changes land in the residual.
        start = CHECK_FROM.get(firm)
        x['residual_checked'] = math.fsum(w['value']['residual'] for w in att if start and w['week_end'] >= start)
        totals[firm] = {**{k: cents(v) for k, v in x.items()}, 'since': ws[0]['week_end'], 'checked_from': start}
    check = load_check(path('check.json'))
    return {'generated_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'title': title(headline),
            'counts': counts_sentence(counts(all_w)), 'example': example(all_act, all_a, all_bal),
            'categories': CATEGORIES, 'headline': headline, 'weeks': weeks, 'totals': totals, 'notes': notes, 'check': check,
            'pages': filing_pages({u for w in weeks for u in w['filing_urls']} | {r['filing_url'] for r in all_act}, site_dir),
            'eth_per_share': eth_per_share(data_dir)}


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
