import csv, re, struct
from dat import x_post

EXPECTED = {'atm_sats': '+332', 'strc_sats': '+179', 'btc_trade_sats': '−43', 'carry_sats': '−801',
            'strc_usd': '$1,379.1M', 'btc_bought': '7,218 BTC / $588.1M', 'btc_sold': '5,553 BTC / $348.5M',
            'returned_sats': '+511'}
FOOTER = 'Source: Strategy 8-Ks, Jul–Sep 2026 · Oct 27'
THREAD = '''1/ Strategy's dividend bill cost shareholders more bitcoin per share in Q3 than every buyback and stock sale added back.

Dividends and interest: −801 sats per share.
Buybacks + stock sales: +511.

2/ From Strategy's Q3 8-Ks:
• Stock sales: +332 sats
• STRC retired below its stated amount ($1,379.1M): +179
• BTC trades (7,218 bought for $588.1M, 5,553 sold for $348.5M), timing vs weekly close: −43
• Dividends and interest: −801

3/ Sats = net BTC per diluted share, Strategy's own definition. BTC's price move is excluded. Every number and filing: https://rahilbhavan.github.io/dat-accretion/
'''


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


def test_thread_is_the_requested_text_exactly():
    assert (x_post.POST / 'thread.md').read_text() == THREAD


def test_thread_is_three_posts_under_280_with_one_caveat_and_sourced_numbers():
    figs, _ = x_post.figures()
    assert x_post.check_thread() == []
    assert x_post.check_text(figs) == []
    assert len(x_post.thread_parts()) == 3


def test_text_check_flags_an_unsourced_number(tmp_path, monkeypatch):
    figs, _ = x_post.figures()
    (tmp_path / 'thread.md').write_text('1/ STRC buybacks added 180 sats.\n')
    (tmp_path / 'alt.txt').write_text('A card.\n')
    monkeypatch.setattr(x_post, 'POST', tmp_path)
    assert x_post.check_text(figs) == ['thread.md: 180 is not a sourced figure']


def card(tmp_path):
    for n in ('Anton-Regular.ttf', 'IBMPlexSans-Regular.ttf', 'IBMPlexSans-SemiBold.ttf', 'IBMPlexSans-Bold.ttf'):
        (tmp_path / n).write_bytes(b'font')
    figs, _ = x_post.figures()
    return figs, x_post.card_html(figs, tmp_path)


def test_card_html_has_title_footer_real_minus_hero_and_both_bars(tmp_path):
    figs, html = card(tmp_path)
    assert f'<p class="source">{FOOTER}</p>' in html
    assert '<h1>DIVIDENDS ATE THE BUYBACKS</h1>' in html
    assert '<span class="num"><span class="minus">\u2212</span>801</span>' in html  # U+2212, not a hyphen-minus
    assert 'sats per share, Q3 dividends + interest' in html
    assert '>+511</span>' in html and '>\u2212801</span>' in html
    strip = lambda h: re.sub(r'base64,[A-Za-z0-9+/=]+', 'base64,', h)  # committed card.html differs only by font bytes
    assert strip((x_post.POST / 'card.html').read_text()) == strip(html)


def test_hero_minus_is_plex_bold_at_anton_digit_cap_height_centered_on_the_digits(tmp_path):
    _, html = card(tmp_path)
    css = re.search(r'\.minus\{font:700 ([\d.]+)px/0 \'Rahil Plex\'.*?top:(-[\d.]+)px', html)
    size, top = float(css.group(1)), float(css.group(2))
    anton_cap, plex_cap, plex_minus_mid = 1761 / 2048, 698 / 1000, (247 + 365) / 2 / 1000  # em, from the font files
    assert abs(size * plex_cap - 84 * anton_cap) < 0.1  # Plex digit cap height = Anton digit cap height at 84px
    assert abs(-top - (84 * anton_cap / 2 - size * plex_minus_mid)) < 0.1  # minus bar centered on the digits
    assert "font-family:'Rahil Plex';font-weight:700;src:url(data:font/ttf;base64," in html


def test_bar_lengths_are_proportional_to_sats(tmp_path):
    figs, html = card(tmp_path)
    assert 'grid-template-columns:801fr 511fr' in html


def test_footer_is_at_least_30px_at_1080_and_18px_in_a_326px_feed(tmp_path):
    _, html = card(tmp_path)
    css = re.search(r'\.source\{font-size:(\d+(?:\.\d+)?)px', html).group(1)
    at_1080, in_feed = float(css) * 3, float(css) * 326 / 360  # authored at 360 CSS px, exported at 3x
    assert at_1080 >= 30 and in_feed >= 18


def test_card_png_is_exactly_1080_square():
    data = (x_post.POST / 'card.png').read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II', data[16:24]) == (1080, 1080)
    assert data[25] == 2  # colour type 2: RGB, no alpha
