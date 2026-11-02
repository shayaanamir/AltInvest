# PLAN_NEXT — from the 2026-11-02 audit to Phase 8

Status: DRAFT for the user's approval. Nothing below has been started. Do the tasks in order; each has a testable
"done when". Tasks marked **[Person B]** touch backend/, frontend/, db/ or docker-compose.yml: Person B agreed on
2026-11-01 to minimal edits (see STATUS.md line 4), and every changed file must be listed in STATUS.md.

Audit verdict: **READY WITH CAVEATS** to hand to backend/frontend. The API is correct, contract-valid and fast
(worst 72 ms over 10 calls per endpoint). Caveats: A1 (restart outage), A2 (log corruption), the pooled 503 (A3),
and the Phase 7 backend pitfalls in section C.

Evidence (2026-11-02, branch ml-phase-7 at 5f447dc, tree clean): `python -m pytest ml -q` -> 225 passed (host and
container); `docker compose build --no-cache ml` 113 s, 846 MB; container healthy; all /predict and /risk 200 and
valid against CONTRACT.md; /predict/doge 404; 39 snapshot/report SHA-256 identical before and after.

## A. ML fixes (ML only, no Person B)

| # | Sev | Task | Files | Done when |
|---|---|---|---|---|
| A0 | - | Finish the rule-16 gap: write `docs/phases/PHASE_6c_gaps_guard.md` (8-section template) and add it to the AGENTS.md docs list. Record the 39 SHA-256 hashes themselves in STATUS.md (today only "identical" is written, so a later audit has nothing to compare with). Mark open question 4 resolved (ml/wbtc_validation_model.csv no longer exists). | ml/docs/phases/PHASE_6c_gaps_guard.md (new), ml/AGENTS.md, ml/docs/STATUS.md | File exists with 8 sections; STATUS.md has a hash table; `Test-Path ml\wbtc_validation_model.csv` False. |
| A1 | High | Restart outage. The ml CMD (`ml/Dockerfile:35`) runs the refresh BEFORE uvicorn under `sh` as PID 1, so (a) the API is down while the startup fetch runs (observed 94 s and 165 s on 2026-11-02 when the container's network was not ready, "Errno 101 Network is unreachable"); (b) `docker stop` during that refresh SIGKILLs it (exit 137): `.refresh.lock` and `.bak` files are left; (c) on the next start the refresh waits `LOCK_WAIT_SECONDS`=600 (`ml/data/refresh.py:39`) on the dead lock, so the API is down ~10 min (observed: still down at 96 s, came up 11 s after the lock was removed). Fix: start uvicorn first and run the startup refresh in the background without waiting for the lock (`lock_wait=0`, the sidecar refreshes anyway); add `init: true` to `ml` and `ml-refresh` in compose so SIGTERM reaches Python; treat a lock as stale when its pid is not alive in this container or it is older than 15 min. | ml/Dockerfile, ml/data/refresh.py, ml/api/service.py (startup hook), ml/tests/test_refresh.py, docker-compose.yml **[Person B: 2 lines]** | Drill: `docker compose start ml`, then `docker stop altinvest-ml` within 3 s, then start again -> /health 200 within 30 s; no `.refresh.lock` or `*.bak` after the next refresh; new pytest case for a dead-pid lock. |
| A2 | High | A truncated or corrupt line in `prediction_log.jsonl` makes `read_log` raise (`ml/serving/prediction_log.py:29`). Then `/debug/live-scorecard` returns 500 (reproduced) and every later `append_served` fails; the refresh only prints "prediction log error", so live tracking stops silently for good. Fix: `read_log` skips unparseable lines and returns a count; `build()` reports `n_corrupt`; append writes whole lines with flush+fsync. | ml/serving/prediction_log.py, ml/evaluation/live_score.py, ml/tests/test_live_tracking.py | Test: a log with one good and one truncated line -> /debug/live-scorecard 200 with `n_corrupt: 1`, and the next append adds rows. |
| A3 | Med | Pooled 503 (D36). `feature_tables` (`ml/serving/responses.py:33-43`) refuses ALL assets if one fails the gate: deleting only SOL's report gave 503 on /predict/btc and /risk/eth too, with a message naming SOL. Choose: (a) keep it and document it for the backend (keep the last good row), or (b) pool over servable assets only, with a note naming the excluded asset (needs a new D41, scores shift slightly). Recommend (a) now, (b) later. Also fix the docstring at `prediction_log.py:5` ("an asset that is not servable is skipped": in fact all are skipped). | ml/docs/DECISIONS.md, ml/serving/prediction_log.py (docstring); for (b) responses.py + tests | (a): the handoff note and STATUS.md say it; docstring matches. (b): test where SOL is unservable -> BTC 200 with the note, SOL 503. |
| A4 | Med | `/health` returns 500 on an unreadable CSV (`responses.py:168` catches only FileNotFoundError; reproduced with a garbage eth CSV) and says "ok" even when no asset is servable (reproduced). Docker then marks it unhealthy for the wrong reason, and the backend cannot use it to tell "up but no data". Fix: catch (OSError, ValueError, KeyError) -> null; add `servable: {asset: bool}` to /health (not in CONTRACT.md). | ml/serving/responses.py, ml/api/service.py, ml/tests/test_serving.py | Test: garbage CSV -> /health 200 with that asset null and servable false. |
| A5 | Low | live_score: rows of an asset that is not servable now stay "pending" forever with `scorable_from` in the past, so `first_scorable` can be a past date (`ml/evaluation/live_score.py:40`, `:91`). Fix: status `blocked` when the date has passed but the asset has no servable data; count it separately. | ml/evaluation/live_score.py, test | Test with a past-dated row and no closes -> `blocked`, not pending. |
| A6 | Low | Lock takeover race: two processes can both see a stale lock and the second `unlink` deletes the first one's new lock (`refresh.py:101-103`). Covered by A1's pid check; take over by `os.replace` of a fresh lock instead of unlink+create. | ml/data/refresh.py | Covered by A1's tests. |
| A7 | Low | Remove the obsolete `version: "3.9"` (docker-compose.yml:1); every compose command warns. | docker-compose.yml **[Person B: 1 line]** | `docker compose config` prints no warning. |

Checked and fine (no task): /debug/scorecard and /debug/live-scorecard win over /debug/{asset} (declared first; 200
with the scorecard JSON); log idempotency (restart and the sidecar both "added nothing"; 6 rows, 0 duplicates);
no circular import (refresh imports prediction_log at the top, prediction_log imports refresh lazily; every import order
works); percent -> log return `log1p(p/100)` is correct; last_bar timezone matches (loader is UTC-aware); no bar after
t+30 is read (labels use rows t+1..t+30); refresh restore on network failure (drill: files byte-identical, API 200);
scorecard.json is not stale (git_dirty false, commit b243823, only docs commits after it). Known window, accepted:
between `os.replace` of the CSV and of the report (refresh.py:176-178) a request can get a brief 503; the backend
pulls at 00:15, not at 00:05.

## B. Hand-over (ML, after A0-A2)

| # | Task | Files | Done when |
|---|---|---|---|
| B1 | Publish the handoff note (Appendix) with numbers re-taken from live responses on the day. | ml/docs/HANDOFF.md (new) or a shared doc | Person B confirms receipt; every number in it matches a response or report. |

## C. Phase 7: backend integration **[Person B]**

Facts from the audit: nothing in backend/ calls the ML service yet (the only `ml:8001` is a compose comment).
backend/models/schemas.py PredictionResponse and RiskResponse match CONTRACT.md field for field, including `note`.

| # | Task | Files | Done when |
|---|---|---|---|
| C1 | Daily pull: a scheduler thread (same pattern as `run_aai_refresh_scheduler`, backend/main.py:161) calls `GET {ML_BASE_URL}/predict/{a}` and `/risk/{a}` for BTC, ETH, SOL at startup and at 00:15 UTC. Each call has a 10 s timeout and 3 retries with backoff; 404 -> skip; 503 or timeout -> write nothing (keep the last good row). Store `timestamp` as a BSON datetime, NOT a string: seeded rows use datetimes, and Mongo sorts Date above String, so `sort timestamp -1` (db/queries.py:35, :43) would keep returning the seed rows. Keep `note` and `signal`. Add `ML_BASE_URL: http://ml:8001` to the backend service env. | backend/controllers/ml_pull_controller.py (new), backend/main.py, db/queries.py, docker-compose.yml | With the stack up: the latest `predictions` row for BTC has model_version `baseline-last-value` and a note. `docker compose stop ml`, run a pull -> the log says 503/timeout and the row is unchanged. Unit test with a mocked HTTP client. |
| C2 | Pass `note` through: `_map_prediction` (backend/routes/prediction.py:12-27) and `_map_risk` (backend/routes/risk.py:13-19) both drop it. Also /risk falls back to mock numbers when no row exists (risk.py:40); for BTC/ETH/SOL that shows invented values. And a stored null risk_score would 500 (schemas.py:94 requires a float). | backend/routes/prediction.py, backend/routes/risk.py | GET /prediction/BTC and /risk/BTC return the ML note; no mock values for a covered asset. |
| C3 | Staleness: when the latest stored row is more than 36 h old, append "data stale" to `note`. ML adds its own note after 48 h from the bar close (D38, config.STALE_DATA_HOURS); the two rules measure different things, so keep both. | backend/routes/prediction.py, backend/routes/risk.py | Test with a 37 h old row -> stale note. |
| C4 | Seeds: db/seed_predictions_risk.py writes invented BTC/ETH/SOL predictions (e.g. STRONG_BUY, +9.8%, model_version seed-v1) and upserts on (asset, date), so re-running it on a pull day overwrites the real row. Stop seeding predictions/risk for the ML-covered assets; remove the v1 `ml/api/prediction_service.py` mentions (seed :5, :57; backend/routes/prediction.py:36). | db/seed_predictions_risk.py, backend/routes/prediction.py | `git grep prediction_service -- backend db` is empty; re-running the seed leaves the BTC latest row unchanged. |
| C5 | AAI with the baseline: prediction_30d = 0 gives pred_score 50 (aai_controller.py:58-60, aai_engine `normalise_expected_return`), so AAI is computed from a "no-change" placeholder as if a model said neutral. Prediction confidence and signal are not used, so null/UNCERTAIN do not break it. Person B decides: keep the neutral 50 and show why, or treat `model_version == "baseline-last-value"` as a missing prediction (AAI null). | backend/controllers/aai_controller.py | The chosen rule has a test, and the AAI note says which. |
| C6 | Frontend: the "Signal" badges (PricePerformanceCard.jsx:262-269, AboutAssetCard.jsx:28-31, AaiScoreCard.jsx:6-15, Discover/Watchlist/Similar badges) come from the AAI score (`aai_signal`, getAaiSignal), never from the ML `signal`. With predicted_price null the forecast chart already says "No model forecast is stored for this asset yet." (PricePerformanceCard.jsx:146), which is correct. Agreed change: label the AAI badge "AAI rating" (or hide it) while the ML signal is UNCERTAIN, and show the ML note on the asset page (backend must add `ml_signal` and `ml_note` to the asset-detail payload, backend/routes/assets.py). | frontend/src/components/assetDetail/*.jsx, frontend/src/utils/scoring.js, backend/routes/assets.py | The BTC asset page shows the ML note and no "Buy/Sell" text presented as the model's signal. |
| C7 | Close Phase 7: end-to-end run with mongodb, backend, ml, ml-refresh; STATUS.md "How to verify Phase 7 yourself" block; docs/phases/PHASE_7_backend_integration.md; list every backend/frontend/db file changed. | ml/docs/STATUS.md, ml/docs/phases/PHASE_7_backend_integration.md | PLAN row 7: the backend calls ML over HTTP end to end, shown by the verify block. |

## D. Phase 8: NFTs (plan only)

| # | Task | Files | Done when |
|---|---|---|---|
| D1 | Write PLAN_NFT.md: data source and licence, collections, validation rules (DATA.md style), the baselines first, the same evaluation rules and contract fields. No code, no data. Starts only after C7. | ml/docs/PLAN_NFT.md (new) | The user approves the file. |

## Appendix: draft handoff note for the backend and frontend teams

(Numbers are from live responses on 2026-11-02 ~08:21 UTC; re-take them on the day you send it.)

**What it is.** The ML service gives one 30-day forecast and one risk score per asset for BTC, ETH and SOL. Today
it serves simple baselines, because no model beat them in testing. The scores are real; the forecast is "no change".

**Base URL.** Inside docker compose: `http://ml:8001`. From your machine: `http://127.0.0.1:8001`. Docs at `/docs`.

**Endpoints.**
- `GET /predict/{asset}` (asset is case-insensitive):
  `{"asset":"BTC","predicted_price":null,"prediction_30d":0.0,"confidence":null,"model_version":"baseline-last-value","timestamp":"2026-11-02T08:21:06Z","lower_bound":null,"upper_bound":null,"risk_score":97.795108,"trend":null,"agreement":null,"signal":"UNCERTAIN","boosted_confidence":null,"ensemble_price":null,"note":"No model beats the no-change baseline (D35): prediction_30d is the last-value baseline (0%); no predicted price or interval. Direction is not served (D33): no demonstrated up/down skill; signal UNCERTAIN, confidence null."}`
- `GET /risk/{asset}`:
  `{"asset":"BTC","risk_score":97.795108,"volatility":0.284906,"sharpe_ratio":-0.772753,"timestamp":"2026-11-02T08:21:04Z","note":"No risk model beats persistence (D27): risk_score is the percentile of today's 30-day volatility among BTC, ETH, SOL up to today (D36), higher = safer."}`
- `GET /health`: `{"status":"ok","model_version":{"price":"baseline-last-value","risk":"persistence-pooled-pct"},"data_last_bar":{"btc":"2026-11-01","eth":"2026-11-01","sol":"2026-11-01"}}`
- `/debug/{asset}`, `/debug/scorecard`, `/debug/live-scorecard`: for us, not for the product.

**What the fields mean.**
- `prediction_30d`: expected change over 30 days, in percent. Always `0.0` for now (D35: no price model beat "no change").
- `predicted_price`, `lower_bound`, `upper_bound`: always null for now (D35). Do not compute a price from 0%.
- `signal`: always `UNCERTAIN`, `confidence` always null (D33: no proven up/down skill).
- `risk_score`: 0-100, higher = safer. It ranks today's 30-day volatility against BTC, ETH and SOL history (D36), so scores compare across assets. The same number appears in /predict and /risk.
- `volatility`: annualised (0.28 = 28%). `sharpe_ratio`: last 365 days, a description of the past, not a forecast.
- `trend`, `agreement`, `boosted_confidence`, `ensemble_price`: always null (no ensemble exists).
- `note`: always set; show it to users or in logs. It gains "data stale: last bar <date>" if the data is over 48 h old.

**Errors.**
- 404: asset not covered (e.g. DOGE). Do not retry.
- 503: the data did not pass its checks. Keep your last good row and retry next day. Today one bad asset makes ALL three return 503 (scores are pooled).
- Timeouts: responses took at most 0.07 s in testing; use a 10 s timeout and 3 retries. Right after the container starts, the API may be unavailable for a few minutes while it downloads data.

**Refresh and staleness.** ML refreshes its data daily at 00:05 UTC. Pull at 00:15 UTC. If ML is down, keep the last good row and mark it stale after 36 h.

**Frontend while signal is UNCERTAIN.** Do not show Buy/Sell as the model's call. Show the note (for example "No reliable direction forecast"); the AAI badge should read "AAI rating", or be hidden. Keep the "No model forecast is stored" text on the chart.

**Run it locally.** From the repo root: `docker compose up -d --build ml ml-refresh`, then `curl http://127.0.0.1:8001/health`. Needs outbound HTTPS to api.binance.com. Stop with `docker compose down` (keeps the `ml-data` volume; `down -v` deletes it).

**Contact.** ML: <name / channel to fill in>.
