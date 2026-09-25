"""Strategy (CIK 1050446) weekly 8-Ks -> data/actions.csv and data/stated.csv. stdlib only.

Sections are found by heading text, tables are read by row and column label. An unknown label
inside a recognized section raises. Acceptance: rolled BTC equals each 8-K's stated holdings.
"""
import csv, os, re, sys, datetime as dt
from decimal import Decimal
from html.parser import HTMLParser

CIK = 1050446
ACTION_FIELDS = ['firm', 'week_end', 'filed', 'filing_url', 'action', 'ticker', 'usd', 'units', 'avg_price']
STATED_FIELDS = ['firm', 'week_end', 'filed', 'filing_url', 'coins', 'usd_reserve', 'usd_cash', 'reserve_in',
                 'reserve_out', 'usd_reserve_prec', 'usd_cash_prec']
PREFS = {'STRF', 'STRC', 'STRK', 'STRD', 'STRE'}
STATED_AMOUNT = 100  # liquidation preference per preferred share, USD (STRE is EUR 100)
HEADINGS = {'atm': r'ATM Updates?', 'btc': r'BTC Updates?', 'atm+btc': r'ATM and BTC Updates?',
            'repurchase': r'Repurchase Program Updates?', 'usd': r'USD Reserve(?: and USD Cash)? Updates?'}
DATE = r'[A-Z][a-z]+ \d{1,2}, \d{4}'
MONEY = r'\$([\d,.]+) (million|billion)'
SCALE = {'million': Decimal(10) ** 6, 'billion': Decimal(10) ** 9}


class Skip(Exception):
    pass


class Blocks(HTMLParser):
    """Flatten HTML into ('p', text) and ('table', [[cell, ...], ...]); empty and bare '$' cells dropped."""
    def __init__(self):
        super().__init__()
        self.blocks, self.buf, self.table, self.row, self.cell = [], [], None, None, None

    def flush(self):
        t = ' '.join(''.join(self.buf).split())
        self.buf = []
        if t:
            self.blocks.append(('p', t))

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.flush()
            self.table = []
        elif tag == 'tr' and self.table is not None:
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []
        elif tag in ('p', 'div', 'br') and self.table is None:
            self.flush()

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            c = ' '.join(''.join(self.cell).split())
            self.cell = None
            if c and c != '$':
                self.row.append(c)
        elif tag == 'tr' and self.row is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            if self.table:
                self.blocks.append(('table', self.table))
            self.table = None
        elif tag in ('p', 'div') and self.table is None:
            self.flush()

    def handle_data(self, data):
        (self.cell if self.cell is not None else self.buf if self.table is None else []).append(data)


def blocks(html):
    b = Blocks()
    b.feed(html)
    b.flush()
    return b.blocks


def iso(s):
    return dt.datetime.strptime(s, '%B %d, %Y').date().isoformat()


def money(amount, unit):
    return Decimal(amount.replace(',', '')) * SCALE[unit.lower()]


def num(cell):
    """Table cell -> Decimal. '-' is zero, '(x)' is negative, footnote marks and '$' dropped."""
    c = re.sub(r'(?<=[\d\-)])\s*\(\d\)$', '', cell.replace('$', '').replace('*', '')).replace(',', '').replace(' ', '')
    if c in ('-', ''):
        return Decimal(0)
    if re.fullmatch(r'\(\d+(\.\d+)?\)', c):
        return -Decimal(c[1:-1])
    if not re.fullmatch(r'\d+(\.\d+)?', c):
        raise ValueError(f'not a number: {cell!r}')
    return Decimal(c)


def key(label):
    """Header label -> compact key: footnote marks and spaces removed, lower case."""
    return re.sub(r'\(\d\)|\*|\s', '', label).lower()


def is_heading(t):
    return (len(t) < 100 and t[0].isupper() and '$' not in t and ':' not in t
            and not t.endswith(('.', ';', ',')))


TRADE_TABLE = r'Security|BTC.*|Shares Repurchased|Shares Sold.*'


