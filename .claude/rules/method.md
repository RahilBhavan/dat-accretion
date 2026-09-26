# Method: the math source of truth

Change this file only when Step 0 shows Strategy's definition differs; the engine then adopts
Strategy's definition and this file changes to match. Tests reference these formulas.

## State (per firm, per week; USD unless noted)

| Symbol | Meaning | Source |
|---|---|---|
| C | coins held (BTC or ETH) | 8-K holdings table |
| R | USD reserve and cash | 8-K USD Reserve / USD Cash lines |
| D | debt notional, incl. out-of-the-money converts at face | 10-Q, rolled forward |
| F | preferred notional (sum of liquidation preferences) | 10-Q and 424B, rolled forward |
| S | diluted shares: common plus in-the-money convert shares | 10-Q, rolled forward |
| p | coin price | CoinGecko daily close |
| s | common share price | Yahoo daily close |
| q | preferred price / notional (STRC $99 on $100 → 0.99) | Yahoo daily close |

N = C + (R − D − F)/p   n = N/S   m = s·S/(p·N) = s/(p·n)

### Strategy's definition (Step 0, confirmed; adopted for both firms)

Source: glossary in the 2026-08-24 FWP,
https://www.sec.gov/Archives/edgar/data/1050446/000119312526363557/d431748dfwp.htm

- R = USD Assets = USD Reserve + USD Cash.
- D = notional of out-of-the-money converts and other debt-like instruments. In-the-money
  converts are not in D; their shares go into S. The $39.8M secured term loan is not deducted.
- F = notional (not trading price, not accrued dividends) of all perpetual preferred, excluding
  in-the-money STRK. STRE (EUR) converts at the Friday 12:30 PM NY rate (API implies ~1.147).
- S = Fully Diluted Shares Outstanding: basic (class A + B) + options + RSUs + PSUs +
  in-the-money converts + in-the-money STRK. (satsPerShare, gross, uses Assumed Diluted:
  every convert converted. Do not mix the two.)
- In the money: MSTR price above conversion price. A convert crossing its price moves notional
  out of D and shares into S; the roll-forward applies this each date, not a fixed list.
- mNAV = s / (N·p / S). Amplification = C·p / (N·p) = BTC reserve / net reserve.

Rebuild pinned in tests/test_balances.py against the 2026-09-25T16:19:32Z snapshot (8-K 9/21 +
Q2 10-Q): netSatsPerShare +0.107%, net reserve −0.003%, amplification +0.004%, mNAV −0.114%.
Gate passed; levels are computed, not anchored to the API. S is ~0.11% below the API's implied
FDSO; gap unexplained, likely post-6/30 award vesting.

BMNP (BitMine q): liquidation preference $100 (Certificate of Designations, ex3-1,
https://www.sec.gov/Archives/edgar/data/1829311/000149315226028140/ex3-1.htm). After BitMine's
first follow-on BMNP sale it floats to max($100, last sale price, 10-day average), which caps q
near 1; recheck each week's ex99-1 for sales. 3.5M shares issued 2026-06-10 at $80 (q = 0.80
at issue). 9.50% cumulative on $100, paid weekly in cash (carry). Not convertible.

## Actions (first order, k = x/(p·S), x = dollars)

| # | action | Δn | adds when |
|---|---|---|---|
| 1 | issue_common | k·(1 − 1/m) | m > 1 |
| 2 | buyback_common | k·(1/m − 1) | m < 1 |
| 3 | issue_pref | k·(1 − 1/q) | q > 1 |
| 4 | retire_pref | k·(1/q − 1) | q < 1 |
| 5 | buy_coin / sell_coin | 0 | neutral on day one |

`carry` rows: preferred dividends and convert interest reduce R; staking adds C (SharpLink only, inferred). They make
attribution sum to the observed change; they are not actions.

Break-even line m = q. Strategy's rotation (1 + 4) adds while m > q: stops when STRC trades
above $100 × m. BitMine's rotation (3 + 2) adds while m < q: stops when BMNP trades below its
liquidation preference × m.

## Attribution (Step 4, decided 2026-09-25)

