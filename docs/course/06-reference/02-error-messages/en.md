# Error Messages and What They Mean

> Every `raise` and non-zero exit in the pipeline, what trips it, and what to do next.

**Type:** Reference
**Files:** `dat/edgar.py`, `dat/snapshot_kpi.py`, `dat/prices.py`, `dat/parse_mstr.py`, `dat/parse_bmnr.py`, `dat/parse_sbet.py`, `dat/balances.py`, `dat/engine.py`, `dat/memo.py`, `dat/refresh.py`, `check.py`
**Prerequisites:** None
**Time:** ~25 minutes

## How to Read This

The project fails loudly by rule: "No synthetic fallback data. If a source fails, fail loudly" (`.claude/rules/data.md`, decision S2), and parsers read tables by row label, so "An unknown label raises; never skip a row silently" (decision S1). Most errors below are that rule doing its job: a filing said something the code has not seen, and a person has to read the filing and extend the parser.

Messages are shown as their f-string pattern; `{where}` is `"<accession> (<url>)"`, the filing that tripped it. Each module's table ends with its non-zero exit codes, which print a line instead of raising.

Three errors reproduced offline from the repo root:

```
.venv/bin/python -c "from dat.prices import load, close_on_or_before; close_on_or_before(load('data/prices.csv'), 'MSTR', '2026-01-10')"
LookupError: MSTR: no close in [2026-01-03, 2026-01-10]

.venv/bin/python -c "from dat.engine import apply; apply({'C':0,'R':0,'prefs':{}}, {'action':'disclosure','usd':'1','units':'0'})"
ValueError: unknown action disclosure

.venv/bin/python -c "from dat.snapshot_kpi import positive; positive('mNav', '1.19')"
ValueError: mNav: expected a finite number > 0, got '1.19'
```

`Skip` is not an error. `parse_mstr` and `parse_bmnr` raise it for a filing with nothing to parse, and `main()` prints a `skip <accession> ...` line and moves on. `parse_sbet` prints `skip <accession> (filed <date>): items <items> (no capital item)` for 8-Ks without a capital item (decision L9). `dat/build_site.py` raises nothing of its own; a missing or invalid `check.json` prints a warning and shows "not yet run".

## dat.edgar

| message | trigger | what to do |
|---|---|---|
| `Provide an identifying SEC User-Agent containing your contact email` | `SECClient` built with a user agent lacking `@` | Pass a UA with a contact address (decision O7). |
| `SEC response exceeded the 25 MB local limit` | a document over 25 MB | Check the URL points at a filing document, not an archive. |
| `SEC access failed; no synthetic substitute: {url}: {exc}` | an HTTP error other than 429/503, a 429/503 after three retries (5, 15, 45 s), a URL error or timeout | Rerun later for 429/503 (decision O6); for 404, check the URL. A `EDGAR {code} on {url}; retry in {wait}s` line precedes each retry. |

## dat.snapshot_kpi

| message | trigger | what to do |
|---|---|---|
| `{name}: expected a finite number > 0, got {v!r}` | a KPI field missing, zero, a string, a bool, NaN | The API changed shape. Nothing is written; inspect the payload before editing `row()`. `check.py` uses the same guard. |

## dat.prices

| message | trigger | what to do |
|---|---|---|
| `{ticker}: no close in [{lo}, {date}]` | `close_on_or_before` finds no close in the 7 days up to `date` | Rerun `python -m dat.prices`; if it persists, the ticker stopped trading or Yahoo dropped it. |
| `{t}: no rows` (SystemExit) | `main()` fetched nothing for a ticker | Check the ticker and the feed; nothing is backfilled. |

## dat.parse_mstr

