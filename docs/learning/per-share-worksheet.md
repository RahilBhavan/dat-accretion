# Worksheet: recompute one share issuance per share

This is a self-check. It has no answers and no worked numbers. Fill in each blank from the source named next to it,
then compare with the repo only at the end (Part E).

**The event.** Strategy sold Class A common stock (MSTR) under its at-the-market program during
October 12 to October 18, 2026, and reported the sale in an 8-K filed on October 19, 2026. The repo records it as the
`issue_common` row for `MSTR`, week ending `2026-10-18`.

**Sources**

| What | Link | Date |
|---|---|---|
| The 8-K for this week (ATM table, BTC table, USD Reserve and USD Cash) | https://www.sec.gov/Archives/edgar/data/1050446/000119312526424688/mstr-20261019.htm | filed 2026-10-19 |
| The previous week's 8-K (for the state before this week) | https://www.sec.gov/Archives/edgar/data/1050446/000119312526419726/mstr-ex99_1.htm | filed 2026-10-13 |
| Definitions of USD Reserve, USD Cash, debt, preferred notional and fully diluted shares (glossary) | https://www.sec.gov/Archives/edgar/data/1050446/000119312526363557/d431748dfwp.htm | filed 2026-08-24 |
| 10-Q for the quarter ended 2026-06-30 (the anchor for debt, preferred and share counts) | https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm | period 2026-06-30 |
| The formulas | [`.claude/rules/method.md`](../../.claude/rules/method.md), sections "State" and "Actions" | |

## Part A: the issue price per share

From the 8-K's ATM table, for MSTR stock only:

| Input | Where in the 8-K | Your value |
|---|---|---|
| Shares sold | ATM Update table, MSTR row, "Shares Sold" | ________ |
| Net proceeds (USD) | Same row, "Net Proceeds (in millions)" | ________ |
| Number of decimals the 8-K gives for net proceeds | Same cell | ________ |

1. Average net price per share = net proceeds / shares sold = ________
2. The 8-K rounds net proceeds. Give the lowest and highest price per share that the rounded figure allows:
   low ________ high ________
3. Does the 8-K state an average sale price per MSTR share anywhere? ________ (If not, write down what that means
   for how precise answer 1 can be.)

## Part B: the state just before the sale

Write the state that applies before the sale. Use the 8-K for C and R, and use the 10-Q (rolled forward) or
`data/balances.csv` for D, F and S. Write down which source you used for each value.

| Symbol | Meaning (method.md) | Source you used | Your value |
|---|---|---|---|
| C | BTC held | | ________ |
| R | USD Reserve + USD Cash | | ________ |
| D | debt notional, out-of-the-money converts at face | | ________ |
| F | preferred notional | | ________ |
| S | fully diluted shares | | ________ |
| p | BTC close on the price date | `data/prices.csv` (CoinGecko close) | ________ |
| s | MSTR close on the price date | `data/prices.csv` (Yahoo close) | ________ |
| Price date | the latest date on or before the week end (2026-10-18) that has an MSTR close | `data/prices.csv`, the `MSTR` rows (the dates the price source lists) | ________ |

Question: did any convertible note cross its conversion price between the previous week's close and this week's?
If one did, D and S change before the sale is applied. Which way does each move? ________

## Part C: recompute

Use the formulas in method.md. Show each step.

1. N = C + (R − D − F)/p = ________
2. n = N/S (BTC per share) = ________
3. m for this sale = (price per share from Part A) / (p · n) = ________
4. k = x/(p · S), with x = net proceeds = ________
5. First-order change in n: Δn = k · (1 − 1/m) = ________
6. Is m above or below 1? ________ Does the sale add BTC per share or remove it? ________

## Part D: explain it in one or two sentences

Why does selling stock at this m change BTC per share in the direction you found? Use only what the filing and the
formulas show; state facts, not verdicts.

________________________________________________________________________________

________________________________________________________________________________

## Part E: check against the repo (only after Parts A to D)

Open `data/attribution.csv` and find the row `MSTR,2026-10-18,issue_common`. Compare its `m` and `dn_first_order`
with your answers to C3 and C5.

- Your m ________ repo m ________
- Your Δn ________ repo `dn_first_order` ________

The engine does not apply the sale to last week's state. It applies the week's steps in order (price, in-the-money
flips, then each action row in `data/actions.csv` order) and applies the sale to the state after the earlier
steps (method.md, "Attribution"). So a recompute from last week's balances, or from this week's final balances, will
not match exactly. If yours differs by more than a few percent, find the input that causes the gap and write it
here: ________
