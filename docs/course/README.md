# dat-accretion from scratch

A course that teaches this project from the ground up: the finance, parsing SEC filings, the math engine, shipping the page, and how it was built. Every lesson uses the repo's real code and data.

Each lesson is a folder with `en.md` (the lesson) and `quiz.json` (two questions before reading, three after). Lessons follow one layout: Learning Objectives, The Problem, The Concept, Build It, Use It, Ship It, Decisions, Exercises. Blocks marked ```` ```widget ```` are interactive in the rendered course and plain text on GitHub.


## 00 · Foundations

| lesson | title | type | time |
|---|---|---|---|
| 00-01 | [What a Crypto Treasury Company Does](00-foundations/01-crypto-treasuries/en.md) | Concept | ~25 minutes |
| 00-02 | [Reading an 8-K](00-foundations/02-reading-an-8k/en.md) | Build | ~35 minutes |
| 00-03 | [The Ruler: Net Coins per Share](00-foundations/03-the-ruler/en.md) | Build | ~30 minutes |
| 00-04 | [m, q and the Five Formulas](00-foundations/04-m-q-and-five-formulas/en.md) | Build | ~40 minutes |

## 01 · Getting the Data

| lesson | title | type | time |
|---|---|---|---|
| 01-01 | [Saving an API With No History](01-data/01-snapshot-an-api/en.md) | Build | ~25 minutes |
| 01-02 | [Parsing Filings by Label, Failing Loudly](01-data/02-parse-by-label/en.md) | Build | ~40 minutes |
| 01-03 | [Rolling Quarterly Anchors Forward](01-data/03-roll-anchors-forward/en.md) | Build | ~35 minutes |
| 01-04 | [Prices and Price Dates](01-data/04-prices-and-dates/en.md) | Build | ~25 minutes |
| 01-05 | [When the Company Won't Tell You: BitMine's Share Count](01-data/05-estimating-bitmine-shares/en.md) | Case study | ~40 minutes |
| 01-06 | [SharpLink: Measuring a Firm That Files Irregularly](01-data/06-irregular-filers/en.md) | Case study | ~35 minutes |

## 02 · The Engine

| lesson | title | type | time |
|---|---|---|---|
| 02-01 | [Splitting a Week Into Parts](02-engine/01-attribution-order/en.md) | Build | ~40 minutes |
| 02-02 | [The Residual as a Bug Detector](02-engine/02-residual-as-bug-detector/en.md) | Case study | ~30 minutes |
| 02-03 | [Trace One Row End to End](02-engine/03-trace-one-row/en.md) | Build | ~35 minutes |

## 03 · Shipping It

| lesson | title | type | time |
|---|---|---|---|
| 03-01 | [Drawing the Map and the Bars](03-shipping/01-map-and-bars/en.md) | Build | ~40 minutes |
| 03-02 | [Facts, Not Verdicts](03-shipping/02-facts-not-verdicts/en.md) | Concept | ~30 minutes |
| 03-03 | [The Done Check](03-shipping/03-done-check/en.md) | Build | ~35 minutes |
| 03-04 | [Running Itself: Cron, Refresh, Reanchor](03-shipping/04-automation/en.md) | Build | ~40 minutes |

## 04 · How It Was Built

| lesson | title | type | time |
|---|---|---|---|
| 04-01 | [Building With Agents](04-process/01-building-with-agents/en.md) | Concept | ~25 minutes |
| 04-02 | [What Went Wrong, and What It Taught](04-process/02-mistakes-and-lessons/en.md) | Case study | ~30 minutes |

## 05 · Capstone

| lesson | title | type | time |
|---|---|---|---|
| 05-01 | [Capstone: Reanchor or Add a Firm](05-capstone/01-capstone/en.md) | Build | ~3 hours per project |

## 06 · Reference

| lesson | title | type | time |
|---|---|---|---|
| 06-01 | [Data Dictionary](06-reference/01-data-dictionary/en.md) | Reference | ~20 minutes |
| 06-02 | [Error Messages and What They Mean](06-reference/02-error-messages/en.md) | Reference | ~25 minutes |
| 06-03 | [Test Catalogue](06-reference/03-test-catalogue/en.md) | Reference | ~20 minutes |
| 06-04 | [FAQ](06-reference/04-faq/en.md) | Reference | ~25 minutes |