def sections(bs, where=''):
    """[(kind, [blocks])] for recognized headings; any other heading ends the current section.
    A trade-looking table outside a recognized section raises (a renamed heading must not drop trades)."""
    out, cur, heading = [], None, None
    for kind_, v in bs:
        if kind_ == 'p' and is_heading(v):
            heading = v
            cur = next((k for k, rx in HEADINGS.items() if re.fullmatch(rx, v)), None)
            if cur:
                out.append((cur, []))
            continue
        if cur:
            out[-1][1].append((kind_, v))
        elif kind_ == 'table' and any(re.fullmatch(TRADE_TABLE, re.sub(r'\s*\(\d\)$', '', c)) for r in v for c in r):
            raise ValueError(f'{where}: trade table under unrecognized heading {heading!r}')
    return out


def period_end(row0):
    m = re.fullmatch(rf'During Period ({DATE}) to ({DATE})\*?', row0) or re.fullmatch(rf'As of ({DATE})\*?', row0)
    return iso(m.groups()[-1]) if m else None


def prose_end(text):
    m = re.search(rf'during the period between ({DATE}) and ({DATE})', text, re.I)
    return iso(m.group(2)) if m else None


def rows_of(sec):
    return [r for k, v in sec if k == 'table' for r in v]


def text_of(sec):
    return ' '.join(v for k, v in sec if k == 'p')


def security_table(rows, cols, where):
    """Rows labelled '<TICKER> Stock' under a 'Security' header -> [(ticker, {col: Decimal}), (period_end)]."""
    out, header, end, done = [], None, None, False
    for r in rows:
        if period_end(r[0]):
            end = period_end(r[0])
        elif r[0] == 'Security':
            header = []
            for h in r[1:]:
                k = next((c for c in cols if key(h).startswith(c)), None)
                if k is None:
                    raise ValueError(f'{where}: unknown column {h!r}')
                header.append(k)
        elif r[0] == 'Total':
            done = True
        elif done and all(re.fullmatch(r'[\d,.$ ]+', c) for c in r):
            continue
        elif m := re.fullmatch(r'([A-Z]{4}) Stock(?: ?\(\d\))?', r[0]):
            t = m.group(1)
            if t != 'MSTR' and t not in PREFS or header is None or len(r) != len(header) + 1:
                raise ValueError(f'{where}: unknown security row {r!r}')
            out.append((t, dict(zip(header, map(num, r[1:])))))
        elif len(r) == 1 and re.fullmatch(r'Class A Common Stock|[\d.]+% Series A Perpetual \w+ Preferred Stock|'
                                          r'Variable Rate Series A Perpetual \w+ Preferred Stock', r[0]):
            continue
        else:
            raise ValueError(f'{where}: unknown label {r[0]!r}')
    if header is None:
        raise ValueError(f'{where}: no Security header')
    return out, end


def atm(sec, where, fallback_end):
    text = text_of(sec)
    rows = rows_of(sec)
    if not rows:
        if re.search(r'did not sell any shares', text):
            return []
        raise ValueError(f'{where}: ATM section has no table and no "did not sell" sentence')
    table, end = security_table(rows, ['sharessold', 'notionalvalue(inmillions)', 'netproceeds(inmillions)', 'available'], where)
    end = end or fallback_end
    out = []
    for t, v in table:
        shares, usd = v['sharessold'], v['netproceeds(inmillions)'] * SCALE['million']
        if shares == 0 and usd == 0:
            continue
        if t == 'MSTR':
            out.append((end, 'issue_common', t, usd, shares, usd / shares))
            continue
        if t == 'STRE':
            raise ValueError(f'{where}: STRE sale is EUR; no USD rate parser for it, add one from this filing')
        notional = shares * STATED_AMOUNT
        if abs(notional - v['notionalvalue(inmillions)'] * SCALE['million']) > Decimal('0.05') * SCALE['million']:
            raise ValueError(f'{where}: {t} notional {v["notionalvalue(inmillions)"]}M != {shares} x ${STATED_AMOUNT}')
        out.append((end, 'issue_pref', t, usd, notional, usd / shares))
    return out


