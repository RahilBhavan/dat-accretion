import pytest
from decimal import Decimal
from dat.parse_sbet import parse, build, check, equity, check_summaries

# Snippets reproduce SharpLink's filings verbatim: 8-K 0001493152-26-031202 (filed 2026-06-30, Item 8.01 and
# ex99-1), 8-K 0001493152-26-029804 (filed 2026-06-23), ex99-1 of 0001493152-26-036741 (filed 2026-08-10).
F = {'accession': '0001493152-26-031202', 'filed': '2026-06-30'}
URL = 'https://example/form8-k.htm'


def p(*ts):
    return ''.join(f'<p>{t}</p>' for t in ts)


REPO = ('During the period from June 24, 2026 through June 26, 2026, the Company repurchased 2,132,773 shares of Common '
        'Stock at an average purchase price of $4.69 per share.')
BUY = ('During the period from June 24, 2026 through June 26, 2026, the Company acquired 10,000 ETH for an aggregate '
       'purchase price of approximately $16.1 million (inclusive of fees and expenses) at a weighted average purchase '
       'price per ETH of $1,611.04 (inclusive of fees and expenses). The purchases were made using the proceeds the '
       'Company received from the Registered Direct as described herein.')
AGG = ('As of June 28, 2026, the Company’s aggregate ETH Holdings were 886,725 of which 632,719 of the total ETH Holdings '
       'are native ETH, 181,299 ETH as-if redeemed from LsETH and 72,707 ETH as-if redeemed from weETH.')
SUMMARY = ('Sharplink, Inc. (Nasdaq: SBET) today announced the purchase of 10,000 ETH at an average price of $1,611 per ETH, '
           'bringing total ETH holdings1 to 886,725. The Company also announced the repurchase of 2,132,773 shares of its '
           'common stock in the open market at an average purchase price of $4.69 per share in connection with its '
           'ongoing stock buyback program.')
DIRECT = ('On June 22, 2026, Sharplink, Inc. (the “Company”) entered into a securities purchase agreement (the “Purchase '
          'Agreement”) with an institutional investor (the “Investor”) to sell in a registered direct offering (the '
          '“Offering”) an aggregate of 10,013,351 shares (the “Shares”) of the Company’s common stock, par value $0.0001 '
          'per share (the “Common Stock”).', 'The price per Share was $7.49, and the gross proceeds from the Offering, before '
          'deducting the placement agent fees and offering expenses, were approximately $75 million.',
          'The Offering closed on June 23, 2026.')
Q2 = ('● Sharplink’s ETH holdings totaled approximately 886,881 ETH1 as of June 30, 2026, and 888,938 ETH2 as of August 3, 2026.',
      '1 Total ETH holdings held as of June 30, 2026, comprised of 632,784 native ETH, 181,321 ETH as-if redeemed from LsETH '
      'and 72,776 ETH as-if redeemed from weETH, using a conversion date of June 30, 2026.',
      '2 Total ETH holdings held as of August 3, 2026, comprised of 634,255 native ETH, 181,748 ETH as-if redeemed from LsETH '
      'and 72,935 ETH as-if redeemed from weETH, using a conversion date of August 3, 2026.')
BS = ('<p>(In thousands, except share and per share data)</p><table><tr><td>June 30, 2026</td><td>December 31, 2025</td></tr>'
      '<tr><td>Cash</td><td>56,195</td><td>28,539</td></tr></table>')


def test_8k_0630_real_text():
    r = parse(p(REPO, BUY, AGG), F, URL)
    assert r['holdings'] == {'2026-06-28': 886_725} and r['parts']['2026-06-28'] == (632_719, 181_299, 72_707)
    assert r['buys'] == [('2026-06-24', '2026-06-26', 10_000, Decimal('1611.04'))]
    assert r['repos'] == [('2026-06-24', '2026-06-26', 2_132_773, Decimal('4.69'))]
    s = parse(p(SUMMARY) + p(AGG.replace('As of', 'Note: As of')), F, 'https://example/ex99-1.htm')
    assert s['sums'] == {'buy': [10_000], 'repo': [2_132_773], 'direct': []}
    check_summaries([(F, URL, r), (F, 'x', s)])


def test_q2_release_two_dates_and_cash():
    r = parse(p(*Q2) + BS, {'accession': '0001493152-26-036741', 'filed': '2026-08-10'}, URL)
    assert r['holdings'] == {'2026-06-30': 886_881, '2026-08-03': 888_938}
    assert r['cash'] == {'2026-06-30': 56_195_000}


def test_direct_offering():
    r = parse(p(*DIRECT), {'accession': '0001493152-26-029804', 'filed': '2026-06-23'}, URL)
    assert r['direct'] == [('2026-06-23', 10_013_351, Decimal('7.49'))]


