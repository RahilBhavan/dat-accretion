# FAQ

> The questions a newcomer asks first, each answered from a recorded decision.

**Type:** Reference
**Files:** `docs/decisions.md`, `docs/build-notes.md`, `.claude/rules/method.md`, `.claude/rules/data.md`, `.claude/rules/framing.md`
**Prerequisites:** None
**Time:** ~25 minutes

## Questions

Each answer ends with the decision ids from `docs/decisions.md` it rests on; "notes #n" points at `docs/build-notes.md`. Symbols follow `.claude/rules/method.md`: C coins, R USD assets, D debt, F preferred notional, S diluted shares, p coin price, s share price, n net coins per share, m net mNAV (share price over net coin value per share), q preferred price over its $100 notional.

### Why does preferred count at $100 a share and not at its trading price?

Strategy's glossary defines F as the notional of each perpetual preferred, "not trading price, not accrued dividends". **Notional** (the liquidation preference) is what the firm owes each share ahead of common. The trading price still matters: it enters as q, and retiring preferred below $100 (q < 1) adds net coins per share. BitMine's BMNP uses its $100 liquidation preference from the Certificate of Designations. Decisions R1, R10.

### Why is Strategy's $39.8M secured term loan not deducted?

The glossary leaves it out of D, and the project uses Strategy's definition as written. Decision R4.

### Why is a convert sometimes debt and sometimes shares?

A **convert** is a bond the holder can swap for shares at a conversion price. When MSTR trades above that price the swap is likely, so the glossary moves the note out of D and adds its shares to S. The test runs at each date's price: the 2030A note ($149.77) crossed back and forth in the period. Decision R3.

### Why do the numbers differ slightly from Strategy's API?

The rebuild pinned in `tests/test_balances.py` lands at +0.107% on net sats per share and −0.114% on mNAV against the 2026-09-25T16:19:32Z snapshot. Known sources: S sits about 0.11% below the API's implied fully diluted count (gap unexplained, likely award vesting after 6/30); the class A count comes from a filing even though an untraceable figure matched better (notes #14); STRE's EUR rate is inferred. `check.py` also notes that the API may reflect a newer 8-K than the repo. The gate was 0.5%. Decisions R2, R5, R7.

### Why does STRE convert at 1.147 USD per EUR?

STRE is a preferred denominated in euros. Strategy converts it at a Friday 12:30 PM New York rate it does not publish; 1.147 is the rate the API implies. A market rate would not match Strategy's figure. For the same reason any STRE trade raises instead of being converted at a guessed rate. Decisions R5, S8.

### What does "first order" mean?

The five formulas in method.md give an action's effect on n from its size x and one ratio, m or q, as if the action were small: for example, retiring preferred adds k·(1/q − 1) with k = x/(p·S). The engine also recomputes n exactly after each action. For an action under 1% of market cap the two agree within 1%; the gap shows issue fees, since exact uses cash actually received. Decisions R8, A7.

### Why is R taken as stated instead of rolled forward?

Filings round R to $10-50M and, before August, don't itemize the flows into it, so an exact roll could not pass (notes #4). R is taken from each 8-K; from 2026-08-02 the roll is a check within half a unit of each filing's last disclosed digit. The $1.59B of USD Cash that appears on 8/23 was funded that week from MSTR sales already booked, so it gets no special row. Decisions S4, S5.

### Why is BitMine's BTC excluded?

Strategy's definition counts only the coin reserve and USD assets. BitMine's releases also list BTC and equity stakes ("moonshots", about $300M), which fit neither. They are left out, and the page states the excluded amount. BitMine's R is its "total cash & marketable securities", labeled as including securities. Decision B1.

### Why are there no staking rows for BitMine but carry rows for SharpLink?

BitMine's "ETH acquired" equals its stated holdings change in 13 of 16 weeks, so it already includes staking; a separate staking row counted it twice and failed the site check (+0.52%; without it −0.0006%, notes #6). SharpLink states purchases separately in ETH and dollars, so its stated change minus purchases is observable and becomes a `carry` row (6/28 +949, 6/30 +156, 8/03 +2,057 ETH). Decisions B2, L4.

### Why are BitMine's share counts marked "S estimated"?

BitMine never states its share count between filings, and about $1.08B of cash arrived 8/16 to 9/20 with no stated source. Shares are anchored at 5/31 and 7/09 and estimated in between from unexplained cash ÷ that week's BMNR close. The known upward bias, about +0.43% of S by 2026-09-20, is stated rather than corrected. Estimates never become `actions.csv` rows. Decisions B3, B4, B5.

### Why does SharpLink have no weekly rows?

SharpLink files no weekly update; its last 8-K was 2026-08-10. Rows exist only on the four dates its filings state ETH holdings: 6/16, 6/28, 6/30 and 8/03. Carried-forward weeks would show numbers no filing states. Decision L1.

### What is the residual, and why is it tested only for Strategy from 2026-08-02?

Each week's change in n is split in a fixed order: price, convert flips, actions, carry, BitMine's estimated issuance. The residual is what is left. It is tested only where R is checked, Strategy from 8/02: a week passes under 5% of its change or within its R rounding. Elsewhere R is not checked, so the residual carries known unexplained flows and is reported, labeled. Decisions A1, A3, A4.

### Why did the KPI snapshot ship before any analysis?

Strategy's KPI API keeps no history. Every day without a snapshot is a lost row, so the daily snapshot went first and saves the raw JSON too. For the same reason the `data` branch is append-only and never force-pushed. Decisions P7, P6.

### Why does `check.py` fail when the network is down?

A check that passes when it cannot reach the API proves nothing, so an exception inside any check is recorded as a failure, never a skip. Decision A5.

### Why is reanchoring manual?

Anchor counts come from 10-Q and 10-K sections the weekly parsers don't read, and a wrong anchor moves every later week. When a newer 10-Q or 10-K appears, the refresh exits 2, leaves its PR open and opens an issue for a person. Decision O4.

### Why no chart library?

One map and a set of bar charts need nothing more than plain HTML, CSS, JavaScript and hand-drawn SVG, with no external scripts to load or break. The project also adds no dependency without asking. Decisions M6, P3.

### Why do the attribution bars leave out the price move?

The weekly price move is often 10 to 50 times the week's actions and would hide them. Price and convert flips appear in tooltips and the table. Decision M8.

### Why does the page say "latest filed week" and never "today"?

The numbers come from the last filing, which can be days old. Decision M3.

### Why do headlines state only figures?

The main reputational risk is reading as a judgment on a firm's decisions. Headlines take one form, a net mNAV and a break-even price anyone can check against the next close. Decisions M1, M2.

## Exercises

1. Pick three answers above and find the row for each cited decision id in `docs/decisions.md`. Check that the "why" column says what the answer says.
2. Using `data/balances.csv` and `data/weekly.csv` for MSTR 2026-09-20, compute how much N and n would fall if the $39.8M term loan were added to D. Express the change in n as a percentage, and compare it with the 0.5% Step 0 gate.
3. Write one new question a newcomer might ask about SharpLink's share count, and answer it from `.claude/rules/method.md` ("SharpLink mapping") with the decision id it rests on.
