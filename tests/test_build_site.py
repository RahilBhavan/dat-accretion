import json
import pytest
from dat.build_site import build, bmnr_r_note, excluded_sentence, BMNR_R_NOTE
from dat.parse_bmnr import excluded_holdings


@pytest.fixture(scope='module')
def site():
    return json.loads(json.dumps(build()))  # offline: cached releases only


def test_headline_break_even_is_100_m(site):
    assert {h['firm'] for h in site['headline']} == {'MSTR', 'BMNR', 'SBET'}
    for h in site['headline']:
        latest = max((w for w in site['weeks'] if w['firm'] == h['firm']), key=lambda w: w['week_end'])
        if h['firm'] == 'SBET':  # no preferred: no break-even price, m vs 1 only
            assert h['m'] == latest['m'] and h['break_even'] is None and 'no rotation' in h['sentence']
            assert f"{h['m']:.3f}" in h['sentence'] and '—' not in h['sentence'] + h['close_sentence']
            continue
        assert h['m'] == latest['m'] and h['break_even'] == round(100 * latest['m'], 2)
        assert f"${h['break_even']:.2f}." in h['sentence']


def test_every_map_point_links_to_a_filing(site):
    # app.js mapPoints: q and m present, or SharpLink (no preferred, drawn at q = 1)
    points = [w for w in site['weeks'] if w['m'] is not None and (w['q'] is not None or w['firm'] == 'SBET')]
    assert len(points) >= 30 and sum(w['firm'] == 'SBET' for w in points) == 4
    for w in points:
        assert w['filing_urls'] and all(u.startswith('https://www.sec.gov/') for u in w['filing_urls'])


def test_bars_sum_to_observed(site):
    weeks = [w for w in site['weeks'] if w['value'] is not None]
    assert len(weeks) == len(site['weeks']) - 3  # one anchor week per firm
    for w in weeks:
        assert set(w['value']) == set(site['categories'])
        total = sum(w['value'].values()) + w['price'] + w['itm_flip']
        assert total == pytest.approx(w['observed'], abs=1), (w['firm'], w['week_end'])


def test_deterministic_apart_from_generated_at():
    a, b = build(), build()
    a.pop('generated_at'), b.pop('generated_at')
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# Holdings sentence of BitMine's 2026-09-21 release (0001493152-26-043486, ex99-1), verbatim.
RELEASE_0921 = ('<p>As of September 20, 2026 at 9:00pm ET, the Company\u2019s crypto holdings are comprised of 5,983,940 ETH '
                'at $2,688 per ETH (per Coinbase), 212 Bitcoin (BTC), $180 million stake in Beast Industries, $105 million '
                'stake in Eightco Holdings (NASDAQ: ORBS) (\u201cmoonshots\u201d) and total cash &amp; marketable securities '
                'of $714 million. Bitmine\u2019s ETH holdings are 4.9% of the ETH supply (of 122.1 million ETH).</p>')


def test_excluded_holdings_0921():
    x = excluded_holdings(RELEASE_0921)
    assert x == {'week_end': '2026-09-20', 'btc': 212,
                 'stakes': [('Beast Industries', 180_000_000), ('Eightco Holdings', 105_000_000)]}
    assert excluded_sentence(x) == ("BitMine's 2026-09-20 release lists 212 BTC, a $180 million stake in Beast Industries "
                                    "and a $105 million stake in Eightco Holdings; these are excluded.")


def test_excluded_holdings_missing_is_omitted():
    assert excluded_holdings('<p>No holdings sentence here.</p>') is None
    url = 'https://www.sec.gov/Archives/edgar/data/1829311/000000000000000000/ex99-1.htm'
    note = bmnr_r_note(url, online=False)  # not cached, offline: warn and omit
    assert note == {'text': BMNR_R_NOTE, 'url': None}


def week(site, firm, w):
    return next(x for x in site['weeks'] if x['firm'] == firm and x['week_end'] == w)


def test_dollars_moved_excludes_carry(site):
    # MSTR 9/20: retire STRC $174.0M + buy BTC $75.7M; the $57.4M dividend/interest carry row is not an action.
    assert week(site, 'MSTR', '2026-09-20')['dollars_moved'] == 249_700_000


def test_est_issuance_in_issue_common_and_flagged(site):
    w = week(site, 'BMNR', '2026-09-20')
    assert w['est_issuance'] == pytest.approx(6_583_230, abs=1)
    assert w['value']['issue_common'] == w['est_issuance']  # BitMine files no issuance: all of it is the estimate


@pytest.mark.parametrize('body', ['', 'not json', '[1, 2]'])
def test_bad_check_json_is_not_yet_run(tmp_path, body, capsys):
    from dat.build_site import load_check
    (tmp_path / 'check.json').write_text(body)
    assert load_check(str(tmp_path / 'check.json')) == {'status': 'not yet run'}
    assert 'warning' in capsys.readouterr().err
    assert load_check(str(tmp_path / 'missing.json')) == {'status': 'not yet run'}
