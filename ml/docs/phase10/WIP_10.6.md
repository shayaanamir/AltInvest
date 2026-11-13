# WIP 10.6: NFT fair value (resume notes for another agent)

Branch `phase-10-nft`. Never touch main. Sealed rule: `ml.nft.item_data.load_dev()` only; nothing on dates >= 2026-01-25.

## Done
- 10.6a declarations: commit `5adadbd` (pushed). Code: `ml/nft/fv_features.py`, `ml/nft/fv_leakage.py`,
  `ml/models/nft_fair_value.py`, `ml/evaluation/nft_fv_protocol.py`, `ml/tests/test_nft_fv.py`; D76.
- Leakage report of record `ml/reports/nft/fv_leakage_check.json` (at 5adadbd, git_dirty false): all features equal.
- `checkpoint_10.6a.md` written and committed with the report.

## In progress
- Nothing. WAITING for the user's OK after checkpoint 10.6a. NO baseline or candidate has been run.

## Next (only after the user's OK)
- 10.6b: write `ml/evaluation/run_nft_fair_value.py`: for each of the 9 folds (`nft_fv_protocol.folds()`), fit B0, B1
  and the 6 candidates (`nft_fair_value.fit_predict`, plus quantile models per `range_key`) on clean training rows
  of `fv_features.build` output; collect ape/lo/hi per test row; `nft_fv_protocol.select()`; write
  `ml/reports/nft/walkforward_fair_value.json`. Commit.
- 10.6c: report, descriptive breakdowns (collection, sale_type via load_dev, floor-age bucket), importances,
  D-entries, `checkpoint_10.6.md` with the HANDOFF FOR 10.7.
