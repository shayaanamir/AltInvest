# Review of Phase 10 (branch `phase-10-nft`)

Reviewer: independent, read-only (only this file was written; nothing committed, pushed or merged; main untouched).
Reviewed at HEAD `7563689` (76 commits ahead of main). The sealed report was read but not re-run.
Read: `ml/docs/PLAN_NFT.md`, `ml/docs/DECISIONS.md` (D49-D85), every checkpoint in `ml/docs/phase10/`, the code
and commits they cite, and the live stack (ML API :8001 and the containers).

## Summary

The protocol was followed: every run came after its declaration commit, and the 10.6 and 10.8 run commits are clean.
The sealed set was read once, by the 10.8 run. Leakage controls hold where I checked them in code. What is served
matches D73, D80, D82 and D84 (I checked the live API). No blocker found. Two operational issues should be fixed
before the first monthly refit on 2026-12-01: the sidecar writes into tracked repo files, and payment records are
not collected for new multi-token sales. There is also a pre-existing leaked Atlas credential in main's history.
It was not introduced by this branch, but it needs rotating.

Tests: ML 441 passed, backend 44 passed and 1 skipped, frontend 21 passed. Every snapshot verifies.

---

## 1. Protocol

| Check | Evidence | Result |
|---|---|---|
| 10.3 risk: declarations before the run | D65 `49c2202` and runner `e00a905` (2026-11-10 21:28), D66 `cd82f32` (2026-11-11 01:19). The run was at `4ee833d` (01:21), report `generated_at` 2026-11-10T19:54:22Z = 01:24 IST, `git_dirty: false`, committed in `f050ea2` | OK |
| 10.3 trial count | `walkforward_risk.json` `trials.total = 2` (ewma 1, garch 1); sensitivity runs are marked "not approvals" | OK |
| 10.3 top-only | **Not applied at run time.** The run confirmed each model type (the D49 practice), with no `protocol` field in the report. D65(i) (`4bc1db4`) re-read the logged results: GARCH ranks first (0.5158 vs EWMA 0.5640, `logs/10.5b_risk_rank_confirm.md`) and its CI [-0.5088, 1.2341] includes 0, so nothing is approved. Serving was already persistence (D73), so the outcome is unchanged | OK in outcome; see SHOULD FIX 3 |
| 10.6 declarations before any run | D76 and code `5adadbd` (01:43), amendments `7fa7ec9` (02:15), leakage report re-run at `7fa7ec9`. Runner `647822b` (03:18), report `generated_at` 2026-11-13T21:58:16Z = 03:28 IST at `647822b`, `git_dirty: false` (`b479ce8`) | OK |
| 10.6 candidates unchanged | `git diff 7fa7ec9 647822b -- ml/models ml/evaluation ml/nft ml/config.py` only adds `run_nft_fair_value.py`. `git diff 5adadbd 7fa7ec9 -- ml/models/nft_fair_value.py` adds B2 and `ordered_range`; `CANDIDATES`, `COMMON` and `N_ROUNDS` are untouched | OK |
| 10.6 trial count and top-only | `walkforward_fair_value.json` `trial_count = 6`. Only the rank-1 config `fv_pooled_l1_nl15` was confirmed; rank 2 (`nl63`, lower confirmation MdAPE 0.0269) was not tested (checkpoint_10.6 §2) | OK |
| 10.8 protocol before sealed access | D79 and the script `2e6cacc` (03:53). Dry run `d574641` (03:55). `git diff 2e6cacc cb6f00c -- ml/models ml/evaluation ml/nft ml/config.py` is empty. Run at `cb6f00c` (15:05), `generated_at` 10:08:13Z = 15:38 IST, `git_dirty: false`, committed in `136126a` | OK |
| Sealed set read only by 10.8 | `git log -G"load_sealed\|load_history\("` lists only definitions, docs and the 10.8 runner. The only current non-test caller is `ml/evaluation/run_nft_sealed_fv.py:145` (`load_history("10.8")`, `--sealed` only); `load_sealed` has no caller. Tests call the loaders only to check that they refuse (`test_nft_item_clean.py:109`, `test_nft_sealed_protocol.py:25`). Disclosed partial exposures, none of them a premium metric: the 10.5 repeat-sale share and monthly counts up to 2026-07-19 (D71); the full-series maxima printed during the D66 work (D66); the denied direct read in 10.6a (checkpoint_10.6a §9) | OK (see MINOR 6) |

