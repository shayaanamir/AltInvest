# WIP 10.6: NFT fair value (resume notes for another agent)

Branch `phase-10-nft`. Never touch main. Sealed rule: `ml.nft.item_data.load_dev()` only; nothing on dates >= 2026-01-25.

## Done
- 10.6a declarations: commit `5adadbd`; checkpoint `c8dc1a9`.
- 10.6a review amendments (B2, per-collection guard, W2 as of cutoffs, range fallback, sorted quantiles): ONE commit
  (the one that adds this text; its SHA goes into checkpoint_10.6a.md and D76 afterwards). No run before it.

## In progress
- Re-run `python -m ml.nft.fv_leakage` on the amendment commit (git_dirty false), commit the report, record the SHA.

## Next
- 10.6b: `ml/evaluation/run_nft_fair_value.py` -> `ml/reports/nft/walkforward_fair_value.json`: 9 folds; training rows
  = clean as of the fold cutoff (`fv_features.clean_mask`), test rows = clean as of 2026-01-25; B0, B1, B2 and the 6
  candidates; quantile ranges sorted; `nft_fv_protocol.select()`. Commit.
- 10.6c: report + descriptive tables + importances + D-entries + `checkpoint_10.6.md` (HANDOFF FOR 10.7). Commit. STOP.
