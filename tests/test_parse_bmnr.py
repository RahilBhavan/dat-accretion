import pytest
from decimal import Decimal
from dat.parse_mstr import blocks
from dat.parse_bmnr import parse, build, check, dividends, ser_bmnr, Skip

# Snippets reproduce BitMine's weekly EX-99.1 prose (8-K 0001493152-26-043486 and earlier releases).
F = {'accession': '0000000000-26-000001', 'filed': '2026-09-21'}
URL = 'https://example/ex99-1.htm'


def p(*ts):
    return ''.join(f'<p>{t}</p>' for t in ts)


HOLD = ('As of September 20, 2026 at 9:00pm ET, the Company’s crypto holdings are comprised of 5,983,940 ETH at $2,688 per '
        'ETH (per Coinbase), 212 Bitcoin (BTC), $180 million stake in Beast Industries, $105 million stake in Eightco '
        'Holdings (NASDAQ: ORBS) (“moonshots”) and total cash &amp; marketable securities of $714 million. Bitmine’s ETH '
        'holdings are 4.96% of the ETH supply.')
ACQ = '“Over the past week, we acquired 27,562 ETH. Bitmine has bought ETH every week,” stated Lee.'
STAKE = ('As of September 20, 2026, Bitmine total staked ETH stands at 5,067,309 ($13.6 billion at $2,688 per ETH). '
         '“The projected ETH staking reward is $365 million on an annualized basis (using 2.62% 7-day BMNR yield),” stated Lee.')
YIELD = '“Bitmine’s own staking operations generated a 7-day yield of 2.62% (annualized),” continued Lee.'
BUY = ('“Bitmine repurchased approximately 5.5 million shares of common stock in the past week at an average price of '
       '$15.6156. We view the purchase of our common shares as accretive,” stated Lee. Since July 1, 2026, Bitmine has '
       'repurchased 5.5 million shares of common stock under the previously authorized $4 billion share repurchase program.')
PREF = ('On June 10, Bitmine closed its offering (the “offering”) registered under the Securities Act of 1933, as amended, of '
        '3,500,000 shares of 9.50% Series A Perpetual Preferred Stock (the “Series A Preferred Stock”), at a public offering '
        'price of $80.00 per share. The Company received net proceeds from the offering of approximately $273.8 million, '
        'after deducting the underwriting discounts and commissions.')


def test_weekly_release():
    r = parse(p(HOLD, ACQ, STAKE, YIELD, BUY), F, URL)
    assert r['week_end'] == '2026-09-20' and r['coins'] == 5_983_940
    assert r['cash'] == 714_000_000 and r['cash_prec'] == 1_000_000
    assert r['acquired'] == 27_562 and r['staked'] == 5_067_309 and r['yield'] == Decimal('2.62')
    assert r['buyback'] == (5_500_000, Decimal('15.6156'))
    assert r['pref'] == []


def test_early_cash_wording_and_pref_closing():
    hold = HOLD.replace('September 20', 'June 14').replace('cash &amp; marketable securities of $714', 'cash of $446')
    r = parse(p(hold, PREF), F, URL)
    assert r['week_end'] == '2026-06-14' and r['cash'] == 446_000_000
    assert r['pref'] == [('2026-06-10', 3_500_000, 80, Decimal('273.8') * 10 ** 6)]


def test_no_holdings_skips():
    with pytest.raises(Skip):
        parse(p(PREF), F, URL)


@pytest.mark.parametrize('s', [
    'Bitmine repurchased $120 million of common stock in the past week.',
    'Bitmine acquired 5,000 ETH from a treasury merger.',
    'The Company sold 2,000,000 shares of common stock under its at-the-market program.',
    'Bitmine priced a registered direct offering of 10,000,000 shares at $20.00.',
    'Over the past week, we bought 27,562 ETH.',
    'The Company issued 12,000,000 shares of common stock to investors.',
    'The Company redeemed 1,000,000 shares of Series A Preferred Stock.',
    'Bitmine raised $300 million through its equity program.',
    'Over the past week, we added 27,562 ETH.',
    'Bitmine placed 10,000,000 shares with investors for $250 million.',
])
def test_unknown_near_variant_raises(s):
    with pytest.raises(ValueError, match='unknown number'):
        parse(p(HOLD, s), F, URL)


def test_date_before_prior_week_raises():
    with pytest.raises(ValueError, match='not after prior'):
        parse(p(HOLD), F, URL, prev_week='2026-09-20')


DIV_PROSE = p('The initial dividend of $0.316667 per share will be paid on June 22, 2026 to holders of record.',
              'Bitmine declared a cash dividend of $0.1056 on the Company’s 9.50% Series A Perpetual Preferred Stock.',
              'The dividend will be paid on July 10, 2026 to holders of record as of June 30, 2026.')
DIV_TABLE = ('<table><tr><td>Div #</td><td>Record Date</td><td>Payment Date</td><td>Amount Per Share</td></tr>'
             '<tr><td>13</td><td>Tue, Sep 1, 2026</td><td>Fri, Sep 11, 2026</td><td>$0.1847</td></tr></table>')


