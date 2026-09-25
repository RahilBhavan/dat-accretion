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

`action` ∈ issue_common, buyback_common, issue_pref, retire_pref, buy_coin, sell_coin, carry.
`units`: shares for common, notional dollars for preferred, coins for coin trades.
`firm` ∈ MSTR, BMNR.
