"""SharpLink (CIK 1981535) 8-Ks and EX-99 releases -> SBET rows in data/actions.csv and data/stated.csv. stdlib only.

SharpLink states ETH holdings only on some dates (method.md "SharpLink mapping"), so its rows are per filed
holdings date, not per week. Prose is read by phrase, as in parse_bmnr: a $ amount or share/coin count in a
sentence about holdings, repurchases, offerings or purchases must be consumed by a known phrase, else it raises.
Holdings totals must equal their stated native + LsETH + weETH parts. Issue and buyback USD come from the
10-Q equity statement when it covers them. The stated ETH change not explained by stated purchases is a `carry`
row (inferred staking/LST accrual), unlike BitMine, whose "acquired" already includes staking.
"""
import csv, os, re, sys, datetime as dt
from decimal import Decimal
from dat.parse_mstr import blocks, iso, fmt, num as cell, ACTION_FIELDS, STATED_FIELDS, DATE
from dat.parse_bmnr import paragraphs, sentences, one, num, merge_write, NUMBER

CIK = 1981535
START = '2026-06-01'
AP = "[’']"
N = r'([\d,]+)'

# Holdings, each -> {date: coins}; parts -> {date: (native, LsETH, weETH)}.
PARTS = (rf'Total ETH holdings held as of ({DATE}),? (?:were )?comprised of {N} native ETH, {N} ETH as-if redeemed from '
         rf'LsETH and {N} ETH as-if redeemed from (?i:weETH)')
AGG = (rf'As of ({DATE}), the Company{AP}s aggregate ETH Holdings were {N} of which {N} of the total ETH Holdings are '
       rf'native ETH, {N} ETH as-if redeemed from LsETH and {N} ETH as-if redeemed from weETH')
TOTALED = rf'ETH holdings totaled approximately {N} ETH\d? as of ({DATE})(?:, (?:increasing to|and) {N} ETH\d? as of ({DATE}))?'
NAV = rf'ETH holdings\d? reported as of ({DATE}) of {N} ETH'
BRINGING = rf'(?:bringing total ETH holdings\d? to|Total ETH holdings\d? increased to) {N}'  # undated; must equal a dated total in the same document
# Flows.
BUY = (rf'During the period from ({DATE}) through ({DATE}), the Company acquired {N} ETH for an aggregate purchase price '
       rf'of approximately \$[\d.]+ million \(inclusive of fees and expenses\) at a weighted average purchase price per '
       rf'ETH of \$([\d,]+\.\d+)')
REPO = (rf'During the period from ({DATE}) through ({DATE}), the Company repurchased {N} shares of Common Stock at an '
        rf'average purchase price of \$(\d+\.\d+) per share')
DIRECT = rf'to sell in a registered direct offering \(the “Offering”\) an aggregate of {N} shares'
DIRECT_PRICE = r'The price per Share was \$(\d+\.\d+)'
DIRECT_CLOSED = rf'The Offering closed on ({DATE})'
# Same-filing summaries of a detailed flow: units captured and matched to a detailed row of the filing.
BUY_SUM = [rf'announced the purchase of {N} ETH at an average price of \$[\d,]+ per ETH',
           rf'Bought {N} ETH at an average price of approximately \$[\d,]+ per ETH']
REPO_SUM = [rf'repurchase of {N} shares of its common stock in the open market at an average purchase price of \$[\d.]+ per share',
            rf'Repurchased {N} shares of common stock, bringing total to [\d,]+ shares repurchased since']
