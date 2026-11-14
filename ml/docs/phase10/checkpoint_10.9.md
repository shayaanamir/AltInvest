# Checkpoint 10.9: apply the sealed result and close Phase 10

Branch `phase-10-nft`, pushed and NOT merged. main was not touched. Backend edits are only in `backend:` commits.
New decisions: D80-D85 in `ml/docs/DECISIONS.md`. D80 and D81 are owner decisions; my own choices are marked
"(A) AUTONOMOUS, needs review".

## 1. What changed for users

| Where | Before 10.9 | Now |
|---|---|---|
| Crypto risk (BTC, ETH, SOL): `risk_score`, `volatility`, the /risk note, the price chart's cone | EWMA volatility (D51) | **30-day volatility (persistence)**, D82. Today's scores: BTC 90.0 (was 86.3), ETH 77.2 (was 69.5), SOL 83.7 (was 74.1). Annualised volatility: BTC 38.4% (was 44.0%), ETH 50.3% (was 57.1%), SOL 44.7% (was 53.6%). Higher score = calmer, so all three now look calmer. The cone is still drawn, now from the persistence volatility, so it is narrower. The note says the EWMA approval was withdrawn |
| NFT item card and holdings: the error line | "Typical error: Accuracy check pending" | **"Median error in testing (Feb-Nov 2026): X%"** with the collection's tested error: azuki 3.8%, boredapeyachtclub 3.6%, doodles-official 3.2%, lilpudgys 2.8% (B2), milady 3.0%, mutant-ape-yacht-club 3.2%, pudgypenguins 2.0%. Items in their collection's rarest 10% also show **"Rarest items: about 9%"** (D84) |
| NFT item estimate | the development fit (training data to 2025-12-24) | **the 2026-11-14 refit** (sales to 2026-11-06), refitted monthly (D83). Example: pudgypenguins #7862 is now 2.308 ETH at a floor of 2.277 ETH (the 10.7 log showed 2.394 ETH from the development model, at an earlier floor) |
| Monitoring | none for item values | a daily log of every served estimate; monthly summaries of served vs floor in `ml/docs/phase10/live_accuracy/` from 2027-01-01 (D85). Nothing changes automatically |

Unchanged: lilpudgys stays on B2 (D80), no range, no drivers, ETH only, the caption, NFT risk (persistence, D73),
crypto price (last value, D35) and direction (UNCERTAIN, D33).

## 2. Commits (all pushed to origin/phase-10-nft)

| Commit | What |
|---|---|
| `8c86c6b` | D80, D81 (owner decisions) |
| `99dcc8a` | D49 audit (`ml/evaluation/d49_audit.py`, report `ml/reports/d49_audit_risk.json`), D82, crypto risk switched to persistence, tests |
| `e0056f6` | frontend: the cone accepts the persistence note (`SERVED_RISK_NOTE_PREFIXES`) |
| `1ba73af` | scorecard regenerated (logged vs top-only approvals) |
| `39c9216` | ML: refit module + monthly job (D83), error line (D84), live accuracy log (D85), contract field, compose mounts, tests |
| `80953b4` | backend: `rarity_accuracy_note` passed through (item value and holdings) |
| `6837982` | frontend: error lines on the item card and holdings |
| `0e083fd` | the first refit (2026-11-14) made by the sidecar job, and its sanity check |
| `67448c0` | screenshots |
| `718eb12`, `33e6eba` | scorecard NFT section, regenerated |
| `2119f2a` | docs: PLAN_NFT status, PHASE_10_nft.md, glossary, STATUS verify block and backlog |
| (this commit) | checkpoint_10.9.md, WIP |

Deployment (the 10.7 method): `docker compose up -d --build --no-deps ml ml-refresh ml-nft-refresh`, then
`docker restart altinvest-backend` (twice: the second after the ML API was up, so the backend pull stored the new
values). The backend and Mongo containers were not recreated.

## 3. D49 audit outcome (D81, D82): the EWMA approval is WITHDRAWN

The audit uses the logged Phase 9 walk-forward results only (run at `acf6ce7`), with nothing re-run. Per asset and
horizon, all configs are ranked together on the first 60% of folds. Both model types were scored on the same
ranking rows; the script checks this. Only the top config is confirmed, with its logged paired CI (block = h,
1,000 resamples, seed 0).

| Asset, h | Ranking QLIKE: EWMA / GARCH / persistence | Top | Top's confirmation CI (persistence - model) | Approved under top-only |
|---|---|---|---|---|
| BTC 30 | 0.5559 / **0.4737** / 0.6797 | GARCH | 0.0587 [-0.0551, 0.1908] | none |
| BTC 7 | 0.7138 / **0.6552** / 0.7882 | GARCH | 0.0780 [-0.0086, 0.1833] | none |
| ETH 30 | 0.3927 / **0.3694** / 0.4776 | GARCH | -0.1483 [-0.3039, 0.0432] | none |
| ETH 7 | 0.5237 / **0.5070** / 0.5569 | GARCH | -0.0014 [-0.1210, 0.1226] | none |
| SOL 30 | 0.6838 / **0.3837** / 0.8630 | GARCH | -0.0889 [-0.2102, 0.0473] | none |
| SOL 7 | 0.6432 / **0.5311** / 0.7837 | GARCH | 0.0304 [-0.0694, 0.1757] | none |

