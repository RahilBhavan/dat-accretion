# How it was made

The project went from an empty repo to a self-refreshing page in two days, 2026-09-25 and 2026-09-26, in
11 pull requests after one scaffold commit. This page tells that story in order: the plan, the working method, each step and what it
found, and how the result differs from the plan. The reasons behind each choice are in
[`decisions.md`](decisions.md); the problems hit along the way are in [`build-notes.md`](build-notes.md).

## The plan

Before any code, a written spec set out the question, the math, the data sources, the architecture, a
build plan of seven steps (0 to 6), and one acceptance check per step. The spec's hypothesis was that both
opposite rotations add net coins per share, because Strategy and BitMine sit on opposite sides of the line
m = q. The spec also said what happens if they don't: the map still states the exact break-even price as a
fact.

The spec lives outside this repo because it also holds material that is not about the engineering. Its
engineering half is mirrored here, in `CLAUDE.md` and `.claude/rules/`.

The shape was copied from an earlier project of the author's, Spine: Python 3.12, the standard library plus
numpy, one `python -m` module per step, a static site, and GitHub Actions committing data to a separate
branch. No database and no framework.

## The working method

The build used Claude Code, with the plan and the decisions kept by the person directing it and the work
split among three kinds of agent:

| role | does | never |
|---|---|---|
| orchestrator | reads the spec and rules, asks the user when a choice changes the output, dispatches the others, writes the PR | writes the step's code |
| `runner` | implements one step against a named acceptance check | decides open questions |
| `reviewer` | adversarially checks a finished change: reruns tests, recomputes numbers by hand, looks for silent failures | edits |
| `filing-verifier` (`.claude/agents/`) | opens each filing at a row's `filing_url` and confirms the row's numbers appear in it | edits |

The `build-step` skill (`.claude/skills/build-step/SKILL.md`) fixes the loop for every step:

1. Read the step's row in the build plan, its spec section, and `.claude/rules/*`. Ask the user about any
   open decision that changes the output.
2. Branch from `main` with the step's branch name.
3. Dispatch `runner` with the exact files, the acceptance check as a command, a style anchor, and the hard
   constraints (stdlib plus numpy, parse by label, fail loudly, every row keeps `filing_url`).
4. Dispatch `reviewer`, and for the parsing steps `filing-verifier`, in parallel. Send must-fix items back to the same runner.
   Repeat until clean.
5. Commit, push, open a PR whose body pastes the acceptance check's real output, and wait for CI.
6. Merge by squash only when the user says so.

`main` is protected: after the scaffold commit, every change landed through a squash-merged PR with the
`tests` check green.

Three rule files keep decisions from drifting between steps. `method.md` is the math source of truth,
`data.md` covers sources and provenance, and `framing.md` covers page language. When a step settled a
question, the decision went into the rule file with its date, in the same PR.

## Step by step

| step | PR | merged | work | tests after |
|---|---|---|---|---|
| scaffold | (direct) | 09-25 | layout, rule files, `build-step` skill, `filing-verifier` agent | 0 |
| 0a | #1 | 09-25 | daily KPI snapshot and CI | 5 |
| 0b | #2 | 09-25 | Strategy's net definition rebuilt from filings; BMNP terms | 11 |
| 1 | #3 | 09-25 | Strategy 8-Ks parsed into `actions.csv`, `stated.csv` | 19 |
| 2 | #4 | 09-25 | Strategy balances, daily prices, weekly m and q | 29 |
| 3 | #5 | 09-25 | BitMine actions, balances, weekly m and q | 72 |
| 4 | #6 | 09-25 | attribution engine with exact recompute | 88 |
| 5 | #7 | 09-25 | public page and Pages deploy | 96 |
| 6 | #8 | 09-26 | `check.py`, memo, methodology, workflow hardening | 107 |
| refresh | #9 | 09-26 | weekly job that rebuilds everything from new filings | 114 |
| 7 | #10 | 09-26 | SharpLink as a third firm | 134 |
| retry | #12 | 09-26 | EDGAR 429 and 503 retry with backoff | 137 |

### Step 0a: start the clock on the KPI snapshot (#1)

Strategy's KPI API returns only the current value. Every day without a saved snapshot is lost for good, so
this went first, before any analysis. `dat/snapshot_kpi.py` fetches the API plus the MSTR close, checks
every field is a finite positive number, appends a row, and saves the raw JSON for the day.
`snapshot.yml` runs it daily and appends to the `data` branch without ever force-pushing.

### Step 0b: rebuild Strategy's metric from filings (#2)

The gate: rebuild net sats per share from the latest 8-K and the Q2 10-Q within 0.5% of the API, or fall
back to anchoring levels on the API. Reading the glossary in Strategy's 2026-08-24 FWP showed the spec's
definition differed in three ways (in-the-money converts, fully diluted shares, USD Cash). The engine
adopted Strategy's version, as the spec required. The rebuild landed at +0.107% on net sats per share and
−0.114% on mNAV, so the gate passed and levels are computed, not borrowed. The test pins those numbers
against one saved snapshot. BMNP's terms came from its Certificate of Designations.

### Step 1: parse Strategy's 8-Ks (#3)

