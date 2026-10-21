# dat-accretion

Measures every capital action by Strategy, BitMine and SharpLink since June 2026 on one ruler: net
coins per share, using Strategy's own definition applied to all three firms. SharpLink is measured
only on the dates its filings state ETH holdings. For each action it gives the
per-share effect per dollar and the price at which that effect changes sign.

**Live page: [rahilbhavan.github.io/dat-accretion](https://rahilbhavan.github.io/dat-accretion/)**. Memo: `docs/memo.pdf`. Method: `docs/methodology.md`. Done check: `python check.py`. Problems hit while building: `docs/build-notes.md`.

## Results

- 98 capital actions parsed from SEC 8-K and 10-Q filings filed 2026-06-01 to 2026-10-13 (Strategy 49, BitMine 43, SharpLink 6), each linked to its sec.gov filing: 37 share issuances, preferred retirements and buybacks; 34 coin purchases and sales; 27 carry rows (preferred dividends, convertible interest and inferred SharpLink staking).
- Break-even prices for preferred rotations, week ending 2026-10-11: Strategy's STRC rotation adds net sats per share while STRC trades below $119.07 (net mNAV 1.191); BitMine's BMNP rotation adds net ETH per share while BMNP trades above $99.79 (net mNAV 0.998). See `docs/memo.md`.
- SharpLink is measured only on the four dates its filings state ETH holdings; nothing is carried forward between them.
- 170 pytest cases pass. A daily workflow appends Strategy KPI snapshots to the `data` branch. A weekly refresh workflow rebuilds the CSVs, memo and site and squash-merges only when pytest, `check.py` and CI pass; its scheduled runs have not yet completed unattended, so refreshes so far were started manually.

**How it works:** parsers turn filing text into `data/actions.csv`; a numpy engine attributes each action's effect on net coins per share and computes the break-even price (liquidation preference x net mNAV); `dat.memo` and the site builder publish the memo and static page.

**Run the tests:** `uv venv && uv pip install -e '.[dev]' && .venv/bin/python -m pytest -q`

## Docs

- [`docs/overview.md`](docs/overview.md): what the project does and how the pieces fit. Start here.
- [`docs/how-it-was-made.md`](docs/how-it-was-made.md): the build, step by step.
- [`docs/decisions.md`](docs/decisions.md): every decision, why, and the alternative it rules out.
- [`docs/methodology.md`](docs/methodology.md): definitions, formulas and labeled estimates.
- [`docs/build-notes.md`](docs/build-notes.md): problems hit while building.
- [`docs/reader-test.md`](docs/reader-test.md): earlier reader results and the final human-test protocol.
- [`docs/course/`](docs/course/README.md): a 24-lesson course that teaches the project from scratch, with quizzes.

## Layout

- `dat/`: one module per step, run as `python -m dat.<module>`
- `data/`: actions, balances, prices, attribution CSVs. Every action row links to its SEC filing.
- `data` branch: daily Strategy KPI snapshots, appended by the `snapshot` workflow
- `site/`: the static page

## Run

```
uv venv && uv pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/python -m dat.snapshot_kpi
.venv/bin/python -m dat.refresh      # weekly: parse new 8-Ks, rebuild CSVs, memo, site (refresh.yml is scheduled for Tuesdays)
```

Method: [`docs/methodology.md`](docs/methodology.md). Done check: `.venv/bin/python check.py` (live network; writes `data/check.json`).

## Memo

`.venv/bin/python -m dat.memo` writes [`docs/memo.md`](docs/memo.md), `docs/memo.html` and `docs/map.svg`. The PDF is built
locally with Playwright's headless Chromium (refresh.yml builds it with the runner's Chrome):

```
~/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell \
  --headless --disable-gpu --no-pdf-header-footer --print-to-pdf=docs/memo.pdf file://$PWD/docs/memo.html
```

All inputs are public: SEC EDGAR filings, Strategy's KPI API, Yahoo and CoinGecko daily closes.
This project states per-share effects and break-even prices. It makes no judgment on any decision
and gives no forecast or investment view.
