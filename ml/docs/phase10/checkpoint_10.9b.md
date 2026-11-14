# Checkpoint 10.9b: pre-merge fixes from the independent review (2026-11-14)

Branch `phase-10-nft`. Fixes from `ml/docs/phase10/REVIEW_phase10.md` (reviewed at `7563689`). Nothing merged or
pushed; main untouched. Backend-touching commits are prefixed `backend:`.

## 1. Fixes and commits

| Item | What changed | Commit |
|---|---|---|
| Commit the review as-is | Already committed by the owner before this step (`f8d6b23`); skipped | `f8d6b23` |
| SHOULD FIX 1: refit storage | `CURRENT`, `refit_log.jsonl`, `refits/<R>/` live on the ml-data volume (`config.NFT_FV_REFIT_DIR` = `/data/nft/fv_refits`). The live accuracy summaries go to `/data/nft/live_accuracy/summaries`. The development artifact folder is mounted `:ro` in both ML containers, and the live_accuracy bind mount is gone. `due()` and `ensure()` refuse a refit folder inside the source checkout, so a branch checkout can never trigger or redirect a refit. A second refit on one date becomes `<R>-r2`. A lock file serialises refits. Log lines carry `trigger` and `tx_payment_records`. The three files are untracked; copies are in `ml/docs/phase10/refits/` (with a README on how to copy). The 2026-11-14 refit was copied into the volume unchanged (sha256 checked). | `9119a90` |
| SHOULD FIX 1: no repo bind mount is written | backend, shared, aai_engine, sentiment_engine, db and frontend are mounted `:ro`, and the backend sets `PYTHONDONTWRITEBYTECODE=1`. Before, the backend wrote `__pycache__` into the mounted source. Checked live: both services answer 200, Vite serves source, and `touch` in `/app/backend` fails with "Read-only file system". A test checks that every `./` mount in `docker-compose.yml` ends with `:ro`. | `93f7f2a` |
| SHOULD FIX 2: multi-token payments | New `tx_payments` stage in `ml.nft.refresh`, after `sales`. It reads new multi-token transactions only (no stored record), by the D74 rule. Errors carry the exception type only, never the RPC URL. Also `python -m ml.nft.tx_payments --live`. | `ba25ed4` |
| SHOULD FIX 2: backfill | It ran in the sidecar on deployment: 5 transactions (sales 2026-11-10 19:06 to 2026-11-13 13:50, 11 rows), 0 not returned, 2,639 records stored. | (data, volume) |
| SHOULD FIX 2: manual D79 refit, logged | `docker exec altinvest-ml-nft-refresh python -m ml.nft.fv_refit --refit` gave `2026-11-14-r2`: cutoff 2026-11-07, 185,052 rows, sha256 `949f66c5…`, the same as the 2026-11-14 refit. The backfilled sales are all after the cutoff, so the served model already matched D79. The backfill changes the request-time history, the D85 matching and every refit from 2026-12-01. Served live: `nft-fv-pooled-l1-nl15-refit-2026-11-14-r2`. | `f05a4ca` (log copy) |
| SHOULD FIX 3 | `run_nft_risk` defaults to `--protocol top-only`, and `build()` does too. `per-model-type` needs `--historical` (otherwise argparse error, exit 2) and prints a warning. The report's rule text names the protocol, and the sensitivity run uses the same protocol. | `549ba11` |
| MINOR 1 | `volCone.js` accepts only "Risk measure: 30-day volatility", so an old D51 row draws no cone. Comments fixed; test fixtures moved off EWMA notes. | `c5da5c8` |
| MINOR 2 | Caption "… Not a forecast of future price."; `no_prior_sale` note "…the estimate leans on recent sales in the collection." | `9ca1b81` |
| MINOR 3 | `accuracy_lines` shows the line only when `accuracy.by_collection[slug].method == NFT_FV_SERVE[slug]`; otherwise "Accuracy check pending". The pooled rarest-decile line needs every tested method to match the served one. Tested. | `8f57aeb` |
| MINOR 4 | `accuracy_note` dropped from refit metadata (code in `9119a90`), from the development artifact metadata and from `train()`. The model sha256 is unchanged. | `9119a90`, `531a2c9`, `b3ef141` |
| MINOR 5 | `load_sealed` and `load_history` raise `PermissionError` for every step, 10.8 included. | `59114ba` |
| MINOR 6 | One disclosure line in D79: the demo holdings were picked from sealed-date sales, and the screenshots show sealed-period last sales. | `60853d6` |
| MINOR 7 | `WIP_10.6/10.7/10.9.md` moved to `ml/docs/phase10/archive/`. | `fe04671` |
| MINOR 8 | D66 relabelled "WITHDRAWN (D73)". | `60853d6` |
| MINOR 9 | ML startup runs `python -m ml.nft.fv_refit --ensure` in the background. It refits (trigger `startup`, logged) only if the volume has live NFT data and no `CURRENT` refit. compose `init: true` reaps the process. Checked live: `{"action": "none", "served": "refits/2026-11-14"}` on the deployment start. Tested. | `dcff0d6` |
| ALSO: memory | `docker stats` showed the idle ml-nft-refresh at 510.6 MiB after its run. The loop now runs each daily cycle as a child process (`--cycle`): 114 MiB after the first cycle, then 95 MiB idle. See section 3. | `e6431be` |
| ALSO: EWMA text | The served `/risk` notes (crypto and NFT) said "the EWMA approval was withdrawn"; they are reworded, with the frontend prefixes unchanged. Today's stored backend rows were re-pulled (0 of 3 mention EWMA). Older dated rows keep the old note, but the backend reads only the latest row (`find_one`). Left alone: the dormant EWMA branches behind config (not served), the GLOSSARY and phase explanations (history), and backend test fixtures. | `4248b14` |
| ALSO: approval | D86 records the owner's approval of every "AUTONOMOUS, needs review" entry D63-D85 per REVIEW section 7: D67 with the disclosure (MINOR 6), D78(A) and D83 after SHOULD FIX 1-2. Labels updated. D78 and D83 amended with the 10.9b facts. | `60853d6` |
| STATUS and this checkpoint | Current state and verify block (step 5 reads the volume; step 8 uses `-p no:cacheprovider` because the source is read-only). | this commit |

