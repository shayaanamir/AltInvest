# WIP 10.9: apply the sealed result and close Phase 10 (resume notes for another agent)

Branch `phase-10-nft`. Never touch main, don't merge. Backend/db edits only in commits prefixed `backend:`.
Commit at the end of each sub-step. Never re-run 10.8 (its report exists; the script refuses).
Deploy: ML only via `docker compose up -d --build --no-deps ml ml-refresh ml-nft-refresh` (the 10.7 method);
the backend only via `docker restart altinvest-backend`.

## Plan (D-numbers)
- D80 owner: lilpudgys keeps B2. D81 owner: D49 replaced, top-only for every phase.
- D82 D49 audit (Phase 9 crypto risk, from logged results).
- D83 serving refit + monthly refit job. D84 item card error line. D85 live accuracy log.

## Status: DONE, stopped after checkpoint_10.9.md
- A. D80, D81 (owner decisions) 8c86c6b.
- B. D49 audit: EWMA withdrawn, persistence served (D82) 99dcc8a ml, e0056f6 frontend, 1ba73af scorecard.
- C-E. Refit + monthly job (D83), error line (D84), live accuracy log (D85): ML 39c9216, backend 80953b4, frontend 6837982.
- F. Deployed (ML compose --no-deps, backend docker restart); first refit 2026-11-14 0e083fd; screenshots 67448c0.
- G. Close: scorecard 718eb12/33e6eba, docs 2119f2a, checkpoint_10.9.md. Tests: ML 441 passed, backend 44 passed 1 skipped,
  frontend 21 passed; snapshots verify.

## Next
- Nothing. Wait for the owner's review of checkpoint_10.9.md (review list, merge steps).
