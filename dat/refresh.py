"""Weekly refresh (`python -m dat.refresh [data_dir]`): every step's main() in order, then a reanchor alert. stdlib only.

A step that raises or returns non-zero stops the run (no step is skipped). After the pipeline, any 10-Q or 10-K
on EDGAR for a period after the anchors the code uses is printed and the exit code is 2: the data files still
update, but refresh.yml leaves them in an open PR (not merged to main) until a human reanchors by hand (method.md;
no automatic reanchoring).
Exit codes: 0 done; 1 a step failed; 2 done, reanchor needed (refresh.yml tells these apart).
"""
import importlib, os, sys
from dat.balances import read, PREF_ANCHOR_DATE, BMNR_A0

# One line per step; a new firm's parser goes in before dat.balances.
STEPS = ['dat.parse_mstr', 'dat.prices', 'dat.parse_bmnr', 'dat.balances', 'dat.engine', 'dat.memo', 'dat.build_site']
# (firm, CIK, period of the 10-Q the anchors come from: Strategy Q2 10-Q; BitMine 5/31 10-Q, whose cover gives BMNR_A1)
ANCHORS = [('MSTR', 1050446, PREF_ANCHOR_DATE), ('BMNR', 1829311, BMNR_A0[0])]


def last_weeks(data_dir):
    rows = read(os.path.join(data_dir, 'stated.csv'))
    return {f: max(r['week_end'] for r in rows if r['firm'] == f) for f, _, _ in ANCHORS}


def newer(filings, period):
    """Filings whose report period is after `period` (the anchor's)."""
    return [f for f in filings if f['period'] > period]


def reanchor_filings():
    """[(firm, filing)] for each 10-Q/10-K (and /A) filed for a period after that firm's anchor."""
    from dat import edgar
    return [(firm, f) for firm, cik, period in ANCHORS for form in ('10-Q', '10-K')
            for f in newer(edgar.filings(cik, form, since=period), period)]


def main(data_dir='data'):
    before = last_weeks(data_dir)
    for name in STEPS:
        print(f'== {name}', flush=True)
        code = importlib.import_module(name).main(data_dir)
        if code:
            raise SystemExit(f'{name} exited {code}: refresh stopped')
    after = last_weeks(data_dir)
    print('last week: ' + ', '.join(f'{f} {before[f]} -> {after[f]}' for f in after))
    found = reanchor_filings()
    for firm, f in found:
        print(f"reanchor needed: {f['form']} {f['url']} ({firm}, period {f['period']}, filed {f['filed']})")
    return 2 if found else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
