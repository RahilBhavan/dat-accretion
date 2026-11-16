import pytest
from dat import supply_share as ss

BODY = ('<p>Bitmine’s ETH holdings are 4.97% of the ETH supply (of 122.2 million ETH). Next.</p>')
HEAD = '<h1>Bitmine owns 4.97% of the total ETH coin supply of 122.2 million</h1>'


def test_parse_reads_the_filings_own_percentage_and_supply():
    assert ss.parse(HEAD + BODY, 'w') == ('4.97', '122.2')
    assert ss.parse(BODY.replace('4.97%', '4.8%').replace('122.2', '120.7'), 'w') == ('4.8', '120.7')  # headline optional


def test_missing_sentence_or_disagreeing_headline_raises():
    with pytest.raises(ValueError, match='expected one'):
        ss.parse('<p>No share stated.</p>', 'w')
    with pytest.raises(ValueError, match='disagrees'):
        ss.parse(HEAD.replace('4.97', '4.96') + BODY, 'w')


def test_rows_use_stated_weeks_and_never_carry_forward():
    stated = [{'firm': 'BMNR', 'week_end': '2026-11-08', 'filed': '2026-11-09', 'coins': '6070092', 'filing_url': 'u2'},
              {'firm': 'MSTR', 'week_end': '2026-11-08', 'filed': '2026-11-09', 'coins': '1', 'filing_url': 'x'},
              {'firm': 'BMNR', 'week_end': '2026-10-25', 'filed': '2026-10-26', 'coins': '6051933', 'filing_url': 'u1'}]
    docs = {'u1': BODY.replace('4.97', '4.95'), 'u2': HEAD + BODY}
    rs = ss.rows(stated, fetch=docs.__getitem__)
    assert [(r['week_end'], r['stated_pct'], r['computed_pct']) for r in rs] == [('2026-10-25', '4.95', '4.95'),
                                                                               ('2026-11-08', '4.97', '4.97')]
    with pytest.raises(ValueError):
        ss.rows(stated, fetch=lambda u: '<p>nothing</p>')


def test_table_links_every_row_to_its_filing():
    rs = [{'week_end': '2026-11-08', 'filed': '2026-11-09', 'eth_held': '6070092', 'stated_pct': '4.97',
           'supply_million': '122.2', 'computed_pct': '4.97', 'filing_url': 'https://www.sec.gov/x/ex99-1.htm'}]
    assert '| 2026-11-08 | 2026-11-09 | 6,070,092 | 4.97% | 122.2 | 4.97% | [Exhibit 99.1](https://www.sec.gov/x/ex99-1.htm) |' in ss.table(rs)
