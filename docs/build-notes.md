# Build notes: problems hit in Steps 0 to 3

What went wrong or surprised us while building, what we did about it, and what it means for the
numbers. Newest decisions are also recorded as rules in `.claude/rules/`.

## Where the spec met the filings

| # | Problem | What we did | Effect on the numbers |
|---|---|---|---|
| 1 | Strategy's net definition differs from the spec: only out-of-the-money converts count as debt, and net sats per share uses Fully Diluted shares (~430M) while gross uses Assumed Diluted (~450M). | Adopted Strategy's definition from the 2026-08-24 FWP glossary, per the spec's own rule. | Rebuild within 0.11% of the API; the 2030A note moves between D and S as MSTR crosses $149.77. |
| 2 | Strategy's own 8-Ks disagree by 1 BTC twice (filed 6/15 and 8/03); the next week balances only from the corrected figure. | Kept the check exact and listed both weeks in `KNOWN_FILING_GAPS` with the arithmetic. | None; any other 1-BTC miss still fails. |
| 3 | Many 8-Ks say dividends were paid without the amount, or from BTC-sale proceeds with no split. | No guessed amounts. Carry rows only where the filing states one. | Pre-August weeks carry unexplained change into Step 4's residual. |
| 4 | Spec's Step 2 test (rolled USD Reserve equals every 8-K) can't pass: the reserve is rounded to $10-50M, early inflows aren't itemized, and it includes unsettled ATM proceeds. | Decision: R taken as stated; roll used as a check from 8/02 within each filing's rounding. | Eight checked weeks pass; earlier weeks print their unexplained change, labeled. |
| 5 | R jumps $1.59B on 8/23 when USD Cash first appears. | First treated as pre-existing cash (a `disclosure` row); the engine's residual ($1,570.1M, exactly) showed the 8-K funds it from that week's MSTR sale proceeds, already booked. Row removed. | 8/23 residual falls from 37.9% to ~0.5%. See #18. |
| 6 | BitMine's "ETH acquired" equals the stated holdings change almost every week, so a separate staking estimate double counts. | Reversed the earlier staking decision: no staking rows; the estimate is a printed diagnostic. | Site check went from +0.52% (fail) to −0.0006%. |
| 7 | BitMine never states its share count between filings; ~$1.08B of cash arrived 8/16-9/20 with no stated source. | Anchored at 5/31 and 7/09; unreported issuance estimated from unexplained cash, labeled, reanchored at the 10-K. | ≈ +0.43% upward bias in S by 9/20 (staked ETH costed as purchases). |
| 8 | strategicethreserve.xyz has no API and lags about four weeks. | Read the data embedded in its page; compare at the site's snapshot date; fail if over six weeks stale. | Check compares 8/23, not the latest week. |
| 9 | One BitMine release is dated "As of June 28" but reports July 5 holdings. | `KNOWN_DATE_ERRATA`, justified by the release's own staking sentence and dateline. | Week assigned to 7/05. |
| 10 | BitMine reports USD only as "cash & marketable securities" and holds ~$300M of BTC and equity stakes. | Decision: R = cash & securities (labeled); BTC and stakes excluded, as Strategy's definition implies. | Stated on the page. |

## Where our own process slipped

| # | Problem | Caught by | Fix and lesson |
|---|---|---|---|
| 11 | `git add -A` committed `egg-info` build output. | Status output after the commit. | Removed and gitignored before merge. Read `git status` before staging everything. |
| 12 | Wrote Step 0 rebuild percentages from a different API snapshot than the test pinned. | Runner. | Doc now cites the pinned snapshot. Numbers in docs come from the test's own output. |
| 13 | A research agent's class A share count didn't trace to a filing (one week counted twice). | Reviewer. | Replaced with the traceable count; error rose from 0.02% to 0.11%, still inside the gate. The honest number wins over the closer one. |
| 14 | Recommended the staking estimate before looking at the weekly data (see #6). | Runner's diagnostic. | Reversed with the user. Check the data before proposing a modeling rule. |
| 15 | Parsers skipped trades silently in edge cases: a filing with trades but no BTC section, a STRE buyback, and phrasings outside a word list. | Reviewer, three rounds. | Replaced word lists with structural rules: every $ amount in a reserve sentence must be consumed, every "USD Reserve" mention must sit in a recognized pattern, hedged flows raise, and a BitMine holdings change with no parsed purchase raises. |
| 16 | `csv` writers defaulted to CRLF line endings. | git's CRLF warning. | `lineterminator='\n'` everywhere. |
| 17 | A quick scan split sentences on the period in "$5.04" and "U.S.". | Empty output. | `sentences()` in `parse_mstr.py` handles both, with a test. |
| 18 | Asserted in method.md that the 8/23 USD Cash "existed before" without reading the 8-K that established it. | Step 4 engine residual; runner traced it to the filing. | Rule corrected from the filing text. Read the source before writing a rule about it, the same lesson as #14. |

## Checks that hold today

- Rebuilt from a fresh clone with an empty filing cache: all four derived CSVs are byte-identical to the committed ones.
- 72 offline tests; filing-verifier matched every row of actions.csv and stated.csv to its filing.
