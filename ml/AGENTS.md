# AGENTS.md — ML v2 entry point (read this first, every session)

Project: AltInvest ML service (crypto first, NFTs later). Produces ONLY `/predict/{asset}` and `/risk/{asset}`.
AAI score is the backend's job. Do not build it.

## Read order (do not read the whole repo)
1. This file  2. docs/STATUS.md  3. Only the docs/files the current task names.

## Commands (run from the repo root, never from inside ml/)
- Tests: `python -m pytest ml`  (plain `pytest` at the root also collects other teams' tests)
- Import check: `python -c "import ml.config"`
- Modules: `python -m ml.<package>.<module>`

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
15. Every phase ends with a 'How to verify yourself' block in docs/STATUS.md: copy-paste PowerShell commands, plus the expected output or value ranges, that the user can run without the agent. A phase is not done until this block exists.
16. Every phase ends with an explanation file at docs/phases/PHASE_<N>_<name>.md, written for a reader who is a student and not an ML expert. Keep it brief and simple, with only the important things (under 1 page). A phase is not done until it exists. Follow the 8-section template in docs/phases/TEMPLATE.md.

## Docs
- docs/STATUS.md: current state and "How to verify" blocks. Update every task.
- docs/PLAN.md, REQUIREMENTS.md, ARCHITECTURE.md, DATA.md, EVALUATION.md, CONTRACT.md: the plan and specs.
- docs/DECISIONS.md (D-numbers), docs/LEARNINGS.md (v1 lessons).
- docs/GLOSSARY.md: plain-English term definitions. Add new terms each phase.
- docs/phases/TEMPLATE.md: the brief 8-section template for phase explanations.
- docs/phases/PHASE_0_scaffold.md, docs/phases/PHASE_1_btc_data.md, docs/phases/PHASE_1b_eth_sol_data.md, docs/phases/PHASE_2_features_labels.md, docs/phases/PHASE_3_baselines.md, docs/phases/PHASE_4_0_walkforward_harness.md, docs/phases/PHASE_4a_risk_model.md, docs/phases/PHASE_4b1_price_model.md: finished phases.
