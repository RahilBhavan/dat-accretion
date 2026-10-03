# Overview: what this project is and how it works

Start here. This page explains the question the project answers, the one number it measures everything
with, what it produces, and how the code turns SEC filings into the page.

**In short.** Strategy, BitMine and SharpLink each sell, buy back and retire stock to change how much
crypto stands behind each share. This project measures every such action since 2026-06-01 with
Strategy's own net coins per share definition, applied to all three firms, and shows the price at which
each program stops adding. Every figure links to the SEC filing it came from. Read the
[page](https://rahilbhavan.github.io/dat-accretion/) first, then come back here for how it works.

The other documents go deeper:

| document | read it for |
|---|---|
| `docs/overview.md` (this page) | what the project does and how the pieces fit |
| [`docs/how-it-was-made.md`](how-it-was-made.md) | the build, step by step, with what each step found |
| [`docs/decisions.md`](decisions.md) | every decision, why it was made, and what was rejected |
| [`docs/methodology.md`](methodology.md) | the definitions, formulas and labeled estimates, for a reader checking the numbers |
| [`docs/build-notes.md`](build-notes.md) | problems hit while building and what they did to the numbers |
| [`.claude/rules/`](../.claude/rules/) | the working rules the code follows: `method.md` (math), `data.md` (sources), `framing.md` (language) |

## The question

Strategy (MSTR) holds bitcoin. BitMine (BMNR) and SharpLink (SBET) hold ether. Each raises and returns
capital every week or month: it sells common stock, buys it back, sells preferred stock, retires
preferred, and buys or sells coins.

In mid-2026 two of these firms ran opposite trades. Strategy sold common stock to retire its STRC
preferred. BitMine sold its new BMNP preferred to buy back common stock. The project asks one question of
both, and of SharpLink:

> Using Strategy's own net coins per share definition, what is each action's per-share effect per dollar,
> and at what price does that effect change sign?

It states the answer as figures. It does not say whether any decision was right.

## The ruler: net coins per share

Strategy publishes a metric called net sats per share: how much bitcoin each fully diluted share owns
after netting out the claims that rank ahead of common stock. The glossary in Strategy's 2026-08-24 FWP
defines it. This project applies that same definition to all three firms.

Per firm, per week:

```
N = C + (R − D − F) / p      net coins: coins held, plus USD assets, less debt and preferred, in coins
n = N / S                    net coins per share
m = s / (p · n)              net mNAV: share price over the net coin value per share
q = preferred price / $100   preferred price over its notional
```

C is coins held, R is USD assets, D is out-of-the-money convertible debt, F is preferred notional, S is
fully diluted shares, p is the coin price, s is the common share price. `docs/methodology.md` gives each
term exactly.

## The break-even line

Every capital action moves n by a predictable amount. With k = dollars / (p · S):

| action | change in n | adds when |
|---|---|---|
| issue common | k · (1 − 1/m) | m > 1 |
| buy back common | k · (1/m − 1) | m < 1 |
| issue preferred | k · (1 − 1/q) | q > 1 |
| retire preferred | k · (1/q − 1) | q < 1 |
| buy or sell coins | 0 | neutral on day one |

The intuition: selling common at m = 1.2 raises $1.20 of coin value for each $1.00 of coin value the new
shares claim, so every existing share gains. Retiring preferred at q = 0.90 removes $1.00 of claim for
$0.90 of cash.

Put the two legs of a rotation together and the effect depends on m against q:

- Strategy's rotation (issue common, retire STRC) adds while m > q. It stops adding when STRC trades above
  $100 × m.
- BitMine's rotation (issue BMNP, buy back common) adds while m < q. It stops adding when BMNP trades below
  $100 × m.
- SharpLink has no preferred, so it has no rotation line. Issuing common adds while m > 1; buying back
  adds while m < 1.

The page plots every firm-week on one chart with q across and m up. The diagonal m = q is the break-even
line for both rotations.

## What it produces

1. **A public page** (https://rahilbhavan.github.io/dat-accretion/). Its h1 is the memo's title. Below
   it:
   - one card per firm for the latest filed week, drawn as a bullet track: the preferred close, a tick at
     break-even, and the gap (#20). STRC stops adding above $100 × m; BMNP adds above $100 × m.
     SharpLink's card gives m and the date of its last filed holdings.
   - a "By week" chart: each week's preferred close against its break-even, $100 × m, for STRC and BMNP, and SharpLink's m against 1
     (#20).
   - the break-even map. Every dot links to its SEC filing.
   - weekly attribution bars in five colours, with a tick for each week's net change and a totals strip per
     firm since its anchor week: filed actions, carry, estimated issuance (BitMine only) and residual, as
     value to common (#20).
   - the method (symbols, formulas and sources fold; caveats and the done check stay open) and CSV downloads.
2. **A one-page memo** (`docs/memo.md`, `docs/memo.pdf`): the finding as counts, the ruler, the line, and
   where each firm sits in its latest filed week.
3. **The data and the engine**: CSVs under `data/`, the Python that builds them, and `check.py`, which
   compares the rebuilt numbers against live sources.
4. **Social drafts** (`python -m dat.social`, #19): post-ready SVG cards, map replay frames and draft
   posts, written to `private/social/<week_end>/`, which is gitignored. The module uses only the standard
   library and reads the same `build()` output as the page. Rendering to PNG, MP4 and GIF happens outside
   the package, and posting stays manual.

## Who it is for and how to use it

The page answers one question with a price, so a reader can check the answer against the filings
instead of taking anyone's view of it.

| reader | start at | what they get |
|---|---|---|
| holders and analysts of MSTR, BMNR, SBET | the firm cards and the break-even map | the preferred price at which each rotation stops adding net coins per share, and where the latest filed week sits against it |
| finance teams at the three firms | `actions.csv` and `attribution.csv` | their own filings measured with Strategy's own definition, one row per action, each linked to its filing, so a wrong number can be pointed to a line |
| journalists and researchers | the memo and the CSVs | a weekly series since 2026-06-01 in which every number traces to a filing URL, and a done check that says when the page last passed |
| engineers working with SEC filings | `dat/` and `tests/` | a worked pattern: parse prose filings by row label and fail loudly, roll quarterly anchors forward inside stated tolerances, split each week's change into parts and report what is left |

### Reading one week

1. Pick a dot on the map. Its position is that week's q (across) and m (up); the diagonal is m = q.
2. Open its filing from the dot's link and find the action rows in `actions.csv` for that week.
3. In `attribution.csv`, the week's parts (price, convert flips, each action, carry, residual) sum to
   the observed change in net coins per share. The bars show the same parts as value to common.

### What it does not tell you

- Whether any decision was right. The project states effects at disclosed prices and where break-even
  sits, nothing more.
- Where prices go next. There are no forecasts or targets.
- Exact values between filings for everything. BitMine's share count is estimated between filings and
  biased upward by its staking (see `docs/methodology.md`); SharpLink has rows only on the dates it
  files holdings; first-order values are labeled where they stand in for exact ones.
- A live value when the done check fails. The page then keeps its last passing build until the check
  passes again.

## How the pipeline works

Each step is one module, run as `python -m dat.<module>`. `dat/refresh.py` runs them in this order,
stopping at the first failure: parse_mstr, prices, parse_bmnr, parse_sbet, balances, engine, memo,
build_site. `dat.social` is not part of the refresh; a person runs it by hand.

```
SEC EDGAR 8-Ks, 10-Qs ──> dat/edgar.py (throttled client, disk cache in data/raw/)
        │
        ├─> dat/parse_mstr.py ──> actions.csv, stated.csv   (Strategy weekly 8-Ks)
        ├─> dat/parse_bmnr.py ──> actions.csv, stated.csv, staking.csv   (BitMine weekly releases)
        └─> dat/parse_sbet.py ──> actions.csv, stated.csv   (SharpLink releases and 10-Q)

Yahoo, CoinGecko ──> dat/prices.py ──> prices.csv

actions + stated + prices ──> dat/balances.py ──> balances.csv, weekly.csv
                                                  (10-Q anchors rolled forward; m, n, q per week)

balances + weekly + actions ──> dat/engine.py ──> attribution.csv
                                                  (five formulas, exact recompute, residual)

CSVs ──> dat/memo.py ──> docs/memo.md, memo.html, map.svg
CSVs ──> dat/build_site.py ──> site/data.json ──> site/ (static HTML, CSS, JS)
      └─> build() ──> dat/social.py ──> private/social/<week_end>/ (cards, replay frames, drafts; gitignored)
```

| file | one row per | holds |
|---|---|---|
| `actions.csv` | capital action | what the filing says was done, in dollars and units, with `filing_url` |
| `stated.csv` | filing | the filing's own totals (coins held, USD Reserve, USD Cash), the parser's targets |
| `balances.csv` | firm-date | C, R, D, F, S after rolling the anchors forward |
| `prices.csv` | ticker-date | daily closes |
| `weekly.csv` | firm-week | the price date used, p, s, q, m, n |
| `attribution.csv` | firm-week-part | each part of the week's change in n: price, convert flips, each action, carry, residual |
| `staking.csv` | BitMine week | a staking estimate used only to size a known bias |

## What runs on its own

| workflow | when | what |
|---|---|---|
| `snapshot.yml` | daily, 21:30 UTC | saves Strategy's KPI API values to the `data` branch (the API keeps no history), then runs `check.py` |
| `refresh.yml` | Tuesdays, 14:00 UTC | reparses new filings, rebuilds every CSV, the memo and the site, opens a PR, and merges it only when tests, `check.py` and CI pass |
| `pages.yml` | each push to `main`, after each snapshot run, and when the refresh dispatches it | deploys the page, only when the latest `data/check.json` on the `data` branch has status `pass` (#17) |
| `ci.yml` | each PR, each push to `main`, and on refresh branches | runs pytest |

A failure in the scheduled jobs opens one GitHub issue per failure streak. When a firm files a new 10-Q or
10-K, the refresh exits 2 and leaves its PR open: a person updates the anchor share counts and balances by
hand.

If the latest done check on the `data` branch is missing or not `pass`, the Pages run fails and the live
page keeps its last passing build (#17).

## How the numbers are checked

- **Parsers**: each week's rolled coin total must equal the filing's stated total. Strategy matches
  exactly (two 1-BTC gaps in Strategy's own filings are listed with their arithmetic). BitMine matches
  strategicethreserve.xyz within 0.1%.
- **Definition**: the rebuilt net sats per share sits within 0.11% of Strategy's live KPI API.
- **Attribution**: the parts of each week sum to the observed change in n, and from 2026-08-02 the
  residual for Strategy is under 5% of the week's change or inside the filings' rounding.
- **Provenance**: every `filing_url` returns HTTP 200. In each parsing step (Strategy, BitMine,
  SharpLink), a read-only agent matched every changed row of `actions.csv` and `stated.csv` to its filing
  before merge. Weekly refresh PRs merge on the automated checks alone.

`python check.py` runs the live checks and exits 0 only if all pass. `pytest` runs 144 offline tests.
