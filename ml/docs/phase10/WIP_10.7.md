# WIP 10.7 (+ 10.8 preparation): resume notes for another agent

Branch `phase-10-nft`. Never touch main. Backend/db edits only in commits prefixed `backend:`.
SEALED: never call `load_sealed()`; compute nothing on dates >= 2026-01-25 (see the open question below).

## Done
- ML serving code (uncommitted until the next commit): config NFT_FV_*, `ml/nft/fv_serving.py`, `ml/nft/fv_artifact.py`,
  `ml/serving/nft_items.py`, endpoints in `ml/api/service.py`, CONTRACT_NFT schemas, lightgbm in the serving image,
  artifact mounted in compose, D78, `ml/tests/test_nft_fv_serving.py` (feature equivalence passes on dev dates).

## Next
1. Commit the code; `python -m ml.nft.fv_artifact --train` (dev only); commit metadata.json; run the serving tests.
2. 10.8 protocol code + D-entry; commit BEFORE any sealed access; dry run on dev (mock window = confirmation months).
3. Backend pull for holdings + item proxy; frontend item card; tests; screenshots (needs live serving: ask the user
   first, it computes features at the current date).
4. checkpoint_10.7.md. STOP.
