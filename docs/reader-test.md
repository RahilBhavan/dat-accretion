# Reader test, 2026-10-08

A 60-second first-screen test, run with the protocol in the `information-design` skill. No human readers were
available, so each reader was a fresh agent given only the first-screen screenshot and the page's headings and
first lines. Treat this as a weak signal; a human test with 3 to 5 people should replace it.

Readers: an equity analyst (knows mNAV), a business journalist (knows Strategy, not mNAV), a fintech hiring
manager (numerate, not finance). Questions: what the page measures, the main figure and its condition, what
they would check next, anything read as a verdict, what confused them first, a 1 to 5 understanding score.

| version | purpose stated | main figure with condition | verdict read in | mean score |
|---|---|---|---|---|
| Before (counts headline, symbols only) | 1 of 3 | 0 of 3 | 1 ("reads like a scorecard where Strategy did well") | 2.3 |
| Phases 0 to 3 (break-even headline, explainer, example) | 3 of 3 | 3 of 3 | 0 | 3.0 |
| Round 2 (rotation, STRC, BMNP, sats defined; one headline line per firm) | 3 of 3 | 3 of 3 | 0 | 3.3 |
| Round 3 (definitions as three short lines; journalist and hiring manager only) | 2 of 2 | 2 of 2 | 0 | 3.0 |

What every round still flagged: the headline uses mNAV, STRC, rotation and sats before the lines that define
them, and the two firms' conditions run opposite ways (below, above). framing.md fixes the headline's form, so
after round 3 a plain-language line now sits above it ("Three crypto treasury companies: the preferred stock
price at which each one's repeated trades stop adding coins per share"). That change is not yet tested.

Other notes from readers: "Residual −$255.9M" reads as a loss until the sentence after it; "adds" can read as
"good". Neither was reported as a recommendation.
