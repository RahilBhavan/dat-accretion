# dat-accretion

Measures every capital action by Strategy, BitMine and SharpLink since June 2026 on one ruler: net
coins per share, using Strategy's own definition applied to all three firms. SharpLink is measured
only on the dates its filings state ETH holdings. For each action it gives the
per-share effect per dollar and the price at which that effect changes sign.

Status: v1 built. Page: https://rahilbhavan.github.io/dat-accretion/. Memo: `docs/memo.pdf`. Method: `docs/methodology.md`. Done check: `python check.py`. Problems hit while building: `docs/build-notes.md`.

## Docs

- [`docs/overview.md`](docs/overview.md): what the project does and how the pieces fit. Start here.
- [`docs/how-it-was-made.md`](docs/how-it-was-made.md): the build, step by step.
- [`docs/decisions.md`](docs/decisions.md): every decision, why, and the alternative it rules out.
- [`docs/methodology.md`](docs/methodology.md): definitions, formulas and labeled estimates.
- [`docs/build-notes.md`](docs/build-notes.md): problems hit while building.

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
.venv/bin/python -m dat.refresh      # weekly: parse new 8-Ks, rebuild CSVs, memo, site (refresh.yml runs it Tuesdays)
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
