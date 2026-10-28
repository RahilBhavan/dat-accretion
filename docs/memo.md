# At net mNAV 1.156, Strategy's STRC rotation adds net sats per share while STRC trades below $115.56; at 0.969, BitMine's BMNP rotation adds net ETH per share while BMNP trades above $96.90 (week ending 2026-10-25)

| Firm | Week ending | Net mNAV m | Preferred close | Break-even ($100 × m) | Rotation adds while |
|---|---|---|---|---|---|
| Strategy | 2026-10-25 | 1.156 | STRC $99.36 | $115.56 | STRC below break-even |
| BitMine | 2026-10-25 | 0.969 | BMNP $97.00 | $96.90 | BMNP above break-even* |
| SharpLink | 2026-08-03 (last filed) | 0.809 | no preferred | m = 1 | issue if m > 1; buy back if m < 1 |

<sub>STRC closed at $99.36 on 2026-10-23 (q = 0.9936). BMNP closed at $97.00 on 2026-10-23 (q = 0.9700). SBET closed at $6.22 on 2026-08-03. SharpLink's filings state ETH holdings only on 2026-06-16, 2026-06-28, 2026-06-30, 2026-08-03. *BitMine's 2026-10-25 gap between m and q is within the S-estimate bias; see the note under the map.</sub>

<sub>Key. m, net mNAV: share price over net coin value per share. q: preferred close over its $100 notional. Net sats: net bitcoin per share in satoshis (100 million per BTC). Rotation: Strategy sells common and retires STRC; BitMine sells BMNP and buys back common. STRC: Strategy's perpetual preferred, $100 stated amount. BMNP: BitMine's 9.50% cumulative preferred, $100 liquidation preference.</sub>

Digital asset treasury (DAT) companies hold bitcoin or ether and raise money by selling stock. This memo measures each share sale, buyback and preferred trade since 2026-06-01 with Strategy's own net coins per share definition, applied to all three firms (glossary, Strategy's 2026-08-24 free writing prospectus, FWP). Net coins N are coins held (C) plus USD assets (R), less out-of-the-money convertible debt and preferred notional, converted to coins at the coin price; n is N per fully diluted share, and S is that share count.

Issuing common adds to n while m is above 1; retiring preferred adds while q is below 1. So Strategy's rotation adds while m > q and stops adding when STRC trades above $100 × m; BitMine's adds while m < q and stops adding when BMNP trades below $100 × m. SharpLink has no preferred, so no rotation line applies.

STRC closed below its break-even in 24 of 24 filed weeks, and BMNP closed below its break-even in 18 of 20. SharpLink's m was below 1 on 4 of 4 filed dates.

| Since first week | Strategy | BitMine | SharpLink |
|---|---|---|---|
| Coin price | +$2,208.4M | +$168.8M | −$9.1M |
| In-the-money flips | −$338.0M | −$9.0M | −$10.9M |
| Filed actions | +$412.8M | −$49.4M | +$10.9M |
| Estimated issuance | n/a | −$18.3M | n/a |
| Carry | −$400.8M | −$12.4M | +$5.6M |
| Residual | −$260.4M | −$27.9M | −$19.2M |
| Observed | +$1,622.0M | +$51.7M | −$22.7M |

<sub>Value to common (change in n × S × coin price) by cause, summed from each firm's first week (Strategy and BitMine 2026-05-31, SharpLink 2026-06-16); the parts sum to the observed change before rounding. Strategy's residual is −$257.4M before 2026-08-02, when the 8-Ks did not itemize cash flows, and −$3.0M in the weeks since, which the R check tests against the filings. BitMine's and SharpLink's residuals are report only.</sub>

![Break-even map: m against q, one mark per firm-week](map.svg)

---

<sub>Closest weeks to the line: Strategy 2026-08-23, m 2.29% above q; BitMine 2026-10-25, m 0.11% below q. BitMine's estimated diluted share count S carries an upward bias of up to 0.64% of S by 2026-10-25 because its releases count staked ETH as purchased, which this memo costs as cash; the bias raises m by the same proportion, and removing it puts m at or below q in 3 of 20 BitMine weeks (2026-10-11, 2026-10-18, 2026-10-25), where BitMine's rotation would add.</sub>

<sub>Period: Strategy weeks ending 2026-05-31 to 2026-10-25 (24 filed dates, including the 2026-06-30 quarter-end holdings row); BitMine weeks ending 2026-06-14 to 2026-10-25 (20 weeks with a BMNP price; BMNP was issued 2026-06-10); SharpLink filed holdings dates 2026-06-16 to 2026-08-03 (4 dates; SharpLink states holdings only on those dates, and this memo carries nothing forward between them).</sub>

<sub>Sources: Strategy weekly 8-Ks and Q2 10-Q (EDGAR CIK 1050446); BitMine weekly 8-K releases and 10-Q (EDGAR CIK 1829311); SharpLink 8-K releases and Q2 10-Q (EDGAR CIK 1981535); Yahoo Finance daily closes for MSTR, STRC, STRK, STRF, STRD, BMNR, BMNP and SBET; CoinGecko BTC and ETH closes. Each week uses closes from the last US trading day on or before the week's end.</sub>

<sub>Labeled estimates: this memo estimates BitMine's diluted share count S between filings. It anchors S to the 10-Q share counts for 2026-05-31 and 2026-07-09 and estimates unreported issuance as the week's unexplained change in cash divided by the BMNR close. BitMine's USD assets R are its stated cash and marketable securities, so R includes securities. The USD of each BitMine ETH purchase is units × that week's ETH close. SharpLink's coins held C include the liquid staking tokens (LSTs) LsETH and weETH at their stated as-if-redeemed ETH equivalence; its ETH change beyond stated purchases is inferred staking and LST accrual; its R is 2026-06-30 balance-sheet cash rolled by filed cash flows.</sub>

<sub>Page: https://rahilbhavan.github.io/dat-accretion/. Method: https://github.com/RahilBhavan/dat-accretion/blob/main/docs/methodology.md. Code and data: https://github.com/RahilBhavan/dat-accretion. Definition source: https://www.sec.gov/Archives/edgar/data/1050446/000119312526363557/d431748dfwp.htm.</sub>
