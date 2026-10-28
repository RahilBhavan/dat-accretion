# Q3 reconciliation against Strategy's 10-Q: not possible yet

Checked 2026-10-26 about 08:04 ET (`checks/source-status.json`): EDGAR lists no Strategy 10-Q for the quarter ended
2026-09-30. The newest is the Q2 10-Q filed 2026-08-03 (period 2026-06-30). The Oct 30 results slot is HELD for the same
reason. So there is no reported Q3 figure to compare with, and this note records no differences.

What the card and copy rest on instead: dat-accretion's weekly model, Strategy rows, weeks ending 2026-07-05 to
2026-09-30 (`python social/2026-10-26/q3_figures.py`, output `checks/q3-figures.json`).

| Item | Sats of net BTC per share |
|---|---|
| STRC retired | +179 |
| Bitcoin trades (bought −39, sold −4) | −43 |
| Price revaluation | +22,411 |
| In-the-money flips | +361 |
| Common issuance | +332 |
| Dividends and interest | −801 |
| Residual | −808 |
| **Sum = observed change in n, 2026-06-30 to 2026-09-30** | **+21,631** (21,630.84) |

The sum equals the observed change by construction (attribution plus residual equals observed Δn, method.md). It is not an
independent check, so +21,631 is the model's figure, not a reconciled one. The earlier +21,633 appears nowhere on the
card, in the copy or in this repo's data.

When the 10-Q lands, compare its Q3 fully diluted shares, USD assets, debt-like notes and preferred notional with the
2026-09-30 `balances.csv` row, then rerun `python -m dat.refresh` (exit 2 flags the reanchor). A reanchor moves these
figures: rerun `q3_figures.py`, correct the card and copy, and commit the differences here.
