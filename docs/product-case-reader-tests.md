# Product case: the reader tests

Draft for a One Lever post (Sat Dec 5). Not approved. Sources: `docs/reader-test.md` and `.claude/rules/framing.md` at `origin/main` a28449f; the test count was re-run on that commit.

## User and problem
A numerate reader who does not know the term mNAV opens the page. The page measures net coins per share for three crypto treasury firms. It has to say what it measures and the break-even figure with its condition, without reading as a verdict on any firm's decision.

## What was tested
Fresh AI agents, each given only the first-screen screenshot and the page's headings. Three roles (equity analyst, business journalist, fintech hiring manager), the same six questions, a 1 to 5 understanding score. No human has read it: every reader was simulated, and the doc calls the result a weak signal. A human test with 3 to 5 people is specified but not run.

## Counts (from reader-test.md)
| Round (date) | Readers | Purpose stated | Figure with condition | Verdict read in | Mean score |
|---|---|---|---|---|---|
| Before: counts headline (Oct 8) | 3 | 1 of 3 | 0 of 3 | 1 | 2.3 |
| Phases 0 to 3 (Oct 8) | 3 | 3 of 3 | 3 of 3 | 0 | 3.0 |
| Round 2 (Oct 8) | 3 | 3 of 3 | 3 of 3 | 0 | 3.3 |
| Round 3 (Oct 8) | 2 | 2 of 2 | 2 of 2 | 0 | 3.0 |
| Final redesign, desktop (Oct 8) | 3 | 3 of 3 | 3 of 3 | 0 | 4.0 |
| Same three readers re-shown the revised heading | 3 | 3 of 3 | 3 of 3 | 0 | 4/5 each |
| Redesign M25 to M29, desktop and phone (Oct 14) | 3 | 3 of 3 | 3 of 3 | 0 | 3.3 |

Totals: 17 fresh agent readers across 6 rounds, plus one repeat of 3 readers. Zero humans.

## What changed because of them
- The first screen led with symbols; one reader took it as "a scorecard where Strategy did well". The headline became break-even first, with the terms defined near it.
- All three Oct 8 final-round readers expected a common-stock price under "company's stock trades". The h1 now names the preferred stock price. All three said the confusion was gone on the re-test, with the same readers.
- Oct 14: no stated direction on the percent column, accent-colored words that looked like links, and dotted terms not read as tappable on phones. Each was changed; that screen was not re-tested.
- The rule that came out of it is in `framing.md`: headlines carry no verdict (decided 2026-10-08, after the reader test).

## Not resolved
Readers still hear "adds" as favorable. The doc records this and keeps the wording because it states the measured direction; the stricter target of nobody reading favorable judgment into the wording is not met. The Oct 14 mean (3.3) is below the earlier final screen (4.0), and the revised screen has not been re-tested.

## Test counts
- Offline pytest suite: 199 passed in 2.42 s, run for this case on a28449f (`uv run --with pytest python -m pytest -q`). It matches the README's "199 passed" (observed 2026-10-28).
- The reader tests are not part of that suite; they are manual, simulated and recorded in `docs/reader-test.md`.
- `check.py` passed 21 of 21 on 2026-10-28 (README, not re-run here: it fetches the network).

## One metric and what disproves the case
Metric: share of readers who state the measure and pair the break-even figure with its condition (project target 80%, human readers). Current human value: not measured. The case is disproved if human readers fall under 80% or read a verdict into the first screen, whatever the agents scored.
