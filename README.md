# dat-accretion

Measures every capital action by Strategy and BitMine since June 2026 on one ruler: net coins per
share, using Strategy's own definition applied to both firms. For each action it gives the
per-share effect per dollar and the price at which that effect changes sign.

Status: in build. Steps 0-3 done: Strategy and BitMine actions, balances and weekly m and q are in `data/`. Engine, page and memo follow. Problems hit so far: `docs/build-notes.md`.

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
```

All inputs are public: SEC EDGAR filings, Strategy's KPI API, Yahoo and CoinGecko daily closes.
This project states per-share effects and break-even prices. It makes no judgment on any decision
and gives no forecast or investment view.