def repurchase(sec, where, fallback_end):
    rows = rows_of(sec)
    if not rows:
        if re.search(r'did not purchase any shares', text_of(sec)):
            return []
        raise ValueError(f'{where}: repurchase section has no table and no "did not purchase" sentence')
    table, end = security_table(rows, ['sharesrepurchased', 'aggregatepurchaseprice(inmillions)'], where)
    end = end or fallback_end
    out = []
    for t, v in table:
        shares, usd = v['sharesrepurchased'], v['aggregatepurchaseprice(inmillions)'] * SCALE['million']
        if shares == 0 and usd == 0:
            continue
        if t == 'MSTR':
            out.append((end, 'buyback_common', t, usd, shares, usd / shares))
        elif t == 'STRE':
            raise ValueError(f'{where}: STRE retirement is EUR; no USD rate parser for it, add one from this filing')
        else:
            out.append((end, 'retire_pref', t, usd, shares * STATED_AMOUNT, usd / shares))
    return out


TRADE = {'btcacquired': 1, 'btcpurchased': 1, 'btcsold': -1, 'btcpurchased/(sold)': 0}
TRADE_USD = ('aggregatepurchaseprice(inmillions)', 'aggregatesaleprice(inmillions)',
             'aggregatepurchase/(sale)price(inmillions)')
TRADE_AVG = ('averagepurchaseprice', 'averagesaleprice', 'averagepurchase/(sale)price')
BASIS = ('aggregatepurchaseprice(inbillions)', 'averagepurchaseprice')


def btc(sec, where):
    """-> (trades [(end, action, 'BTC', usd, units, avg)], holdings [(as_of, coins)])."""
    trades, holdings, end, header = [], [], None, None
    for r in rows_of(sec):
        if period_end(r[0]):
            end = period_end(r[0])
        elif header is None:
            header = [key(h) for h in r]
        else:
            if len(r) != len(header):
                raise ValueError(f'{where}: BTC row {r!r} does not fit header {header!r}')
            basis, trade = False, {}
            for h, c in zip(header, r):
                if h == 'aggregatebtcholdings':
                    holdings.append((end, num(c)))
                    basis = True
                elif basis and h in BASIS:
                    continue
                elif h in TRADE:
                    trade['sign'], trade['units'] = TRADE[h], num(c)
                elif h in TRADE_USD:
                    trade['usd'] = num(c) * SCALE['million']
                elif h in TRADE_AVG:
                    trade['avg'] = num(c)
                else:
                    raise ValueError(f'{where}: unknown BTC column {h!r}')
            if trade:
                sign = trade['sign'] or (-1 if trade['units'] < 0 else 1)
                units, usd, avg = abs(trade['units']), abs(trade['usd']), abs(trade['avg'])
                if units:
                    trades.append((end, 'buy_coin' if sign > 0 else 'sell_coin', 'BTC', usd, units, avg))
            header = None
    text = text_of(sec)
    if not holdings:
        m = re.search(rf'As of ({DATE}), Strategy holds approximately ([\d,]+) bitcoin', text)
        if not m or not re.search(r'did not purchase or sell any bitcoin', text):
            raise ValueError(f'{where}: BTC section has no holdings table or holdings sentence')
        holdings.append((iso(m.group(1)), Decimal(m.group(2).replace(',', ''))))
    if any(e is None for e, _ in holdings):
        raise ValueError(f'{where}: BTC holdings without an as-of date')
    return trades, holdings


def ulp(amount, unit):
    """Unit in the last disclosed digit, USD: ('5.10', 'billion') -> 10,000,000."""
    return Decimal(1).scaleb(Decimal(amount.replace(',', '')).as_tuple().exponent) * SCALE[unit.lower()]


def balances(bs):
    """{as_of: {'usd_reserve', 'usd_cash', 'usd_reserve_prec', 'usd_cash_prec': Decimal}} from any paragraph.
    *_prec is the unit in the last disclosed digit (the R check's tolerance is half of it)."""
    out, pending = {}, None

    def put(as_of, name, amount, unit):
        out.setdefault(as_of, {}).update({name: money(amount, unit), name + '_prec': ulp(amount, unit)})

    for k, t in bs:
        if k != 'p':
            continue
        if m := re.search(rf'As of ({DATE}), the balance of the USD Reserve (?:is|was) {MONEY}', t, re.I):
            put(iso(m.group(1)), 'usd_reserve', *m.group(2, 3))
        elif m := re.search(rf'As of ({DATE}), the balances of the USD Reserve and USD Cash were {MONEY} and {MONEY}', t):
            put(iso(m.group(1)), 'usd_reserve', *m.group(2, 3))
            put(iso(m.group(1)), 'usd_cash', *m.group(4, 5))
        elif m := re.search(rf'As of ({DATE}), the balances of the USD Reserve and USD Cash were as follows', t):
            pending = iso(m.group(1))
        elif pending and (m := re.fullmatch(rf'USD (Reserve|Cash): {MONEY}', t)):
            put(pending, 'usd_' + m.group(1).lower(), *m.group(2, 3))
    return out


