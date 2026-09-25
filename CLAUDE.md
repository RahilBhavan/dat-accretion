# dat-accretion

Measures every capital action by Strategy (BTC) and BitMine (ETH) since 2026-06-01 on one ruler,
net coins per share, and shows the price where each program stops adding. Output: a GitHub Pages
site, a one-page memo, and the CSVs plus engine behind them.

Full spec (includes outreach, kept out of this public repo):
`~/projects/networking/projects/dat-accretion-spec.md`. Read it before starting a build step.

## Stack

Python 3.12, stdlib plus numpy. One `python -m dat.<module>` per step. Static site in `site/`.
No database, no framework, no new dependency without asking. Shape copied from `~/projects/spine`.

```
uv venv && uv pip install -e '.[dev]'   # once
.venv/bin/python -m pytest -q           # tests
.venv/bin/python -m dat.snapshot_kpi    # save today's Strategy KPI row
.venv/bin/python check.py               # done check (Step 6)
```

## Rules

- `.claude/rules/method.md`: definitions, the five formulas, schemas. The math source of truth.
- `.claude/rules/data.md`: sources, EDGAR fair access, parsing and provenance rules.
- `.claude/rules/framing.md`: page and memo language. Facts, never verdicts.

## Build plan

Run a step with `/build-step <n>`. One branch and one PR per step.

| Step | Branch | Work | Acceptance check |
|---|---|---|---|
| 0 | step-0-kpi-snapshot | snapshot_kpi.py + snapshot.yml; rebuild netSatsPerShare; BMNP terms | cron row lands on `data`; rebuild within 0.5% of API |
| 1 | step-1-parse-mstr | Strategy 8-Ks → actions.csv | each week's rolled BTC equals the 8-K's stated holdings exactly |
| 2 | step-2-balances | 10-Q anchors rolled forward; prices.csv | R roll within disclosure rounding from 8/02 (method.md); every week has m and q for STRC |
| 3 | step-3-parse-bmnr | BitMine rows, balances, weekly m and q (no staking carry; S estimated between filings) | rolled ETH within 0.1% of strategicethreserve.xyz at its snapshot date (data.md) |
| 4 | step-4-engine | five formulas, exact recompute, attribution + residual | pytest incl. $3.895M STRC case; attribution + residual = observed Δn |
| 5 | step-5-site | break-even map and attribution bars | 375px wide, no horizontal scroll; every dot links to its filing |
| 6 | step-6-memo-check | memo, methodology, check.py | `python check.py` exits 0 against live API |

Step 0 gate: if the rebuild misses 0.5% after an hour, anchor levels to the API snapshot and
attribute changes only. Step 4 overrun: ship first-order values, labeled as such.

## Git

- `main` is protected: changes land by squash-merged PR with CI green. Branch names as above.
- The PR body pastes the acceptance check's real output.
- `data` branch belongs to the snapshot bot. Append-only commits, never force-push: the KPI API
  keeps no history, so a lost row is lost for good.
- Nothing about contacts or outreach goes in this repo. Drafts go in `private/` (gitignored).
