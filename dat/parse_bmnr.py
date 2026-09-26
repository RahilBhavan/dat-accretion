"""BitMine (CIK 1829311) weekly EX-99 releases -> BMNR rows in data/actions.csv and data/stated.csv. stdlib only.

Releases are prose: numbers are read by phrase. A $ amount or share/coin count in a sentence that
mentions "repurchas", "buyback", "offering", "acquired" or a common-stock sale must be consumed by a
known phrase, else it raises. No staking carry rows (data.md): "acquired" matches the stated
holdings change, so the estimate (staked ETH x 7-day annualized yield x 7/365) is a printed
diagnostic only. Checks: stated dETH vs acquired vs staking estimate; rolled ETH vs
strategicethreserve.xyz at the site's snapshot week.
"""
import csv, json, os, re, sys, urllib.request, datetime as dt
from decimal import Decimal
from dat.parse_mstr import blocks, iso, money, ulp, fmt, ACTION_FIELDS, STATED_FIELDS, DATE, MONEY

CIK = 1829311
BMNP_STATED = 100  # liquidation preference per BMNP share, USD (method.md)
AP = "[’']"
STAKING_FIELDS = ['week_end', 'eth_est']  # staked ETH x 7-day yield x 7/365, diagnostic only (data.md)

HOLDINGS = (rf'As of ({DATE})(?: at [^,]+)?, the Company{AP}s crypto holdings are comprised of ([\d,]+) ETH\b'
            rf'.*? and total cash(?: & marketable securities)? of {MONEY}')
ACQUIRED = r'\bwe acquired ([\d,]+) ETH\b'
STAKED = rf'As of ({DATE}), Bitmine total staked ETH stands at ([\d,]+)'
YIELD = r'\b(\d+\.\d+)% 7-day BMNR yield|7-day yield of (\d+\.\d+)% \(annualized\)'
BUYBACK = (r'\brepurchased (?:approximately )?(\d+(?:\.\d+)?) million (?:shares of common stock|common stock|'
           r'common shares|shares) (?:in|during) the past week')
BUYBACK_AVG = r'\bat an average price of \$([\d,]+\.\d+)'
PREF_CLOSED = (r'\bOn ([A-Z][a-z]+ \d{1,2}), Bitmine closed its offering\b.*? of ([\d,]+) shares of 9\.50% Series A '
               r'Perpetual Preferred Stock\b.*? at a public offering price of \$([\d.]+) per share')
PREF_NET = r'\breceived net proceeds from the offering of approximately \$([\d.]+) million'
# Phrases whose numbers are known and not flows of the week (cumulative totals, program size, pricing release).
KNOWN = [ACQUIRED, BUYBACK, BUYBACK_AVG, PREF_CLOSED, PREF_NET,
         r'\$[\d.]+ billion share repurchase program',
         r'\brepurchased (?:over )?[\d.]+ million shares (?:of common stock )?(?:cumulatively|under)',
         r'\bover [\d.]+ million shares of common stock repurchased',
         r'\btotal common equity repurchases to over [\d.]+ million common shares',
         r'\bexecuted the [\d.]+ million common stock buyback',
         r'\bfrom the [\d.]+ million purchased the week prior',
         r'\bpast week{AP}s [\d.]+ million buyback'.replace('{AP}', AP),
         r'\breduced pace of buys reflects that Bitmine repurchased [\d.]+ million common shares',
         r'\bof [\d,]+ shares of 9\.50% Series A Perpetual Preferred Stock\b.*? at a public offering price of \$[\d.]+ per share',
         r'\bpreviously announced offering of [\d,]+ shares of Series A Preferred Stock',
         r'\bnet proceeds (?:it will receive )?from the (?:offering|Offering) will be approximately \$[\d.]+ million']
NEAR = (r'repurchas|buyback|\boffering\b|\bacquired\b|at-the-market|registered direct|\bsold\b|\bATM\b|\bbought\b|purchas|'
        r'\bissued\b|redeem|\braised\b|\badded\b|\bplaced\b|\bproceeds\b')
