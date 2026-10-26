"""Q3 2026 figures for the Strategy card and copy, recomputed from data/ (`python social/2026-10-26/q3_figures.py`).

Q3 = Strategy weekly rows with week_end 2026-07-05 to 2026-09-30 (the 2026-06-30 row is the opening level).
Sats = Δn × 1e8, summed from attribution.csv dn_exact. Asserts the figures the card and copy print, and that the
parts add to the observed change in n between the 2026-06-30 and 2026-09-30 weekly.csv rows. Writes
checks/q3-figures.json. Not wired into pytest: a Q3 10-Q reanchor will move these, and then the card must be rebuilt.
"""
import csv, collections, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
LO, HI = '2026-07-01', '2026-09-30'


def rows(name):
    with open(os.path.join(ROOT, 'data', name)) as f:
        return [r for r in csv.DictReader(f) if r['firm'] == 'MSTR']


def main():
    sats, usd = collections.defaultdict(float), collections.defaultdict(float)
    for r in rows('attribution.csv'):
        if LO <= r['week_end'] <= HI:
            sats[r['action']] += float(r['dn_exact']) * 1e8
            usd[r['action']] += float(r['usd'] or 0)
    units = collections.defaultdict(float)
    for r in rows('actions.csv'):
        if LO <= r['week_end'] <= HI and r['action'] in ('buy_coin', 'sell_coin'):
            units[r['action']] += float(r['units'])
    n = {r['week_end']: float(r['n']) for r in rows('weekly.csv')}
    observed = (n[HI] - n['2026-06-30']) * 1e8
    trades = sats['buy_coin'] + sats['sell_coin']
    total = sum(sats.values())
    figures = {'strc_retired': round(sats['retire_pref']), 'bitcoin_trades': round(trades), 'total': round(total),
               'price_revaluation': round(sats['price']), 'itm_flip': round(sats['itm_flip']), 'common_issuance': round(sats['issue_common']),
               'carry_dividends_interest': round(sats['carry']), 'residual': round(sats['residual']),
               'observed_dn_sats': round(observed, 2), 'sum_of_parts_sats': round(total, 2),
               'strc_retired_usd_m': round(usd['retire_pref'] / 1e6, 1), 'btc_bought': units['buy_coin'], 'btc_bought_usd_m': round(usd['buy_coin'] / 1e6, 1),
               'btc_sold': units['sell_coin'], 'btc_sold_usd_m': round(usd['sell_coin'] / 1e6, 1)}
    expect = {'strc_retired': 179, 'bitcoin_trades': -43, 'total': 21631, 'price_revaluation': 22411, 'itm_flip': 361,
              'common_issuance': 332, 'carry_dividends_interest': -801, 'residual': -808, 'strc_retired_usd_m': 1379.1,
              'btc_bought': 7218, 'btc_bought_usd_m': 588.1, 'btc_sold': 5553, 'btc_sold_usd_m': 348.5}
    wrong = {k: (figures[k], v) for k, v in expect.items() if figures[k] != v}
    assert abs(observed - total) < 0.01, f'parts {total} != observed {observed}'
    assert figures['total'] != 21633
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'checks', 'q3-figures.json'), 'w') as f:
        json.dump(figures, f, indent=2)
    print(json.dumps(figures, indent=1))
    if wrong:
        raise SystemExit(f'MISMATCH (got, printed on the card or in the copy): {wrong}')
    print('Q3 figures match the card and copy; parts equal the observed change.')


if __name__ == '__main__':
    main()