- **Risk:** the result does not match the current approval (EWMA), so the approval is withdrawn as instructed.
  - Crypto risk serves persistence vol_30d with the D36 pooled percentile, and the cone uses it (`config.RISK_VOL_COLUMN = "vol_30d"`, `RISK_MODEL_SERVED = False`, model_version `persistence-pooled-pct`).
  - EWMA is still logged for the D46 monitor, whose risk status is now "info" and never "ALERT".
  - D44 has a clause allowing EWMA to be served through a new D-number. I did not use it: reviving EWMA would be a new owner decision.
- **Direction** (the only other part with a logged approval): logreg_c0.1 ranks first for every asset (ETH: 1.1694 vs LightGBM 1.2258), and ETH's CI 0.0359 [0.0035, 0.0604] passes. So the ETH approval stands; it is still not served (D33/D50).
- **Price and range** logged no approval, and top-only can only remove approvals.
- **Scorecard:** it now shows the logged (D49) and the top-only approvals side by side. 5 of 60 Phase 9 rows were approved as logged; 1 is approved under top-only; 0 are served.

## 4. Tests and snapshots

| Suite | Result |
|---|---|
| ML `python -m pytest ml -q` | 441 passed, 0 failed, 4 warnings (deprecation/FutureWarning only), 2 h 40 min on this machine (low free RAM) |
| Backend (container) `python -m pytest tests -q` | **44 passed, 1 skipped** (the skip is the compose-file test, as before) |
| Frontend `npm test` | **21 passed**. ESLint is clean on all 21 frontend files this branch changed. `eslint src` also reports errors in files this branch never touched (App.jsx, charts, Sidebar, onboarding and others, unchanged from main); not fixed here |
| Snapshots | `ml.nft.snapshot --verify` (2026-11-10), `ml.nft.item_snapshot --verify` (-items), `ml.nft.item_data --verify` (-items-v2, -items-v3): all "OK, all hashes match". Crypto evaluation snapshot: `require_snapshot()` OK |

New tests:
- `test_d49_audit.py`;
- `test_nft_fv_refit.py`: a refit dated 2026-01-01 on the live folder reproduces the development artifact byte for byte (137,040 rows, same model sha256); the guard refuses changed parameters or features; one refit per month; the pointer stays inside the folder; accuracy.json equals the sealed report;
- `test_nft_live_accuracy.py`: matching, settling, alerts, job failures;
- in `test_nft_fv_serving.py`: the rarest-item line, and the logged estimates equal the API values;
- updated serving, live-score and scorecard tests for D82.

## 5. Serving refit (D83)

- **Refit made by the sidecar job at deployment:** R = 2026-11-14, cutoff 2026-11-07.
  - 185,052 training rows, sales from 2024-11-10 to 2026-11-06.
  - Model sha256 `949f66c5bb549ae12dfeae1077e4a0b99ad120d0ebff98dced8b6cf0b1ee7e3d`.
  - Served via `ml/artifacts/nft_fv/CURRENT` and logged in `refit_log.jsonl`.
- **For comparison:** the sealed test's November fold trained on 183,669 rows to 2026-10-25.
- **Sanity check** (report only, `ml/reports/nft/fv_refit_sanity.json`): 180 tokens, 30 per model collection, seed 0, at the same request time.
  - The value difference between the refit and the development model is 0.45% median and 2.9% at p90. Spearman is 0.98.
  - The largest difference is 43% (one azuki token). The per-collection p90 is highest for azuki (20%) and pudgypenguins (8.7%).
  - Nothing was selected or changed on this result.
- **Monthly job:** on the first refresh of each month (00:10 UTC on the 1st), the same procedure runs. It refuses if the parameters, rounds or feature columns differ from the development artifact.

## 6. Live accuracy log (D85)

- **First daily record:** 2026-11-14 11:02 UTC. Served estimates for all 90,395 tokens, all with an estimate, in `/data/nft/live_accuracy/estimates/` (ml-data volume, not tracked).
- **Summaries:** a month is summarised once its sales are 30 days old, so W2 has settled. The first summary (November 2026, from the 14th) is due on 2027-01-01.
- **Monitoring only:** a collection behind B0 for two consecutive months is marked ALERT, and only the owner acts on it.

## 7. Decisions still "AUTONOMOUS, needs review" (Phase 10)