## 2. Leakage

| Check | Evidence | Result |
|---|---|---|
| Floor strictly before the sale | `ml/nft/item_clean.py:53` (`searchsorted(..., side="left") - 1`). Features use the same rule: `ml/nft/fv_features.py:160`. Serving: `fv_serving.floor_before` (`time < t`) | OK |
| Every feature is as-of | Rolling windows use `closed="left"` (`fv_features.py:148`), so rows at the same timestamp never enter. `_previous` uses `merge_asof(allow_exact_matches=False)` (`:186`) and `prev_n = rank(min) - 1`. Floor returns and volatility use points before t only. Static traits and rarity are static metadata (D60, D68). The leakage report at `7fa7ec9` reproduces 2,000 sales independently and shows the price-x1000 invariance (`fv_leakage_check.json`) | OK |
| W2 look-ahead cut (D76 amended (3)) | Training rows: `clean_mask(feats, sales, train_end)` (`run_nft_fair_value.py:43`). Test rows: `clean_mask(..., dev_end_timestamp())` = 2026-01-25 (`fv_leakage.py:44`). Sealed: per-month training cutoff and test W2 up to 2026-11-10 (`run_nft_sealed_fv.py:107,115`). Refit: cutoff C only (`fv_refit.py` `training_rows`). W2 rows stay in the feature history; the `clean` flag is never a feature | OK |
| Forbidden columns | `fv_features.matrix` (`:216-224`) refuses `FORBIDDEN`, ID-like trait columns and anything off the allow-list. Every fit and predict goes through it: `nft_fair_value.py:140-141`, `fv_artifact.py:53,104`, `fv_refit.py:99` | OK |
| Request time uses the training code | `fv_serving.query_features` calls `fv.build` on H plus one pseudo-sale per token. `history_asof` runs the training cleaning (dedupe, C1, C2, C3, W1). The refit dated 2026-01-01 reproduces the development artifact byte for byte (`test_nft_fv_refit.py`, checkpoint_10.9 §4) | OK (but see SHOULD FIX 2: C2 differs after the snapshot) |

## 3. Code matches decisions

| Check | Evidence | Result |
|---|---|---|
| D80: model for 6 collections, B2 for lilpudgys | `ml/config.py:122-123`. Live: `pudgypenguins:7862` → `method: model`, `nft-fv-pooled-l1-nl15-refit-2026-11-14`; `lilpudgys:1` → `baseline_b2` | OK |
| Crypto risk is persistence (D82) | `config.py:64-66` (`persistence-pooled-pct`, `RISK_MODEL_SERVED = False`, `vol_30d`). Live `/risk/BTC` note: "Risk measure: 30-day volatility (persistence). No risk model is served…" | OK |
| NFT risk is persistence (D73) | `config.py:102,104`. Live `/nft/pudgypenguins/risk` → `nft-persistence-pooled-pct` | OK |
| No range anywhere | `nft_items.py` has no lower/upper output. `CONTRACT_NFT.md:184` says "No range is served (D77)". The sealed report has `range_served: null` | OK |
| ETH-only estimates | Only `estimated_value_eth` in the ML, backend (`backend/models/schemas.py:271-276`, `routes/portfolio.py:45-48`) and frontend (`nftItemValue.js:12,52`) | OK |
| Item-card values = the 10.8 report | `accuracy.json` `source_sha256 e70148f4…ae97a` = the sha256 of `sealed_fair_value.json`. MdAPE azuki 0.03835→3.8%, BAYC 0.03578→3.6%, doodles 0.03156→3.2%, lilpudgys (B2) 0.02808→2.8%, milady 0.03001→3.0%, MAYC 0.03246→3.2%, pudgypenguins 0.01956→2.0%, rarest decile 0.09062→"about 9%". Live azuki #278 (rank 786/10,000) shows both lines | OK |
| Monthly refit follows D79 | Cutoff R − 7 days, clean as of C, declared parameters with a guard (`fv_refit.py` `cutoff_for`, `training_rows`, `guard`). `due()` refits on the first refresh of a month. First refit 2026-11-14: 185,052 rows, sha `949f66c5…` (`refit_log.jsonl`) | OK, except that the training data drifts from D79 (SHOULD FIX 2) |