DIRECT_SUM = [rf'purchase and sale of {N} shares of its common stock\b.*?at a combined purchase price of \$[\d.]+ per Share and Warrant']
# Numbers that are not flows of the period: program sizes, terms, cumulative totals, quarter recaps of the flows above.
KNOWN = [PARTS, AGG, TOTALED, NAV, BRINGING, BUY, REPO, DIRECT, DIRECT_PRICE, *BUY_SUM, *REPO_SUM, *DIRECT_SUM,
         r'repurchase of up to \$[\d.]+ billion of the Company’s outstanding shares',
         r'gross proceeds from the Offering, before deducting the placement agent fees and offering expenses, were approximately \$\d+ million',
         r'aggregate gross proceeds from the registered direct offering \(the “Offering”\) are expected to be approximately \$\d+ million',
         r'Pricing of \$\d+ Million Registered Direct Offering',
         r'granted the Investor [\d,]+ warrants to purchase up to [\d,]+ shares of Common Stock',
         r'accompanying warrants to purchase up to [\d,]+ shares of common stock',
         r'exercise price of \$[\d.]+ per (?:share|Share)', r'receive approximately \$[\d.]+ million in additional aggregate gross proceeds',
         r'closing share price of \$[\d.]+ on', r'reported as of June 16, 2026 of [\d,]+ ETH',
         r'Raised \$\d+ million via a registered direct offering of common stock and warrants',
         r'completion of our \$\d+ million registered direct offering',
         r'Acquires [\d,]+ ETH, Bringing Total ETH Holdings to [\d,]+; Repurchases Over [\d.]+ Million Shares',
         r'completed a \$[\d.]+ million registered direct offering, issuing [\d,]+ shares of common stock and '
         r'accompanying warrants at a combined purchase price of \$[\d.]+ per share and warrant',
         r'par value \$0\.0001 per share',
         r'acquire approximately [\d,]+ ETH at an average purchase price of approximately \$[\d,]+ per ETH',
         r'repurchased approximately [\d.]+ million shares of its common stock at an average price of approximately '
         r'\$[\d.]+ per share, for an aggregate purchase price of approximately \$[\d.]+ million',
         r'has repurchased [\d,]+ shares of its common stock at an aggregate cost of approximately \$[\d.]+ million',
         r'Crypto assets totaled approximately \$[\d.]+ billion',
         r'\$[\d.]+ million in committed capital, including \$[\d.]+ million from Sharplink and \$[\d.]+ million from Galaxy',
         r'purchases were made using the proceeds']
NEAR = (r'repurchas|buyback|\boffering\b|\bacquired?\b|at-the-market|registered direct|\bsold\b|\bATM\b|\bbought\b|purchas|'
        r'\bissu|redeem|\braised\b|\bproceeds\b|ETH holdings|ETH Holdings|Total ETH')
CASH_ROW = 'Cash'  # balance sheet row label (in thousands)


def check_near(paras, where):
    for para in paras:
        if re.search(r'forward-looking statements', para, re.I):
            continue
        for s in sentences(para):
            if not re.search(NEAR, s, re.I):
                continue
            known = [m.span() for rx in KNOWN for m in re.finditer(rx, s)]
            for m in re.finditer(NUMBER, s):
                if not any(a <= m.start() < b for a, b in known):
                    raise ValueError(f'{where}: unknown number {m.group(0)!r} near holdings/repurchase/offering/purchase: {s!r}')


def cash_table(bs, where):
    """{date: Decimal USD} from a balance sheet table whose 'Cash' row follows a date header, in thousands."""
    out, thousands = {}, False
    for k, v in bs:
        if k == 'p':
            thousands = thousands or '(In thousands' in v
            continue
        dates = None
        for r in v:
            if r and all(re.fullmatch(DATE, c) for c in r):
                dates = [iso(c) for c in r]
            elif r and r[0] == CASH_ROW and dates:
                if not thousands:
                    raise ValueError(f'{where}: balance sheet Cash row without an "(In thousands" heading')
                vals = r[1:1 + len(dates)]
                out[dates[0]] = num(vals[0].replace(',', '')) * 1000
    return out


# Holdings dates that contradict the filing sequence, corrected with the evidence cited (parse_bmnr pattern).
# None found in SharpLink's filings as of 2026-09-26.
KNOWN_DATE_ERRATA = {}