Observed Δn for a week = n(this week's balances, this week's p and s) − n(last week's). It is
split in this order, each step exact (recompute n after it) and the rest left as residual:
1. `price`: last week's balances revalued at this week's p (the (R − D − F)/p term moves).
2. `itm_flip`: converts or STRK crossing their conversion price at this week's s (D or F ↔ S).
3. Each action row, in actions.csv order, applied at its own price: common at avg_price
   (m_action = avg_price/(p·n)), preferred at q = avg_price/100 (BMNP issue: 80/100), coins at
   their usd. `dn_first_order` uses the table's formulas with that m or q; `dn_exact` is the
   recomputed change.
4. `carry` rows (R or C change).
5. `residual` = observed − sum of the above. The residual test (check.py #4) applies only to
   weeks where R is checked (MSTR from 2026-08-02); other weeks report it, labeled. A week passes
   if |residual| < 5% of |observed Δn| OR |residual| is within that week's R rounding tolerance
   (the Step 2 tolerance, converted to Δn); the output says which. Decided 2026-09-25, extending
   the R rounding decision: a quiet week with rounded disclosures otherwise fails with nothing
   wrong (8/30: −$10.6M on a $107M week, inside ±$20M rounding).
Unit: Δn in coins per share; the page also shows Δn × S × p in USD ("value to common"), using
this week's S and p. First order uses the price q or m; exact uses the cash actually received,
so issue fees show as the gap between them (BMNP issue: q = 0.80 at $80, net $273.8M on $350M
notional, a $6.2M gap).
attribution.csv adds `ticker` and `filing_url` (empty for non-action rows) so each bar and dot
links to its filing.

Rounding note: the 7/26 STRC 8-K states $25.0M, so the data row gives (1/q − 1)·x = $3.893M; the
Bitcoin Magazine figure $3.895M uses $24.998M and is the unit-test anchor below.

## Test anchors (tests/test_engine.py)

1. Bitcoin Magazine STRC week: $24.998M retires $28.893M notional → q = 0.8652, action 4 adds
   (1/q − 1)·x = $3.895M to common. Reproduce to the dollar.
2. Each formula at m = 1 or q = 1 gives zero.
3. Combined rotation at m = q gives zero for both firms.
4. First order within 1% of exact recompute for an action under 1% of market cap.

## Schemas (dates ISO, money USD, coins whole BTC/ETH)

| file | columns |
|---|---|
| actions.csv | firm, week_end, filed, filing_url, action, ticker, usd, units, avg_price, note |
| balances.csv | firm, date, coins, usd_reserve, debt, pref_notional, shares_diluted, source |
| prices.csv | date, ticker, close |
| kpi_snapshots.csv | fetched_at, netSatsPerShare, netBtcReserve, amplification, mNav, btc_price, mstr_price |
| attribution.csv | firm, week_end, action, ticker, usd, m, q, dn_first_order, dn_exact, dn_per_dollar, filing_url |
| stated.csv | firm, week_end, filed, filing_url, coins, usd_reserve, usd_cash, reserve_in, reserve_out, usd_reserve_prec, usd_cash_prec |
| weekly.csv | firm, week_end, price_date, p, s, q, m, n |
| staking.csv | week_end, eth_est (BitMine staking estimate; sizes the S bias, never booked) |

stated.csv holds each 8-K's own aggregates, the targets for Step 1 (coins) and Step 2 (reserve).
`reserve_in`: sum of amounts the 8-K says were "used to increase the USD Reserve"; `reserve_out`:
sum of "$X of the USD Reserve to ..." amounts (blank when none). `*_prec`: unit in the last
disclosed digit of that balance ($5.10 billion → 10,000,000). weekly.csv (Step 2, for Step 4):
per stated week, the price date used, p, s, q (the firm's own preferred: STRC for MSTR, BMNP for BMNR), and m and n from net().

### R: stated levels, rolled check with tolerance (decided 2026-09-25)

balances.csv `usd_reserve` = R = the 8-K's stated USD Reserve + USD Cash (USD Cash is first
disclosed for 2026-08-23; before that R = USD Reserve alone, labeled). Filings round R and, before
August, don't itemize flows into it, so R is taken as stated, not rolled. The roll is a check:
- From 2026-08-23 (both balances disclosed): ΔR must equal the week's cash flows from actions.csv
  (+ ATM net proceeds, + BTC sale proceeds, − BTC purchases, − repurchases, + carry).
- 2026-08-02 to 2026-08-16 (reserve only): ΔReserve must equal the itemized "used to increase the
  USD Reserve" amounts plus reserve-funded carry (reserve_in − reserve_out). Also 2026-08-23,
  whose prior week has no USD Cash.
- 2026-06-30 (quarter-end holdings row, no balance stated): R carried from the prior 8-K, labeled.
- Tolerance per week: half a unit in the last disclosed digit of each of the two stated figures,
  summed ($5.10 billion → ±$5M; $4.0 billion → ±$50M).
- Before 2026-08-02: no check. Print the unexplained ΔR per week, labeled; it lands in Step 4's
  residual.
- USD Cash, 2026-08-23: R jumps $1.59B because USD Cash was established that week, funded by
  "the remaining net proceeds from MSTR Stock sales" (8-K filed 2026-08-24):
  $2,006.5M − $136.4M STRC − $300.0M reserve = $1,570.1M, already booked by `issue_common`.
  It is not a disclosure change; no special row. (An earlier version of this file said the
  cash pre-existed; the filing says otherwise.)

### BitMine mapping (decided 2026-09-25)

C = ETH held (weekly release, exact). R = the release's "total cash & marketable securities",
labeled as including securities. BTC holdings and "moonshots" (equity stakes) are excluded, as
Strategy's definition counts only the coin reserve and USD assets; the page states the excluded
amount. F = BMNP notional ($100 × shares). Releases give ETH bought in coins only, so a BMNR
`buy_coin` row's usd = units × that week's ETH close, labeled estimated (neutral in attribution).

BitMine S (decided 2026-09-25). Filed anchors: 579,652,432 (5/31 10-Q balance sheet) and
603,226,394 (7/09, 10-Q cover). Roll by disclosed buybacks. Unreported issuance per week is
estimated as the week's unexplained ΔR ÷ that week's BMNR close (unexplained = ΔR − disclosed
cash flows). Between the two anchors, estimates are scaled so 5/31 + issuance = 7/09 exactly;
after 7/09 they accumulate unscaled until the fiscal-year 10-K cover count reanchors. Estimates
live in balances.csv (`source` says "S estimated"), never as actions.csv rows. Awards and
warrants follow the in-the-money rule at the week's BMNR close. Known bias: "acquired" ETH
includes staking (~2,500 ETH/week), so it is costed as a cash purchase, which inflates
unexplained ΔR and S (≈ +0.43% of S by 2026-09-20); the 10-K reanchor removes it. Weeks with
negative unexplained ΔR add 0 shares (two weeks; ≈ +0.015% of S). Warrants and options are
counted from the 10-Q; an exercise before the next 10-K would be counted twice (as a warrant
and via unexplained ΔR). Releases don't disclose exercises; the 10-K reanchor resets both.

### SharpLink mapping (decided 2026-09-26)

SharpLink, Inc., Nasdaq SBET, CIK 1981535 (the old SharpLink Gaming Ltd., CIK 1025561, last
filed 2024-02-23). Filings since 2026-06-01: 8-Ks 0001493152-26-029804 (6/23, registered
direct), -031202 (6/30, ETH and buyback update), -036741 (8/10, Q2 results); Q2 10-Q -036620
(8/07). No 8-K after 8/10 (checked 2026-09-26).

Rows per filed holdings date, not per week (decided with the user, 2026-09-26). SharpLink states
ETH held on 2026-06-16 (875,776, in passing in the -029804 pricing release), 2026-06-28 (886,725,
8-K -031202), 2026-06-30 (886,881) and 2026-08-03 (888,938), both in the -036741 release. No
weekly carry-forward between them. The 6/16 row is the anchor, so the June actions are attributed.
dat/parse_sbet.py assigns each action to the first filed date on or after it; an action after the
last filed date raises.

C = "Total ETH Holdings": native ETH plus LsETH and weETH as-if redeemed at the protocol rate on
the measurement date (10-Q glossary), taken as stated, labeled as including LsETH and weETH at
their stated equivalence. No BitMine analogue. The parser checks that native + LsETH + weETH
equals the total wherever the filing gives the parts (6/28, 6/30, 8/03).

Staking: SharpLink states purchases in ETH and dollars (6/24 to 6/26: 10,000 ETH at $1,611.04
weighted average), and holdings change without purchases. So, unlike BitMine (whose "acquired"
already includes staking, data.md), each filed date gets a `carry` row: units = stated ΔETH −
stated purchases (6/28 +949, 6/30 +156, 8/03 +2,057), usd 0, ticker STAKE, labeled "inferred
staking/LST accrual". Rolled ETH therefore equals stated ETH by construction; the independent
checks are the parts sum and strategicethreserve.xyz.

R = cash, stated on the balance sheet only: 6/30 $56,195K (in the -036741 release). Other filed
dates roll it from 6/30 by filed cash flows (6/16: $8,996,400), labeled; operating costs and
staking revenue are not itemized, so they are not in R and land in the residual. USDC line is $0.
The $100M Galaxy fund commitment (8/07) is not in R or D.
D = 0: total liabilities $5,572K at 6/30 are payables and accrued expenses; no debt or converts.
F = 0: Series A-1 and Series B preferred authorized, 0 issued. No preferred, so q is blank and
there is no rotation line; only issue_common (adds while m > 1) and buyback_common (adds while
m < 1) apply. The map draws SharpLink at q = 1, where m = q is m = 1.

S (decided 2026-09-26): basic from the 10-Q counts, 216,983,308 at 6/30 (221,054,539 issued −
4,071,231 treasury, balance sheet) and 217,223,604 at 8/03 (cover), rolled by filed issuance and
buybacks (6/16: 209,102,730). No R-based estimate (BitMine's needs weekly R). Awards and warrants
follow the in-the-money rule at the SBET close: RSUs 1,315,859 unvested at 6/30, plus 1,456,375
time-based July grants from 7/31 (10-Q Note 14); warrants 80,000 pre-funded at $0.0001 (always
in), Consensys 1,382,007 at $6.15, 691,004 each at $6.77, $7.38, $8.00; placement agent 2,764,013
at $7.68; June 2026 investor 10,013,351 at $8.15 (from 6/23); options 3,146 at $122.88. Excluded:
728,183 performance RSUs (metrics not set) and 252 warrants in the 10-Q total (16,312,635) not
itemized by tranche. Pre-funded exercises and RSU vesting move shares between basic and awards,
so they leave S unchanged; 6/30 to 8/03 vestings (up to 240,296 shares) may be counted twice,
about 0.11% of S. The 10-Q restates 12/31 outstanding as 196,707,797; the Q1 10-Q said
198,646,255 (the Q2 10-Q's 12/31 "issued"); not used.

Actions since 6/01: issue_common 6/23, 10,013,351 shares at $7.49, usd = net $73,331K from the
10-Q equity statement (8-K gross ~$75M); buyback_common 6/24 to 6/26, 2,132,773 at $4.69, usd =
$10,022K treasury cost from the 10-Q (shares × average = $10,002,705); buy_coin 10,000 ETH, usd =
units × $1,611.04 = $16,110,400. Notes on the rows say where the usd comes from.

Residuals are reported, not tested (no R check). 6/28 and 6/30 are zero by construction (R rolled
by the same flows, carry inferred); 8/03 shows −$13.2M, the July RSU grants and award shares.

strategicethreserve.xyz lists SBET: currentReserve 888,938, snapshotDate 2026-08-03, equal to the
filed figure (data.md gives the staleness rule).

actions.csv `note`: blank for filed figures; says what was estimated otherwise (e.g. "usd
estimated: units × ETH close").

Price date for a week: the last US trading day on or before week_end, for every ticker (BTC/ETH
close for that same date). q for STRC = STRC close / 100. The coin close for date D is
CoinGecko's point at 00:00 UTC on D+1, about 4 hours after the US equity close.

Signs: for actions, `usd` and `units` are positive magnitudes; the action gives direction.
`carry` rows are signed changes to R (`usd`) and C (`units`): a dividend paid is negative usd,
staking earned is positive units.

`action` ∈ issue_common, buyback_common, issue_pref, retire_pref, buy_coin, sell_coin, carry (actions.csv); attribution.csv adds price, itm_flip, est_issuance (BMNR only: the week's estimated basic-share change from balances.csv "S estimated", booked at that week's BMNR close with its cash; not an actions.csv row), residual.
`units`: shares for common, notional dollars for preferred, coins for coin trades.
`firm` ∈ MSTR, BMNR, SBET.
