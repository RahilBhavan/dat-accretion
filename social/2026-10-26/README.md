# Oct 26 week: dat-accretion X slots (request cr-f72ff8b1)

Draft only. Nothing here was posted, merged, deployed or published. Supersedes cr-6194040b (no PR).

## Status of the six event slots

Source check: `python social/2026-10-26/source_status.py`, EDGAR submissions index, 2026-10-26T12:04:03+00:00 UTC (Oct 26 08:0x ET); output in `checks/source-status.json`. Latest filed in this repo's data: Strategy and BitMine week ended 2026-10-18 (8-Ks of 2026-10-19: Strategy 0001193125-26-424688, BitMine 0001493152-26-047517).

| # | Slot (ET) | Status | What was checked |
|---|---|---|---|
| 1 | Oct 26 09:30 Sats per Share, break-even vs STRC | HELD | EDGAR, Strategy (CIK 1050446): no 8-K filed on or after 2026-10-26; newest is the 2026-10-19 8-K for the week ended Oct 18, already in data. Strategy's company post was not checked (no X access). No refresh run, no card built. |
| 2 | Oct 26 18:00 ETH per Share | HELD | EDGAR, BitMine (CIK 1829311): no 8-K on or after 2026-10-26. `monday_refresh.py --since 2026-10-26` (hub, `content-studio/outbox/2026-10-20-eth-per-share/build/`) run at 2026-10-26 08:00:56 ET: "NOT FILED YET", **exit code 3**. No card built. |
| 3 | Oct 27 09:30 Q3 card | CARD BUILT; 10-Q HELD | Card re-rendered (below). EDGAR, Strategy: no 10-Q filed after the 2026-08-03 Q2 10-Q. No reconciliation possible; see `RECONCILIATION.md`. |
| 4 | Oct 27 18:00 per-share illustration | CARD BUILT | Made-up numbers; no source needed. Re-rendered (below). |
| 5a | Oct 30 09:30 Strategy Q3 results | HELD | Future event. EDGAR: no Q3 10-Q or results 8-K yet. |
| 5b | Oct 31 17:00 ETH poll (week ending Oct 25) | HELD | Depends on the Oct 26 BitMine 8-K (not out). BitMine shares are estimated, never filed weekly, so the poll answer is an estimate and has to say so. |
| 5c | Nov 2 09:30 BitMine 8-K | HELD | Future event (Monday Nov 2). EDGAR: nothing filed after Oct 19. |

Slots 1, 2 and 5b can be rebuilt after the filings land: run `python -m dat.refresh`, then `python social/2026-10-26/source_status.py`. They need new card specs in `cards.json`.

## Built cards

Rahil Design: skill VERSION 3.10.0 (hub `.agents/skills/rahil-design`), social-table template `rahil-design-3.3.2-social-table` (the "3.3.2" in the request). Tokens read from `assets/tokens.json`: canvas #111214, ink #F5F5EF, accent #FFE500, secondary #B7B8B1, figure #F5F5EF/#111214/#52545A. Anton display, IBM Plex Sans body (bundled fonts, embedded).

| Card | File (1080x1080) | SHA256 |
|---|---|---|
| Q3, Oct 27 09:30 | `cards/tue27-am-q3-square.png` | `720c4649590e9e9eb3c8b71bd2b3b08cfe40233380174f86652c57935e1ef0cc` |
| Per-share illustration, Oct 27 18:00 | `cards/tue27-pm-per-share-square.png` | `94ff833daa615fba44f4d4384124c8a79326b90015ccf48e9225fecffe36668d` |

Other files per card (hashes in `checks/sha256.json`): `-phone.png` (390x390), `-feed-360.png` and `-feed-390.png` (post text plus card in a mock feed at those widths; the black frame is not part of the design, so the pixel audit skips it).

Checks run (`python social/2026-10-26/build_cards.py`, Firefox, bundled fonts):
- Layout (`checks/render-checks.json`): 0 issues on both cards; at 360px feed the smallest label measures 18.39px (floor 18) and the title 40.12px (floor 40); at 390px, 20.08px and 43.82px; no horizontal overflow.
- Palette (`checks/palette-check.json`): every colour in both card sources is a token; contrast ink/canvas 17.13, figure-ink/figure-surface 17.13, figure-secondary/figure-surface 6.92, secondary/canvas 9.38, figure-ink/accent 14.69 (minimum 4.5). Passed.
- Pixels (`checks/pixel-audit.txt`): `pixel_audit.py` on the 1080 and 390 PNGs, 0.00% off-system. `design_check.py lint` on both card sources (`checks/design-lint.txt`): exit 0.
- Q3 figures (`python social/2026-10-26/q3_figures.py`, `checks/q3-figures.json`): recomputed from `data/attribution.csv` and `data/actions.csv`; asserts every number on the card and in the copy.