def parse(html, filing, url):
    """One document -> dict(holdings {date: coins}, parts {date: (native, ls, we)}, cash {date: usd},
    buys [(start, end, units, avg)], repos [(start, end, shares, avg)], direct [(closed, shares, price)])."""
    where = f"{filing['accession']} ({url})"
    bs = blocks(html)
    paras = paragraphs(bs)
    check_near(paras, where)
    text = ' '.join(paras)
    hold, parts = {}, {}

    def put(d, coins):
        d = iso(d)
        if filing['accession'] in KNOWN_DATE_ERRATA:
            stated, fixed, _ = KNOWN_DATE_ERRATA[filing['accession']]
            d = fixed if d == stated else d
        if hold.setdefault(d, coins) != coins:
            raise ValueError(f'{where}: conflicting ETH holdings for {d}: {hold[d]} vs {coins}')
        return d

    for m in re.finditer(PARTS, text):  # a footnote's parts state the total when the dated sentence doesn't
        ps = tuple(num(x) for x in m.group(2, 3, 4))
        parts[put(m.group(1), sum(ps))] = ps
    for m in re.finditer(AGG, text):
        d = put(m.group(1), num(m.group(2)))
        parts[d] = tuple(num(x) for x in m.group(3, 4, 5))
    for m in re.finditer(TOTALED, text):
        put(m.group(2), num(m.group(1)))
        if m.group(3):
            put(m.group(4), num(m.group(3)))
    for m in re.finditer(NAV, text):
        put(m.group(1), num(m.group(2)))
    for d, ps in parts.items():
        if sum(ps) != hold[d]:
            raise ValueError(f'{where}: {d} parts {ps} sum to {sum(ps)}, stated total {hold[d]}')
    for m in re.finditer(BRINGING, text):
        if num(m.group(1)) not in hold.values():
            raise ValueError(f'{where}: undated total "{m.group(0)}" matches no dated total')
    buys = [(iso(a), iso(b), num(u), num(p)) for a, b, u, p in re.findall(BUY, text)]
    repos = [(iso(a), iso(b), num(u), num(p)) for a, b, u, p in re.findall(REPO, text)]
    direct = []
    for m in re.finditer(DIRECT, text):
        price = one([num(x) for x in re.findall(DIRECT_PRICE, text)], 'offering price', where)
        closed = one([iso(x) for x in re.findall(DIRECT_CLOSED, text)], 'offering closing date', where)
        if price is None or closed is None:
            raise ValueError(f'{where}: registered direct offering without a price or closing date')
        direct.append((closed, num(m.group(1)), price))
    sums = {'buy': [num(u) for rx in BUY_SUM for u in re.findall(rx, text)],
            'repo': [num(u) for rx in REPO_SUM for u in re.findall(rx, text)],
            'direct': [num(u) for rx in DIRECT_SUM for u in re.findall(rx, text)]}
    return {'holdings': hold, 'parts': parts, 'cash': cash_table(bs, where), 'buys': buys, 'repos': repos,
            'direct': direct, 'sums': sums}


def check_summaries(docs):
    """Each summary's units must match a detailed row of the same filing (a summary alone is not a flow)."""
    by = {}
    for f, url, r in docs:
        by.setdefault(f['accession'], []).append(r)
    for acc, rs in by.items():
        detail = {'buy': {x[2] for r in rs for x in r['buys']}, 'repo': {x[2] for r in rs for x in r['repos']},
                  'direct': {x[1] for r in rs for x in r['direct']}}
        for r in rs:
            for k, units in r['sums'].items():
                for u in units:
                    if u not in detail[k]:
                        raise ValueError(f'{acc}: {k} summary of {u} has no detailed statement in the filing')


# ---- Q2 10-Q equity statement: net proceeds and treasury cost (in thousands) ----
EQ_ROWS = {  # label -> key (None: known, not used)
    'Net loss': None, 'Stock-based compensation expense': None, 'Shares issued for vested restricted stock': None,
    'Issuance of Common Stock for exercise of pre-funded warrants': None,
    'Shares of Common Stock withheld for taxes for net share settlement': None,
    'Shares of common stock withheld for taxes for net share settlement': None,
    'Settlement of accrued bonuses in shares (gross) of common stock': None,
    'Stock repurchased (treasury stock)': 'treasury'}
# Column order of the statement's header: Series A-1 (shares, amount), Series B (shares, amount), common (shares,
# amount), additional paid-in capital, treasury (shares, amount), accumulated deficit, total; amounts in thousands.
EQ_COLS = ['a1_shares', 'a1', 'b_shares', 'b', 'common_shares', 'common', 'apic', 'treasury_shares', 'treasury',
           'deficit', 'total']
EQ_ISSUE = r'Issuance of Common Stock sold in (?:private placement|registered direct offering) (' + DATE + ')'


def equity(html, url, start, end):
    """Rows of the equity statement between 'Balance as of <start>' and 'Balance at <end>' ->
    {'issue': [(date, shares, usd)], 'treasury': (shares, usd)}. Unknown row labels raise."""
    out, on = {'issue': [], 'treasury': None}, False
    for k, v in blocks(html):
        if k != 'table':
            continue
        for r in v:
            label = r[0] if r else ''
            if re.fullmatch(rf'Balance (?:as of|at) {start}', label):
                on = True
                continue
            if on and re.fullmatch(rf'Balance (?:as of|at) {end}', label):
                return out
            if not on:
                continue
            cells = [c for c in r[1:] if c not in (')', '')]
            vals = [cell(c + ')' if c.startswith('(') and not c.endswith(')') else c) for c in cells]
            if len(vals) != len(EQ_COLS):
                raise ValueError(f'{url}: equity row {label!r} has {len(vals)} values, expected {len(EQ_COLS)} {EQ_COLS}')
            c = dict(zip(EQ_COLS, vals))
            if m := re.fullmatch(EQ_ISSUE, label):
                out['issue'].append((iso(m.group(1)), c['common_shares'], c['total'] * 1000))
            elif label not in EQ_ROWS:
                raise ValueError(f'{url}: unknown equity statement row {label!r} between {start} and {end}')
            elif EQ_ROWS[label] == 'treasury':
                out['treasury'] = (-c['treasury_shares'], -c['total'] * 1000)
    raise ValueError(f'{url}: equity statement section {start} .. {end} not found')


