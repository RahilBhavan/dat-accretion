import pytest
from dat.prices import yahoo_rows, gecko_rows, close_on_or_before

# Real-shaped: STRC chart timestamps are 09:30 New York; the third close is null.
YAHOO = {'chart': {'result': [{
    'meta': {'symbol': 'STRC', 'exchangeTimezoneName': 'America/New_York', 'gmtoffset': -14400},
    'timestamp': [1779802200, 1779888600, 1779975000],
    'indicators': {'quote': [{'close': [99.47000122070312, 99.16999816894531, None]}],
                   'adjclose': [{'adjclose': [98.0, 98.0, 98.0]}]}}], 'error': None}}

# Daily points at 00:00 UTC, plus a live intraday point for the unfinished day.
GECKO = {'prices': [[1779753600000, 77258.39], [1779840000000, 75851.10],
                    [1779926400000, 74339.61], [1779960000000, 74100.00]]}


def test_yahoo_rows_skip_null_and_use_close():
    assert yahoo_rows(YAHOO, 'STRC') == [('2026-05-26', 'STRC', 99.47000122070312),
                                         ('2026-05-27', 'STRC', 99.16999816894531)]


def test_yahoo_rows_drop_today_until_1630_local():
    import datetime as dt
    ny = dt.timezone(dt.timedelta(hours=-4))
    at = lambda h, m: dt.datetime(2026, 5, 27, h, m, tzinfo=ny)
    assert [r[0] for r in yahoo_rows(YAHOO, 'STRC', at(15, 0))] == ['2026-05-26']
    assert [r[0] for r in yahoo_rows(YAHOO, 'STRC', at(16, 31))] == ['2026-05-26', '2026-05-27']


def test_gecko_rows_midnight_is_prior_day_close():
    # 05-26 00:00 closes 05-25; the 05-28 09:20 live point (day not over) is dropped.
    assert gecko_rows(GECKO, 'BTC') == [('2026-05-25', 'BTC', 77258.39), ('2026-05-26', 'BTC', 75851.10),
                                        ('2026-05-27', 'BTC', 74339.61)]


PRICES = [('2026-06-04', 'MSTR', 150.0), ('2026-06-05', 'MSTR', 151.0), ('2026-06-05', 'STRC', 99.0),
          ('2026-06-07', 'BTC', 70000.0)]


def test_close_on_or_before_weekend_uses_friday():
    assert close_on_or_before(PRICES, 'MSTR', '2026-06-07') == ('2026-06-05', 151.0)
    assert close_on_or_before([{'date': '2026-06-05', 'ticker': 'STRC', 'close': '99.0'}], 'STRC',
                              '2026-06-07') == ('2026-06-05', 99.0)
    assert close_on_or_before(PRICES, 'BTC', '2026-06-07') == ('2026-06-07', 70000.0)


def test_close_on_or_before_raises_past_7_days():
    with pytest.raises(LookupError):
        close_on_or_before(PRICES, 'MSTR', '2026-06-13')
    with pytest.raises(LookupError):
        close_on_or_before(PRICES, 'MSTR', '2026-06-03')