RESERVE_IN = rf'{MONEY}[^$;]{{0,120}}? were used to increase the USD Reserve\b'
RESERVE_OUT = rf'{MONEY} of the USD Reserve to\b'
# Any other "$X ... <verb> ... USD Reserve" must be a known sentence or it raises.
RESERVE_NEAR = (rf'{MONEY}[^$;]{{0,160}}?\b(?:increas|fund|add|contribut|allocat|deposit|transfer|replenish)\w*'
                rf'\b[^$;]{{0,20}}?\bUSD Reserve\b')
RESERVE_CAPACITY = r'up to \$1\.25 billion of additional proceeds to fund the USD Reserve'  # BTC Monetization Program size, not a flow


def reserve_flows(bs, where=''):
    """(in, out): sums of amounts "used to increase the USD Reserve" and "$X of the USD Reserve to ...";
    None when none disclosed. An unknown sentence moving money into the USD Reserve raises."""
    ins, outs = [], []
    for k, t in bs:
        if k != 'p':
            continue
        known = {m.start() for m in re.finditer(RESERVE_IN, t)} | {m.start() + 6 for m in re.finditer(RESERVE_CAPACITY, t)}
        for m in re.finditer(RESERVE_NEAR, t):
            if m.start() not in known:
                raise ValueError(f'{where}: unknown USD Reserve flow sentence: {m.group(0)!r}')
        ins += [money(*m.group(1, 2)) for m in re.finditer(RESERVE_IN, t)]
        outs += [money(*m.group(1, 2)) for m in re.finditer(RESERVE_OUT, t)]
    return (sum(ins) if ins else None), (sum(outs) if outs else None)


def dividends_paid(bs):
    """Distinct amounts disclosed as used to fund dividends/interest, from any source (USD Reserve,
    ATM or BTC-sale proceeds). The same amount twice in one filing is one payment."""
    # ponytail: dedupe by amount, so two equal separate payments in one filing merge; revisit if
    # semi-monthly STRC dividends are disclosed per payment.
    rx = rf'{MONEY}[^$]{{0,160}}?\bto fund (?:the )?(?:payment of )?(?:dividends|distributions|interest)'
    return sorted({money(m.group(1), m.group(2)) for k, t in bs if k == 'p' for m in re.finditer(rx, t)})


def parse(html, filing):
    """One 8-K -> (actions rows, stated rows). Raises Skip if it has no ATM, BTC or repurchase section."""
    where = f"{filing['accession']} ({filing['url']})"
    bs = blocks(html)
    secs = sections(bs, where)
    if not secs:
        raise Skip('no ATM, BTC or repurchase section')
    if not any(k in ('btc', 'atm+btc') for k, _ in secs):
        raise ValueError(f'{where}: {[k for k, _ in secs]} section(s) but no BTC Update section')
    acts, holdings = [], []
    for k, sec in secs:
        if k in ('btc', 'atm+btc'):
            t, h = btc(sec, where)
            acts += t
            holdings += h
    week_end = max(e for e, _ in holdings)
    for k, sec in secs:
        end = prose_end(text_of(sec)) or week_end
        if k in ('atm', 'atm+btc'):
            acts += atm(sec, where, end)
        elif k == 'repurchase':
            acts += repurchase(sec, where, end)
    for used in dividends_paid(bs):
        acts.append((week_end, 'carry', 'DIV_INT', -used, Decimal(0), None))
    bal = balances(bs)
    r_in, r_out = reserve_flows(bs, where)
    if stray := set(bal) - {e for e, _ in holdings}:
        raise ValueError(f'{where}: USD balance dated {sorted(stray)} matches no BTC holdings date')
    base = {'firm': 'MSTR', 'filed': filing['filed'], 'filing_url': filing['url']}
    actions = [dict(base, week_end=e, action=a, ticker=t, usd=fmt(u), units=fmt(n), avg_price=fmt(p))
               for e, a, t, u, n, p in acts]
    stated = [dict(base, week_end=e, coins=fmt(c), reserve_in=fmt(r_in if e == week_end else None),
                   reserve_out=fmt(r_out if e == week_end else None),
                   **{f: fmt(bal.get(e, {}).get(f)) for f in ('usd_reserve', 'usd_cash', 'usd_reserve_prec', 'usd_cash_prec')})
              for e, c in holdings]
    return actions, stated