def build(docs, eq, eq_url, eq_period, prices):
    """docs: [(filing, url, parsed)] oldest first. eq: equity() for eq_period (start, end ISO) or None.
    -> (actions, stated, notes). One stated row per holdings date on or after START."""
    from dat.prices import close_on_or_before
    check_summaries(docs)
    hold, src, cash = {}, {}, {}
    for f, url, r in docs:
        for d, c in r['holdings'].items():
            if hold.setdefault(d, c) != c:
                raise ValueError(f'{d}: ETH holdings {hold[d]} ({src[d][1]}) vs {c} ({url})')
            src.setdefault(d, (f, url))
        cash.update({d: v for d, v in r['cash'].items() if d in r['holdings']})
    weeks = sorted(d for d in hold if d >= START)
    notes, acts = [], []

    def week_of(d, what):
        w = min((x for x in weeks if x >= d), default=None)
        if w is None:
            raise ValueError(f'{what} dated {d} is after the last stated holdings date {weeks[-1]}: no row to hold it')
        return w

    def base(w, f, url):
        return {'firm': 'SBET', 'week_end': w, 'filed': f['filed'], 'filing_url': url}

    in_q = lambda d: eq is not None and eq_period[0] < d <= eq_period[1]
    q_repos = []
    for f, url, r in docs:
        for closed, shares, price in r['direct']:
            if closed < START:
                continue
            w = week_of(closed, 'registered direct offering')
            got = [x for x in (eq['issue'] if in_q(closed) else []) if x[0] == closed]
            if got and got[0][1] != shares:
                raise ValueError(f'10-Q issue on {closed}: {got[0][1]} shares, 8-K says {shares}')
            usd, note = (got[0][2], f'usd: net proceeds, 10-Q equity statement ({eq_url})') if got else \
                (shares * price, 'usd gross: shares × price (net proceeds not yet filed)')
            acts.append(dict(base(w, f, url), action='issue_common', ticker='SBET', usd=fmt(usd), units=fmt(shares),
                             avg_price=fmt(price), note=note))
        for a, b, shares, avg in r['repos']:
            if b < START:
                continue
            row = dict(base(week_of(b, 'repurchase'), f, url), action='buyback_common', ticker='SBET',
                       usd=fmt(shares * avg), units=fmt(shares), avg_price=fmt(avg), note='usd: shares × stated average price')
            acts.append(row)
            if in_q(b):
                q_repos.append(row)
        for a, b, units, avg in r['buys']:
            if b < START:
                continue
            acts.append(dict(base(week_of(b, 'ETH purchase'), f, url), action='buy_coin', ticker='ETH', usd=fmt(units * avg),
                             units=fmt(units), avg_price=fmt(avg), note=''))
    if eq is not None and eq['treasury'] and q_repos:  # one repurchase row in the quarter: take the 10-Q cost
        shares, usd = eq['treasury']
        if len(q_repos) == 1 and Decimal(q_repos[0]['units']) == shares:
            q_repos[0].update(usd=fmt(usd), note=f'usd: treasury stock cost, 10-Q equity statement ({eq_url})')
        else:
            notes.append(f'10-Q treasury {shares} shares vs {len(q_repos)} filed repurchase rows: kept shares × average')
    stated, prev = [], None
    for w in weeks:
        f, url = src[w]
        stated.append({'firm': 'SBET', 'week_end': w, 'filed': f['filed'], 'filing_url': url, 'coins': fmt(hold[w]),
                       'usd_reserve': fmt(cash.get(w)), 'usd_cash': '', 'reserve_in': '', 'reserve_out': '',
                       'usd_reserve_prec': '1000' if w in cash else '', 'usd_cash_prec': ''})
        close_on_or_before(prices, 'SBET', w)  # every filed date needs an SBET close
        if prev:
            bought = sum(Decimal(a['units']) for a in acts if a['action'] == 'buy_coin' and prev < a['week_end'] <= w)
            accr = hold[w] - hold[prev] - bought
            acts.append(dict(base(w, f, url), action='carry', ticker='STAKE', usd='0', units=fmt(accr), avg_price='',
                             note='inferred staking/LST accrual: stated ETH change less stated purchases'))
            if accr < 0:
                notes.append(f'{w}: stated ETH fell {-accr} more than purchases explain (negative carry row)')
        prev = w
    return acts, stated, notes


