# WIP 10.7 (+ 10.8 preparation): resume notes for another agent

Branch `phase-10-nft`. Never touch main. Backend/db edits only in commits prefixed `backend:`.
SEALED: never call `load_sealed()` / `load_history()`; no metric on dates >= 2026-01-25 (live serving is allowed, D78
amended; the live accuracy log stays off until after 10.8).

## Done (step complete)
- ML serving a5b33a7, artifact 50c0ced, warm-up baa6fe6; 10.8 protocol 2e6cacc (D79); dry run d574641;
  backend 750b90c; frontend 87adf68; screenshots 7d471fb; checkpoint_10.7.md (final commit of the step).

## In progress
- Nothing. 10.8 done: ONE sealed run at cb6f00c, PASS (ml/docs/phase10/checkpoint_10.8.md). STOPPED, waiting for review.

## Next (only after the user's OK)
- 10.9: apply the 10.8 outcome (error line, live accuracy log, retrain), as the planner decides. Never re-run 10.8:
  `ml/reports/nft/sealed_fair_value.json` exists and the script refuses.