## 4. User-facing honesty

- Item card (`frontend/src/components/nft/NftItemCard.jsx`, `utils/nftItemValue.js`): "Estimated value", last floor,
  last sale, rarity rank, method ("Model" / "Similar-rarity sales (baseline)"), the error lines. There are no
  drivers, no range, no USD and no "fair value from traits". The caption says "mostly driven by the collection floor
  and recent sales", which matches the 10.6 importances. OK.
- API notes for crypto and NFT risk describe persistence and the withdrawal. The EWMA branches in
  `ml/serving/responses.py:120` and `nft_responses.py:183` are dormant behind config. OK.
- `PHASE_10_nft.md` and `GLOSSARY.md:136` say "no range, no drivers, no comparable sales" and "not a forecast". OK.
- Leftovers: MINOR 1 and MINOR 2.

## 5. Safety

| Check | Evidence | Result |
|---|---|---|
| Compose defaults to local Mongo (D69) | `docker-compose.yml:36-37` `${BACKEND_MONGO_URI:-mongodb://mongodb:27017}`. `.env`'s `MONGO_URI` is not passed to the container. `load_dotenv` (`db/mongo_connection.py:7`) does not override | OK |
| Seeds guarded | `db/seed_guard.py` refuses non-local hosts and every `mongodb+srv` URI without `--allow-remote`. All 11 `db/seed*.py` entry points import it (`seed_all.py:36`, `seed_nft.py:75`, …). `test_seed_guard.py` | OK |
| `backend:` prefix | All 7 branch commits touching `backend/` or `db/` start with `backend:` (`a9edff3`, `eca725c`, `7351e3c`, `68c1df7`, `fd146bb`, `750b90c`, `80953b4`) | OK |
| Secrets added by this branch | `git log --all -G` for `alchemy.com/v2/<key>`, `mongodb+srv://user:pass@` and key assignments found nothing from Phase 10. The only `mongodb+srv` added is a fake test URI (`68c1df7`, `user:secret@cluster0.abcde`). `.env` is gitignored (`.gitignore:34`) | OK |
| Secrets in history (pre-existing) | A **real Atlas URI with a password** was committed in `.env.example` in `58649d2` and removed in `563039a` (both 2026-08-28, both already on main) | See SHOULD FIX 4 |

## 6. Tests and snapshots (run by the reviewer at `7563689`)

| Suite | Result |
|---|---|
| ML `python -m pytest ml -q` (`.venv-train`) | **441 passed**, 0 failed, 4 warnings (deprecation/FutureWarning), 15 min 26 s |
| Backend, in the container (`docker exec -w /app/backend altinvest-backend python -m pytest tests -q`) | **44 passed, 1 skipped**, 1 deprecation warning |
| Frontend `npm test` | **21 passed**, 0 failed |
| `ml.nft.snapshot --verify` (2026-11-10) | OK, all hashes match |
| `ml.nft.item_snapshot --verify` (-items) | OK, all hashes match |
| `ml.nft.item_data --verify` (-items-v2, -items-v3) | OK, all hashes match |
| Crypto `ml.data.snapshot_guard.require_snapshot()` | OK |

`git status` was clean after the runs.

---

## Findings

### BLOCKER (must fix before merge)

None.

### SHOULD FIX

