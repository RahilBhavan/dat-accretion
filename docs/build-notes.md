# Build notes: problems hit in Steps 0 to 6

What went wrong or surprised us while building, what we did about it, and what it means for the
numbers. Newest decisions are also recorded as rules in `.claude/rules/`.

## Where the spec met the filings

| # | Problem | What we did | Effect on the numbers |
|---|---|---|---|
| 1 | Strategy's net definition differs from the spec: only out-of-the-money converts count as debt, and net sats per share uses Fully Diluted shares (~430M) while gross uses Assumed Diluted (~450M). | Adopted Strategy's definition from the 2026-08-24 FWP glossary, per the spec's own rule. | Rebuild within 0.11% of the API; the 2030A note moves between D and S as MSTR crosses $149.77. |
| 2 | Strategy's own 8-Ks disagree by 1 BTC twice (filed 6/15 and 8/03); the next week balances only from the corrected figure. | Kept the check exact and listed both weeks in `KNOWN_FILING_GAPS` with the arithmetic. | None; any other 1-BTC miss still fails. |
| 3 | Many 8-Ks say dividends were paid without the amount, or from BTC-sale proceeds with no split. | No guessed amounts. Carry rows only where the filing states one. | Pre-August weeks carry unexplained change into Step 4's residual. |
| 4 | Spec's Step 2 test (rolled USD Reserve equals every 8-K) can't pass: the reserve is rounded to the nearest $1M, $10M or $100M, early inflows aren't itemized, and it includes unsettled ATM proceeds. | Decision: R taken as stated; roll used as a check from 8/02 within each filing's rounding. | Eight checked weeks pass; earlier weeks print their unexplained change, labeled. |
| 5 | R jumps $1.59B on 8/23 when USD Cash first appears. | First treated as pre-existing cash (a `disclosure` row); the engine's residual ($1,570.1M, exactly) showed the 8-K funds it from that week's MSTR sale proceeds, already booked. Row removed. | 8/23 residual falls from 37.9% to ~0.5%. See #19. |
| 6 | BitMine's "ETH acquired" equals the stated holdings change almost every week, so a separate staking estimate double counts. | Reversed the earlier staking decision: no staking rows; the estimate is a printed diagnostic. | Site check went from +0.52% (fail) to −0.0006%. |
| 7 | BitMine never states its share count between filings; ~$1.08B of cash arrived 8/16-9/20 with no stated source. | Anchored at 5/31 and 7/09; unreported issuance estimated from unexplained cash, labeled, reanchored at the 10-K. | ≈ +0.43% upward bias in S by 9/20 (staked ETH costed as purchases). |
| 8 | strategicethreserve.xyz has no API and lags about four weeks. | Read the data embedded in its page; compare at the site's snapshot date; fail if over six weeks stale. | Check compares 8/23, not the latest week. |
| 9 | One BitMine release is dated "As of June 28" but reports July 5 holdings. | `KNOWN_DATE_ERRATA`, justified by the release's own staking sentence and dateline. | Week assigned to 7/05. |
| 10 | BitMine reports USD only as "cash & marketable securities" and holds ~$300M of BTC and equity stakes. | Decision: R = cash & securities (labeled); BTC and stakes excluded, as Strategy's definition implies. | Stated on the page. |
| 11 | The spec's hypothesis was that both rotations add. The data: Strategy's rotation sat on its adding side in 18 of 18 filed weeks, BitMine's in 0 of 15. BitMine's closest week (8/23) is 0.53% above the line, near the 0.43% upward bias in its estimated share count. | The memo title states the counts; a footnote states the margin; `dat/memo.py` fails the build if removing the bias would put any week on the other side, or if a newer week arrives without the bias being recomputed. | Finding stated as counts, with its sensitivity. |

## Where our own process slipped

| # | Problem | Caught by | Fix and lesson |
|---|---|---|---|
| 12 | `git add -A` committed `egg-info` build output. | Status output after the commit. | Removed and gitignored before merge. Read `git status` before staging everything. |
| 13 | Wrote Step 0 rebuild percentages from a different API snapshot than the test pinned. | Runner. | Doc now cites the pinned snapshot. Numbers in docs come from the test's own output. |
| 14 | A research agent's class A share count didn't trace to a filing (one week counted twice). | Reviewer. | Replaced with the traceable count; error rose from 0.02% to 0.11%, still inside the gate. The honest number wins over the closer one. |
| 15 | Recommended the staking estimate before looking at the weekly data (see #6). | Runner's diagnostic. | Reversed with the user. Check the data before proposing a modeling rule. |
| 16 | Parsers skipped trades silently in edge cases: a filing with trades but no BTC section, a STRE buyback, and phrasings outside a word list. | Reviewer, three rounds. | Replaced word lists with structural rules: every $ amount in a reserve sentence must be consumed, every "USD Reserve" mention must sit in a recognized pattern, hedged flows raise, and a BitMine holdings change with no parsed purchase raises. |
| 17 | `csv` writers defaulted to CRLF line endings. | git's CRLF warning. | `lineterminator='\n'` everywhere. |
| 18 | A quick scan split sentences on the period in "$5.04" and "U.S.". | Empty output. | `sentences()` in `parse_mstr.py` handles both, with a test. |
| 19 | Asserted in method.md that the 8/23 USD Cash "existed before" without reading the 8-K that established it. | Step 4 engine residual; runner traced it to the filing. | Rule corrected from the filing text. Read the source before writing a rule about it, the same lesson as #15. |
| 20 | `check.py` ran before the daily KPI commit. A slow EDGAR could exceed the job timeout; GitHub then cancels (not fails) the job, skipping both the commit and the alert. | Reviewer. | KPI row now commits first; the check has a 5-minute step timeout and the fetch a 3-minute one; a crash or timeout still records a fail status. |
| 21 | `git show ... > data/check.json \|\| true` left a 0-byte file when the branch had none, which would have broken the first Pages deploy. | Reviewer, reproduced in a scratch shell. | Write to a temp file and move it; `build_site` also tolerates an empty or invalid check file. |
| 22 | A runner stalled for 10 minutes on a long live-network run with no output. | Watchdog. | Resumed with a 300-second cap on network commands and progress output every 10 URLs. |
| 23 | Asked for a tighter shared map domain without checking that m reaches 1.42. | Runner. | Kept the full shared domain: a true 45° line matters more than filling the right third. |

## Checks that hold today

- Rebuilt from a fresh clone with an empty filing cache: all four derived CSVs are byte-identical to the committed ones.
- At v1: 107 offline tests and `python check.py` 12/12 against live data (after SharpLink: 137 tests, 16/16); filing-verifier matched every row of actions.csv and stated.csv to its filing.
