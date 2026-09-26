# Data Dictionary

> Every column of every file the pipeline writes, with its unit, its sign rule and a value from the real file.

**Type:** Reference
**Files:** `data/actions.csv`, `data/stated.csv`, `data/balances.csv`, `data/prices.csv`, `data/weekly.csv`, `data/attribution.csv`, `data/staking.csv`, `data/check.json`, `data/kpi_snapshots.csv` (on the `data` branch), `.claude/rules/method.md` (Schemas)
**Prerequisites:** None
**Time:** ~20 minutes

## How to Read This

The schemas in `.claude/rules/method.md` are the source of truth; this page adds units and a real example per column. General rules from that file:

- Dates are ISO (`2026-09-20`). Money is USD. Coins are whole BTC or ETH.
- `firm` is one of `MSTR` (Strategy), `BMNR` (BitMine), `SBET` (SharpLink).
- `week_end` is the "as of" date a filing states holdings for. For SharpLink it is a filed holdings date, not a week (decision L1).
- An empty cell means "not stated" or "does not apply", never zero.

Finance terms used below: an **8-K** is a current-report filing with the SEC; a **10-Q** is a quarterly report. **Preferred** stock pays a fixed dividend and ranks ahead of common; its **notional** (liquidation preference) is the fixed amount per share it is owed, $100 for every preferred here. A **convert** is a bond that can turn into shares at a set **conversion price**.

The files and their sizes, from the repo root:

```
.venv/bin/python -c "
import csv, glob
for f in sorted(glob.glob('data/*.csv')):
    rows = list(csv.DictReader(open(f)))
    print(f'{f:22} {len(rows):4} rows  {\",\".join(rows[0].keys())}')
"
```

```
data/actions.csv         79 rows  firm,week_end,filed,filing_url,action,ticker,usd,units,avg_price,note
data/attribution.csv    198 rows  firm,week_end,action,ticker,usd,m,q,dn_first_order,dn_exact,dn_per_dollar,filing_url
data/balances.csv        39 rows  firm,date,coins,usd_reserve,debt,pref_notional,shares_diluted,source
data/prices.csv         921 rows  date,ticker,close
data/staking.csv         17 rows  week_end,eth_est
data/stated.csv          39 rows  firm,week_end,filed,filing_url,coins,usd_reserve,usd_cash,reserve_in,reserve_out,usd_reserve_prec,usd_cash_prec
data/weekly.csv          39 rows  firm,week_end,price_date,p,s,q,m,n
```

Pipeline order: the parsers write `actions.csv`, `stated.csv` and `staking.csv`; `dat.prices` writes `prices.csv`; `dat.balances` writes `balances.csv` and `weekly.csv`; `dat.engine` writes `attribution.csv`; `check.py` writes `check.json`.

## actions.csv

