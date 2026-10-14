from dat import figures


def test_figures_build_in_both_themes(tmp_path):
    assert figures.main('data', str(tmp_path)) == 0  # weekparts asserts its parts sum to the observed change
    for name in figures.FIGURES:
        for mode in figures.THEMES:
            svg = (tmp_path / f'{name}-{mode}.svg').read_text()
            assert svg.startswith('<svg') and 'aria-label=' in svg and '—' not in svg


def test_ruler_matches_engine_n(tmp_path):
    svg = figures.ruler('data', 'MSTR', '2026-09-20', figures.THEMES['light'])  # asserts n against weekly.csv
    assert '671,441' in svg and '156,379 sats per share' in svg
