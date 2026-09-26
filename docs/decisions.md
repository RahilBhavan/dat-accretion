# Decisions

Every decision that shapes the code or the numbers, why it was made, and what it replaced. Dates are when
the decision was settled; all fall on 2026-09-25 or 2026-09-26. Where a decision is also a working rule, the
rule lives in `.claude/rules/` and the code follows the rule file. Problems that forced a decision are
numbered in [`build-notes.md`](build-notes.md) and cited here as "notes #n". The last column names the
alternative each decision rules out; where the build reversed an earlier choice, the row says so.

Sections: [Project and repo](#project-and-repo) · [The ruler](#the-ruler) ·
[Strategy data](#strategy-data) · [BitMine data](#bitmine-data) · [SharpLink data](#sharplink-data) ·
[Attribution and checks](#attribution-and-checks) · [Page and memo](#page-and-memo) ·
[Automation](#automation)

## Project and repo

| # | decision | why | alternative |
|---|---|---|---|
| P1 | The repo is public from the first commit. | The author's choice at setup. Every input is public data, and the page links each number to its filing. | Private until launch. |
| P2 | The full spec stays outside the repo; its engineering half is mirrored in `CLAUDE.md` and `.claude/rules/`. | The spec also holds material that is not about the engineering, which does not belong in a public repo. | One spec file in the repo. |
| P3 | Python 3.12, standard library plus numpy, one `python -m dat.<module>` per step, static site, no database or framework. No new dependency without asking. | The shape of the author's earlier project, Spine. Every step is a small script that reads and writes CSVs, so anyone can rerun one step and diff the output. | A framework or database; a notebook. |
| P4 | One branch and one squash-merged PR per build step. `main` is protected by the `tests` check. Each PR body pastes the acceptance check's real output. | Each step is reviewable alone, and the numbers claimed in a PR are the ones the code printed. | Direct commits to `main`. |
| P5 | Commit messages are one imperative sentence with no prefix. | The `build-step` skill's rule. Five step PRs kept a "Step n:" title before the rule was applied consistently. | Conventional-commit prefixes. |
| P6 | The `data` branch belongs to the snapshot bot: append-only commits, never force-pushed. | Strategy's KPI API keeps no history, so a lost row cannot be recovered. This differs from Spine on purpose. | Force-pushed data branch, as in Spine. |
| P7 | The KPI snapshot shipped first, before any analysis, and saves each day's raw JSON too. | Every day without a snapshot is lost. The raw JSON keeps fields the CSV drops, in case Step 0 needed them. | Starting with the parsers. |
| P8 | Work is split among an orchestrator, a `runner` that implements, a `reviewer` that checks adversarially, and a `filing-verifier` that matches rows to filings. Each dispatch names exact files, an acceptance command and a style anchor. | Checks by a separate agent caught silent-skip paths, an untraceable share count and two workflow failure modes that the implementing agent missed (notes #14, #16, #20, #21). | One agent writing and checking its own work. |
| P9 | Decisions are written into the rule files with their date, in the same PR that makes them. | Later steps and the weekly refresh read the rules, not the conversation that produced them. | Decisions left in PR threads. |

## The ruler

| # | decision | why | alternative |
|---|---|---|---|
| R1 | Use Strategy's own net coins per share definition, from the glossary in its 2026-08-24 FWP, for all three firms. | One ruler across firms, and it is the firm's own. The spec committed to adopting Strategy's definition if Step 0 found a difference; it found three (notes #1). | The spec's first definition, which counted every convert as debt and used a different share count. |
| R2 | Levels are computed from filings, not anchored to the KPI API. | The rebuild landed within 0.11% of the API against a 0.5% gate, so the fallback was not needed. | The spec's fallback: take levels from the API and attribute only changes. |
| R3 | A convert or preferred is in the money when MSTR trades above its conversion price. It then leaves D or F and its shares join S, re-tested at each date's price. | The glossary defines it that way, and the 2030A note ($149.77 conversion price) crossed back and forth in the period. | A fixed list of in-the-money instruments. |
| R4 | Strategy's $39.8M secured term loan is not deducted. | The glossary leaves it out. | Deducting all debt. |
| R5 | STRE (EUR) converts at 1.147 USD per EUR. | The Friday 12:30 PM New York fixing Strategy uses is not published; 1.147 is the rate the API implies. | A market EUR rate, which would not match Strategy's figure. |
| R6 | Net sats per share uses Fully Diluted shares; gross sats per share uses Assumed Diluted. The two are never mixed. | That is how Strategy computes them; it explains why the two API figures imply about 430M and 450M shares. | One share count for both. |
| R7 | Every rebuild input traces to a filing: the class A count comes from one even though a research agent's figure (with one week counted twice) matched the API better. | Every input must trace to a filing. The error rose from 0.02% to 0.11%, still inside the gate (notes #14). | The closer, untraceable count. |
| R8 | The five first-order formulas stand next to an exact recompute of n. | First-order values explain the sign and the break-even; the exact recompute uses the cash actually received, so issue fees show as the gap. | First-order only (the spec's overrun fallback, not needed). |
| R9 | The price date for a week is the last US trading day on or before the week's end, for every ticker. The coin close for day D is CoinGecko's 00:00 UTC point on D+1. Yahoo's quote close is used, not the adjusted close. | One rule for all tickers; the coin point sits about four hours after the US equity close; adjusted closes change after the fact. | Week-end coin prices against Friday stock prices. |
| R10 | BMNP's q uses its $100 liquidation preference, and the issue week uses its $80 issue price (q = 0.80). | Certificate of Designations. After a follow-on BMNP sale the preference floats to max($100, last sale, 10-day average); none through 9/21. Checking each week's release for a sale is a manual rule; no code does it yet. | Trading price as notional. |

## Strategy data

| # | decision | why | alternative |
|---|---|---|---|
| S1 | Parse 8-K tables by row label, never by position. An unknown label, ticker or heading raises. | A new security or a moved table fails loudly instead of landing in the wrong column. | Positional parsing. |
| S2 | No synthetic fallback data. If a source fails, the run fails. | A number on the page must trace to a filing or a named price feed. | Filling gaps with estimates silently. |
| S3 | Each week's rolled BTC must equal the 8-K's stated holdings exactly. Two 1-BTC gaps, where Strategy's own filings disagree with each other, are listed in `KNOWN_FILING_GAPS` with their arithmetic. | Keeps the check exact; any other 1-BTC miss still fails (notes #2). | A tolerance that would hide real misses. |
| S4 | R is taken as each 8-K states it. From 2026-08-02 the roll is a check, within half a unit of each filing's last disclosed digit. Before that, the unexplained change prints, labeled. | Filings round R to $10-50M and, before August, don't itemize flows into it, so the spec's exact roll could not pass (notes #4). | The spec's rule: rolled reserve equals every 8-K. |
| S5 | Before 2026-08-23, R is the USD Reserve alone. The $1.59B of USD Cash that appears that week gets no special row. | The 8-K filed 2026-08-24 funds it from that week's MSTR sale proceeds, already booked. The rule first said the cash existed before; the engine's residual of exactly $1,570.1M showed otherwise, and the rule was corrected from the filing (notes #5, #19). | A `disclosure` row for pre-existing cash. |
| S6 | The 2026-06-30 quarter-end holdings row carries R from the prior 8-K, labeled. | No balance is stated for that date. | Dropping the row. |
| S7 | Dividend and interest `carry` rows exist only where a filing states an amount. | Many 8-Ks say dividends were paid without the amount, or from BTC-sale proceeds with no split. Unstated amounts land in the residual, labeled (notes #3). | Estimating dividends from rate × notional. |
| S8 | Any STRE trade raises. | STRE trades in EUR and the filings state no rate. | Converting at an assumed rate. |
| S9 | STRC retirements use the 8-K's disclosed average price where given, else the daily close; `avg_price` records which. | The filings do not always state it. | Always the daily close. |
| S10 | Preferred notional and class A shares roll forward from Q2 10-Q anchors by each 8-K's sales and repurchases; class B and awards stay at 10-Q values until the next 10-Q. | The weekly 8-Ks give flows, not levels. | Levels from the API. |
| S11 | Parsers use structural guards instead of word lists: every $ amount in a reserve sentence must be consumed, every "USD Reserve" mention must sit inside a recognized pattern, hedged or negated flows ("may use up to", "did not use") raise. | Three review rounds of word lists kept finding new phrasings; structural rules held on the full corpus (notes #16). | Growing lists of phrasings. |
| S12 | Sentence splitting handles "$5.04" and "U.S.". | A naive split on periods produced empty output (notes #18). | Splitting on every period. |

## BitMine data

| # | decision | why | alternative |
|---|---|---|---|
| B1 | C = ETH held. R = the release's "total cash & marketable securities", labeled as including securities. BitMine's BTC and equity stakes ("moonshots", about $300M) are excluded, and the page states the excluded amount. | Strategy's definition counts only the coin reserve and USD assets (notes #10). | Counting BTC and stakes as reserve. |
| B2 | No staking carry rows. The stated holdings change is the week's ETH change. A staking estimate is saved to `staking.csv` only to size a bias. | "ETH acquired" equals the stated holdings change in 13 of 16 weeks, so it already includes staking; a separate estimate counted it twice (site check +0.52%, a fail). Without it: −0.0006%. This reversed an earlier recommendation made before looking at the weekly data (notes #6, #15). | Staking as carry, per the spec and the first decision. |
| B3 | BitMine S is estimated between filings: anchored at 5/31 (579,652,432) and 7/09 (603,226,394), rolled by disclosed buybacks, with unreported issuance = the week's unexplained change in R ÷ that week's BMNR close. Between anchors the estimates are scaled to land on 7/09 exactly; after it they accumulate until the fiscal-year 10-K. | BitMine never states its share count weekly, and about $1.08B of cash arrived 8/16 to 9/20 with no stated source (notes #7). | Holding S flat between filings, which would miss the issuance. |
| B4 | Estimated shares live in `balances.csv` (`source` says "S estimated") and in `attribution.csv` as `est_issuance`, never as `actions.csv` rows. | `actions.csv` holds only what a filing states. | Synthetic action rows. |
| B5 | The known upward bias in S is stated, not corrected: staked ETH costed as purchases inflates unexplained cash, about +0.43% of S by 2026-09-20. Weeks with negative unexplained cash add 0 shares. | The 10-K reanchor removes it; a correction would add a second estimate on top of the first. | An adjusted S. |
| B6 | The USD of each ETH purchase is units × that week's ETH close, labeled in `note`. Four buyback prices use the BMNR close, labeled. | Releases give ETH bought in coins only. Coin trades are neutral on day one, so the estimate does not move n. | Leaving usd blank. |
| B7 | One release dated "As of June 28" is assigned to 2026-07-05, listed in `KNOWN_DATE_ERRATA`. | The release's own staking sentence and dateline give July 5 (notes #9). | Trusting the header date. |
| B8 | A BitMine holdings change with no parsed purchase raises. | A missed purchase sentence would otherwise pass silently. | Inferring the purchase from the change. |
| B9 | The ETH check compares against strategicethreserve.xyz at the site's own snapshot date and fails if the snapshot is over six weeks old. The site's data is read from its page. | The site has no API and lags about four weeks (notes #8). | The spec's check on the latest date, which could not pass. |

## SharpLink data

| # | decision | why | alternative |
|---|---|---|---|
| L1 | Add SharpLink (SBET, CIK 1981535) as a third firm, with rows only on the dates its filings state ETH holdings: 6/16, 6/28, 6/30, 8/03. Nothing carries forward between them. | The user's choice. SharpLink files no weekly update; its last 8-K was 2026-08-10. Carried-forward weeks would show numbers no filing states. | Weekly rows with carried-forward holdings; leaving SharpLink out. |
| L2 | Use CIK 1981535, SharpLink, Inc. | The old SharpLink Gaming Ltd. (CIK 1025561) stopped filing in 2024. | The old CIK. |
| L3 | C = stated "Total ETH Holdings", including LsETH and weETH at their stated as-if-redeemed equivalence. The parser requires native + LsETH + weETH = total wherever the filing gives the parts. | The filings state the total and its parts; there is no BitMine analogue. | Native ETH only. |
| L4 | A `carry` row per filed date = stated ETH change − stated purchases, labeled "inferred staking/LST accrual". | Unlike BitMine, SharpLink states purchases separately in ETH and dollars, so the difference is observable. | No carry, as for BitMine. |
| L5 | R = 6/30 balance-sheet cash, rolled to other dates by filed cash flows. D = 0 and F = 0. | Cash is stated only for 6/30 (in the 8/10 release and the 10-Q). The 10-Q shows only payables, no debt, converts or issued preferred. | Estimating operating costs. |
| L6 | No q and no rotation line. The map draws SharpLink at q = 1, where m = q means m = 1. | With no preferred, only issuing (adds while m > 1) and buying back (adds while m < 1) apply. | A separate chart. |
| L7 | S = 10-Q basic counts rolled by filed issuance and buybacks, plus RSUs, performance RSUs, and warrants and options in the money at the SBET close. July grants are taken as of 7/31, stated as an assumption. | Strategy's definition counts awards and in-the-money instruments. The 10-Q says only "In July 2026". | BitMine's cash-based estimate, which needs weekly R. |
| L8 | Issue and buyback dollars come from the 10-Q equity statement (net proceeds, treasury cost), with a note saying so. | The 8-K gives only gross figures. | Gross proceeds. |
| L9 | Only 8-Ks with a capital-relevant item (1.01, 2.02, 2.03, 3.02, 3.03, 7.01, 8.01) are read; others print a skip line. Every 10-Q since 6/01 is read for its own quarter. | An unrelated 8-K (e.g. a director change) should not stop the weekly refresh; a capital action with no holdings figure still raises. Reading each 10-Q for its own quarter keeps Q2 figures after Q3 files. | Reading every 8-K. |
| L10 | The ETH site check's six-week limit is measured from SharpLink's last filed holdings date, not the calendar, and prints how old that filing is. | Otherwise the check fails every run while SharpLink is not filing, with nothing wrong. | Calendar staleness. |

## Attribution and checks

| # | decision | why | alternative |
|---|---|---|---|
| A1 | Each week's change in n splits in a fixed order, recomputing n exactly after each part: price, in-the-money flips, each action in filing order at its own price, carry, BitMine estimated issuance, residual. | Order-dependent parts need one fixed order to be reproducible, and the parts must sum to the observed change. | First-order sums only, which would not add up. |
| A2 | The unit is Δn in coins per share; the page also shows Δn × S × p in USD, "value to common". | Coins per share is the ruler; dollars are easier to read. | Dollars only. |
| A3 | A Strategy week from 2026-08-02 passes the residual test if the residual is under 5% of the week's change, or within that week's R rounding. The output says which. | A quiet week with rounded filings fails otherwise with nothing wrong: 8/30 had a $10.6M residual on a $107M week, inside ±$20M rounding. | The spec's flat 5%. |
| A4 | Weeks before 2026-08-02, all BitMine weeks and all SharpLink dates report their residual, labeled, without a test. | R is not checked there, so the residual carries known unexplained flows. | Testing them against a bar they cannot meet. |
| A5 | `check.py` runs against live sources; a network failure counts as a failure. | A check that passes when it cannot reach the API proves nothing. | Skipping on network errors. |
| A6 | Numbers written in docs come from a test's pinned output, not a separate run. | Step 0 percentages were first written from a different API snapshot than the test pinned (notes #13). | Copying from a console session. |
| A7 | Test anchors: the Bitcoin Magazine STRC week ($24.998M retiring $28.893M notional adds $3.895M) to the dollar; each formula is zero at m = 1 or q = 1; each rotation is zero at m = q; first order within 1% of exact for an action under 1% of market cap. | A public figure to reproduce, plus identities any correct engine satisfies. | Tests only against our own outputs. |
| A8 | The data row for 7/26 uses the 8-K's rounded $25.0M ($3.893M); the test uses $24.998M ($3.895M). | Data follows the filing; the test anchors to the published figure. | Editing the data to match the article. |

## Page and memo

| # | decision | why | alternative |
|---|---|---|---|
| M1 | Facts, never verdicts: state each action's per-share effect and where break-even sits. No price targets, forecasts or investment words. No adjectives on numbers, no em dashes. Applies to the page, memo, README, PRs and commits. | The main reputational risk is reading as a judgment on a firm's decisions. | Commentary. |
| M2 | Headlines are figures only, in one form: "At a net mNAV of m, Strategy's STRC rotation adds net sats per share while STRC trades below $X." | The break-even price is a fact anyone can check against the next close. | A headline about which firm did better. |
| M3 | "Latest filed week", never "today". | The numbers come from the last filing, which can be days old. | "Today". |
| M4 | The memo title states counts: Strategy on its adding side in 18 of 18 filed weeks, BitMine in 0 of 15, SharpLink with m below 1 on 4 of 4 dates. | The spec's hypothesis (both rotations add) did not hold for BitMine; counts state that without a verdict (notes #11). | The hypothesis as the title. |
| M5 | A memo footnote states BitMine's closest week (8/23, 0.53% above the line) next to its share-estimate bias, and `dat/memo.py` fails the build if removing the bias would move any week across the line. The bias is computed per week from `staking.csv`. | The finding's margin is near the bias, so the build guards it. A hardcoded bias would have failed every run from about 2026-10-13. | A footnote with no guard; a hardcoded bias. |
| M6 | Plain HTML, CSS and JavaScript with hand-drawn SVG, no external scripts or styles. | Enough for one map and bar charts, nothing to load or break. | The spec's chart library from jsDelivr. |
| M7 | The map shares one axis range (0.65 to 1.50) for q and m, so m = q is a true 45° diagonal. The right side stays empty. | A true diagonal matters more than filling the space; m reaches 1.42 (notes #23). | Separate ranges that bend the line visually. |
| M8 | Attribution bars leave out price and convert-flip moves; they appear in tooltips and the table. | The price move is often 10 to 50 times a week's actions and would hide them. | Bars dominated by price. |
| M9 | Map dots are links to filings; each bar chart is one tab stop with arrow keys; every chart has a table view; the seven-color palette is validated in light and dark. | Keyboard and screen-reader access, and every mark traces to a filing. | Hover-only charts. |
| M10 | The memo PDF is printed by headless Chrome from `docs/memo.html`. | No new dependency; the CI runner already has Chrome. | A PDF library. |
| M11 | Fallbacks and estimates are labeled on the page itself, not only in the methodology. | A reader of one chart should see which numbers are estimated. | A methods page only. |

## Automation

| # | decision | why | alternative |
|---|---|---|---|
| O1 | `snapshot.yml` runs daily at 21:30 UTC, after the US close, commits the KPI row first, then runs `check.py` with a 5-minute step timeout. | GitHub cancels (does not fail) a timed-out job, which would skip both the commit and the alert. Committing first keeps the row whatever happens after (notes #20). | Checking before committing. |
| O2 | `check.json` is written to a temp file and moved into place; `build_site` tolerates a missing or invalid one. | A shell redirect left a 0-byte file that would have broken the first deploy (notes #21). | Redirecting straight to the file. |
| O3 | `refresh.yml` runs Tuesdays at 14:00 UTC, reruns the whole pipeline, builds the PDF, runs pytest and `check.py`, opens a `refresh/<date>` PR with the check output, and squash-merges only when all pass and CI on that commit is green. | Strategy and BitMine file on Mondays. Without a refresh the page froze at the last hand-run week. Merging through a PR keeps `main` protected. | Hand-run updates; pushing to `main` directly. |
| O4 | A new 10-Q or 10-K for a period after the anchors makes the refresh exit 2: data rebuilds, the PR stays open, and an issue asks a person to reanchor. No automatic reanchoring. | Anchor counts come from filing sections the weekly parsers don't read, and a wrong anchor moves every later week. | Parsing 10-Q balance sheets automatically. |
| O5 | Scheduled failures open one issue per failure streak and comment on it after. | One alert per problem, not one per day. | An issue per failed run. |
| O6 | The EDGAR client retries only HTTP 429 and 503, three times with 5, 15 and 45 s backoff, then fails loudly. Other errors fail at once. | The first refresh run (started by hand) failed on one transient 503. Retrying only rate-limit and unavailable responses keeps real errors loud. | Retrying everything; a cached fallback. |
| O7 | EDGAR requests send a User-Agent with a contact address and stay under 10 per second (0.6 s throttle); filings are cached in `data/raw/`, gitignored, and across refresh runs. | SEC fair-access rules. The cache makes reruns fast and rebuildable. | Unthrottled fetches. |
| O8 | The repo setting "Allow GitHub Actions to create and approve pull requests" is on. | `refresh.yml` needs it to open and merge its PR. Turned on with the user's approval. | Merging refresh PRs by hand. |
| O9 | CSVs are written with `\n` line endings. | Python's `csv` default is CRLF, which git flagged (notes #17). | Default endings. |
