# Sats per Share #15, "Q3 preview", v3 (draft, not published)

Card, thread and alt text for the Tue Oct 27, 2026 9:30 AM ET X post (content package 563fe59e, plan revision
7581e9a3). Nothing here is posted, scheduled or approved for posting. Grok Bot publishes only after Rahil's design
review of the exact card bytes below; this file does not authorize posting. v3 replaces the v2 card (four-row table,
"Q3 STRC buybacks added 179 sats a share") and the four-part thread of PR #59 and keeps its `sources.csv`.

| file | what |
|---|---|
| `card.png` | 1080x1080 RGB card, rendered from `card.html` at 3x (authored at 360 CSS px) |
| `card.html` | exact render source, fonts embedded |
| `thread.md` | three posts, exactly the requested text; each under 280 characters |
| `alt.txt` | alt text for `card.png` |
| `sources.csv` | 48 rows: every figure's underlying filed row with its 8-K accession number and `filing_url` (unchanged from PR #59) |

Regenerate: `python -m dat.x_post --card DIR --fonts <rahil-design>/assets/fonts` rewrites `sources.csv`, checks the
thread and alt text, and writes `DIR/card.html`. Render that file at 360x360 with device scale factor 3 in Firefox,
then drop the alpha channel (`card.png` is RGB). `tests/test_x_post.py` pins every figure, the thread text, the footer
and its size, the U+2212 hero, the bar scale and the PNG size and colour type.

## Where each number comes from

Window: Strategy rows with `week_end` after 2026-06-30 through 2026-09-30 (Q3). The 2026-06-30 row (1,363 BTC sold)
belongs to Q2 and is left out. The 9/30 row sits in the 8-K filed 2026-10-05, accession 0001193125-26-413164.
All 14 accession numbers in `sources.csv` are Form 8-K filings by CIK 1050446 (checked against EDGAR's submissions
index on 2026-10-26).

| figure | value | file and rows |
|---|---|---|
| Dividends and interest | -801 sats | `data/attribution.csv`, `carry` `DIV_INT`, 5 rows, `dn_exact` x 1e8 summed |
| Stock sales | +332 | same file, `issue_common`, 9 rows (the week of 8/23, `m` below 1, is negative) |
| STRC retired below its stated amount | +179 sats; $1,379.1M | same file, `retire_pref`, 11 rows; `data/actions.csv`, `retire_pref`, `usd` |
| Buybacks + stock sales | +511 | 332 + 179, the two rounded figures shown. Q3 has no `buyback_common` rows, so every buyback is an STRC retirement |
| BTC trades | -43 sats | same file, `buy_coin` + `sell_coin`, 6 rows; first order is zero by the method, the exact recompute gives the gap between each trade's price and that week's BTC close |
| BTC bought | 7,218 BTC / $588.1M | `data/actions.csv`, `buy_coin`, 3 rows |
| BTC sold | 5,553 BTC / $348.5M | `data/actions.csv`, `sell_coin`, 3 rows |

The thread's claim that BTC's price move is excluded rests on `price` rows in `data/attribution.csv` (+22,411 sats),
which are not shown. Those rows have no accession of their own, so the public text gives no number for them.

## Design review: pending

- Governing system: rahil-design 3.11.0 (current in the hub). The request named 3.3.2, which 3.11.0 supersedes;
  colors and fonts are unchanged between them: charcoal #111214, off-white #F5F5EF, yellow #FFE500, Anton title and
  hero, IBM Plex Sans body and footer. The 1080x1080 square is taken from the request.
- Artifact hashes (sha256): `card.png` ed885eeb8c21dcc76f1d5be6b1308a1084328c5c8bba9e9b6a045acfbd6a9a09, `card.html` 3085fc02cd881edce678c1a92f4fc83a4a840338ce77c6842e0075e252e2573c.
- Form: one hero number, one two-bar comparison on a shared scale and zero line (bar lengths proportional: 801 to
  511 as 801fr to 511fr), the one accent on the value the title names. The bars sit on the light figure surface;
  gray `chart.series-2` for +511 (off-white text on it has over 8:1 contrast), yellow with a charcoal outline for -801.
- Hero minus: Anton has U+2212 (checked with fontTools); the card uses it, as do the thread and alt text.
- Footer: 20px at 360 CSS px, so 60px in the 1080 export and 18.1px in a 326px feed box. It passes the 30px
  requirement and the 18px feed floor, on two lines.
- Checks run: `design_check.py lint card.html` ok; `design_check.py system` ok (0 errors); `design_check.py feed` at
  326px: labels 18.1px, title 40.8px, ok; `pixel_audit.py card.png` 0.00% of pixels off-system; the card renderer's
  Firefox measurement: no overflow, token fonts only, every glyph present, text contrast at least 4.5:1.
- Inspected by an agent only: full size and downsized to 326, 360 and 390px. Title, the yellow -801, both bars with
  their values, and the footer read at each width. Post-to-image agreement: the post and card give the same -801 and
  +511, and the card's "buybacks" are the same STRC retirements the post counts.
- `review_record.py` cannot re-render this card: it rebuilds a 390px card, and this one is authored at 360px for an
  exact 1080px export. No named reviewer has passed these bytes, so this stays **design review pending**.
- Not additive: +511 and -801 are two of the effects in the quarter. They leave out BTC trades (-43) and
  BTC's price move, so they do not give the quarter's change in net sats per share.