def main(data_dir='data'):
    from dat import edgar
    from dat.parse_bmnr import exhibits
    from dat.prices import load
    docs = []
    for f in edgar.filings(CIK, since=START):
        for url in [f['url']] + exhibits(f, CIK):
            docs.append((f, url, parse(edgar.fetch(url), f, url)))
    q = [f for f in edgar.filings(CIK, '10-Q', since=START)]
    eq, eq_url, period = None, '', None
    if q:
        f = q[-1]
        html = edgar.fetch(f['url'])
        end = re.search(rf'For the quarterly period ended ({DATE})', ' '.join(v for k, v in blocks(html) if k == 'p'))
        if not end:
            raise ValueError(f"{f['url']}: quarterly period end not found")
        e = dt.date.fromisoformat(iso(end.group(1)))
        s = dt.date(e.year, e.month - 2, 1) - dt.timedelta(days=1)  # prior quarter end
        label = lambda d: d.strftime('%B %-d, %Y')
        eq, eq_url, period = equity(html, f['url'], label(s), label(e)), f['url'], (s.isoformat(), e.isoformat())
    acts, stated, notes = build(docs, eq, eq_url, period, load(os.path.join(data_dir, 'prices.csv')))
    acts.sort(key=lambda r: (r['week_end'], r['action'], r['ticker']))
    merge_write(os.path.join(data_dir, 'actions.csv'), ACTION_FIELDS, 'SBET', acts)
    merge_write(os.path.join(data_dir, 'stated.csv'), STATED_FIELDS, 'SBET', stated)
    print(f'documents parsed {len(docs)}; SBET actions.csv {len(acts)} rows, stated.csv {len(stated)} rows (filed dates only)')
    print('\n'.join(notes))
    parsed = [{'week_end': s['week_end'], 'coins': Decimal(s['coins'])} for s in stated]
    return check(parsed, acts, [r for _, _, r in docs])


def ser_sbet(html=None):
    from dat.parse_bmnr import ser
    return ser('SBET', html)


SITE_MAX_AGE = 42  # days before SBET's own last filed date (not the calendar): SharpLink files holdings rarely


def check(parsed, acts, docs=(), site=None):
    """Print rolled (first stated + stated purchases) vs stated per filed date, the inferred carry, and the
    parts check; compare stated ETH at the site's snapshot date. -> exit code."""
    first = parsed[0]
    rolled = first['coins']
    print(f"{first['week_end']} anchor stated={first['coins']}")
    for prev, r in zip(parsed, parsed[1:]):
        w = r['week_end']
        bought = sum(Decimal(a['units']) for a in acts if a['action'] == 'buy_coin' and prev['week_end'] < a['week_end'] <= w)
        carry = sum(Decimal(a['units']) for a in acts if a['action'] == 'carry' and a['week_end'] == w)
        rolled += bought + carry
        print(f"{w} dstated={r['coins'] - prev['coins']} purchases={bought} inferred_carry={carry} "
              f"rolled={rolled} stated={r['coins']} rolled-stated={rolled - r['coins']:+}")
    for d, ps in sorted({(d, ps) for r in docs for d, ps in r['parts'].items()}):
        print(f'{d} parts native+LsETH+weETH = {sum(ps)} = stated total (parse raises otherwise)')
    site, snap = site or ser_sbet()
    last = parsed[-1]['week_end']
    by = {r['week_end']: r['coins'] for r in parsed}
    at = max((w for w in by if w <= snap), default=None)
    if at is None:
        print(f'site snapshotDate {snap} is before the first stated date {first["week_end"]}: FAIL')
        return 1
    pct = float(by[at] / site - 1) * 100
    age = (dt.date.fromisoformat(last) - dt.date.fromisoformat(snap)).days
    idle = (dt.date.today() - dt.date.fromisoformat(last)).days
    ok, fresh = abs(pct) <= 0.1, age <= SITE_MAX_AGE
    print(f'strategicethreserve.xyz SBET {site} (snapshotDate {snap}) vs stated {by[at]} (filed date {at}): {pct:+.4f}% '
          f'{"OK" if ok else "FAIL"} (tolerance 0.1%); snapshot {age} days before SBET\'s last filed date {last} '
          f'{"OK" if fresh else "FAIL"} (max {SITE_MAX_AGE}; measured against SharpLink\'s own last filing, which is '
          f'{idle} days before today)')
    return 0 if ok and fresh else 1


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
