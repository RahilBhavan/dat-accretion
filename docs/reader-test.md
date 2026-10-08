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
price at which each one's repeated trades stop adding coins per share"). That intermediate change was not tested before the final redesign replaced it.

Other notes from readers: "Residual −$255.9M" reads as a loss until the sentence after it; "adds" can read as
"good". Neither was reported as a recommendation.


## Final redesign: AI reader test, 2026-10-08

The final first screen (PR #28, commit `36a09c5`) uses a plain heading, figure sentence and gauges,
followed by three term cards. Three fresh AI readers tested the final desktop first screen at 1280 × 800, using only a screenshot
of the deployed page at commit `36a09c5`, with data through October 4. It has not been tested with
human readers. The agent scores above
apply to the earlier versions and are not evidence for this version.

### Results

| AI reader role | purpose understood | correct figure and condition | opposite directions clear | explicit recommendation read | score |
|---|---|---|---|---|---|
| Equity analyst | yes | STRC $99.41 below $119.92; BMNP $99.48 below $101.77, adds only above | yes | no | 4/5 |
| Business journalist | yes | both prices and thresholds, with correct conditions | yes | no | 4/5 |
| Fintech hiring manager | yes | both prices and thresholds, with correct conditions | yes | no | 4/5 |

All three identified the measure and conditions; mean understanding was 4.0/5. They all wanted to
check the formula and filings next. All three said "Rotation adds" sounds favorable, while recognizing
that it describes conditional per-share accretion and does not explicitly recommend an investment.
This does not satisfy the stricter target of nobody reading favorable judgment into the wording.

First confusion, independently repeated:
- Analyst: "The headline says ‘company’s stock trades,’ which initially made me expect a common-stock
  price threshold. The cards instead emphasize preferred prices."
- Journalist: "The headline says ‘each company’s stock trades,’ which initially makes me think of
  MSTR’s common-share price. The prominently displayed $99.41 is actually STRC’s preferred-share price."
- Hiring manager: "The headline sounds as though it will tell me the company’s ordinary stock price
  threshold, but the cards show preferred stock prices."

Response: the page heading now says "The preferred stock price where each rotation stops adding coins
per share." SharpLink's separate card continues to say it has no preferred. The same three AI readers repeated the screenshot test on the revised heading. All three
reported that the common-versus-preferred confusion resolved, retained both correct conditions and
scored understanding 4/5. This is a follow-up with the same readers, not a fresh blind sample.
They still described "adds" as favorable for this metric, but none read an explicit investment
recommendation. The metric wording is retained because it states the measured direction; this
remaining interpretation is recorded rather than treating the stricter no-favorable-judgment target
as passed. These are simulated roles, not actual readers; no human responses are
claimed. Below is a reusable protocol for a future human test.

### Run with 3 to 5 people

Include an analyst, a journalist or researcher, and a numerate reader without a finance background.
Use the deployed page at https://rahilbhavan.github.io/dat-accretion/ and record the commit, data date,
viewport and test date. Each participant works alone; do not explain the metric before the test.

1. Show only the first screen for 60 seconds. No scrolling or coaching.
2. Hide it and ask, in this order:
   - What does this page measure?
   - What is the main figure, and under what condition does it apply?
   - What would you check next?
   - Does the page say a company's decision was good or bad? What wording gave that impression?
   - What confused you first?
   - Rate your understanding from 1 (unclear) to 5 (clear).
3. Restore the page and allow scrolling. Ask them to explain why Strategy adds below break-even
   while BitMine adds above it, and to find a filing supporting one figure.
4. Record exact words before assigning scores. Do not infer a correct answer from confidence.

First-screen criteria: at least 80% identify net coins per share as the measure and correctly pair
one break-even figure with its condition; nobody reads it as a recommendation. After scrolling,
at least 80% explain both directions and locate a filing. These are project targets, not statistical
proof. Report counts and quotes; revise repeated confusion, then test the revised page again.

### Response sheet

Copy one row per participant. Leave cells empty until a real reader responds.

| reader ID / background | date / viewport / commit / data date | purpose (verbatim) | figure and condition (verbatim) | next check | verdict wording | first confusion | score 1–5 | both directions explained? | filing found? |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

Keep names and contact details in gitignored `private/`, not in this report. Add anonymized results
here once the test is complete. Recruitment and responses are still pending.
