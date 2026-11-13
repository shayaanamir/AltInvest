# WIP 10.6: NFT fair value (resume notes for another agent)

Branch `phase-10-nft`. Never touch main. Sealed rule: `ml.nft.item_data.load_dev()` only; nothing on dates >= 2026-01-25.

## Done
- 10.6a declarations: commit `5adadbd`; checkpoint `c8dc1a9`.
- 10.6a review amendments: commit `7fa7ec9` (recorded in D76 and checkpoint_10.6a.md). No run before it.
- Leakage report re-run at 7fa7ec9 (git_dirty false): all equal, no leaks; committed with the checkpoint addendum.

## In progress
- 10.6b: runner `ml/evaluation/run_nft_fair_value.py` written; commit it, then run it (about 30-40 min; W2 recompute
  ~100 s per cutoff). If interrupted: just re-run the module from a clean tree.

## Next
- 10.6b: `ml/evaluation/run_nft_fair_value.py` -> `ml/reports/nft/walkforward_fair_value.json`: 9 folds; training rows
  = clean as of the fold cutoff (`fv_features.clean_mask`), test rows = clean as of 2026-01-25; B0, B1, B2 and the 6
  candidates; quantile ranges sorted; `nft_fv_protocol.select()`. Commit.
- 10.6c: report + descriptive tables + importances + D-entries + `checkpoint_10.6.md` (HANDOFF FOR 10.7). Commit. STOP.
