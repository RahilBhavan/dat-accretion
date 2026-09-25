import pytest
from dat.parse_mstr import parse, roll, Skip

# Snippets reproduce the structure of Strategy's weekly 8-Ks (italic heading <p>, prose <p>, tables
# with '$' in its own cell and a full-name row under each ticker row).
F = {'accession': '0000000000-26-000001', 'filed': '2026-09-21', 'url': 'https://example/8k.htm'}


def p(t):
    return f'<p><span style="font-style:italic;">{t}</span></p>'


def table(*rows):
    return '<table>' + ''.join('<tr>' + ''.join(f'<td>{c}</td><td></td>' for c in r) + '</tr>' for r in rows) + '</table>'


BTC_BUY = p('BTC Update') + p('On September 21, 2026, Strategy announced updates with respect to its bitcoin holdings:') + table(
    ['During Period September 14, 2026 to September 20, 2026', 'As of September 20, 2026'],
    ['BTC Purchased (1)', 'AggregatePurchase Price (in millions) (2)', 'Average Purchase Price (2)',
     'Aggregate BTC Holdings', 'Aggregate Purchase Price (in billions) (2)', 'Average Purchase Price (2)'],
    ['950', '75.7', '79,670', '846,000', '63.80', '75,416'])

BTC_SELL = p('BTC Update') + table(
    ['During Period July 27, 2026 to August 2, 2026', 'As of August 2, 2026'],
    ['BTC Sold (1)', 'Aggregate Sale Price (in millions) (2)', 'Average Sale Price (2)',
     'Aggregate BTC Holdings', 'Aggregate Purchase Price (in billions) (2)', 'Average Purchase Price (2)'],
    ['1,638', '$', '104.73', '$', '63,957', '842,138', '$', '63.51', '$', '75,419'])

ATM_NONE = p('ATM Update') + p('On September 21, 2026, Strategy Inc ("Strategy") announced that, during the period between '
                               'September 14, 2026 and September 20, 2026, Strategy did not sell any shares under its '
                               'at-the-market offering program.')


def atm_sale(ticker='STRC'):
    return p('ATM Update') + table(
        ['During Period July 27, 2026 to August 2, 2026', 'As of August 2, 2026'],
        ['Security', 'Shares Sold(1)', 'Notional Value (in millions) (2)', 'Net Proceeds (in millions) (3)',
         'Available for Issuance and Sale (in millions)(4)'],
        ['STRF Stock', '-', '$', '-', '$', '-', '$', '1,619.3'],
        ['10.00% Series A Perpetual Strife Preferred Stock'],
        [f'{ticker} Stock', '500,000', '$', '50.0', '$', '49.5', '$', '17,460.8'],
        ['Variable Rate Series A Perpetual Stretch Preferred Stock'],
        ['MSTR Stock', '3,011,361', '$', '-', '$ 290.6 (5)', '$', '22,690.5'],
        ['Class A Common Stock'],
        ['Total', '$', '340.1'])


REPURCHASE = p('Repurchase Program Updates') + p('On September 21, 2026, Strategy announced the following update:') + table(
    ['During Period September 14, 2026 to September 20, 2026'],
    ['Security', 'Shares Repurchased', 'Aggregate Purchase Price (in millions)'],
    ['STRF Stock (1)', '-', '-'], ['10.00% Series A Perpetual Strife Preferred Stock'],
    ['STRC Stock (1)', '1,771,238', '174.0'], ['Variable Rate Series A Perpetual Stretch Preferred Stock'],
    ['STRK Stock (1)', '-', '-'], ['8.00% Series A Perpetual Strike Preferred Stock'],
    ['MSTR Stock (2)', '-', '-'], ['Class A Common Stock'],
    ['Total'], ['1,771,238', '174.0'])

USD = p('USD Reserve and USD Cash Updates') + p(
    'During the period from September 14, 2026 to September 20, 2026, Strategy used $174.0 million of USD Cash to fund '
    'repurchases of STRC Stock and $75.7 million of USD Cash to purchase bitcoin. During the same period, Strategy used '
    '$57.4 million of the USD Reserve to fund the payment of dividends on its preferred stock and interest on its '
    'outstanding indebtedness.') + p(
    'As of September 20, 2026, the balances of the USD Reserve and USD Cash were $5.04 billion and $1.05 billion, respectively.')


def rows(actions):
    return {(a['action'], a['ticker']): a for a in actions}


def test_no_sale_week_with_buy_repurchase_and_reserve():
    actions, stated = parse(p('Item 8.01 Other Events.') + ATM_NONE + BTC_BUY + REPURCHASE + USD, F)
    r = rows(actions)
    assert set(r) == {('buy_coin', 'BTC'), ('retire_pref', 'STRC'), ('carry', 'DIV_INT')}
    buy = r['buy_coin', 'BTC']
    assert (buy['usd'], buy['units'], buy['avg_price']) == ('75700000', '950', '79670')
    strc = r['retire_pref', 'STRC']
    assert (strc['usd'], strc['units'], strc['week_end']) == ('174000000', '177123800', '2026-09-20')
    assert float(strc['avg_price']) == pytest.approx(174.0e6 / 1_771_238)
    carry = r['carry', 'DIV_INT']
    assert (carry['usd'], carry['units'], carry['avg_price']) == ('-57400000', '0', '')
    assert all(a['filing_url'] == F['url'] and a['firm'] == 'MSTR' for a in actions)
    assert stated == [dict(firm='MSTR', week_end='2026-09-20', filed='2026-09-21', filing_url=F['url'],
                           coins='846000', usd_reserve='5040000000', usd_cash='1050000000',
                           reserve_in='', reserve_out='57400000', usd_reserve_prec='10000000', usd_cash_prec='10000000')]


