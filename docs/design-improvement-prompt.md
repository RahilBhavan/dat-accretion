# Graph and information design implementation prompt

Improve DAT Accretion for two audiences: a numerate first-time reader and an analyst who wants to inspect the evidence. Give them a plain-language opening and progressively deeper analysis.

Read `/home/rahil/.agents/design-routing.md`, CLAUDE.md, `.claude/rules/`, `docs/decisions.md`, and `docs/reader-test.md` first. Apply `design-system-workflow`, `impeccable`, and `tufte-graphics`. Apply `dataviz` if installed; otherwise retain the validated palette and disclose that limitation. Use `anatomy` if changing the isometric balance and `typescript-best-practices` if editing TypeScript. Keep the existing stack, self-hosted fonts, and research-note identity. No new dependency.

## Intended result

Within the opening screen, readers should identify the measure, read a preferred close and its break-even price, and understand why Strategy adds below its threshold while BitMine adds above it. Analysts should reach history, attribution, assumptions, and source filings directly.

## Work plan

1. Simplify the introduction without repeating every ledger value. Explain each company's trade direction beside its figures. Preserve explicit preferred-price terminology and the conditional figure sentences required by framing.md.
2. Improve historical charts: shared scales and real dates; explicit units, threshold, and adding side; readable endpoint labels; sparse SharpLink observations shown as points without interpolation. Preserve its distinct `1 / m` metric and reporting dates.
3. Make section titles answer reader questions. Explain the bars' basis-point unit, net tick, omitted components, and residual in plain language beside the graphic. Preserve exact attribution and filing links.
4. Keep important qualifications beside the affected result. Never imply that model estimates are precise observations or that stale filings are current.
5. Consider a later balance interaction pass: synchronize a worked example with its controls and readout, using the existing pure model. Do not change the illustration just to add motion.

## Constraints

Do not change formulas, generated financial inputs, or source provenance. Facts, never verdicts: no forecasts, recommendations, company rankings, or good/bad status colors. Do not make SharpLink look as though it has preferred stock. Keep arrows, keyboard navigation, touch sheets, themes, and filing links usable. No publication or outbound messages.

## Verification and handoff

Inspect actual desktop and phone layouts in T3's collaborative browser, including narrow widths and both themes. Check chart-label collisions, horizontal overflow, accessible descriptions, focus, term definitions, firm tabs, and filing targets. Run the relevant existing tests and JavaScript syntax checks; run the Impeccable detector once and assess its findings against the incumbent design. Report actual checks, remaining limits, and changes in docs/decisions.md. Reader-test success remains unproven until real readers complete the protocol; never invent responses.

## Current pass

Implement steps 1–3 first as a focused, reviewable change. Preserve the ledger's percentage column for comparison with the history charts; make the trade directions and conditions explicit before removing useful numbers. Defer the balance's model and interaction changes to their own pass.