NUMBER = r'\$\d[\d,.]*|\b\d[\d,.]*\s(?:million|billion)\b|\b\d{1,3}(?:,\d{3})+\b'


class Skip(Exception):
    pass


def paragraphs(bs):
    """Prose paragraphs; one-row bullet tables ('●', text) read as prose too."""
    out = []
    for k, v in bs:
        if k == 'p':
            out.append(v)
        else:
            out += [' '.join(c for c in r if c != '●') for r in v if r and (r[0] == '●' or len(r) == 1)]
    return out


def sentences(text):
    return re.split(r'(?<=[.!?”])\s+(?=[“"A-Z])', text)


def check_near(paras, where):
    """Raise on a number in a repurchase/offering/acquired/sale sentence that no known phrase consumes."""
    for para in paras:
        if re.search(r'forward-looking statements', para, re.I):
            continue
        for s in sentences(para):
            if not re.search(NEAR, s, re.I):
                continue
            known = [m.span() for rx in KNOWN for m in re.finditer(rx, s)]
            for m in re.finditer(NUMBER, s):
                if not any(a <= m.start() < b for a, b in known):
                    raise ValueError(f'{where}: unknown number {m.group(0)!r} near repurchase/offering/acquired/sale: {s!r}')


def one(values, what, where):
    vals = set(values)
    if len(vals) > 1:
        raise ValueError(f'{where}: conflicting {what}: {sorted(vals)}')
    return vals.pop() if vals else None


def num(s):
    return Decimal(s.replace(',', ''))


def dividends(bs, url, filed):
    """[(pay_date, per_share, url, filed)] declared in one document: prose '... dividend of $X ... paid on DATE'
    (amount carried to a later paragraph when the date comes there) and 'Payment Date' / 'Amount Per Share' tables."""
    out, pending = [], None
    for k, v in bs:
        if k == 'table':
            head = [c.lower() for c in v[0]]
            if 'payment date' in head and any(h.startswith('amount per share') for h in head):
                pi = head.index('payment date')
                ai = next(i for i, h in enumerate(head) if h.startswith('amount per share'))
                for r in v[1:]:
                    d = dt.datetime.strptime(r[pi], '%a, %b %d, %Y').date().isoformat()
                    out.append((d, num(r[ai].lstrip('$')), url, filed))
            continue
        if re.search(r'forward-looking statements', v, re.I):
            continue
        for s in sentences(v):
            a = re.search(r'\bdividend (?:of|in the amount of) \$(\d+\.\d+)', s)
            pending = num(a.group(1)) if a else pending
            if (d := re.search(rf'\bpaid on ({DATE})', s)) and pending is not None:
                out.append((iso(d.group(1)), pending, url, filed))
                pending = None
    return out


EXCL_BTC = r'\b([\d,]+) Bitcoin \(BTC\)'
EXCL_STAKE = rf'{MONEY} stake in ([A-Z][\w&.]*(?: [A-Z][\w&.]*)*)'


def excluded_holdings(html):
    """Holdings Strategy's definition leaves out of BitMine's net (method.md "BitMine mapping"), from the release's
    holdings sentence -> {'week_end', 'btc', 'stakes': [(name, usd)]}, or None when the sentence isn't there."""
    for p in paragraphs(blocks(html)):
        for m in re.finditer(HOLDINGS, p):
            text = m.group(0)
            btc = re.search(EXCL_BTC, text)
            stakes = [(s[3], int(money(s[1], s[2]))) for s in re.finditer(EXCL_STAKE, text)]
            if btc or stakes:
                return {'week_end': iso(m.group(1)), 'btc': int(btc[1].replace(',', '')) if btc else 0, 'stakes': stakes}
    return None


