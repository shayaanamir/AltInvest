# AGENTS.md — ML v2 entry point (read this first, every session)

Project: AltInvest ML service (crypto first, NFTs later). Produces ONLY `/predict/{asset}` and `/risk/{asset}`.
AAI score is the backend's job. Do not build it.

## Read order (do not read the whole repo)
1. This file  2. docs/STATUS.md  3. Only the docs/files the current task names.

## Rules
1. One phase at a time. Next phase starts only when the current phase's "done when" (docs/PLAN.md) passes.
2. Every task needs a testable "done when". If it can't be tested, ask me to define it.
3. TWO-ATTEMPT RULE: if the same error survives two fixes, STOP. Write the problem, what you tried, and your suspected cause to docs/STATUS.md, then ask me. No third variation.
4. Real data only. Never generate synthetic data. Never use data that failed docs/DATA.md validation.
5. No hand-typed metrics anywhere. Metrics come from code that writes JSON reports.
6. One source of truth per thing: one config (`ml/config.py`), one loader, one `generate_signal()`.
7. Modules under ~300 lines. One concern per commit. Small diffs.
8. Do not retrain or overwrite artifacts unless the task says so.
9. Run modules with `python -m ml.x.y`, never `python file.py` (pickles saved as `__main__.X` break loading).
10. Every saved artifact gets a `metadata.json` (data range, split dates, git commit, metrics).
11. Report what ran and what it output. Never write "improved" without a number from a report.
12. Never put a price in a field named as a percentage.
13. Update docs/STATUS.md at the end of every task.
14. API responses must validate against docs/CONTRACT.md (additionalProperties: false).
