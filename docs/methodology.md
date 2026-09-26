# Methodology

This project measures each capital action by Strategy (BTC), BitMine (ETH) and SharpLink (ETH) since 2026-06-01
on one ruler: Strategy's own net coins per share definition, applied to all three firms. For each action it states the per-share
effect at disclosed prices and the price where that effect changes sign. It makes no judgment on any decision
and gives no forecast.

## Definition and source

The definition comes from the glossary in Strategy's 2026-08-24 FWP:
https://www.sec.gov/Archives/edgar/data/1050446/000119312526363557/d431748dfwp.htm

Per firm, per week (USD unless noted):

| symbol | meaning |
|---|---|
| C | coins held (BTC or ETH) |
| R | USD assets. Strategy: USD Reserve plus USD Cash. BitMine: cash and marketable securities |
| D | notional of out-of-the-money convertible notes and other debt-like instruments |
| F | notional of perpetual preferred (liquidation preference, not trading price) |
| S | fully diluted shares: common, awards, and shares from in-the-money converts and preferred |
| p | coin close |
| s | common close |
| q | preferred close / $100 notional (STRC for Strategy, BMNP for BitMine) |

N = C + (R − D − F) / p, the net coins. n = N / S, net coins per share. m = s / (p·n), net mNAV.
Amplification = C / N.

A convert or preferred is in the money when the common price is above its conversion price. It then leaves D or F
and its shares join S. This is applied at each date's price, not from a fixed list. Strategy's $39.8M secured
term loan is not deducted, following the glossary. STRE (EUR) converts at 1.147 USD per EUR, the rate implied by
Strategy's KPI API; the Friday 12:30 PM New York fixing Strategy uses is not published.

## The five formulas

An action moves x dollars. With k = x / (p·S), the first-order change in n is:

| # | action | Δn | adds when |
|---|---|---|---|
| 1 | issue common | k·(1 − 1/m) | m > 1 |
| 2 | buy back common | k·(1/m − 1) | m < 1 |
| 3 | issue preferred | k·(1 − 1/q) | q > 1 |
| 4 | retire preferred | k·(1/q − 1) | q < 1 |
| 5 | buy or sell coins | 0 | neutral on day one |

The break-even line is m = q. Strategy's rotation (1 and 4: issue common, retire STRC) adds while m > q, so it
stops adding when STRC trades above $100 × m. BitMine's rotation (3 and 2: issue BMNP, buy back common) adds while
m < q, so it stops adding when BMNP trades below its $100 liquidation preference × m.

Test anchor: the Bitcoin Magazine STRC week, $24.998M retiring $28.893M notional (q = 0.8652), adds
(1/q − 1)·x = $3.895M to common. The tests reproduce it to the dollar.

## Attribution order

Each week's observed change in n is n at this week's balances and prices minus n at last week's. It is split in
this order. Each step recomputes n exactly; the rest is the residual.

1. Price: last week's balances revalued at this week's coin price.
2. In-the-money flips: converts or preferred crossing their conversion price at this week's common price.
3. Each action, in filing order, at its own price: common at its average sale or repurchase price, preferred at
   q = average price / 100 (BMNP issue: $80, q = 0.80), coins at their USD cost.
4. Carry: preferred dividends and convert interest paid from R.
5. BitMine only: estimated share issuance (see below), at that week's BMNR close.
6. Residual: observed change minus the sum of the above.

The page shows each part as value to common: Δn × S × p at this week's S and p. First-order values use the
table's formulas; exact values use the cash actually received, so issue fees show as the gap between them.

## Labeled estimates and decisions