# Release dates that contradict the filing sequence; corrected with the evidence cited.
KNOWN_DATE_ERRATA = {
    '0001493152-26-032090': ('2026-06-28', '2026-07-05',
                             'release filed 2026-07-06 says "As of June 28, 2026 at 6:30pm ET" but 0001493152-26-030428 '
                             '(filed 6/29) already reported June 28 at 3:00pm ET; its staked-ETH sentence is dated July 5, 2026'),
}


def parse(html, filing, url, prev_week=None):
    """One weekly release -> dict(week_end, coins, cash, cash_prec, acquired, staked, staked_date, yield,
    buyback (shares, avg or None), pref [(closing_date, shares, price, net_usd)]). Raises Skip without a holdings sentence."""
    where = f"{filing['accession']} ({url})"
    bs = blocks(html)
    paras = paragraphs(bs)
    check_near(paras, where)
    hold = [m for p in paras for m in re.finditer(HOLDINGS, p)]
    if not hold:
        raise Skip('no holdings sentence')
    as_of, coins, cash = one([(iso(m.group(1)), num(m.group(2)), m.group(3, 4)) for m in hold], 'holdings', where)
    if filing['accession'] in KNOWN_DATE_ERRATA:
        stated, fixed, _ = KNOWN_DATE_ERRATA[filing['accession']]
        if as_of != stated:
            raise ValueError(f'{where}: erratum expects as-of {stated}, release says {as_of}')
        as_of = fixed
    if prev_week and as_of <= prev_week:
        raise ValueError(f'{where}: as-of {as_of} not after prior release week {prev_week}')
    text = ' '.join(paras)
    staked = one([(iso(m.group(1)), num(m.group(2))) for m in re.finditer(STAKED, text)], 'staked ETH', where)
    buy = one([num(m.group(1)) * 10 ** 6 for m in re.finditer(BUYBACK, text)], 'weekly repurchase', where)
    pref = []
    for m in re.finditer(PREF_CLOSED, text):
        d = dt.datetime.strptime(f'{m.group(1)}, {as_of[:4]}', '%B %d, %Y').date().isoformat()
        net = one([num(n.group(1)) * 10 ** 6 for n in re.finditer(PREF_NET, text)], 'offering net proceeds', where)
        if net is None:
            raise ValueError(f'{where}: offering closed without net proceeds')
        pref.append((d, num(m.group(2)), num(m.group(3)), net))
    return {'week_end': as_of, 'coins': coins, 'cash': money(*cash), 'cash_prec': ulp(*cash),
            'acquired': one([num(m.group(1)) for m in re.finditer(ACQUIRED, text)], 'acquired ETH', where),
            'staked': staked and staked[1], 'staked_date': staked and staked[0],
            'yield': one([num(a or b) for a, b in re.findall(YIELD, text)], '7-day yield', where),
            'buyback': buy and (buy, one([num(m.group(1)) for m in re.finditer(BUYBACK_AVG, text)], 'buyback avg', where)),
            'pref': list(dict.fromkeys(pref))}