| message | trigger | what to do |
|---|---|---|
| `not a number: {cell!r}` | a table cell that is not a number, `-` or `(n)` | Read the cell in the filing; extend `num()` only for a real new format. |
| `{where}: trade table under unrecognized heading {heading!r}` | an ATM or repurchase table under a new section heading | Add the heading to the section map (test: "Share Repurchase Update"). |
| `{where}: unknown column {h!r}` / `unknown BTC column {h!r}` | a new column header | Map it by label; never by position. |
| `{where}: unknown security row {r!r}` | a ticker row that is not MSTR or a known preferred, or a row that does not fit the header | Add the new security to `PREFS` with its terms. |
| `{where}: unknown label {r[0]!r}` | any other unknown row label (test: "Class B Common Stock") | Read the row and decide where it belongs. |
| `{where}: no Security header` | a security table without its header row | Check the table layout in the filing. |
| `{where}: ATM section has no table and no "did not sell" sentence` | an ATM section with neither | New wording; read it and add the phrase. |
| `{where}: repurchase section has no table and no "did not purchase" sentence` | same, for repurchases | Same. |
| `{where}: STRE sale is EUR; ...` / `STRE retirement is EUR; no USD rate parser for it, add one from this filing` | any STRE trade (decision S8) | Add a rate parser from the filing that states the rate. |
| `{where}: {t} notional {n}M != {shares} x ${STATED_AMOUNT}` | stated notional differs from shares × $100 by more than $0.05M | Read the table; a preferred with another stated amount needs its own entry. |
| `{where}: BTC row {r!r} does not fit header {header!r}` | BTC table row length differs from the header | Check for merged cells in the filing. |
| `{where}: BTC section has no holdings table or holdings sentence` / `BTC holdings without an as-of date` | BTC section lacks a dated holdings figure | Read the section; add the new holdings wording. |
| `{where}: hypothetical or negated USD Reserve flow ({h!r}) in {s!r}` | "may use up to", "did not use" before a reserve flow | Confirm no flow happened; the parser will not guess (decision S11). |
| `{where}: unknown USD Reserve flow: ...` (four variants) | a "USD Reserve" mention outside a known phrase, a `$` amount no phrase consumes, an "increase the USD Reserve" clause without its own amount, or "the remaining ... proceeds" | Read the sentence and add the exact phrase with its amount. |
| `{where}: {sections} section(s) but no BTC Update section` | an ATM or repurchase section without a BTC section | Trades need a holdings date; read the filing. |
| `{where}: USD balance dated {dates} matches no BTC holdings date` | a reserve balance on a date with no holdings | Check the dates in the filing. |
| `duplicate stated week_end: {weeks}` | two 8-Ks state the same week (for example an 8-K/A) | Decide which filing wins and document it. |
| exit 1 | a week's rolled BTC differs from the 8-K's stated holdings (`MISMATCH`) and is not in `KNOWN_FILING_GAPS` | Find the missed trade; decision S3 allows only the two documented 1-BTC gaps. |

## dat.parse_bmnr

| message | trigger | what to do |
|---|---|---|
| `{where}: unknown number {n!r} near repurchase/offering/acquired/sale: {s!r}` | a number in a capital sentence no known phrase consumes | Read it; add a phrase to `KNOWN` or parse it as a flow. |
| `{where}: conflicting {what}: {vals}` | two different values for one figure in a release (holdings, acquired ETH, yield, buyback average) | Read the release; one may be a prior-week figure. |
| `{where}: erratum expects as-of {stated}, release says {as_of}` | a `KNOWN_DATE_ERRATA` release no longer says the date it was listed for | Recheck the erratum (decision B7). |
| `{where}: as-of {as_of} not after prior release week {prev}` | a release dated on or before the prior one | Look for a misdated release; add an erratum with evidence. |
| `{where}: offering closed without net proceeds` | a BMNP closing sentence with no net proceeds | Find the net figure in the filing. |
| `{acc} ({url}): ETH holdings changed {a} -> {b} but no 'we acquired N ETH' sentence; unknown source of the change` | holdings moved and no purchase was parsed (decision B8) | Read the release for the source. |
| `BMNP dividend paid {d}: conflicting per-share amounts {paid}` | two per-share amounts for one payment date | Read both declarations. |
| `{t}: no close on {date} (BMNR price date for week {week})` | ETH or BMNR close missing on the BMNR price date | Rerun `dat.prices`. |
| `{SER_URL}: no {ticker} currentReserve/snapshotDate in page data` | strategicethreserve.xyz changed its page | Update the regex in `ser()`. |
| exit 1 | rolled ETH more than 0.1% off the site, or the site snapshot over 42 days before the last week | Compare the printed dates (decision B9). |

## dat.parse_sbet

