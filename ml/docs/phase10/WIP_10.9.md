# WIP 10.9: apply the sealed result and close Phase 10 (resume notes for another agent)

Branch `phase-10-nft`. Never touch main, don't merge. Backend/db edits only in commits prefixed `backend:`.
Commit at the end of each sub-step. Never re-run 10.8 (its report exists; the script refuses).
Deploy: ML only via `docker compose up -d --build --no-deps ml ml-refresh ml-nft-refresh` (the 10.7 method);
the backend only via `docker restart altinvest-backend`.

## Plan (D-numbers)
- D80 owner: lilpudgys keeps B2. D81 owner: D49 replaced, top-only for every phase.
- D82 D49 audit (Phase 9 crypto risk, from logged results).
- D83 serving refit + monthly refit job. D84 item card error line. D85 live accuracy log.

## Done
- A. D80, D81 (owner decisions) 8c86c6b.
- B. D49 audit: EWMA withdrawn, persistence served (D82) 99dcc8a ml, e0056f6 frontend, 1ba73af scorecard. Not yet deployed.

## In progress
- F. Deploy (ML compose up --no-deps; backend docker restart), check the sidecar's first refit + first log,
  sanity check, screenshots.
- Code done: C+D+E ML 39c9216 (D83-D85), backend 80953b4, frontend 6837982.

## Next
- B. D49 audit -> report + D82 (+ serving switch if it fails).
- F. Deploy, screenshots.  G. Close: PLAN_NFT statuses, review list, backlog, STATUS how-to-verify,
  PHASE_10_nft.md, GLOSSARY, scorecard, all tests, snapshot verify, checkpoint_10.9.md.