def build(releases, divs, prices):
    """releases: [(filing, url, parsed)] oldest first. -> (actions, stated, notes, staking estimate by week)."""
    from dat.prices import close_on_or_before
    acts, stated, notes, stake, prev = [], [], [], {}, None
    bmnp_shares = Decimal(0)
    prev_coins = None
    for f, url, r in releases:
        week = r['week_end']
        if prev_coins is not None and r['coins'] != prev_coins and r['acquired'] is None:
            raise ValueError(f"{f.get('accession', '')} ({url}): ETH holdings changed {prev_coins} -> {r['coins']} "
                             f"but no 'we acquired N ETH' sentence; unknown source of the change")
        prev_coins = r['coins']
        base = {'firm': 'BMNR', 'week_end': week, 'filed': f['filed'], 'filing_url': url}
        price_date, _ = close_on_or_before(prices, 'BMNR', week)
        stated.append(dict(base, coins=fmt(r['coins']), usd_reserve=fmt(r['cash']), usd_cash='', reserve_in='',
                           reserve_out='', usd_reserve_prec=fmt(r['cash_prec']), usd_cash_prec=''))

        def close(t):
            d, c = close_on_or_before(prices, t, price_date)
            if d != price_date:
                raise LookupError(f'{t}: no close on {price_date} (BMNR price date for week {week})')
            return Decimal(repr(c))

        if r['acquired']:
            eth = close('ETH')
            acts.append(dict(base, action='buy_coin', ticker='ETH', usd=fmt(r['acquired'] * eth), units=fmt(r['acquired']),
                             avg_price=fmt(eth), note='usd estimated: units × ETH close'))
        if r['buyback']:
            shares, avg = r['buyback']
            note = ''
            if avg is None:
                avg, note = close('BMNR'), 'usd estimated: units × BMNR close'
                notes.append(f'{week} buyback avg price not disclosed; BMNR close {price_date} used')
            acts.append(dict(base, action='buyback_common', ticker='BMNR', usd=fmt(shares * avg), units=fmt(shares),
                             avg_price=fmt(avg), note=note))
        for d, shares, price, net in r['pref']:
            if (prev or '0000') < d <= week:
                bmnp_shares += shares
                acts.append(dict(base, action='issue_pref', ticker='BMNP', usd=fmt(net), units=fmt(shares * BMNP_STATED),
                                 avg_price=fmt(price)))
        if r['staked'] is None or r['yield'] is None:
            notes.append(f"{week} no staking estimate: {'staked ETH' if r['staked'] is None else '7-day yield'} not stated")
        else:
            if r['staked_date'] != week:
                notes.append(f"{week} staking estimate uses staked ETH dated {r['staked_date']} (release's own figure)")
            stake[week] = r['staked'] * r['yield'] / 100 * 7 / 365
        # BMNP dividends paid in (prev, week]
        paid = sorted({(d, a) for d, a, _, _ in divs if (prev or '0000') < d <= week})
        for d in {d for d, _ in paid}:
            if len({a for x, a in paid if x == d}) > 1:
                raise ValueError(f'BMNP dividend paid {d}: conflicting per-share amounts {paid}')
        for d, a in paid:
            u, fl = next((u, fl) for x, y, u, fl in divs if (x, y) == (d, a))
            acts.append(dict(base, filed=fl, filing_url=u, action='carry', ticker='DIV', usd=fmt(-a * bmnp_shares),
                             units='0', avg_price=''))
        if bmnp_shares and not paid:
            notes.append(f'{week} no BMNP dividend paid: no declared payment date falls in this week')
        prev = week
    return acts, stated, notes, stake


SER_URL = 'https://www.strategicethreserve.xyz/'


def ser_bmnr(html=None):
    """(currentReserve ETH, snapshotDate) for ticker BMNR from strategicethreserve.xyz's server-rendered data."""
    if html is None:
        req = urllib.request.Request(SER_URL, headers={'User-Agent': 'dat-accretion rbhavanzim@gmail.com'})
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode('utf-8', errors='replace')
    t = html.replace('\\"', '"')
    m = re.search(r'"ticker":"BMNR","currentReserve":(\d+(?:\.\d+)?)[^{}]*?"snapshotDate":"\$D(\d{4}-\d\d-\d\d)', t)
    if not m:
        raise LookupError(f'{SER_URL}: no BMNR currentReserve/snapshotDate in page data')
    return Decimal(m.group(1)), m.group(2)


def merge_write(path, fields, firm, rows):
    """Replace `firm`'s rows in a CSV, keeping other firms' rows byte-identical; firms sorted, rows in given order."""
    with open(path, newline='') as f:
        keep = [r for r in csv.DictReader(f) if r['firm'] != firm]
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(sorted(keep + rows, key=lambda r: r['firm']))