def test_atm_sale_week_and_btc_sale():
    actions, stated = parse(atm_sale() + BTC_SELL + p('Cash Dividend Declaration') +
                            table(['Preferred Stock', 'Ticker', 'Period', 'Cash Dividend Per Share']), F)
    r = rows(actions)
    assert set(r) == {('issue_common', 'MSTR'), ('issue_pref', 'STRC'), ('sell_coin', 'BTC')}
    assert (r['issue_common', 'MSTR']['usd'], r['issue_common', 'MSTR']['units']) == ('290600000', '3011361')
    pref = r['issue_pref', 'STRC']
    assert (pref['usd'], pref['units'], pref['avg_price']) == ('49500000', '50000000', '99')
    sell = r['sell_coin', 'BTC']
    assert (sell['usd'], sell['units'], sell['avg_price'], sell['week_end']) == ('104730000', '1638', '63957', '2026-08-02')
    assert stated[0]['coins'] == '842138' and stated[0]['usd_reserve'] == '' and stated[0]['usd_cash'] == ''


def test_unknown_ticker_raises():
    with pytest.raises(ValueError, match='STRX'):
        parse(atm_sale('STRX') + BTC_SELL, F)
    bad = REPURCHASE.replace('Class A Common Stock', 'Class B Common Stock')
    with pytest.raises(ValueError, match='Class B Common Stock'):
        parse(BTC_BUY + bad, F)


def test_no_section_skips_but_trades_without_btc_raise():
    with pytest.raises(Skip):
        parse(p('Cash Dividend Declaration') + table(['Preferred Stock', 'Ticker', 'Period', 'Cash Dividend Per Share']), F)
    for only in (atm_sale(), REPURCHASE):
        with pytest.raises(ValueError, match='no BTC Update section'):
            parse(only, F)


def test_stre_retirement_raises():
    stre = REPURCHASE.replace('STRK Stock (1)</td><td></td><td>-</td><td></td><td>-', 'STRE Stock (1)</td><td></td><td>1,000</td><td></td><td>0.1')
    assert stre != REPURCHASE
    with pytest.raises(ValueError, match='STRE retirement is EUR'):
        parse(BTC_BUY + stre, F)


def test_trade_table_under_renamed_heading_raises():
    renamed = REPURCHASE.replace('Repurchase Program Updates', 'Share Repurchase Update')
    with pytest.raises(ValueError, match='Share Repurchase Update'):
        parse(BTC_BUY + renamed, F)


def test_roll():
    stated = [{'week_end': '2026-08-02', 'coins': '842138'}, {'week_end': '2026-09-20', 'coins': '846000'}]
    acts = [{'week_end': '2026-08-02', 'action': 'sell_coin', 'units': '1638'},
            {'week_end': '2026-09-20', 'action': 'buy_coin', 'units': '3862'}]
    assert [st for *_, st in roll(acts, stated)] == ['OK', 'OK']
    acts[1]['units'] = '3861'
    assert [st for *_, st in roll(acts, stated, gaps={})] == ['OK', 'MISMATCH']  # undocumented 1 BTC fails
    assert [st for *_, st in roll(acts, stated, gaps={'2026-09-20': 'x'})] == ['OK', 'GAP']
    acts[1]['units'] = '3860'
    assert [st for *_, st in roll(acts, stated, gaps={'2026-09-20': 'x'})] == ['OK', 'MISMATCH']  # gap > 1 BTC fails


def test_dividend_carry_from_every_source():
    footnote = p('(5) $52.4 million in net proceeds from MSTR Stock sales were used to fund dividends on Strategy\'s '
                 'STRC Stock, $132.2 million in net proceeds from MSTR Stock sales were used to fund repurchases of STRC '
                 'Stock, and $149.1 million in net proceeds from MSTR Stock sales were used to increase the USD Reserve.')
    btc_note = p('(1) $52.4 million in proceeds from the bitcoin sales were used to fund dividends on Strategy\'s preferred '
                 'stock and $52.3 million in proceeds from the bitcoin sales were used to fund repurchases of STRC Stock.')
    reserve = p('During the same period, Strategy used $57.4 million of the USD Reserve to fund the payment of '
                'dividends on its preferred stock and interest on its outstanding indebtedness.')
    actions, _ = parse(atm_sale() + footnote + BTC_SELL + btc_note + p('USD Reserve and USD Cash Updates') + reserve, F)
    carry = sorted(a['usd'] for a in actions if a['action'] == 'carry')
    assert carry == ['-52400000', '-52400000', '-57400000']  # two funding sentences, equal amounts -> two rows
    assert all(a['ticker'] == 'DIV_INT' and a['units'] == '0' for a in actions if a['action'] == 'carry')


