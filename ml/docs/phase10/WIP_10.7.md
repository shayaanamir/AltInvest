# WIP 10.7 (+ 10.8 preparation): resume notes for another agent

Branch `phase-10-nft`. Never touch main. Backend/db edits only in commits prefixed `backend:`.
SEALED: never call `load_sealed()`; compute nothing on dates >= 2026-01-25 (see the open question below).

## Done
- ML serving code (uncommitted until the next commit): config NFT_FV_*, `ml/nft/fv_serving.py`, `ml/nft/fv_artifact.py`,
  `ml/serving/nft_items.py`, endpoints in `ml/api/service.py`, CONTRACT_NFT schemas, lightgbm in the serving image,
  artifact mounted in compose, D78, `ml/tests/test_nft_fv_serving.py` (feature equivalence passes on dev dates).

- Code a5b33a7; artifact metadata 50c0ced (dev only, 137,040 rows; predictions equal the 10.6 fold 9); 7 serving tests pass.
- 10.8 protocol: `ml/evaluation/run_nft_sealed_fv.py`, `item_data.load_history('10.8')` (never called here), D79,
  `ml/tests/test_nft_sealed_protocol.py`: committed in the "10.8 protocol" commit (SHA in checkpoint_10.7.md).

## Next
2. Dry run: `python -m ml.evaluation.run_nft_sealed_fv --dry-run` (dev only); compare with the 10.6 confirmation.
3. Backend pull for holdings + item proxy; frontend item card; tests; screenshots (needs live serving: ask the user
   first, it computes features at the current date).
4. checkpoint_10.7.md. STOP.