1. **The refit sidecar writes into tracked repo files.**
   - `docker-compose.yml` (commit `39c9216`) bind-mounts `./ml/artifacts/nft_fv` read-write and
     `./ml/docs/phase10/live_accuracy` into `ml-nft-refresh`.
   - `CURRENT`, `refit_log.jsonl` and `refits/<R>/metadata.json` are tracked (`git ls-files ml/artifacts/nft_fv`).
   - On 2026-12-01 the container will dirty whatever branch is checked out. Every evaluation runner that refuses a
     dirty tree would then refuse.
   - If someone checks out a branch without `refit_log.jsonl`, `fv_refit.due()` returns True
     (`fv_refit.py:139-140`). The container then refits into that checkout, and what is served follows the checkout.
   - Fix: keep the refits, `CURRENT` and the log on the `ml-data` volume, and commit snapshots of the log by hand.
     Alternatively, untrack the files the container writes.
2. **New multi-token sales are dropped from the refit and from the live log.**
   - `tx_payments.csv` in the volume is dated 2026-11-10 and is never updated. `ml.nft.refresh` does not call
     `ml.nft.tx_payments`.
   - `fv_serving.clean_rows` → `classify_multi_token` drops every multi-token transaction without a payment record
     (D78(A)).
   - So every multi-token group after 2026-11-10 is missing from the history, the monthly training set and the D85
     matching. In v3 these groups were 7,571 kept rows (D75), about 4% of clean sales. D79 kept them.
   - The monthly refit therefore moves away from the procedure the sealed test measured. Listed as open since 10.7.
     Fix before the 2026-12-01 refit.
3. **`run_nft_risk` still defaults to `--protocol per-model-type`** (`ml/evaluation/run_nft_risk.py:140`).
   - This contradicts D81 (top-only for every phase, past and future) and D65(h-i).
   - Make `top-only` the default, or remove the old mode, before the declared 2027-05 re-evaluation, so the run
     cannot pick the old rule by accident.
4. **A leaked MongoDB Atlas credential is in main's history (pre-existing, not from this branch).**
   - Commits `58649d2` and `563039a` (`.env.example`, 2026-08-28) contain a real `mongodb+srv://<user>:<password>@altinvest-cluster…` URI.
   - Rotate the database user's password now. Rewriting the history is optional and can come after rotating.
   - This does not block merging Phase 10, but it is the most urgent item in this review.

### MINOR

1. `frontend/src/utils/volCone.js:23` still accepts `"Risk model: EWMA volatility"` as a served note. The comment at
   `:60` still says "not the ML's served EWMA model". Since D82 only the persistence prefix is served. Drop the EWMA
   prefix, so that an old stored EWMA row cannot draw a cone.