| message | trigger | what to do |
|---|---|---|
| `{where}: unknown number {n!r} near holdings/repurchase/offering/purchase: {s!r}` | as in parse_bmnr; applies only to capital-item 8-Ks | Add the phrase or parse the flow. |
| `{where}: balance sheet Cash row without an "(In thousands" heading` | a Cash row whose unit is unknown | Confirm the unit in the filing. |
| `{where}: conflicting ETH holdings for {d}: {a} vs {b}` / `{d}: ETH holdings {a} ({src}) vs {b} ({url})` | two figures for one date, within or across documents | Read both. |
| `{where}: {d} parts {ps} sum to {sum}, stated total {total}` | native + LsETH + weETH differs from the total (decision L3) | Read the footnote. |
| `{where}: undated total "{text}" matches no dated total` | "bringing total ETH holdings to N" with no dated match | Find the date for N. |
| `{where}: registered direct offering without a price or closing date` | an offering sentence missing its terms | Find the price and closing date. |
| `{acc}: {k} summary of {u} has no detailed statement in the filing` | a headline figure with no detailed sentence behind it | Read the full filing. |
| `{url}: equity row {label!r} has {n} values, expected {k} {cols}` / `unknown equity statement row {label!r} ...` / `equity statement section {start} .. {end} not found` | the 10-Q equity statement changed | Read the statement; add the row. |
| `{what} dated {d} is after the last stated holdings date {last}: no row to hold it` | an action after SharpLink's last filed holdings date | Wait for a filing that states holdings, or decide with the user. |
| `10-Q issue on {date}: {a} shares, 8-K says {b}` | 10-Q and 8-K disagree on shares issued | Read both. |
| `{url}: quarterly period end not found` | a 10-Q without "For the quarterly period ended" | Read the cover. |
| exit 1 | stated ETH more than 0.1% off the site at its snapshot date, or the snapshot over 42 days before SharpLink's last filed date (decision L10) | Compare the printed dates. |

## dat.balances

| message | trigger | what to do |
|---|---|---|
| `{t}: no close on {date} (MSTR / BMNR / SBET price date for ...)` (four sites) | a STRC, BTC, ETH or other close missing on the week's price date | Rerun `dat.prices`. |
| `buyback in week {w}, which holds the 2026-07-09 anchor: cannot tell if it is before or after the cover count; split the week by trade date before rolling` | a BitMine buyback in the anchor week | Split the week by trade date (decision B3). |
| `BMNR {w}: no staking estimate in staking.csv (release gives no staked ETH or yield); the S bias cannot be computed` | a BitMine week without an `eth_est` | Read the release; the memo footnote needs it (decision M5). |
| exit 1 | an R check fails (`reserve check FAILED: [weeks]`), a week lacks m or q, or the STRC notional check fails | Read the printed line for the week (decision S4). |

## dat.engine

| message | trigger | what to do |
|---|---|---|
| `unknown action {act}` | an actions.csv `action` outside the enum | Fix the parser row; the enum is in method.md. |
| exit 1 | rows do not sum to observed Δn (`identity FAILED`) or rebuilt n differs from weekly.csv | Rerun `dat.balances`; then debug `attribute()`. |

## dat.memo

| message | trigger | what to do |
|---|---|---|
| `BitMine weeks {weeks} have no S bias: rerun dat.balances` | a new BitMine week without a bias | Rerun the pipeline in order. |
| `BitMine m x (1 - that week's S bias) is not above q in weeks {bad}: rewrite the footnote` | removing the share bias moves a week across the line (decision M5) | The memo's footnote no longer holds; rewrite it from the data. |

## dat.refresh

| message | trigger | what to do |
|---|---|---|
| `{name} exited {code}: refresh stopped` (SystemExit) | a step returned non-zero | Read that step's output above the line. |
| exit 2 | a 10-Q or 10-K for a period after the anchors (`reanchor needed: ...`) | Reanchor by hand (decision O4). |

## check.py

`check.py` catches every exception inside a check and records it as a failed check, `error: {Type}: {message}` (decision A5). A crash or SIGTERM still writes `did not finish (crash or signal)`. It exits 1 unless every check passes.

## Exercises

1. Run `.venv/bin/python -m pytest -q -k "raises"` (it selects 44 of 137 tests) and match five of them to rows on this page.
2. In `tests/test_parse_mstr.py`, `test_hypothetical_or_negated_reserve_flow_raises` feeds `parse()` the sentence "Strategy may use up to $50.0 million of the USD Reserve to pay future dividends." Predict the message from the tables above, then write a third sentence of your own that should raise the same error and add it to the test's parameter list.
3. Delete the 2026-09-20 row from a copy of `data/staking.csv` in a scratch data directory, run `.venv/bin/python -c "from dat.balances import bmnr_s_bias; print(bmnr_s_bias('<dir>', '2026-09-20'))"`, and find the message above. The directory needs `balances.csv`, `prices.csv` and `staking.csv`.
