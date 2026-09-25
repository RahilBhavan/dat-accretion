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

`carry` rows: preferred dividends and convert interest reduce R; staking adds C. They make
attribution sum to the observed change; they are not actions.

Break-even line m = q. Strategy's rotation (1 + 4) adds while m > q: stops when STRC trades
above $100 × m. BitMine's rotation (3 + 2) adds while m < q: stops when BMNP trades below its
liquidation preference × m.

## Test anchors (tests/test_engine.py)

1. Bitcoin Magazine STRC week: $24.998M retires $28.893M notional → q = 0.8652, action 4 adds
   (1/q − 1)·x = $3.895M to common. Reproduce to the dollar.
2. Each formula at m = 1 or q = 1 gives zero.
3. Combined rotation at m = q gives zero for both firms.
4. First order within 1% of exact recompute for an action under 1% of market cap.

## Schemas (dates ISO, money USD, coins whole BTC/ETH)

| file | columns |
|---|---|
| actions.csv | firm, week_end, filed, filing_url, action, ticker, usd, units, avg_price |
| balances.csv | firm, date, coins, usd_reserve, debt, pref_notional, shares_diluted, source |
| prices.csv | date, ticker, close |
| kpi_snapshots.csv | fetched_at, netSatsPerShare, netBtcReserve, amplification, mNav, btc_price, mstr_price |
| attribution.csv | firm, week_end, action, usd, m, q, dn_first_order, dn_exact, dn_per_dollar |
| stated.csv | firm, week_end, filed, filing_url, coins, usd_reserve, usd_cash, reserve_in, reserve_out, usd_reserve_prec, usd_cash_prec |
| weekly.csv | firm, week_end, price_date, p, s, q_strc, m, n |

stated.csv holds each 8-K's own aggregates, the targets for Step 1 (coins) and Step 2 (reserve).
`reserve_in`: sum of amounts the 8-K says were "used to increase the USD Reserve"; `reserve_out`:
sum of "$X of the USD Reserve to ..." amounts (blank when none). `*_prec`: unit in the last
disclosed digit of that balance ($5.10 billion → 10,000,000). weekly.csv (Step 2, for Step 4):
per stated week, the price date used, p, s, q for STRC, and m and n from net().

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
- Disclosure change, 2026-08-23: R jumps by the first-disclosed USD Cash ($1.59B). That cash
  existed before; it was not reported. Step 4 books it as its own row (`disclosure`, labeled
  "USD Cash first disclosed"), never as an action or inside the 5% residual test.

Price date for a week: the last US trading day on or before week_end, for every ticker (BTC/ETH
close for that same date). q for STRC = STRC close / 100. The coin close for date D is
CoinGecko's point at 00:00 UTC on D+1, about 4 hours after the US equity close.

Signs: for actions, `usd` and `units` are positive magnitudes; the action gives direction.
`carry` rows are signed changes to R (`usd`) and C (`units`): a dividend paid is negative usd,
staking earned is positive units.

`action` ∈ issue_common, buyback_common, issue_pref, retire_pref, buy_coin, sell_coin, carry.
`units`: shares for common, notional dollars for preferred, coins for coin trades.
`firm` ∈ MSTR, BMNR.
