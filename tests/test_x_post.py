import csv, re, struct
from dat import x_post

EXPECTED = {'atm_sats': '+332', 'strc_sats': '+179', 'btc_trade_sats': '−43', 'carry_sats': '−801',
            'strc_usd': '$1,379.1M', 'btc_bought': '7,218 BTC / $588.1M', 'btc_sold': '5,553 BTC / $348.5M'}
FOOTER = 'Source: Strategy 8-Ks Jul–Sep 2026 · dat-accretion · as of Oct 27, 2026'


def test_figures_are_the_ones_on_the_card():
    figs, _ = x_post.figures()
    assert {k: v for k, v in figs.items() if k != '_values'} == EXPECTED


def test_every_source_row_has_an_8k_accession_and_matches_its_url():
    _, sources = x_post.figures()
    assert sources
    for r in sources:
        assert re.fullmatch(r'0001193125-26-\d{6}', r['accession'])
        assert r['accession'].replace('-', '') in r['filing_url']
        assert x_post.START < r['week_end'] <= x_post.END


def test_committed_sources_csv_is_current():
    _, sources = x_post.figures()
    with open(x_post.POST / 'sources.csv', newline='') as f:
        assert list(csv.DictReader(f)) == sources


def test_thread_is_four_parts_under_280_with_one_caveat_and_sourced_numbers():
    figs, _ = x_post.figures()
    assert x_post.check_thread() == []
    assert x_post.check_text(figs) == []


def test_text_check_flags_an_unsourced_number(tmp_path, monkeypatch):
    figs, _ = x_post.figures()
    (tmp_path / 'thread.md').write_text('## Part 1/4\n\nSTRC buybacks added 180 sats.\n')
    (tmp_path / 'alt.txt').write_text('A card.\n')
    monkeypatch.setattr(x_post, 'POST', tmp_path)
    assert x_post.check_text(figs) == ['thread.md: 180 is not a sourced figure']


def test_card_html_has_the_exact_footer_definition_and_figures(tmp_path):
    for n in ('Anton-Regular.ttf', 'IBMPlexSans-Regular.ttf', 'IBMPlexSans-SemiBold.ttf'):
        (tmp_path / n).write_bytes(b'font')
    figs, _ = x_post.figures()
    html = x_post.card_html(figs, tmp_path)
    assert f'<p class="source">{FOOTER}</p>' in html
    assert "Net sats per share: Strategy's own net bitcoin per share, in satoshis." in html
    for k in ('atm_sats', 'strc_sats', 'btc_trade_sats', 'carry_sats'):
        assert f'{figs[k]} sats' in html
    strip = lambda h: re.sub(r'base64,[A-Za-z0-9+/=]+', 'base64,', h)  # committed card.html differs only by font bytes
    assert strip((x_post.POST / 'card.html').read_text()) == strip(html)


def test_card_png_is_exactly_1080_square():
    data = (x_post.POST / 'card.png').read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II', data[16:24]) == (1080, 1080)
