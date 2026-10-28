import os, struct, pytest
from dat import eth_card
from dat.balances import read

CSV = 'data/eth_per_share.csv'
CARD = 'docs/social/eth-per-share-2026-10-25'


def rows():
    return read(CSV)


def test_every_row_recomputes_from_its_own_inputs():
    for r in rows():
        n = eth_card.net_per_1000(int(r['eth_held']), int(r['cash_securities_usd']), float(r['bmnp_notional_usd']),
                                  float(r['eth_close_usd']), float(r['shares_diluted_est']))
        assert f'{n:.4f}' == r['net_eth_per_1000_shares'], r['week_end']


def test_cited_values_and_figures_of_the_oct_25_release():
    by = {r['week_end']: r for r in rows()}
    prev, last = by['2026-10-18'], by['2026-10-25']
    assert (prev['net_eth_per_1000_shares'], last['net_eth_per_1000_shares']) == ('9.6912', '9.6938')
    assert round(float(last['change_pct']), 2) == 0.03
    assert (last['eth_held'], last['eth_staked'], last['eth_added']) == ('6051933', '5227037', '10452')
    assert (last['buyback_shares'], last['buyback_avg_usd']) == ('2040000', '22.48')
    assert last['filing_url'].endswith('/000149315226048429/ex99-1.htm')
    assert int(last['eth_held']) - int(prev['eth_held']) == int(last['eth_added'])
    assert float(last['s_bias_pct_of_s']) > abs(float(last['change_pct']))  # the "within error" basis


def test_series_agrees_with_weekly_csv_where_both_exist():
    weekly = {r['week_end']: float(r['n']) for r in read('data/weekly.csv') if r['firm'] == 'BMNR'}
    shared = [r for r in rows() if r['week_end'] in weekly]
    assert len(shared) >= 20
    for r in shared:
        assert abs(float(r['net_eth_per_1000_shares']) - 1000 * weekly[r['week_end']]) < 5e-5, r['week_end']


def test_card_is_square_1080_and_labels_every_plotted_week():
    with open(f'{CARD}/card.png', 'rb') as f:
        head = f.read(24)
    assert head[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', head[16:24]) == (1080, 1080)
    html = open(f'{CARD}/card.html').read()
    on_card = [r for r in rows() if r['on_card'] == 'yes']
    assert len(on_card) == eth_card.CARD_WEEKS
    for r in on_card:
        assert f'>{eth_card.md(r["week_end"])}</text>' in html
    assert all(f'>{r["net_eth_per_1000_shares"]}</text>' in html for r in on_card[-2:])  # the two values the title compares
    assert eth_card.AXIS in html and eth_card.LABEL in html and '0.044% a week' in html
    assert '.source{font-size:15px;line-height:1.08;color:#F5F5EF' in html
    assert 'as of Oct 25, 2026, 2:00 PM ET' in html and 'BitMine 8-K ex99-1 plus dat-accretion model' in html


def test_alt_text_quotes_only_values_the_card_labels():
    import json
    on_card = [r for r in rows() if r['on_card'] == 'yes']
    html = open(f'{CARD}/card.html').read()
    alt = open(f'{CARD}/alt.txt').read()
    assert alt.strip() == json.load(open(f'{CARD}/brief.json'))['alt']
    for r in on_card:
        labelled = f'>{r["net_eth_per_1000_shares"]}</text>' in html
        assert (r['net_eth_per_1000_shares'] in alt) == labelled, r['week_end']
    assert eth_card.LABEL in alt and eth_card.AXIS in alt


def test_brief_records_the_bundle_version_and_the_390_check():
    import json
    brief = json.load(open(f'{CARD}/brief.json'))
    assert '390x390' in brief['sizes_checked'] and brief['overflow'] == []
    if os.path.isdir(eth_card.BUNDLE):
        assert brief['system_version'] == open(os.path.join(eth_card.BUNDLE, 'VERSION')).read().strip()


@pytest.mark.skipif(not os.path.isdir(eth_card.BUNDLE), reason='rahil-design bundle not on this machine')
def test_card_html_is_what_the_series_draws():
    import base64
    import sys
    sys.path.insert(0, os.path.join(eth_card.BUNDLE, 'scripts'))
    from chart_theme import T
    fonts = {n: base64.b64encode(open(os.path.join(eth_card.BUNDLE, 'assets/fonts', n), 'rb').read()).decode()
             for n in ('Anton-Regular.ttf', 'IBMPlexSans-Regular.ttf', 'IBMPlexSans-SemiBold.ttf')}
    assert eth_card.card_html(rows()[-eth_card.CARD_WEEKS:], T, fonts) == open(f'{CARD}/card.html').read()
