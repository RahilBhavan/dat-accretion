# Data: sources, access, provenance

## Sources

| source | use | notes |
|---|---|---|
| Strategy 8-Ks, CIK 1050446 | ATM sales by ticker, STRC repurchases, BTC trades, USD Reserve/Cash | weekly, Mondays |
| Strategy Q2 10-Q | shares, each preferred's notional, converts, debt | anchor; reanchor on Q3 10-Q |
| `https://api.strategy.com/btc/bitcoinKpis` | netSatsPerShare, netBtcReserve, amplification, mNav | current value only, no history |
| BitMine 8-K ex99-1, CIK 1829311 | ETH held, buybacks, BMNP and direct offerings, staking | weekly |
| BitMine May 31 10-Q | shares, balance sheet anchor | |
| BitMine 9.50% preferred release + 424B | BMNP liquidation preference, dividend | verify in Step 0 |
| `https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>` | MSTR STRC STRK STRF STRD BMNR BMNP closes | |
| CoinGecko | BTC, ETH daily closes | |
| strategicethreserve.xyz | independent ETH holdings check | |

## Rules

- EDGAR: every request sends `User-Agent: dat-accretion rbhavanzim@gmail.com` and stays under
  10 req/s (throttle 0.6s, as filing-tracker's `SECClient` does). Cache raw filings in
  `data/raw/` (gitignored, rebuildable).
- Parse 8-K tables by row label, never by position. An unknown label raises; never skip a row
  silently.
- Every actions.csv row carries `filing_url`. A number on the page must trace to a filing.
- No synthetic fallback data. If a source fails, fail loudly.
- The KPI snapshot saves the raw JSON for each day too (`data/kpi/<date>.json`), since the API
  keeps no history and Step 0 may need fields the CSV drops.
- BitMine staking: weekly releases give staked ETH (often unchanged for weeks) and annualized
  projections only, never realized rewards. Decision (2026-09-25): estimate weekly staking carry
  as staked ETH × the release's 7-day annualized yield × 7/365, one `carry` row per week citing
  that release's filing_url. The page labels it an estimate. When a 10-Q reports realized
  rewards, compare the quarter's summed estimates to it and publish the difference.
- Open question: which STRC price prices a retirement. Use the 8-K's disclosed average where
  given, else the daily close, and record which in `avg_price`.