One row per capital action a filing states. Written by `dat.parse_mstr`, `dat.parse_bmnr` and `dat.parse_sbet` (each replaces only its own firm's rows). 79 rows: 36 MSTR, 37 BMNR, 6 SBET.

| column | type / unit | meaning | example (MSTR, 2026-07-26 STRC row) |
|---|---|---|---|
| firm | text | firm code | `MSTR` |
| week_end | date | holdings date the action belongs to | `2026-07-26` |
| filed | date | filing date on EDGAR | `2026-07-27` |
| filing_url | URL | the filing the row came from; never empty | `https://www.sec.gov/Archives/edgar/data/1050446/000119312526316917/mstr-20260727.htm` |
| action | enum | `issue_common`, `buyback_common`, `issue_pref`, `retire_pref`, `buy_coin`, `sell_coin`, `carry` | `retire_pref` |
| ticker | text | security traded: common MSTR (issue_common), BMNR (buyback_common), SBET (issue_common, buyback_common); preferred STRC, BMNP; coins BTC, ETH; carry rows use DIV_INT (MSTR), DIV (BMNR), STAKE (SBET) | `STRC` |
| usd | USD | cash moved | `25000000` |
| units | shares, notional USD, or coins | shares for common, notional dollars for preferred, coins for coin trades | `28893000` |
| avg_price | USD per unit | price per share or per coin; for preferred, price per $100 share | `86.526148` |
| note | text | blank for filed figures; says what was estimated otherwise | `usd estimated: units × ETH close` (BMNR buy_coin rows) |

Sign rules: for actions, `usd` and `units` are positive magnitudes and the action gives direction. `carry` rows are signed changes: a dividend paid is negative `usd` (MSTR 9/20: `-57400000`), SharpLink's inferred staking is positive `units` (8/03: `2057`). Row counts by action and ticker: 13 `issue_common,MSTR`, 9 `retire_pref,STRC`, 18 `buy_coin,ETH`, 14 `carry,DIV`, 1 `issue_pref,BMNP`.

## stated.csv

Each filing's own aggregates, the targets the rolled figures are checked against. One row per `week_end`. Written by the parsers.

| column | type / unit | meaning | example (MSTR 2026-09-20) |
|---|---|---|---|
| firm, week_end, filed, filing_url | as in actions.csv | the filing that states the figures | `MSTR`, `2026-09-20`, `2026-09-21`, `.../mstr-20260914.htm` |
| coins | BTC or ETH | stated holdings | `846000` |
| usd_reserve | USD | stated USD Reserve (BMNR: cash & marketable securities; SBET: balance-sheet cash, 6/30 only) | `5040000000` |
| usd_cash | USD | stated USD Cash, first disclosed for 2026-08-23 | `1050000000` |
| reserve_in | USD | sum of amounts "used to increase the USD Reserve"; blank when none | blank (8/23: `300000000`) |
| reserve_out | USD | sum of "$X of the USD Reserve to ..." amounts; blank when none | `57400000` |
| usd_reserve_prec | USD | one unit in the last disclosed digit of usd_reserve ($5.04 billion → 10,000,000) | `10000000` |
| usd_cash_prec | USD | same, for usd_cash | `10000000` |

The 2026-06-30 MSTR row has `coins` only: a quarter-end holdings row with no balance stated (decision S6).

## balances.csv

The state vector per firm per holdings date, the inputs to `net()`. Written by `dat.balances`.

| column | type / unit | meaning | example (MSTR 2026-09-20) |
|---|---|---|---|
| firm | text | firm code | `MSTR` |
| date | date | same as stated.csv `week_end` | `2026-09-20` |
| coins | BTC or ETH | C, coins held | `846000` |
| usd_reserve | USD | R, USD Reserve + USD Cash (before 8/23: Reserve alone) | `6090000000` |
| debt | USD | D, notional of out-of-the-money converts at this date's price | `5913659000` |
| pref_notional | USD | F, sum of preferred notional, excluding in-the-money STRK; STRE at 1.147 USD/EUR | `14293581300` |
| shares_diluted | shares | S, fully diluted: basic + awards + in-the-money converts and warrants | `429366277` |
| source | text | the filings used and every label or estimate | `8-K 000119312526396093; 10-Q 6/30 roll` |

For BitMine the `source` text says "S estimated" on weeks where shares come from the cash-based estimate (decision B3). Rows: 18 MSTR, 17 BMNR, 4 SBET.

## prices.csv

Daily closes, long format. Written by `dat.prices`. 921 rows, 2026-05-25 to 2026-09-25.

| column | type / unit | meaning | example |
|---|---|---|---|
| date | date | trading date (stocks, exchange-local) or UTC day (coins) | `2026-05-25` |
| ticker | text | MSTR, STRC, STRK, STRF, STRD, BMNR, BMNP, SBET (Yahoo); BTC, ETH (CoinGecko) | `BTC` |
| close | USD | Yahoo quote close (not adjusted close); coin close for day D is CoinGecko's 00:00 UTC point on D+1 | `77258.39912360838` |

BTC and ETH have 124 rows each (every calendar day); each stock ticker 86 (trading days); BMNP 71 (first close 2026-06-16).

## weekly.csv

Prices and the ruler per holdings date. Written by `dat.balances`.

| column | type / unit | meaning | example (MSTR 2026-09-20) |
|---|---|---|---|
| firm, week_end | as above | | `MSTR`, `2026-09-20` |
| price_date | date | last US trading day on or before week_end | `2026-09-18` |
| p | USD per coin | coin close on price_date | `80873.58287659245` |
| s | USD per share | common close on price_date | `153.9199981689453` |
| q | ratio | the firm's preferred close / 100 (STRC for MSTR, BMNP for BMNR); BMNR issue week `0.8`; blank for SBET and for BMNR before BMNP | `0.9851000213623047` |
| m | ratio | net mNAV, s / (p · n) | `1.217051` |
| n | coins per share | net coins per share, N / S | `0.001563794558` |

## attribution.csv

Each week's change in n split into parts. Written by `dat.engine`. 198 rows; the first date of each firm is the anchor and has none.

| column | type / unit | meaning | example (MSTR 2026-09-20, STRC row) |
|---|---|---|---|
| firm, week_end | as above | | `MSTR`, `2026-09-20` |
| action | enum | actions.csv actions plus `price`, `itm_flip`, `est_issuance` (BMNR only), `residual` | `retire_pref` |
| ticker | text | as in actions.csv; `BMNR` on est_issuance rows; empty for price, itm_flip and residual rows | `STRC` |
| usd | USD | the row's cash; signed for carry; empty for price, itm_flip and residual rows | `174000000` |
| m | ratio | m at the action's price, avg_price / (p · n); common and est_issuance rows only | blank |
| q | ratio | avg_price / 100; preferred rows only | `0.982364` |
| dn_first_order | coins per share | the method.md formula at that m or q (0 for coin trades); blank for carry, price, itm_flip and residual rows | `8.995981459702607e-08` |
| dn_exact | coins per share | n recomputed after the row minus n before it | `8.995982580259701e-08` |
| dn_per_dollar | coins per share per USD | dn_exact / usd; filled for action and est_issuance rows, blank for carry, price, itm_flip and residual rows | `5.170104931183736e-16` |
| filing_url | URL | the action's filing; empty for price, itm_flip, est_issuance and residual | `.../mstr-20260914.htm` |

Order within a week: price, itm_flip, each action in actions.csv order, carry, est_issuance, residual (decision A1). The `dn_exact` column of a week sums to the observed change in n.

## staking.csv

BitMine only. Written by `dat.parse_bmnr`. A diagnostic that sizes the upward bias in BitMine's estimated shares; never booked (decision B2).

| column | type / unit | meaning | example |
|---|---|---|---|
| week_end | date | BitMine release week | `2026-09-20` |
| eth_est | ETH | staked ETH × 7-day yield × 7/365 | `2546.1` |

17 rows. `dat.balances.bmnr_s_bias` reads it; `dat.memo` fails the build if a BitMine week has no entry.

## kpi_snapshots.csv

On the `data` branch, not `main`. One row per daily run of `dat.snapshot_kpi` (decisions P6, P7). The raw payload for each day sits beside it in `data/kpi/<date>.json`.

```
git show origin/data:data/kpi_snapshots.csv
```

```
fetched_at,netSatsPerShare,netBtcReserve,amplification,mNav,btc_price,mstr_price
2026-09-25T16:19:32Z,157730.9538,56961379020,1.2478,1.1994,84015,158.93
2026-09-25T23:58:29Z,157744.0645,56985227760,1.2477,1.1971,84044,158.61
2026-09-26T12:41:03Z,157758.0352,57010658520,1.2476,1.1971,84074,158.61
```

| column | type / unit | meaning |
|---|---|---|
| fetched_at | UTC timestamp | when the run fetched the API |
| netSatsPerShare | sats per share | Strategy's figure (1 BTC = 100,000,000 sats) |
| netBtcReserve | USD | net reserve, N · p |
| amplification | ratio | C / N |
| mNav | ratio | Strategy's net mNAV |
| btc_price | USD | the API's `latestPrice` |
| mstr_price | USD | Yahoo `regularMarketPrice` for MSTR |

Every field must be a finite number above 0, or the run raises before writing.

## check.json

Written by `check.py` into the data directory. `data/check.json` is gitignored on `main`; the daily `snapshot.yml` run commits it to the `data` branch, and `pages.yml` copies it from there before building. `build_site` shows it and treats a missing or invalid file as "not yet run".

| key | type | meaning | example |
|---|---|---|---|
| status | `pass` or `fail` | pass only if at least one check ran and all passed | `pass` |
| run_at | UTC timestamp | end of the run | `2026-09-26T12:41:26Z` (committed copy on `origin/data`) |
| checks | list | one object per check | |
| checks[].name | text | check name | `residual MSTR 2026-08-30` |
| checks[].compared | text | both sides of the comparison and the tolerance | `\|residual\| $10.6M vs 5% of \|observed\| $106.9M = $5.3M or R rounding ±$20.0M: rounding` |
| checks[].ok | bool | this check passed | `true` |

Read the committed copy with `git show origin/data:data/check.json` (needs a fetch of `data`). It has 12 checks. `check.py`'s current `CHECKS` list also adds SharpLink's ETH site check and one report-only residual per SharpLink date after the first.

## Exercises

1. Pick the MSTR 2026-08-23 row in `stated.csv` and confirm that its `usd_reserve` plus `usd_cash` equals `usd_reserve` in `balances.csv` for the same date.
2. For MSTR 2026-09-20, divide `dn_exact` by `usd` on the `retire_pref` row of `attribution.csv` and confirm you get `dn_per_dollar`. Then multiply `dn_exact` by that week's S and p to get the value to common in USD.
3. Write a ten-line script that loads `prices.csv` and prints, for each ticker, the first and last date and the row count. Explain why BTC has more rows than MSTR.