| decision | reason |
|---|---|
| Strategy R is taken as each 8-K states it, not rolled forward. From 2026-08-02 the roll is a check within each filing's rounding (half the last disclosed digit of each figure). | Filings round R to the nearest $1M, $10M or $100M and, before August, do not itemize flows into it. Before 2026-08-02 the unexplained change lands in the residual, labeled. |
| Before 2026-08-23 Strategy R is the USD Reserve alone. | USD Cash was first disclosed that week, funded by that week's MSTR sale proceeds (8-K filed 2026-08-24). |
| The 2026-06-30 quarter-end holdings row carries R from the prior 8-K. | No balance is stated for that date. |
| Strategy's preferred and class A share counts start from the Q2 10-Q and roll by each 8-K's sales and repurchases. | The weekly 8-Ks give flows, not levels. |
| Two Strategy 8-Ks (filed 6/15 and 8/03) disagree with the next week's holdings by 1 BTC; both are listed as known filing gaps. | The next filing balances only from the corrected figure. Any other 1 BTC miss fails the parser. |
| BitMine R is its stated "total cash & marketable securities", labeled as including securities. BitMine's BTC and equity stakes are excluded. | Strategy's definition counts only the coin reserve and USD assets. |
| BitMine S is estimated between filings: anchored to the 10-Q counts for 2026-05-31 (579,652,432) and 2026-07-09 (603,226,394), rolled by disclosed buybacks, with unreported issuance estimated as the week's unexplained change in R divided by the BMNR close. Between the anchors the estimates are scaled to land on the 7/09 count; after it they accumulate until the next 10-K. | BitMine does not state its share count weekly, and about $1.08B of cash arrived 8/16 to 9/20 with no stated source. Known bias: ETH counted as bought includes staking, which raises S by about 0.43% by 2026-09-20; the next 10-K count resets it. |
| The USD of each BitMine ETH purchase is units × that week's ETH close. | Releases give ETH bought in coins only. Coin trades are neutral on day one, so this does not move n. |
| No BitMine staking rows. The stated holdings change is the week's ETH change. | "ETH acquired" equals the stated change in 13 of 16 weeks, so a separate staking estimate would count it twice. Releases do not separate staking rewards from purchases. |
| One BitMine release dated "As of June 28" is assigned to 2026-07-05. | The release's own staking sentence and dateline give July 5. |
| BMNP q uses its $100 liquidation preference. | Certificate of Designations. After a follow-on BMNP sale the preference floats to max($100, last sale price, 10-day average). |
| STRC retirements use the 8-K's disclosed average price where given, else the daily close. | The filings do not always state it. |
| The residual test applies to Strategy weeks from 2026-08-02. A week passes if the residual is under 5% of the week's change, or within that week's R rounding. | R is checked only from that date. A quiet week with rounded disclosures would otherwise fail with nothing wrong (8/30: $10.6M on a $107M week, inside ±$20M rounding). BitMine residuals are reported, not tested. |
| SharpLink rows exist only on the dates its filings state ETH holdings (2026-06-16, 06-28, 06-30, 08-03); nothing is carried forward between them. | SharpLink files no weekly holdings update; its last 8-K was filed 2026-08-10. |
| SharpLink C is its stated Total ETH Holdings: native ETH plus LsETH and weETH at the stated as-if-redeemed equivalence. | The filings state the total and its three parts; the parser checks that the parts sum to the total. |
| SharpLink carry rows: the stated ETH change less stated purchases, labeled inferred staking and LST accrual. | SharpLink states its purchases separately (unlike BitMine, whose "acquired" figure includes staking). |
| SharpLink R is 2026-06-30 balance-sheet cash, rolled to other dates by filed cash flows. S uses the 10-Q counts for 2026-06-30 and 2026-08-03, rolled by filed issuance and buybacks, plus RSUs, performance RSUs and in-the-money warrants (July grants taken as of 7/31, an assumption). Issue and buyback USD come from the 10-Q equity statement. | Cash is stated only for 2026-06-30; the 10-Q gives net proceeds and treasury cost. Operating costs and staking revenue are not in R. |
| SharpLink has no preferred, so no q and no rotation line: issuing common adds while m > 1, buying back common while m < 1. Its map marks sit at q = 1. Its residuals are reported, not tested. | 10-Q 6/30: no preferred, debt or converts outstanding. |

## Data sources

| source | use |
|---|---|
| Strategy 8-Ks, EDGAR CIK 1050446 | weekly ATM sales, STRC repurchases, BTC trades, USD Reserve and Cash |
| Strategy Q2 10-Q | shares, each preferred's notional, converts |
| https://api.strategy.com/btc/bitcoinKpis | netSatsPerShare, amplification, mNAV (current value only; saved daily) |
| BitMine 8-K releases (ex99-1), EDGAR CIK 1829311 | ETH held, buybacks, BMNP offering and dividends, cash |
| BitMine 10-Q (5/31) and Certificate of Designations | shares, balance sheet anchor, BMNP terms |
| SharpLink 8-Ks and ex99-1 releases, EDGAR CIK 1981535 | ETH held on stated dates, registered direct offering, buybacks, ETH purchases |
| SharpLink Q2 10-Q | shares, cash, warrants and awards, net proceeds, treasury cost |
| Yahoo Finance daily closes | MSTR, STRC, STRK, STRF, STRD, BMNR, BMNP, SBET |
| CoinGecko | BTC and ETH daily closes |
| strategicethreserve.xyz | independent check of BitMine and SharpLink ETH holdings |

Each week uses closes from the last US trading day on or before the week's end. Every row of `data/actions.csv`
links to its SEC filing. EDGAR requests identify the project in the User-Agent and stay under 10 per second.

## Done check

`python check.py` runs daily after the KPI snapshot and exits 0 only if every assertion passes. Network failures
count as failures.

1. Rebuilt netSatsPerShare within 0.5% of the live API: the latest Strategy state, revalued at the API's BTC price
   and the live MSTR price.
2. Rebuilt amplification within 0.5% of the API.
3. BitMine rolled ETH within 0.1% of strategicethreserve.xyz at that site's snapshot week, with the snapshot no more
   than 6 weeks old. SharpLink stated ETH within 0.1% at the site's snapshot date, with the snapshot no more than
   6 weeks before SharpLink's own last filed holdings date (not the calendar, since SharpLink files rarely).
4. The residual test above, for every Strategy week from 2026-08-02. SharpLink residuals are printed per filed
   date, not tested.
5. Every filing link in `data/actions.csv` returns HTTP 200 from EDGAR.

The result and its run time appear in the page's Method section.
