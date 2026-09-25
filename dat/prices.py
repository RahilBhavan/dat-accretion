"""Daily closes -> data/prices.csv (date, ticker, close). Yahoo for listed tickers, CoinGecko for BTC/ETH. stdlib only.

Yahoo uses quote close, not adjclose: preferred dividends would distort q.
"""
import csv, json, os, sys, urllib.request, datetime as dt
from zoneinfo import ZoneInfo

START = dt.date(2026, 5, 25)
YAHOO = ['MSTR', 'STRC', 'STRK', 'STRF', 'STRD', 'BMNR', 'BMNP']
GECKO = {'BTC': 'bitcoin', 'ETH': 'ethereum'}
YAHOO_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{}?period1={}&period2={}&interval=1d'
GECKO_URL = 'https://api.coingecko.com/api/v3/coins/{}/market_chart/range?vs_currency=usd&from={}&to={}'
UA = 'dat-accretion rbhavanzim@gmail.com'
FIELDS = ['date', 'ticker', 'close']
DAY = 86400


def get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def yahoo_rows(j, ticker, now=None):
    """[(date, ticker, close)] keyed by exchange-local trading date; null closes skipped."""
    r = j['chart']['result'][0]
    tz = ZoneInfo(r['meta']['exchangeTimezoneName'])
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(tz)
    closes = r['indicators']['quote'][0]['close']
    rows = [(dt.datetime.fromtimestamp(t, tz).date().isoformat(), ticker, c)
            for t, c in zip(r['timestamp'], closes) if c is not None]
    # Today's bar is live until 16:30 exchange-local; keep only settled closes, like gecko_rows.
    return [x for x in rows if x[0] != now.date().isoformat() or now.time() > dt.time(16, 30)]


def gecko_rows(j, ticker):
    """[(date, ticker, close)] for each complete UTC day."""
    pts = sorted(j['prices'])
    last = pts[-1][0] // 1000
    out = {}
    # Close for D = last point at or before 00:00 UTC of D+1; D is kept only once that instant has passed.
    for ms, p in pts:
        t = ms // 1000
        end = -(-t // DAY) * DAY  # next 00:00 UTC at or after t
        if end <= last:
            out[dt.datetime.fromtimestamp(end - DAY, dt.timezone.utc).date().isoformat()] = p
    return [(d, ticker, p) for d, p in out.items()]


def close_on_or_before(prices, ticker, date):
    """(date_used, close): last close for ticker on or before date; raises if none within 7 days.

    prices: rows of (date, ticker, close) or dicts with those keys; dates ISO strings.
    """
    date = str(date)
    lo = (dt.date.fromisoformat(date) - dt.timedelta(days=7)).isoformat()
    best = None
    for r in prices:
        d, t, c = (r['date'], r['ticker'], r['close']) if isinstance(r, dict) else r
        if t == ticker and lo <= d <= date and (best is None or d > best[0]):
            best = (d, float(c))
    if best is None:
        raise LookupError(f'{ticker}: no close in [{lo}, {date}]')
    return best


def load(path='data/prices.csv'):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def fetch(start=START, end=None):
    end = end or dt.datetime.now(dt.timezone.utc)
    p1 = int(dt.datetime.combine(start, dt.time(), dt.timezone.utc).timestamp())
    p2 = int(end.timestamp())
    rows = []
    for t in YAHOO:
        rows += yahoo_rows(get_json(YAHOO_URL.format(t, p1, p2)), t)
    for t, cid in GECKO.items():
        rows += gecko_rows(get_json(GECKO_URL.format(cid, p1, p2)), t)
    rows = [r for r in rows if r[0] >= start.isoformat()]
    return sorted(rows, key=lambda r: (r[0], r[1]))


def save(path, rows):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        w.writerows(rows)


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join('data', 'prices.csv')
    rows = fetch()
    save(path, rows)
    for t in YAHOO + list(GECKO):
        ds = [r[0] for r in rows if r[1] == t]
        if not ds:
            raise SystemExit(f'{t}: no rows')
        print(f'{t:5} {len(ds):4} rows {ds[0]} .. {ds[-1]}')
    print(f'wrote {len(rows)} rows to {path}')
