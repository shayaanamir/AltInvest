# WIP 10.6: NFT fair value (resume notes for another agent)

Branch `phase-10-nft`. Never touch main. Sealed rule: `ml.nft.item_data.load_dev()` only; nothing on dates >= 2026-01-25.
NO baseline or candidate has been run. Do not run `ml.models.nft_fair_value` fits until the user says continue after checkpoint 10.6a.

## Done (10.6a, declarations)
- `ml/nft/item_data.py`: `load_dev(include_flagged=False)`; also returns `floor_points` cut at 2026-01-25 00:00 UTC.
- `ml/nft/fv_features.py`: features + as-of definitions (docstring), allow-list, `matrix()` refuses forbidden columns.
- `ml/nft/fv_leakage.py`: CLI `python -m ml.nft.fv_leakage` -> `ml/reports/nft/fv_leakage_check.json` (features only).
- `ml/models/nft_fair_value.py`: B0, B1, 6 LightGBM candidates (one file), range method.
- `ml/evaluation/nft_fv_protocol.py`: folds, APE, median date-block bootstrap, `select()` (top-only, D32, D44 range).
- `ml/tests/test_nft_fv.py`: 12 unit tests pass; 2 real-data tests.
- `ml/docs/DECISIONS.md` D76.

## In progress
- Leakage check run on the uncommitted tree (to verify), then: commit the declarations, push, re-run the check on the
  committed tree (git_dirty false), commit the report.

## Next
- Write `checkpoint_10.6a.md` (declarations SHA, features, leakage results, folds, candidates, block, range), commit, push. STOP.
- 10.6b (after the user's OK): write `ml/evaluation/run_nft_fair_value.py`, run baselines + 6 candidates over the 9 folds.