**Design review pending.** I inspected the square and feed PNGs by eye and applied the Tufte/dataviz rules (a table, no encodings, one accent, the illustration labelled, colours from tokens). No Chart Reviewer pass, no independent review and no timed reader test happened, and only Rahil passes a review. CI and this PR are not design approval.

### Q3 card, Oct 27 09:30 (Sats per Share)

Post: Strategy's net BTC per share rose 21,631 sats in Q3 2026 in the weekly model. Retiring STRC added 179 of those sats; bitcoin trades took 43. Revaluing at Bitcoin's price added 22,411.

Replies:
1. Q3 2026 rows: $1,379.1M of STRC retired; 7,218 BTC bought for $588.1M; 5,553 BTC sold for $348.5M. Each row links its 8-K in data/actions.csv.
2. The rest of the 21,631: price revaluation +22,411, in-the-money flips +361, common issuance +332, dividends and interest −801, residual −808. The model sums weekly effects, so the parts add to the observed change.
3. Limits: Q3 is the weeks ending Jul 5 to Sep 30, 2026. Strategy's Q3 10-Q is not filed yet, so nothing is reconciled to its reported quarter. Data and every 8-K link: https://github.com/RahilBhavan/dat-accretion

Alt text: Table titled STRC retirement: +179 sats/share. Q3 2026 net bitcoin per share effects in sats: STRC retired +179, bitcoin trades −43, all causes +21,631. Source: 8-Ks and the dat-accretion model, October 26, 2026. The first two are selected weekly effects; the total includes bitcoin price moves and other effects.

### Per-share illustration, Oct 27 18:00 (Sats per Share)

Post: Holdings can rise while coins per share fall. This illustration adds 10% more coins and 25% more shares. Each share ends up with 12% less. The numbers are made up.

Replies:
1. This example uses gross coins. Strategy's Net Bitcoin Per Share instead nets USD assets and debt/preferred claims before dividing by fully diluted shares. Definition: https://www.sec.gov/Archives/edgar/data/1050446/000119312526363557/d431748dfwp.htm
2. dat-accretion applies Strategy's definition to BitMine. BitMine's weekly shares are estimated, not filed counts. Coins per share is one measure; it leaves out price and risk. Method and limits: https://github.com/RahilBhavan/dat-accretion/blob/main/docs/methodology.md

Alt text: Table titled Coins +10%. Per share −12%. An illustration of before and after: coins 100 to 110, shares 100 to 125, per share 1.00 to 0.88. Made-up numbers, not a filing, dated October 27, 2026.

## Corrections and judgment calls

- **Q3 source path.** `final-drafts.json` in this folder is the corrected copy; I did not edit the hub's files (outside this
  repo, and its working tree is dirty). Every `local` path in it is repo-relative and exists (`data/attribution.csv`,
  `data/actions.csv`, `docs/methodology.md`, `social/2026-10-26/cards.json`). I could not find a nonexistent Q3 path in the
  current hub files. What I found: the hub's design-r4 Q3 draft points at `/home/rahil/projects/dat-accretion/data/attribution.csv`
  (absolute, one machine; its sha256 prefix `dbe3e577` no longer matches the current data, which is `674e8df2`), and the
  hub's per-share draft cites `cards.py per_share()`, a file that does not exist. Both are replaced. Port the corrected
  entries into the hub's `final-drafts.json` if you want the kit to carry them.
- **Q3 total.** +21,631 (not +21,633): sum of exact weekly effects, 21,630.84. The old design-r4 card dropped the total; the new
  card shows it as "All causes" under the two effects, so a reader sees that +179 is a small part of it.
- **Design version.** The request says 3.3.2; that is the social-table template version. The skill is at 3.10.0 and I rendered
  with its current tokens and checks. Palette and fonts are the ones the request lists.
- **Hub tooling.** `build_cards.py` imports Rahil Design's renderer and fonts from the hub checkout (`HUB` env var). It adds
  no dependency to this repo (`uv run --with ...`). The card HTML (fonts embedded, 500KB each) goes to
  `~/scratch/dat-accretion/` and is not committed.
- **monday_refresh.py** lives in the hub (`exports/content-studio/outbox/2026-10-20-eth-per-share/build/`) and reads
  `/home/rahil/projects/dat-accretion`, which is at commit ce3b715, behind this branch (2d789c0). Update that checkout
  before running it with `--apply`. Run for this request without `--apply`; exit 3 before it writes anything.
- BitMine shares are estimated, not filed: any BitMine card or poll has to say so.
- Framing: figures only, no verdict language (framing.md).