| D | One line |
|---|---|
| D63 | The modelling floor is the last OpenSea point at or before 00:00 UTC with no age limit (carried over gap days); the displayed floor stays null on gaps |
| D64 | One frozen snapshot (2026-11-10) for collection and item data; small files tracked, large ones by hash only |
| D65 (a)-(e) | NFT risk run details: trial count 2, n_effective reported two ways, GARCH with normal errors, served measure = the winner, sidecar added in 10.4. (f)-(i) came from user review |
| D66 | The floor spike guard. Withdrawn by D73, so there is nothing to decide; listed because it still carries the label |
| D67 | NFT API details: schemas in CONTRACT_NFT.md, field changes to D61, the last-floor-date rule, stale notes, Docker settings |
| D68 | 348 tokens without metadata were filled from OpenSea in a separate frozen item snapshot; rarity is computed over known tokens only |
| D76 | Fair-value declarations (target, features, folds, 6 configs, MdAPE, bootstrap); the 7fa7ec9 amendments came from user review |
| D77 | How the 10.6 result was read: approved against B2, no range (the fallback B2 range was out of band), lilpudgys to B2 by the guard |
| D78 (A) | Request-time history subset; transactions without a payment record dropped; serving refuses on a trait-hash mismatch; last-sale definition; 48 h stale note; lightgbm in the serving image with the artifact mounted |
| D79 (A) | "Best of B0/B1/B2" = the lowest pooled MdAPE; embargo rows enter later training cutoffs |
| D83 (A) | Refits use the live folder (not a snapshot); versioned folders and a CURRENT pointer; a refit is due on the first refresh of a month |
| D84 (A) | X has 1 decimal, Y is a whole percent; Y = the pooled rarest-decile MdAPE (not per collection); a new API field `rarity_accuracy_note` |
| D85 (A) | Every token logged daily; 48 h match window; a month is summarised 30 days after it ends; ALERT after 2 months behind B0 |
| D82 (not marked, but two readings) | I extended the audit to direction (the only other logged approval), and I did not use D44's EWMA clause |

## 8. Backlog (also in STATUS.md)

- Hardcoded asset header prices (demo seed data, not the market).
- Phone sidebar (opens expanded).
- NFT risk re-evaluation on or after 2027-05-10: top-only, raw floor, new frozen snapshot (D65 h-i, D73).
- NFT range calibration as a future declared phase (no range is served, D77).
- lilpudgys guard revisit at the next declared fair-value re-evaluation, on sales after 2026-11-10 (D80).
- Still open from 10.7:
  - payment records for new multi-token sales (`ml.nft.tx_payments` is not in the sidecar);
  - Binance unreachable from Docker on this machine (at this deployment the ML API waited for its crypto refresh retries before starting, and the NFT sidecar's ETH stage failed; the last good data is kept, D40);
  - two different floors on screen;
  - the unrounded floor on the holdings card.
- Also seen at deployment: the floor stage refused an OpenSea answer with 2 fewer points (`OlderData`) and kept the stored file. This is the existing guard working, not a bug.

## 9. Screenshots (`ml/docs/phase10/screenshots/10.9_*`, live stack, demo user, headless Edge)

- `10.9_item_card_desktop_dark.png`, `_desktop_light.png`, `_phone_dark.png`: pudgypenguins #7862, "Median error in testing (Feb-Nov 2026): 2.0%".
- `10.9_item_card_azuki_desktop_dark.png`: azuki #8604, 3.8%.
- `10.9_item_card_rarest_decile_desktop_dark.png`: azuki #278 (rank 786 of 10,000), with "Rarest items: about 9%".
- `10.9_demo_holdings_desktop_dark.png`: both holdings with their error lines.
- `10.9_btc_asset_cone_desktop_dark.png`: the BTC cone from the persistence volatility.
- `10.9_dashboard_desktop_dark.png`: the dashboard.
- The BTC page has no Risk Overview card (the backend sends an empty `risk_overview`), so the cone is where the served volatility shows.
- Checked text: `10.9_screenshot_facts.json`. The pending line is gone, the rarest line appears only on the rarest item, there is no USD, range or driver text, and the phone page width is 390 (no horizontal scroll).

## 10. Steps for the owner to merge

1. Review sections 1, 3 and 7 (and D80-D85).
2. Merge: the branch is 0 commits behind `origin/main`, so the merge is clean.
   - `git fetch origin`, then `gh pr create --base main --head phase-10-nft --title "Phase 10: NFTs"`, and merge on GitHub;
   - or locally: `git checkout main`, `git pull`, `git merge --no-ff phase-10-nft`, `git push origin main`.
3. After merging, on this machine nothing needs rebuilding: the running containers already serve this code.
4. On another machine or a fresh clone, some files are not in git (D64, D78, D83): the `model.txt` files, and
   the NFT data in the ml-data volume. That volume includes `tx_payments.csv` and the D68 fill files, which were
   copied in by hand in 10.7. Copy them in the same way, start the stack with `docker compose up -d --build`, then
   run `docker exec altinvest-ml-nft-refresh python -m ml.nft.fv_refit --refit`. That writes a refit for that day
   and points CURRENT at it. Until then the item value endpoints answer 503; the rest of the app works.
5. Optional: run the "How to verify Phase 10 yourself" block in `ml/docs/STATUS.md`.

STOP. Phase 10 is closed on the branch, waiting for the owner's review and merge.
