import copy, csv, json
import pytest
from dat.snapshot_kpi import row, save, FIELDS

KPI = {'timestamp': '2026-09-25T16:16:00', 'results': {
    'netSatsPerShare': 157712, 'netBtcReserve': 56926929900, 'amplification': 1.248,
    'mNav': 1.1956, 'latestPrice': 83975, 'btcHoldings': '846,000'}}
CHART = {'chart': {'result': [{'meta': {'symbol': 'MSTR', 'regularMarketPrice': 159.18}}]}}
AT = '2026-09-25T21:30:05Z'


def test_row():
    r = row(KPI, CHART, AT)
    assert r == {'fetched_at': AT, 'netSatsPerShare': 157712, 'netBtcReserve': 56926929900,
                 'amplification': 1.248, 'mNav': 1.1956, 'btc_price': 83975, 'mstr_price': 159.18}
    assert list(r) == FIELDS


@pytest.mark.parametrize('bad', [None, 0, '157,712'])
def test_bad_net_sats(bad):
    kpi = copy.deepcopy(KPI)
    if bad is None:
        del kpi['results']['netSatsPerShare']
    else:
        kpi['results']['netSatsPerShare'] = bad
    with pytest.raises(ValueError, match='netSatsPerShare'):
        row(kpi, CHART, AT)


def test_save_appends(tmp_path):
    r = row(KPI, CHART, AT)
    save(tmp_path, r, KPI)
    save(tmp_path, r, KPI)
    with open(tmp_path / 'kpi_snapshots.csv') as f:
        rows = list(csv.reader(f))
    assert rows[0] == FIELDS and len(rows) == 3
    assert json.loads((tmp_path / 'kpi' / '2026-09-25.json').read_text()) == KPI