2. The item caption "An estimate of what this item might sell for now … Not a price prediction" contradicts itself
   a little. "Not a forecast of future price" (the plan's wording) would be cleaner. The `no_prior_sale` note "the
   estimate leans on similar items" overstates what traits contribute, since 10.6 found mostly market features.
   Consider "leans on recent sales in the collection".
3. `nft_items.accuracy_lines` (`ml/serving/nft_items.py:52-60`) reads `by_collection[slug]` from the metadata without
   checking that its `method` equals `config.NFT_FV_SERVE[slug]`. If the serve map changes, the error line would
   silently describe the other method. Add a check, or show the line only when the two match.
4. Refit metadata still carries `"accuracy_note": "Accuracy check pending"` next to the `accuracy` block
   (`fv_refit.py:116`, `fv_artifact.py:71`). It is harmless because the block wins, but confusing.
5. The sealed gate is only a string (`item_data.load_history("10.8")`), and run-once is only "the report file
   exists". Both are honour-system. Acceptable now that the sealed test is spent. Consider making both loaders raise
   unconditionally now that 10.8 is done.
6. Disclosure gaps, no metric involved:
   - The demo holdings (D67g, 10.4) were picked from real sales on 2026-06-01. That date became sealed when T was
     set later (D71).
   - The 10.7 and 10.9 screenshots and logs show sealed-period last sales next to estimates (pudgypenguins #7862:
     4.32 ETH on 2026-06-01).
   - Worth one line in checkpoint_10.8 §5 or D79.
7. `WIP_10.6.md`, `WIP_10.7.md` and `WIP_10.9.md` remain in `ml/docs/phase10/`. Archive them or delete them before
   merging.
8. D66 still carries the "AUTONOMOUS, needs review" label although D73 withdrew it. Relabel it "WITHDRAWN (D73)".
9. A fresh clone answers 503 on the item endpoints until someone runs `fv_refit --refit` by hand, because `model.txt`
   is untracked (checkpoint_10.9 §10.4). This is documented. A startup check that runs the refit when no model exists
   would remove the manual step.

---

## 7. D-entries marked "AUTONOMOUS, needs review"

| D | Verdict | Reason |
|---|---|---|
| D63 | Approve | The as-of floor with no age limit uses nothing after D 00:00, and gap days are counted. The alternative (dropping windows) would break the 30-row = 30-day equivalence. |
| D64 | Approve | One snapshot avoids two floor cut-offs. Tracking the large files by hash only is the D13 policy. |
| D65 (a)-(e) | Approve | The trial count and the two n_eff readings are honest; the dates/30 reading is the right one. GARCH-normal reuse is fine. (i) correctly shows the 10.3 run was per-type; SHOULD FIX 3 makes the code agree. |
| D66 | Approve the withdrawal | Moot since D73. It was written after inspecting pre-test moves and the full-series maxima (disclosed), and its approval depended on it, so withdrawing it was right. Relabel (MINOR 8). |
| D67 | Approve, with a question | The API, the Docker setup and the cone rules are sound and tested. Question: should the demo holdings be re-picked from development dates, or the sealed-date pick just disclosed (MINOR 6)? |
| D68 | Approve | Filling failed metadata reads in a separate frozen snapshot is correct. Ranking unread tokens as rare would have leaked data errors into the model. |
| D76 | Approve | It was fully declared before any run (`5adadbd`, `7fa7ec9`). Top-only, pooled date-block CI, the D32 check, the as-of W2 and the forbidden list were all enforced in code. Pooled approval with a per-collection guard is reasonable. |
| D77 | Approve | A mechanical reading of D76. Not switching to the B0/B1 range after seeing the results is correct. |
| D78 (A) | Approve 4, question 1 | Approve the 91-day subset (tested equal), the 503 on a trait-hash mismatch, the last-sale definition, and the 48 h stale note with LightGBM in the serving image. Question the dropping of new multi-token transactions: acceptable as a stopgap only (SHOULD FIX 2). |
| D79 (A) | Approve | "Best of B0/B1/B2" by the lowest pooled MdAPE is the walk-forward's rule. Embargo rows lie before later cutoffs, so including them is causal. |
| D83 (A) | Approve the procedure, question the layout | The live-folder refit is shown equal to the development path (byte-identical at 2026-01-01). The monthly schedule is fine. The tracked, container-written layout is the problem (SHOULD FIX 1). |
| D84 (A) | Approve | One decimal and a whole "about" percent are fair precision. A pooled rarest decile avoids new sealed computation. `rarity_accuracy_note` is nullable and additive. Values verified against the report. |
| D85 (A) | Approve | Logging every token daily, a 48 h match window, settling W2 after 30 days, and ALERT after 2 months behind B0 with no auto-switch are all monitoring only. Note that matching inherits SHOULD FIX 2. |
| D82 (two readings) | Approve | Extending the audit to direction is the consistent reading of D81. Not reviving EWMA through D44's clause is correct: that would be a new owner decision. |

---

## Merge verdict

**Ready after fixes.**
- No blocker: the protocol, leakage controls, served configuration, user-facing text and DB safety all check out.
  All three suites pass and every snapshot verifies.
- Fix SHOULD FIX 1-3 before 2026-12-01, the first monthly refit. They can go in this branch before merging, or in a
  follow-up merged before that date.
- Rotate the Atlas credential (SHOULD FIX 4) now, whatever happens to the merge.
