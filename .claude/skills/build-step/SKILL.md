---
name: build-step
description: Run one dat-accretion build step (0-6) end to end - branch, delegate to runner with the step's acceptance check, verify, open a PR. Use when the user says "/build-step <n>", "do step <n>", or "next step".
---

# build-step <n>

1. **Read.** The step's row in CLAUDE.md's build plan, its section in the full spec
   (`~/projects/networking/projects/dat-accretion-spec.md`), and `.claude/rules/*`.
   If the spec leaves a decision open that changes the output (see the spec's open questions),
   ask the user before building.

2. **Branch.** `git switch main && git pull --ff-only && git switch -c <branch from CLAUDE.md>`.

3. **Delegate.** Dispatch `runner` with:
   - exact files to create or edit (from the spec's repo layout),
   - the acceptance check as a command or observable outcome, copied from the build plan,
   - style anchor: existing `dat/` modules; for patterns not yet here, `~/projects/spine`
     (`spine/*.py` for modules, `site/` for the page),
   - constraints: stdlib + numpy only, `python -m dat.<module>` entry, parse by label and fail
     loudly, every row keeps `filing_url`.

4. **Verify.** Dispatch in parallel:
   - `reviewer` on the diff against the acceptance check and `.claude/rules/method.md`,
   - `filing-verifier` on changed CSV rows (steps 1-3),
   - for steps 5-6, check page and memo text against `.claude/rules/framing.md` yourself.
   Send must-fix items back to the same runner. Repeat until clean.

5. **Commit and PR.** Commits in the repo's style: one imperative sentence, no prefix. Push,
   then `gh pr create` with: what changed, the acceptance check command and its real output,
   any fallback taken (labeled). Wait for CI with `gh pr checks --watch`.

6. **Stop.** Report the PR link and CI result. Merge (`gh pr merge --squash --delete-branch`)
   only when the user says to, unless they already said so for this step.
