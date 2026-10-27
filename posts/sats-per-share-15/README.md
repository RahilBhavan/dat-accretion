# Sats per Share #15, "Q3 preview" (draft, not published)

Card, thread and alt text for the Tue Oct 27, 2026 9:30 AM ET X post (content package 563fe59e, plan revision
7581e9a3). Nothing here is posted, scheduled or approved for posting.

| file | what |
|---|---|
| `card.png` | 1080x1080 RGB card, rendered from `card.html` at 3x (authored at 360 CSS px) |
| `card.html` | exact render source, fonts embedded |
| `thread.md` | four parts, each under 280 characters; the one caveat is in part 4 |
| `alt.txt` | alt text for `card.png` |
| `sources.csv` | 48 rows: every figure's underlying filed row with its 8-K accession number and `filing_url` |

Regenerate: `python -m dat.x_post --card DIR --fonts <rahil-design>/assets/fonts` rewrites `sources.csv`, checks the
thread and alt text, and writes `DIR/card.html`. Render that file at 360x360 with device scale factor 3 in Firefox.
`tests/test_x_post.py` pins every figure, the footer, the four-part limit, the single caveat and the PNG size.

## Where each number comes from

Window: Strategy rows with `week_end` after 2026-06-30 through 2026-09-30 (Q3). The 2026-06-30 row (1,363 BTC sold)
belongs to Q2 and is left out. The 9/30 row sits in the 8-K filed 2026-10-05, accession 0001193125-26-413164.
All 14 accession numbers in `sources.csv` are Form 8-K filings by CIK 1050446 (checked against EDGAR's submissions
index on 2026-10-26).

| figure | value | file and rows |
|---|---|---|
| STRC buybacks | +179 sats | `data/attribution.csv`, `retire_pref`, 11 rows, `dn_exact` x 1e8 summed |
| Stock sales | +332 | same file, `issue_common`, 9 rows (the week of 8/23, `m` below 1, is negative) |
| BTC trades | -43 | same file, `buy_coin` + `sell_coin`, 6 rows; first order is zero by the method, the exact recompute gives the gap between each trade's price and that week's BTC close |
| Dividends, interest | -801 | same file, `carry` `DIV_INT`, 5 rows |
| STRC retired | $1,379.1M | `data/actions.csv`, `retire_pref`, `usd`, 11 rows |
| BTC bought | 7,218 BTC / $588.1M | `data/actions.csv`, `buy_coin`, 3 rows |
| BTC sold | 5,553 BTC / $348.5M | `data/actions.csv`, `sell_coin`, 3 rows |

The caveat in part 4 (BTC's price move is larger than the four effects) rests on `data/attribution.csv`, rows
`price`: +22,411 sats against a total change of +21,631 in `data/weekly.csv` (136,146 on 6/30 to 157,777 on 9/30).
Those rows have no accession of their own, so the public text states the claim without the numbers. The original
caveat wording was not in the request; this wording is new and appears once.

## Design review: pending

- Governing system: rahil-design 3.11.0 (current in the hub). The request named 3.3.2, which 3.11.0 supersedes;
  colors and fonts are unchanged between them: charcoal #111214, off-white #F5F5EF, yellow #FFE500, Anton
  titles, IBM Plex Sans body. Rahil's explicit decision for a 1080x1080 square is taken from the request.
- Artifact hashes (sha256): `card.png` f1cf85136b28012913ac362917c3a579ff6714b3a115365063403d5d00b8b637,
  `card.html` cab49cf16f53f8e138c2c675f4aad2f93c26bb2a5d17c4878d6ceedd5a3d2433.
- Checks run: `design_check.py lint card.html` ok; `design_check.py system` ok; `pixel_audit.py card.png` 0.00% of
  pixels off-system; the card renderer's measurement (Firefox): no overflow, token fonts only, every glyph present;
  `design_check.py feed` at 326px: title 40.8px (floor 40) and body text 18.1px (floor 18) pass, **the 18px source
  line draws at 16.3px (floor 18) and fails**. The footer text is fixed by the request (70 characters) and cannot
  fit two lines at 20px beside a three-line takeaway title, a four-row table and the metric definition. It is
  fine print by the 2026-10-26 landscape decision; whether a square card may carry it needs Rahil's call.
- Inspected by an agent only: full size, and downsized to 326, 360 and 390px. Title, the yellow 179 and all four
  rows read at each width; the source line is the smallest text. Title-to-image agreement: the post names the same
  four figures. No named reviewer has passed these bytes, so this stays **design review pending** until
  `review_record.py` records a pass.
- Form: four numbers go in a table, not a bar chart (design.md: small sets in a table). The rows are not additive
  to the quarter's change, which part 4 says once.