`dat/edgar.py` became the one SEC client: identifying User-Agent, 0.6 s throttle, disk cache. The parser
reads each 8-K's ATM, bitcoin, repurchase and reserve sections by label. Acceptance: each week's rolled BTC
equals the 8-K's stated holdings exactly. It did, except for two weeks where Strategy's own filings
disagree with each other by 1 BTC. Both are listed with their arithmetic; any other miss fails. The
reviewer's first pass found a path where a trade could be skipped silently. It was closed before merge.

### Step 2: balances and prices (#4)

The spec's check (rolled USD Reserve equals every 8-K) could not pass: the filings round the reserve to
$10 to 50 million and, before August, don't itemize flows into it. With the user, the rule changed to:
take R as stated, and use the roll as a check within each filing's rounding from 2026-08-02. Eight checked
weeks pass. Prices come from Yahoo (settled closes, not adjusted) and CoinGecko.

### Step 3: BitMine (#5)

BitMine's weekly releases are prose, not tables, and never state a share count. Three decisions came out of
this step: what counts as C, R and F for BitMine; no separate staking rows (the data showed "ETH acquired"
already includes staking); and how to estimate S between filings. The reviewer ran three rounds, each
finding a new phrasing the parsers' word lists missed. Rounds 2 and 3 replaced the lists with structural
rules: every dollar amount in a reserve sentence must be consumed, every "USD Reserve" mention must sit in
a known pattern, hedged flows raise, and a holdings change with no parsed purchase raises. BitMine's
rolled ETH matched strategicethreserve.xyz at −0.0006%.

### Step 4: the engine (#6)

`dat/engine.py` splits each week's change in n into price, convert flips, each action, carry, and a
residual, recomputing n exactly after each part. The residual caught an error in the rules: `method.md`
said the $1.59 billion of USD Cash first reported for 2026-08-23 already existed. The residual was
$1,570.1 million, exactly the 8-K's "remaining net proceeds from MSTR Stock sales". The cash was new and was
already counted. The rule was corrected from the filing, and the week's residual fell from 37.9% to 0.5%.
The reviewer rebuilt four weeks from raw balances in an independent script; every row matched to 7 or more
digits.

### Step 5: the page (#7)

Plain HTML, CSS and JavaScript with hand-drawn SVG and no external scripts. The map shares one axis range
for q and m so the line m = q is a true diagonal. Every line of copy was checked against `framing.md`.
Acceptance was measured in headless Chromium: at 375 px, the page width equals the viewport and all 33 dots
link to filings. Screenshots at 375 and 1280 px led to three fixes.

### Step 6: done check, memo, methodology (#8)

`check.py` compares the rebuild against live sources and exits 0 only if every check passes: 12 of 12 at
merge. The first review failed the workflow: `check.py` ran before the KPI row was committed, so a slow
EDGAR could time out the job, and GitHub cancels rather than fails a timed-out job, skipping both the commit
and the alert. The KPI row now commits first. The data showed the spec's hypothesis did not hold for
BitMine, so the memo states the counts: Strategy on its adding side in 18 of 18 weeks, BitMine in 0 of 15.
Because BitMine's closest week is near the size of a known bias in its share estimate, `dat/memo.py` fails
the build if removing that bias would move any week across the line.

### After v1: weekly refresh, SharpLink, retry (#9, #10, #12)

- **Refresh (#9)**: without it the page would freeze at the last hand-run week. `refresh.yml` runs the
  pipeline every Tuesday, opens a PR with the check output, and merges it only when everything passes. It
  stops for a person when a new 10-Q or 10-K means the anchors need updating.
- **SharpLink (#10)**: the spec's planned v1.1. SharpLink files irregularly, so, by the user's choice, it
  has rows only on the four dates its filings state ETH holdings. MSTR and BMNR rows came out byte-identical.
- **Retry (#12)**: the first refresh run, started by hand, failed on one HTTP 503 from EDGAR. The client now retries
  429 and 503 three times with backoff, then fails loudly as before.

## Plan against result

| spec said | result | why |
|---|---|---|
| Strategy and BitMine only; SharpLink in v1.1 | three firms | SharpLink added the same day as v1, on filed dates only |
| spec's definition of N and S | Strategy's own glossary definition | the spec's rule: Step 0 adopts Strategy's definition if it differs |
| rolled USD Reserve equals every 8-K | R as stated; roll checked within rounding from 8/02 | filings round R and don't itemize early flows |
| BitMine staking as carry rows | no staking rows | "ETH acquired" already includes staking |
| BitMine ETH within 0.1% of the site on the latest date | compared at the site's snapshot date | the site lags about four weeks |
| residual under 5% every week | under 5% or within R rounding, Strategy from 8/02 | a quiet week with rounded filings fails with nothing wrong |
| one chart library from jsDelivr | no external scripts | hand-drawn SVG was enough |
| hypothesis: both rotations add | Strategy 18 of 18 weeks, BitMine 0 of 15 | stated as counts, with the bias sensitivity |
| hand-run build | weekly automatic refresh | added after v1 |

## Verified

- At v1, a fresh clone with an empty filing cache rebuilds all four derived CSVs byte-identical to the committed
  ones.
- After SharpLink, 137 offline tests pass and `python check.py` passes 16 of 16 against live data.
- `filing-verifier` matched every row of `actions.csv` and `stated.csv` to its filing.
