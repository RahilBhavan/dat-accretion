"""dat.filings: restyled filing pages keep the filing's words and only change layout."""
import pytest
from dat import filings

URL = 'https://www.sec.gov/Archives/edgar/data/1050446/000119312526413164/mstr-20261005.htm'
ROW = {'firm': 'MSTR', 'week_end': '2026-10-04', 'filed': '2026-10-05', 'filing_url': URL, 'action': 'issue_common',
       'ticker': 'MSTR', 'usd': '15700000', 'units': '92894', 'avg_price': '169.01', 'note': ''}
EIGHT_K = '''<html><head><title>x</title></head><body>
<div style="display:none"><ix:header>0001050446false</ix:header></div>
<p>FORM 8-K</p><p><b>Item 8.01 Other Events.</b></p><p><i>ATM Update</i></p>
<table><tr><td>Security</td><td></td><td>Shares Sold</td><td></td><td colspan="2">Net Proceeds</td></tr>
<tr><td>MSTR Stock</td><td></td><td>92,894</td><td></td><td>$</td><td>15.7</td></tr>
<tr><td>Class A Common Stock</td><td></td><td></td><td></td><td></td><td></td></tr></table>
<p>&#8226;</p><p>$20.91 billion gain on digital assets; and</p>
<p><img src="logo.gif"></p></body></html>'''


def test_tidy_drops_spacer_columns_and_folds_dollar_signs():
    rows = filings.parse('<table><tr><td>A</td><td></td><td>$</td><td>1.5</td><td>)</td></tr></table>')[0][1]
    (row,) = filings.tidy(rows)
    assert [filings.cell_text(c) for c, _ in row] == ['A', '$1.5)']


def test_page_keeps_every_word_and_marks_filed_figures():
    html = filings.page(URL, EIGHT_K, [ROW], [])
    body = html.split('<article', 1)[1]
    assert '0001050446false' not in html  # hidden XBRL header dropped
    assert '<details class="cover"><summary>Cover page</summary>' in body  # cover folds before Item 8.01
    assert '<h3><em>ATM Update</em></h3>' in body
    assert '<mark id="f1">92,894</mark><sup class="snr" data-gen>1</sup>' in body and '$15.7' in body
    assert '<aside class="sn" data-gen><p><span class="snn">1</span><b>Issue common · MSTR</b> 92,894 shares' in body
    assert '<li>• $20.91 billion gain' in body
    assert 'https://www.sec.gov/Archives/edgar/data/1050446/000119312526413164/logo.gif' in body
    assert 'class="sub"' in body  # the security's description row under its figures


def test_word_guard_raises_when_text_is_lost(monkeypatch):
    monkeypatch.setattr(filings, 'inline', lambda runs, marks=(): '')
    with pytest.raises(RuntimeError, match='differs from the filing'):
        filings.page(URL, EIGHT_K, [ROW], [])


def test_page_name_is_accession_and_document():
    assert filings.page_name(URL) == '000119312526413164-mstr-20261005.html'


def test_rows_of_dashes_are_dimmed_not_dropped():
    t = filings.render_table(filings.parse(
        '<table><tr><td>Security</td><td>Sold</td><td>Proceeds</td><td>Available</td></tr>'
        '<tr><td>STRF Stock</td><td>-</td><td>$-</td><td>1,619.3</td></tr>'
        '<tr><td>MSTR Stock</td><td>92,894</td><td>15.7</td><td>18,828.7</td></tr></table>')[0][1], None)
    assert '<tr class="nil"><td>STRF Stock</td>' in t and '<tr><td>MSTR Stock</td>' in t


def test_share_price_split_multiplies_back_exactly():
    w = lambda week, s, p, n: {'firm': 'BMNR', 'week_end': week, 's': str(s), 'p': str(p), 'n': str(n)}
    html = filings.ruler('BMNR', '2026-06-07', [w('2026-05-31', 30, 2000, .004), w('2026-06-07', 33, 2100, .00404)])
    # share +10.0% = ETH +5.0% × ETH per share +1.0% × mNAV (1.1 / (1.05 × 1.01) − 1 = +3.7%)
    assert 'BMNR closed +10.0%: ETH price +5.0%, ETH per share +1.0% and mNAV +3.7%' in html
    assert html.count('<svg') == 2  # a wide drawing and a phone drawing, so labels never shrink below 11px
    assert filings.ruler('BMNR', '2026-05-31', [w('2026-05-31', 30, 2000, .004)]) == ''
