"""Read-only EDGAR check for the Oct 26 week's slots (`python social/2026-10-26/source_status.py`).

Prints the newest Strategy and BitMine 8-Ks, any Strategy 10-Q for the quarter ended 2026-09-30, and the last row
dat-accretion holds, then writes checks/source-status.json. One request per firm, EDGAR fair-access throttle.
SOURCE OUT means a filing exists on EDGAR with an acceptance time after the week-end date in the slot.
"""
import csv, datetime as dt, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from dat.edgar import SECClient, UA  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
FIRMS = {'MSTR': 1050446, 'BMNR': 1829311}
# slot -> (firm, form, filed on or after, what must be in it)
SLOTS = [('2026-10-26 09:30 Sats per Share', 'MSTR', '8-K', '2026-10-26', 'weekly 8-K for the week ended Oct 25'),
         ('2026-10-26 18:00 ETH per Share', 'BMNR', '8-K', '2026-10-26', 'weekly release as of Oct 25'),
         ('2026-10-27 09:30 Q3 card', 'MSTR', '10-Q', '2026-10-01', 'Q3 10-Q, quarter ended 2026-09-30'),
         ('2026-10-30 09:30 Strategy Q3 results', 'MSTR', '10-Q', '2026-10-01', 'Q3 10-Q / results'),
         ('2026-10-31 17:00 ETH poll', 'BMNR', '8-K', '2026-10-26', 'Oct 25 release (poll answer)'),
         ('2026-11-02 09:30 BitMine 8-K', 'BMNR', '8-K', '2026-11-02', 'weekly release as of Nov 1')]


def main():
    client, subs, now = SECClient(UA), {}, dt.datetime.now(dt.timezone.utc)
    for firm, cik in FIRMS.items():
        subs[firm] = json.loads(client.get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json'))['filings']['recent']
    held = {f: max(r['week_end'] for r in csv.DictReader(open(os.path.join(ROOT, 'data/stated.csv'))) if r['firm'] == f) for f in FIRMS}
    out = {'checked_utc': now.isoformat(timespec='seconds'), 'data_last_week': held, 'slots': []}
    for slot, firm, form, since, what in SLOTS:
        r = subs[firm]
        hits = [{'form': r['form'][i], 'filed': r['filingDate'][i], 'accepted_utc': r['acceptanceDateTime'][i], 'accession': r['accessionNumber'][i],
                 'document': r['primaryDocument'][i]} for i in range(len(r['form'])) if r['form'][i] == form and r['filingDate'][i] >= since]
        out['slots'].append({'slot': slot, 'firm': firm, 'looking_for': what, 'status': 'SOURCE OUT' if hits else 'HELD', 'filings': hits[:3]})
        print(f"{'SOURCE OUT' if hits else 'HELD':10} {slot}: {what}; {form} filed on or after {since}: {len(hits)}")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'checks', 'source-status.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print('checked', out['checked_utc'], '| data last week', held)


if __name__ == '__main__':
    main()