def fmt(d):
    """Decimal -> plain string (disclosed values exact); computed averages to 6 dp; None -> ''."""
    if d is None:
        return ''
    d = Decimal(d)
    if d.as_tuple().exponent < -6:
        d = d.quantize(Decimal('0.000001'))
    return format(d.normalize(), 'f')


# Weeks whose 8-K holdings disagree by 1 BTC with the prior 8-K plus that week's trade (whole-BTC
# rounding in the filings; the next 8-K balances only from the rolled figure).
KNOWN_FILING_GAPS = {
    '2026-06-14': '845,256 + 1,587 = 846,843 but 8-K 0001193125-26-270311 (filed 6/15) states 846,842; '
                  '8-K 0001193125-26-276717 (filed 6/22) balances only from 846,843 (+520 = 847,363)',
    '2026-08-02': '843,775 - 1,638 = 842,137 but 8-K 0001193125-26-329565 (filed 8/03) states 842,138; '
                  '8-K 0001193125-26-341297 (filed 8/10) balances only from 842,137 (-1,690 = 840,447)',
}


def roll(actions, stated, gaps=KNOWN_FILING_GAPS):
    """-> [(week_end, rolled, stated, status)], status OK, GAP (documented, off by <= 1 BTC) or MISMATCH.
    Start = first stated coins minus that week's net buys."""
    net = {}
    for a in actions:
        if a['action'] in ('buy_coin', 'sell_coin'):
            net[a['week_end']] = net.get(a['week_end'], 0) + (1 if a['action'] == 'buy_coin' else -1) * Decimal(a['units'])
    stated = sorted(stated, key=lambda s: s['week_end'])
    first = stated[0]['week_end']
    start = Decimal(stated[0]['coins']) - sum(v for w, v in net.items() if w <= first)
    out = []
    for s in stated:
        rolled = start + sum(v for w, v in net.items() if w <= s['week_end'])
        diff = abs(rolled - Decimal(s['coins']))
        status = 'OK' if diff == 0 else 'GAP' if s['week_end'] in gaps and diff <= 1 else 'MISMATCH'
        out.append((s['week_end'], rolled, Decimal(s['coins']), status))
    return out


def write(path, fields, rows):
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def main(data_dir='data'):
    from dat import edgar
    actions, stated, read, skipped = [], [], 0, []
    for f in edgar.filings(CIK):
        read += 1
        try:
            a, s = parse(edgar.fetch(f['url']), f)
        except Skip as e:
            skipped.append(f"skip {f['accession']} ({f['form']} filed {f['filed']}): {e}")
            continue
        actions += a
        stated += s
    weeks = [s['week_end'] for s in stated]
    if len(weeks) != len(set(weeks)):
        raise ValueError(f'duplicate stated week_end: {sorted(w for w in set(weeks) if weeks.count(w) > 1)}')
    actions.sort(key=lambda r: (r['week_end'], r['action'], r['ticker']))
    stated.sort(key=lambda r: r['week_end'])
    write(os.path.join(data_dir, 'actions.csv'), ACTION_FIELDS, actions)
    write(os.path.join(data_dir, 'stated.csv'), STATED_FIELDS, stated)
    print('\n'.join(skipped))
    print(f'8-Ks read {read}, skipped {len(skipped)}, parsed {read - len(skipped)}; '
          f'actions.csv {len(actions)} rows, stated.csv {len(stated)} rows')
    bad = 0
    for i, (week, rolled, st, status) in enumerate(roll(actions, stated)):
        note = f'FILING GAP (documented): {KNOWN_FILING_GAPS[week]}' if status == 'GAP' else status
        if i == 0:
            note += ' (anchor: start derived from this week)'
        print(f'{week} rolled={rolled} stated={st} {note}')
        bad += status == 'MISMATCH'
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