@pytest.mark.parametrize('s', [
    'Sharplink repurchased $12 million of common stock in the past week.',
    'The Company sold 2,000,000 shares of common stock under its at-the-market program.',
    'Over the past week, Sharplink bought 5,000 ETH.',
    'Sharplink raised $50 million through a registered direct offering.',
    'The Company’s ETH holdings grew to 890,000 ETH.',
])
def test_unknown_number_raises(s):
    with pytest.raises(ValueError, match='unknown number'):
        parse(p(AGG, s), F, URL)


def test_parts_must_sum_to_total():
    with pytest.raises(ValueError, match='sum to 886725, stated total 886726'):
        parse(p(AGG.replace('886,725', '886,726')), F, URL)


def test_summary_without_detail_raises():
    s = parse(p(SUMMARY) + p(AGG), F, URL)
    with pytest.raises(ValueError, match='no detailed statement'):
        check_summaries([(F, URL, s)])


EQ = ('<table><tr><td>Balance as of March 31, 2026</td></tr>'
      '<tr><td>Issuance of Common Stock sold in private placement June 23, 2026</td><td>-</td><td>-</td><td>-</td><td>-</td>'
      '<td>10,013,351</td><td>1</td><td>73,330</td><td>-</td><td>-</td><td>-</td><td>73,331</td></tr>'
      '<tr><td>Stock repurchased (treasury stock)</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td>'
      '<td>(2,132,773</td><td>)</td><td>(10,022</td><td>)</td><td>-</td><td>(10,022</td><td>)</td></tr>'
      '<tr><td>Balance at June 30, 2026</td></tr></table>')


def test_equity_statement():
    assert equity(EQ, URL, 'March 31, 2026', 'June 30, 2026') == {
        'issue': [('2026-06-23', 10_013_351, 73_331_000)], 'treasury': (2_132_773, 10_022_000)}
    bad = EQ.replace('Stock repurchased (treasury stock)', 'Shares issued in merger')
    with pytest.raises(ValueError, match='unknown equity statement row'):
        equity(bad, URL, 'March 31, 2026', 'June 30, 2026')


def docs():
    f23, f30, f810 = ({'accession': a, 'filed': d} for a, d in (('a-23', '2026-06-23'), ('a-30', '2026-06-30'),
                                                                 ('a-810', '2026-08-10')))
    nav = 'Priced at a premium to the net asset value (“NAV”) of Sharplink’s ETH holdings1 reported as of June 16, 2026 of 875,776 ETH.'
    return [(f23, 'u23', parse(p(*DIRECT, nav), f23, 'u23')), (f30, 'u30', parse(p(REPO, BUY, AGG), f30, 'u30')),
            (f810, 'u810', parse(p(*Q2) + BS, f810, 'u810'))]


PRICES = [(d, 'SBET', 5.0) for d in ('2026-06-16', '2026-06-26', '2026-06-30', '2026-08-03')]


def test_build_rows_per_filed_date():
    eq = {'issue': [('2026-06-23', Decimal(10_013_351), Decimal(73_331_000))], 'treasury': (Decimal(2_132_773), Decimal(10_022_000))}
    acts, stated, notes = build(docs(), eq, '10q', ('2026-03-31', '2026-06-30'), PRICES)
    assert [s['week_end'] for s in stated] == ['2026-06-16', '2026-06-28', '2026-06-30', '2026-08-03']
    assert [s['usd_reserve'] for s in stated] == ['', '', '56195000', '']
    by = {(a['week_end'], a['action']): a for a in acts}
    assert by['2026-06-28', 'issue_common']['usd'] == '73331000' and by['2026-06-28', 'issue_common']['filing_url'] == 'u23'
    assert by['2026-06-28', 'buyback_common']['usd'] == '10022000'
    assert by['2026-06-28', 'buy_coin']['usd'] == '16110400'
    # carry = stated change less stated purchases (inferred staking/LST accrual), per filed date
    assert [(w, by[w, 'carry']['units']) for w in ('2026-06-28', '2026-06-30', '2026-08-03')] == \
        [('2026-06-28', '949'), ('2026-06-30', '156'), ('2026-08-03', '2057')]
    assert all(a['filing_url'] for a in acts)


def test_action_after_last_holdings_date_raises():
    d = docs()
    late = REPO.replace('June 24', 'August 24').replace('June 26', 'August 26')
    d.append(({'accession': 'a-9', 'filed': '2026-09-01'}, 'u9', parse(p(late), {'accession': 'a-9'}, 'u9')))
    with pytest.raises(ValueError, match='after the last stated holdings date'):
        build(d, None, '', None, PRICES)


def test_site_check_staleness_is_against_own_last_filing():
    parsed = [{'week_end': w, 'coins': Decimal(c)} for w, c in (('2026-06-30', 886_881), ('2026-08-03', 888_938))]
    assert check(parsed, [], site=(Decimal(888_938), '2026-08-03')) == 0  # passes however long SharpLink stays silent
    assert check(parsed, [], site=(Decimal(900_000), '2026-08-03')) == 1  # 1.2% off