def test_dividends_prose_and_table():
    got = [(d, a) for d, a, _, _ in dividends(blocks(DIV_PROSE + DIV_TABLE), URL, '2026-06-12')]
    assert got == [('2026-06-22', Decimal('0.316667')), ('2026-07-10', Decimal('0.1056')), ('2026-09-11', Decimal('0.1847'))]


def rel(week, coins, acquired, **kw):
    return dict({'week_end': week, 'coins': Decimal(coins), 'cash': Decimal(10 ** 8), 'cash_prec': Decimal(10 ** 6),
                 'acquired': Decimal(acquired), 'staked': Decimal(5_000_000), 'staked_date': week,
                 'yield': Decimal('2.60'), 'buyback': None, 'pref': []}, **kw)


def test_build_rows():
    prices = [('2026-06-12', 'BMNR', 30.0), ('2026-06-12', 'ETH', 2000.0), ('2026-06-19', 'BMNR', 31.0),
              ('2026-06-19', 'ETH', 2100.0)]
    rels = [({'filed': '2026-06-15'}, URL, rel('2026-06-14', 100, 10, pref=[('2026-06-10', 3_500_000, 80, 273_800_000)])),
            ({'filed': '2026-06-22'}, URL, rel('2026-06-21', 110, 10, buyback=(Decimal(1_000_000), None)))]
    divs = [('2026-06-19', Decimal('0.1847'), 'https://example/div.htm', '2026-06-12')]
    acts, stated, notes, stake = build(rels, divs, prices)
    by = {(a['week_end'], a['ticker']): a for a in acts}
    assert by['2026-06-14', 'ETH']['usd'] == '20000' and by['2026-06-14', 'ETH']['avg_price'] == '2000'
    assert by['2026-06-14', 'ETH']['note'] == 'usd estimated: units × ETH close'
    assert by['2026-06-14', 'BMNP'].get('note', '') == ''
    assert by['2026-06-14', 'BMNP']['units'] == '350000000' and by['2026-06-14', 'BMNP']['usd'] == '273800000'
    assert by['2026-06-21', 'DIV']['usd'] == '-646450' and by['2026-06-21', 'DIV']['filing_url'].endswith('div.htm')
    assert by['2026-06-21', 'BMNR']['usd'] == '31000000' and by['2026-06-21', 'BMNR']['action'] == 'buyback_common'
    assert by['2026-06-21', 'BMNR']['note'] == 'usd estimated: units × BMNR close'
    assert stated[1]['usd_reserve'] == '100000000' and stated[1]['usd_cash'] == ''
    assert any('BMNR close 2026-06-19' in n for n in notes)


def test_ser_bmnr_reads_escaped_page_data():
    html = r'x{\"ticker\":\"BMNR\",\"currentReserve\":5847611,\"logo\":\"a\",\"snapshotDate\":\"$D2026-08-23T00:00:00.000Z\"}'
    assert ser_bmnr(html) == (5_847_611, '2026-08-23')


def test_site_check_at_snapshot_week_and_age():
    parsed = [rel('2026-08-16', 1000, 0), rel('2026-08-23', 1010, 10), rel('2026-08-30', 1020, 10)]
    assert check(parsed, {}, site=(Decimal(1010), '2026-08-23')) == 0
    assert check(parsed, {}, site=(Decimal(1020), '2026-08-23')) == 1  # 0.99% off
    old = [rel('2026-08-16', 1000, 0)] + [rel(f'2026-10-{d:02d}', 1000, 0) for d in (4, 11)]
    assert check(old, {}, site=(Decimal(1000), '2026-08-16')) == 1  # 56 days stale


def test_no_staking_carry_rows():
    # data.md staking decision (2026-09-25, revised): "acquired" already matches the stated change; estimate is print-only
    prices = [('2026-06-12', 'BMNR', 30.0), ('2026-06-12', 'ETH', 2000.0)]
    acts, _, _, stake = build([({'filed': '2026-06-15'}, URL, rel('2026-06-14', 100, 10))], [], prices)
    assert not any(a['ticker'] == 'STAKE_EST' or a['action'] == 'carry' for a in acts)
    assert stake['2026-06-14'] == pytest.approx(Decimal(5_000_000) * Decimal('0.026') * 7 / 365)


@pytest.mark.parametrize('s', ['Bitmine received $300 million from an equity financing.',
                               'This week our ETH holdings grew by 27,562 ETH.'])
def test_holdings_change_without_acquired_raises(s):
    week1 = parse(p(HOLD.replace('September 20', 'September 13').replace('5,983,940', '5,956,378')), F, URL)
    week2 = parse(p(HOLD, s), F, URL, prev_week='2026-09-13')
    assert week2['acquired'] is None
    prices = [('2026-09-11', 'BMNR', 25.0), ('2026-09-11', 'ETH', 2500.0), ('2026-09-18', 'BMNR', 26.0),
              ('2026-09-18', 'ETH', 2600.0)]
    with pytest.raises(ValueError, match='no .we acquired N ETH. sentence'):
        build([({'filed': '2026-09-14'}, URL, week1), ({'filed': '2026-09-21'}, URL, week2)], [], prices)