def exhibits(f):
    """EX-99.* document URLs of a filing, from its index.json."""
    from dat import edgar
    base = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{f['accession'].replace('-', '')}/"
    items = json.loads(edgar.fetch(base + 'index.json'))['directory']['item']
    return [base + i['name'] for i in items if re.fullmatch(r'ex99-?\d+\.html?', i['name'], re.I)]


def main(data_dir='data'):
    from dat import edgar
    from dat.prices import load
    releases, divs, prev = [], [], None
    for f in edgar.filings(CIK):
        for url in exhibits(f):
            html = edgar.fetch(url)
            divs += dividends(blocks(html), url, f['filed'])
            try:
                r = parse(html, f, url, prev)
            except Skip as e:
                print(f"skip {f['accession']} {url.rsplit('/', 1)[-1]} (filed {f['filed']}): {e}")
                continue
            if f['accession'] in KNOWN_DATE_ERRATA:
                print(f"date erratum {f['accession']}: {KNOWN_DATE_ERRATA[f['accession']][2]}")
            releases.append((f, url, r))
            prev = r['week_end']
    acts, stated, notes, stake = build(releases, divs, load(os.path.join(data_dir, 'prices.csv')))
    acts.sort(key=lambda r: (r['week_end'], r['action'], r['ticker']))
    merge_write(os.path.join(data_dir, 'actions.csv'), ACTION_FIELDS, 'BMNR', acts)
    merge_write(os.path.join(data_dir, 'stated.csv'), STATED_FIELDS, 'BMNR', stated)
    with open(os.path.join(data_dir, 'staking.csv'), 'w', newline='') as f:  # diagnostic, read by dat.balances.bmnr_s_bias
        w = csv.writer(f, lineterminator='\n')
        w.writerow(STAKING_FIELDS)
        w.writerows([wk, f'{float(v):.1f}'] for wk, v in stake.items())
    print(f'releases parsed {len(releases)}; BMNR actions.csv {len(acts)} rows, stated.csv {len(stated)} rows')
    print('\n'.join(notes))
    return check([r for _, _, r in releases], stake)


SITE_MAX_AGE = 42  # days: snapshot older than 6 weeks before the last week fails (data.md)


def check(parsed, stake, site=None):
    """Print dstated vs acquired vs staking estimate and rolled (first stated + cumulative acquired) vs stated
    per week; compare rolled ETH at the site's snapshot week. -> exit code."""
    first = parsed[0]
    rolled, out = first['coins'], {first['week_end']: first['coins']}
    print(f"{first['week_end']} anchor stated={first['coins']}")
    for prev, r in zip(parsed, parsed[1:]):
        w, d, acq = r['week_end'], r['coins'] - prev['coins'], r['acquired'] or 0
        rolled += acq
        out[w] = rolled
        print(f"{w} dstated={d} acquired={acq} residual={d - acq} staking_est={stake.get(w, 0):.1f} (diagnostic) "
              f"rolled={rolled} stated={r['coins']} rolled-stated={rolled - r['coins']:+}")
    site, snap = site or ser_bmnr()
    last = parsed[-1]['week_end']
    at = max((w for w in out if w <= snap), default=None)
    if at is None:
        print(f'site snapshotDate {snap} is before the first stated week {first["week_end"]}: FAIL')
        return 1
    pct = float(out[at] / site - 1) * 100
    age = (dt.date.fromisoformat(last) - dt.date.fromisoformat(snap)).days
    ok, fresh = abs(pct) <= 0.1, age <= SITE_MAX_AGE
    print(f'strategicethreserve.xyz BMNR {site} (snapshotDate {snap}) vs rolled {out[at]} (week {at}): {pct:+.4f}% '
          f'{"OK" if ok else "FAIL"} (tolerance 0.1%); snapshot {age} days before last week {last} '
          f'{"OK" if fresh else "FAIL"} (max {SITE_MAX_AGE})')
    return 0 if ok and fresh else 1


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