Not in scope and not done: SHOULD FIX 4 (rotate the leaked Atlas credential). The owner must do it on Atlas.

## 2. Tests and snapshots (run at `b3ef141`, all to completion)

| Suite | Result |
|---|---|
| ML `python -m pytest ml -q -p no:cacheprovider` (`.venv-train`) | **452 passed**, 0 failed, 4 warnings, 359.6 s. The first run had 1 failure: `test_served_artifact_is_the_fold_9_fit_of_the_walk_forward` still expected `accuracy_note`. Fixed in `b3ef141`; the full re-run is the line above. |
| Backend (`docker exec -w /app/backend altinvest-backend python -m pytest tests -q -p no:cacheprovider`) | **44 passed, 1 skipped**, 1 warning |
| Frontend `npm test` | **21 passed**, 0 failed |
| `ml.nft.snapshot --verify` | 2026-11-10: OK, all hashes match |
| `ml.nft.item_snapshot --verify` | -items: OK, all hashes match |
| `ml.nft.item_data --verify` | -items-v2 and -items-v3: OK, all hashes match |
| `ml.data.snapshot_guard.require_snapshot()` | OK |

Tests added: volume-only `due` and `ensure`, untracked refit outputs and read-only mounts, the refit writing only to the volume, the pointer staying inside the refit folder, `-r2` labels, the lock, the startup refit, the cycle child process, the tx payment stage (only new transactions, read once, no URL in errors, stage present), run_nft_risk protocol flags, the always-raising sealed loaders, and the serve-map check on the error line.

## 3. docker stats (2026-11-14, after the fixes and the redeploy)

| Container | Memory | Note |
|---|---|---|
| altinvest-ml-nft-refresh | 94.9 MiB (was 510.6 MiB idle) | fixed: each cycle is a child process |
| altinvest-ml-refresh | 58.6 MiB | no job state held |
| altinvest-ml | 504.2 MiB | the API process; holds the item value tables cache by design (D78) |
| altinvest-backend | 857.7 MiB after restart (1.597 GiB before, after 3 h) | keeps FinBERT loaded on purpose for `/sentiment` (`backend/main.py:110`), with the sentiment pipeline running in-process. Backend team's design; not changed here. The growth is worth a look by Person B. |
| altinvest-frontend | 144.6 MiB | Vite dev server |
| altinvest-mongo | 217.2 MiB | database |

## 4. Deployment done in this step

- `docker build -f ml/Dockerfile -t altinvest-ml .`, twice. `docker compose up -d --build` refused here: the bake builder asked for `--allow=fs.read=ml\Dockerfile`.
- Then `docker compose up -d --no-deps ml ml-refresh ml-nft-refresh`.
- `docker compose up -d --no-deps backend frontend` to apply the read-only mounts, then `docker restart altinvest-backend` to re-pull the reworded notes.
- The ml-data volume received `/data/nft/fv_refits/` (the 2026-11-14 refit copied by `docker cp`, then `-r2`).

## 5. git

`git status` is clean after this commit (checked; see the final message of the step). No container writes into the repository any more.