def test_reserve_in_and_precision():
    note = p('(5) $250.0 million in proceeds from MSTR Stock sales were used to increase the USD Reserve, $28.9 million '
             'in proceeds from MSTR Stock sales were used to fund repurchases of STRC Stock, and $149.1 million in net '
             'proceeds from MSTR Stock sales were used to increase the USD Reserve (defined below).')
    cap = p('On June 29, 2026, Strategy announced a BTC Monetization Program pursuant to which Strategy may sell bitcoin '
            'from time to time, including for the purpose of generating up to $1.25 billion of additional proceeds to fund '
            'the USD Reserve.') + p('to generate up to $1.25 billion of additional proceeds to fund the USD Reserve;')
    bal = p('As of August 2, 2026, the balance of the USD Reserve is $4.0 billion.')
    _, stated = parse(atm_sale() + note + cap + BTC_SELL + bal, F)
    s = stated[0]
    assert (s['reserve_in'], s['reserve_out'], s['usd_reserve'], s['usd_reserve_prec'], s['usd_cash_prec']) == \
        ('399100000', '', '4000000000', '100000000', '')


def test_unknown_reserve_flow_raises():
    for t in ('$75.0 million in net proceeds from MSTR Stock sales were added to the USD Reserve.',
              '$75.0 million of the proceeds was used to fund the USD Reserve.'):
        with pytest.raises(ValueError, match='unknown USD Reserve flow'):
            parse(BTC_SELL + p(t), F)


def test_dividend_footnote_repeated_in_reserve_paragraph_counts_once():
    note = p('(4) $57.4 million in net proceeds from MSTR Stock sales were used to fund dividends on Strategy\'s STRC Stock.')
    reserve = p('During the same period, Strategy used $57.4 million of the USD Reserve to fund the payment of '
                'dividends on its preferred stock.')
    actions, _ = parse(note + BTC_SELL + p('USD Reserve and USD Cash Updates') + reserve, F)
    assert [a['usd'] for a in actions if a['action'] == 'carry'] == ['-57400000']


@pytest.mark.parametrize('t', [
    'During the period, Strategy withdrew $40.0 million from the USD Reserve to purchase bitcoin.',
    'The USD Reserve was used to pay $40.0 million of dividends.',
    'Strategy drew down the USD Reserve by $40.0 million.',
    'Strategy drew down $50.0 million of its USD Reserve.',
    'Strategy withdrew $50.0 million out of the USD Reserve.',
    'Dividends of $50.0 million were paid out of the USD Reserve.',
    'Strategy reduced the USD Reserve by $50.0 million.',
    'Strategy applied $50.0 million of USD Reserve funds to dividends.',
    'Net proceeds of $100.0 million were used to buy bitcoin and the rest were used to increase the USD Reserve.',
    '$100.0 million in net proceeds from MSTR Stock sales were used to fund repurchases of STRC Stock and used to '
    'increase the USD Reserve.',
    'The remaining proceeds were used to increase the USD Reserve.',
    'Strategy withdrew $50.0 million from the USD Reserve to fund dividends.',
    '$50.0 million in net proceeds from the STRC ATM were used to increase the USD Cash liquidity account and the USD Reserve.',
    '$50.0 million in net proceeds from the STRC ATM were added to Strategy’s cash balance, including the USD Reserve.',
])
def test_unknown_reserve_outflow_raises(t):
    with pytest.raises(ValueError, match='unknown USD Reserve flow'):
        parse(BTC_SELL + p(t), F)


def test_remaining_clause_does_not_borrow_amount():
    # 8/24 8-K sentence shape, with USD Reserve in place of USD Cash
    t = ('(4) $136.4 million in net proceeds from MSTR Stock sales were used to fund repurchases of STRC Stock under the '
         'Digital Credit Securities Repurchase Program (defined below), $300.0 million in net proceeds from MSTR Stock '
         'sales were used to increase the USD Cash liquidity account, and the remaining net proceeds from MSTR Stock '
         'sales were used to increase the USD Reserve.')
    with pytest.raises(ValueError, match='USD Reserve'):
        parse(BTC_SELL + p(t), F)


def test_sentence_split_keeps_numbers_and_abbreviations():
    from dat.parse_mstr import sentences
    assert sentences('The U.S. balance of the USD Reserve is $5.04 billion. Next sentence.') == \
        ['The U.S. balance of the USD Reserve is $5.04 billion.', 'Next sentence.']


@pytest.mark.parametrize('t', ['Strategy may use up to $50.0 million of the USD Reserve to pay future dividends.',
                               'The Company did not use $50.0 million of the USD Reserve to fund dividends.'])
def test_hypothetical_or_negated_reserve_flow_raises(t):
    with pytest.raises(ValueError, match='hypothetical or negated'):
        parse(BTC_SELL + p(t), F)
