"""Daily Strategy KPI row -> data/kpi_snapshots.csv, raw JSON -> data/kpi/<date>.json. stdlib only.

The KPI API keeps no history, so each run's row and raw payload are the only record.
"""
import csv, json, math, os, sys, urllib.request, datetime as dt

KPI_URL = 'https://api.strategy.com/btc/bitcoinKpis'
CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/MSTR'
UA = 'dat-accretion rbhavanzim@gmail.com'
FIELDS = ['fetched_at', 'netSatsPerShare', 'netBtcReserve', 'amplification', 'mNav', 'btc_price', 'mstr_price']


def get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def positive(name, v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
        raise ValueError(f'{name}: expected a finite number > 0, got {v!r}')
    return v


def row(kpi, chart, fetched_at):
    """One kpi_snapshots.csv row; raises ValueError on any missing or non-positive field."""
    r = kpi['results']
    out = {'fetched_at': fetched_at}
    for k in ('netSatsPerShare', 'netBtcReserve', 'amplification', 'mNav'):
        out[k] = positive(k, r.get(k))
    out['btc_price'] = positive('btc_price', r.get('latestPrice'))
    out['mstr_price'] = positive('mstr_price', chart['chart']['result'][0]['meta'].get('regularMarketPrice'))
    return out


def save(data_dir, r, kpi):
    path = os.path.join(data_dir, 'kpi_snapshots.csv')
    os.makedirs(os.path.join(data_dir, 'kpi'), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(r)
    raw = os.path.join(data_dir, 'kpi', r['fetched_at'][:10] + '.json')
    with open(raw, 'w') as f:
        json.dump(kpi, f, indent=1)
    return path, raw


if __name__ == '__main__':
    data_dir = sys.argv[1] if len(sys.argv) > 1 else 'data'
    kpi, chart = get_json(KPI_URL), get_json(CHART_URL)
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    r = row(kpi, chart, now)
    path, raw = save(data_dir, r, kpi)
    print(f"saved {r['fetched_at']} netSatsPerShare={r['netSatsPerShare']} mNav={r['mNav']} to {path} and {raw}")
