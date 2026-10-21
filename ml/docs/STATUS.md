# STATUS

Current phase: 6c (hardening before the PR) DONE (2026-10-21), on top of 6b (daily refresh, serving gate, v2 Docker image and compose services). The service runs from a fresh clone with `docker compose up -d --build ml ml-refresh`.
Next: the PR from ml-v2 into main (not pushed, not opened), then Phase 7 (backend integration, Person B).

## Phase 6c: what ran (from repo root, 2026-10-21)

- Started from a clean tree: HEAD d994366. Hashes of all 39 files under ml/data/raw and ml/reports taken first.
- 1. Gaps:
  - The refresh treats new data with any missing day as a failure (`ValidationFailed: N missing day(s), first <date>`). The previous files are restored.
  - Serving turns the gap error from `build_features` into NotServable -> 503 (it used to be a 500).
  - validate.py is unchanged, so the snapshot reports are byte-identical.
- 2. Monotonicity: the refresh rejects new data with fewer rows or an earlier last bar than the CSV it would replace (`OlderData: ...`). The previous files are restored.
- 3. Evaluation guard: `ml/data/snapshot_guard.require_snapshot()` is the first line of `main()` in all 10 report writers: the six run_* modules, power_check, direction_mechanism, risk_mapping_check and ml.data.dataset_summary.
  - It exits 1 with a D40 message when ML_RAW_DIR or ML_VALIDATION_DIR is not the snapshot default.
  - ml/README.md now warns that ml.data.fetch and ml.data.validate overwrite the snapshot on the host.
- 4. DOCKER.md: `down -v` now also mentions the `ml-data` volume. The v1 Prophet/TensorFlow image note is replaced by the v2 image (small; needs HTTPS to Binance). No other v1 mentions remain in DOCKER.md.
- Tests:
  - `test_snapshot_guard.py` (11): the helper, plus one refuse/run smoke test per guarded module.
  - `test_refresh.py` +4: a gap, fewer rows and earlier last bar, fewer rows only, earlier last bar only. Each restores all three files.
  - `test_serving.py` +1: a gap gives 503 through the API.
  - `python -m pytest ml` -> `199 passed` (183 + 16).
  - First run: 1 failure in my own fixture arithmetic (a 2-day shift of 402 rows still ends 2026-10-17, which the refresh correctly accepted). Changed it to a 3-day shift; the assertion is unchanged.
- Docker: `docker compose up -d --build ml` -> healthy.
  - `/predict/btc` validates against PredictionResponse.
  - The startup refresh on the existing ml-data volume accepted the new day (3351 -> 3352 rows, last bar 2026-10-20).
  - `docker compose exec ml python -m ml.evaluation.run_backtest --asset btc` refuses with the D40 message.
  - `docker compose down` keeps the volume.
- All 39 snapshot and report files are byte-identical after the phase (SHA-256).

## How to verify Phase 6c yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests, then only the 6c ones (hand-made fixtures, no network)
python -m pytest ml -q
python -m pytest ml/tests/test_snapshot_guard.py -q
python -m pytest ml/tests/test_refresh.py ml/tests/test_serving.py -q -k "gaps_and_older or gap_in_bars"

# 2. The guard: refuses with a serving directory set, passes on the snapshot (no report is written)
$env:ML_RAW_DIR = "$env:TEMP\ml-serving-raw"; python -m ml.evaluation.power_check --asset btc; "exit: $LASTEXITCODE"
Remove-Item Env:ML_RAW_DIR; python -c "from ml.data.snapshot_guard import snapshot_mismatches; print(snapshot_mismatches())"

# 3. Docker: rebuild, wait until healthy, call /predict/btc, the guard inside the container, stop
docker compose up -d --build ml
curl.exe -s --retry 60 --retry-all-errors --retry-delay 2 http://127.0.0.1:8001/predict/btc; ""
docker compose exec ml python -m ml.evaluation.run_backtest --asset btc
docker compose down
```

Expected (observed 2026-10-21):

1. `199 passed`; `11 passed`; `5 passed` (4 refresh cases plus the API gap case).
2. `refusing to write evaluation reports: ML_RAW_DIR=...ml-serving-raw is not the evaluation snapshot (D40). ...`, then `exit: 1`; then `[]`.
3. A PredictionResponse with `"prediction_30d":0.0` and `"signal":"UNCERTAIN"`. Then the refusal, naming `ML_RAW_DIR=/data/raw, ML_VALIDATION_DIR=/data/validation`. The containers are removed and the volume is kept.

## Phase 6b: what ran (from repo root, 2026-10-21)

- Started from a clean tree: HEAD 7aaa1db. Docker 29.1.3 (Docker Desktop), Compose v5.0.1.
- Step 0a: re-ran run_backtest and risk_mapping_check once per asset. Only generated_at, git_commit and git_dirty (true -> false) changed (JSON diff).
- Step 0b: `rfc3339-validator==0.1.4` pinned. Steps 0c-0e: D38, D39, D40 appended in order. CONTRACT.md: only the two `note` descriptions changed (D39).
- Data paths (D40): config.py reads `ML_RAW_DIR` and `ML_VALIDATION_DIR` once; unset, they are ml/data/raw and ml/reports/data. Loader, fetch, validate, require_validated, the gate and the refresh read them.
  - Proof nothing changed on the host: SHA-256 of all 12 snapshot files and all 27 other report files identical before and after the phase; `validate.build_report` reproduces the committed validation reports (except validated_at). No report writer ran except Step 0a.
  - `git status` cannot show this for ml/data/raw (git-ignored), hence the hashes.
- New modules: `ml/data/serving_gate.py` (passed report + same rows + same last timestamp, else NotServable -> 503) and `ml/data/refresh.py` (back up, fetch into staging, validate, os.replace; restore on any failure; lock file; refresh_status.json).
  - Changed only for paths: fetch.fetch and loader take an optional `raw_dir`; validate.main's report building moved into `build_report` (same output). require_validated keeps its CLI behaviour and message.
  - Added beyond the task text, needed for correctness: a lock file (the ml startup refresh and ml-refresh's at-start run share one volume) and `healthcheck: disable` for ml-refresh (it inherits the image's /health check).
- On the host, `python -m ml.data.refresh` refuses: exit 1, "refusing to write to the evaluation snapshot", nothing written.
- Tests: `test_refresh.py` (16) and 7 gate cases in `test_serving.py`. `python -m pytest ml` -> `183 passed` on the host and in the container (contract test ran, 12 passed, not skipped).
- Docker: image `altinvest-ml` 846 MB, python:3.12-slim, no raw CSVs inside. `docker compose up -d ml ml-refresh` -> /health 200, container healthy. Both startup refreshes ran one after the other (lock). /predict/btc, /risk/sol, /risk/btc, /risk/eth validate against CONTRACT.md; /predict/doge 404. `docker compose down` kept volume `altinvest_ml-data`.

refresh_status.json from the container (2026-10-20T20:15:33Z): btc ok, 3351 rows, last bar 2026-10-19; eth ok, 3351, 2026-10-19; sol ok, 2261, 2026-10-19; all_servable true.

```
GET /predict/btc -> 200
{"asset":"BTC","predicted_price":null,"prediction_30d":0.0,"confidence":null,"model_version":"baseline-last-value","timestamp":"2026-10-20T20:15:48Z","lower_bound":null,"upper_bound":null,"risk_score":95.70044,"trend":null,"agreement":null,"signal":"UNCERTAIN","boosted_confidence":null,"ensemble_price":null,"note":"No model beats the no-change baseline (D35): prediction_30d is the last-value baseline (0%); no predicted price or interval. Direction is not served (D33): no demonstrated up/down skill; signal UNCERTAIN, confidence null."}
GET /risk/sol -> 200
{"asset":"SOL","risk_score":81.601488,"volatility":0.470177,"sharpe_ratio":-0.909517,"timestamp":"2026-10-20T20:15:48Z","note":"No risk model beats persistence (D27): risk_score is the percentile of today's 30-day volatility among BTC, ETH, SOL up to today (D36), higher = safer."}
GET /predict/doge -> 404
```

- No stale note: the container's last bar closed 20.3 h before the calls. Scores differ from 6a because Docker serves two more days.

## For the PR (ml-v2 into main)

- Files changed outside ml/: `docker-compose.yml` (ml service replaced; `ml-refresh` and volume `ml-data` added), `.dockerignore` (v1 ML block replaced), `DOCKER.md` (ml row, hot-reload line), `package-lock.json` (deleted: empty, from v1 commit 7eb67c2, referenced nowhere).
- v1 mentions left in other teams' files (not edited):
  - backend/routes/prediction.py:36 (predictions "written by ml/api/prediction_service.py").
  - db/seed_predictions_risk.py:5, :54 (Prophet + LSTM), :57 (trend rule), :73 (`prophetPrice30d`).
  - db/seed_all.py:24 label "prices (from ml/data/raw CSVs)"; db/seed_prices.py:5 says there is no such dependency.
  - db/seed_data/assetDetail.json (`modelComparison.prophet/lstm`), assets.json (`prophetPrice30d`), nftCollections.json (`prophetFloor30dEth`).
  - DOCKER.md:56-60 (ml image installs prophet/tensorflow) and :43 (`down -v` now also wipes ml-data).
  - CONTRACT.md `agreement` and `ensemble_price` descriptions name Prophet/LSTM/RandomForest (contract text, unchanged).
- What changes for the team: a small ml image built from the repo root, no bind mount or hot reload; a new sidecar and volume; ML needs outbound HTTPS to api.binance.com at startup and daily at 00:05 UTC; a covered asset with bad data returns 503 (keep the last good row); `prediction_30d` 0, `predicted_price` null, signal UNCERTAIN.

## How to verify Phase 6b yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. Host tests (hand-made fixtures, no network), then the refresh refusing the evaluation snapshot
python -m pytest ml -q
python -m ml.data.refresh; "exit: $LASTEXITCODE"

# 2. The decisions and the CONTRACT wording
Select-String -Path ml\docs\DECISIONS.md -Pattern '^\| D3[8-9] |^\| D40 ' | ForEach-Object { $_.Line.Substring(0, 60) }
Select-String -Path ml\docs\CONTRACT.md -Pattern '"note": \{' | ForEach-Object { $_.Line.Trim() }

# 3. Build, start, wait for /health and for the sidecar's first run
docker compose build ml
docker compose up -d ml ml-refresh
curl.exe -s --retry 60 --retry-all-errors --retry-delay 2 http://127.0.0.1:8001/health; ""
while (-not ((docker logs altinvest-ml-refresh 2>&1 | Out-String) -match 'next refresh at')) { Start-Sleep -Seconds 2 }

# 4. Routes from the host
curl.exe -s http://127.0.0.1:8001/predict/btc; ""
curl.exe -s http://127.0.0.1:8001/risk/sol; ""
curl.exe -s -o NUL -w "doge: HTTP %{http_code}`n" http://127.0.0.1:8001/predict/doge

# 5. Refresh status and the test suite inside the container (contract test not skipped)
docker compose exec ml cat /data/validation/refresh_status.json
docker compose exec ml python -m pytest ml -q -rs

# 6. Host snapshot untouched (dates stay 18-19 Oct 2026), then stop; the ml-data volume is kept
git status --porcelain -- ml/data/raw ml/reports/data
Get-ChildItem ml\data\raw, ml\reports\data | Format-Table Name, Length, LastWriteTime
docker compose down
```

Expected (observed 2026-10-21; container clock 2026-10-20 ~20:17 UTC):

1. `183 passed`; then the "refusing to write to the evaluation snapshot ... (D40)" message and `exit: 1`.
2. Three lines `| D38 | Staleness`, `| D39 | CONTRACT.md`, `| D40 | Refines D10`; two `"note"` lines with the D39 description.
3. `Image altinvest-ml Built`, both containers `Started`, then `{"status":"ok",...,"data_last_bar":{"btc":"2026-10-19",...}}` (the last closed day when you run it). Every compose command also warns that `version` is obsolete; harmless.
4. `/predict/btc` with `"prediction_30d":0.0`, `"signal":"UNCERTAIN"`, risk_score near 95.7; `/risk/sol` near 81.6; `doge: HTTP 404`. Numbers move with each day of new data.
5. `"all_servable": true` with all three `"status": "ok"`; `183 passed` and no skip lines.
6. No git output; CSVs dated 18-10-2026, reports 19-10-2026; the containers and network are removed.

## Phase 6a: what ran (from repo root, 2026-10-21)

- Started from a clean tree: HEAD 62ec3bc, `git status --porcelain` empty, `python -m pytest ml` -> `136 passed`.
- Step 0a: `random_baseline` (ml/evaluation/backtest.py) now also reports `max_drawdown_median` and `hit_rate_median`.
  - The hit-rate median is taken over runs that were in the market at least once; it is null if there were none.
  - Re-ran run_backtest once per asset: exit 0, `git_dirty: true` (code uncommitted; expected).
  - JSON diff vs the committed backtest.json: only generated_at, git_commit and the two new fields differ. git_dirty was already true in the committed reports.

| backtest.json, random baseline medians | BTC | ETH | SOL |
|---|---|---|---|
| trades / max drawdown / in-market hit rate | 34 / -0.591118 / 0.645161 | 34 / -0.645638 / 0.558824 | 19 / -0.56033 / 0.65 |

- Steps 0b-0d: D35, D36, D37 appended after D34, in order (DECISIONS.md diff: 3 added rows).
- Step 0e skipped: there was no confirmation in the chat that Person B agreed to the CONTRACT note wording.
- Step 1: config.py `STALE_DATA_HOURS` 48, `SHARPE_WINDOW_DAYS` 365 (D37), `MODEL_VERSION_PRICE` "baseline-last-value" (D35), `MODEL_VERSION_RISK` "persistence-pooled-pct" (D36).
  - `STALE_DATA_HOURS` has no D-number; it cites the CONTRACT.md note rule.
  - requirements.txt: `httpx==0.28.1`.
- New modules:
  - `ml/serving/responses.py`: pure response builders (no FastAPI, no models). Reads features only (vol_30d, ret_1d).
  - `ml/api/contract.py`: parses both schemas from CONTRACT.md; Draft-07 validator with date-time format checking.
  - `ml/api/service.py`: the FastAPI app. /predict and /risk bodies are validated before they are returned.
  - `ml/evaluation/risk_mapping_check.py`: the read-only D36 check. It reads labels, so it lives in evaluation, not serving.
  - No earlier module changed except backtest.py (Step 0a), config.py and requirements.txt.
- Interpretations (no D-number):
  - Staleness is measured from the latest bar's close (open time + 1 day). Measured from the open, a normal daily refresh would show the note for part of each day.
  - The D36 pool needs every asset in config.ASSETS. If any one fails validation, all three return 503 (AGENTS rule 4). Dropping it from the pool would change every score, and D36 says that needs a new D-number.
  - sharpe_ratio uses the trailing 365 values of the `ret_1d` feature.
  - `require_validated` calls `sys.exit` (written for CLIs). Serving catches that and raises `NotServable`, which the API maps to 503.
  - The check cuts every asset at its own b2. SOL rows dated after 2025-06-06 (133 of 1104) therefore see a pool without BTC/ETH's later values. Served scores use the full pool.
- Tests: `test_serving.py` (10), `test_contract.py` (12 with parametrised cases), `test_backtest_random_medians.py` (2). `python -m pytest ml` -> `160 passed`; all passed on the first run.
  - `test_contract.py` skips if ml/data/raw/*.csv is missing (git-ignored).
- Step 6: `python -m ml.evaluation.risk_mapping_check --asset btc|eth|sol` -> exit 0, `git_dirty: true` (expected; not re-run). uvicorn was started once and each route called (outputs below).

| risk_mapping_check.json (walk-forward rows) [95% CI, block 30] | BTC | ETH | SOL |
|---|---|---|---|
| rows / n_effective | [760, 2791) / 67.7 | [760, 2791) / 67.7 | [760, 1864) / 36.8 |
| Spearman(D36 risk_score, fwd_vol_30d) | -0.287596 [-0.46301, -0.090986] | -0.506792 [-0.655774, -0.318042] | -0.204127 [-0.452395, -0.01536] |
| same, sign flipped (100 - risk_score) | 0.287596 [0.090986, 0.46301] | 0.506792 [0.318042, 0.655774] | 0.204127 [0.01536, 0.452395] |
| persistence Spearman(vol_30d, fwd_vol_30d), walkforward_baselines.json | 0.347215 [0.161079, 0.514323] | 0.515039 [0.332578, 0.659126] | 0.210949 [0.020382, 0.442397] |
| persistence recomputed on the same rows matches | True | True | True |
| rows with a cut pool / max_label_row_reached (b2) | 0 / 2820 (2821) | 0 / 2820 (2821) | 133 / 1893 (1894) |

- risk_score is higher = safer, so a good mapping has a negative Spearman. The pooled mapping keeps persistence's sign and most of its size.
  - BTC is 0.06 lower. The pool grows over time, so the same vol_30d gets a different score on a different date.
  - Report only. No paired CI was computed, so there is no claim either way that the gap is real.

| Served (uvicorn, 2026-10-20T19:07:50Z) | BTC | ETH | SOL |
|---|---|---|---|
| risk_score / volatility / sharpe_ratio | 91.062366 / 0.376012 / -0.606621 | 86.190369 / 0.432201 / -0.764863 | 64.72877 / 0.598477 / -0.882813 |
| last bar / stale | 2026-10-17 / yes | 2026-10-17 / yes | 2026-10-17 / yes |

- Every response carries the stale note. The CSVs end at 2026-10-17, and that bar closed 67.1 h before the calls (more than 48 h). This is correct behaviour; the Phase 6b daily refresh fixes it.
- Real responses, one per route (`curl.exe -s`):

```
GET /health -> 200
{"status":"ok","model_version":{"price":"baseline-last-value","risk":"persistence-pooled-pct"},"data_last_bar":{"btc":"2026-10-17","eth":"2026-10-17","sol":"2026-10-17"}}
GET /predict/btc -> 200
{"asset":"BTC","predicted_price":null,"prediction_30d":0.0,"confidence":null,"model_version":"baseline-last-value","timestamp":"2026-10-20T19:07:42Z","lower_bound":null,"upper_bound":null,"risk_score":91.062366,"trend":null,"agreement":null,"signal":"UNCERTAIN","boosted_confidence":null,"ensemble_price":null,"note":"No model beats the no-change baseline (D35): prediction_30d is the last-value baseline (0%); no predicted price or interval. Direction is not served (D33): no demonstrated up/down skill; signal UNCERTAIN, confidence null. data stale: last bar 2026-10-17"}
GET /risk/sol -> 200
{"asset":"SOL","risk_score":64.72877,"volatility":0.598477,"sharpe_ratio":-0.882813,"timestamp":"2026-10-20T19:07:42Z","note":"No risk model beats persistence (D27): risk_score is the percentile of today's 30-day volatility among BTC, ETH, SOL up to today (D36), higher = safer. data stale: last bar 2026-10-17"}
GET /debug/btc -> 200
{"asset":"BTC","timestamp":"2026-10-20T19:07:50Z","inputs":{"last_bar":"2026-10-17","last_bar_close":"2026-10-18T00:00:00Z","age_hours":67.13080223888889,"stale":true,"vol_30d":0.0196813476423941,"volatility":0.37601161874679045,"sharpe_ratio":-0.6066207921806744,"returns_available":3319,"pool_assets":["btc","eth","sol"],"pool_size":8867,"p":0.0893763392353671,"risk_score":91.06236607646329},"stale_after_hours":48,"sharpe_window_days":365,"served":{"price_model":false,"risk_model":false,"direction":false},"model_version":{"price":"baseline-last-value","risk":"persistence-pooled-pct"},"decisions_in_force":["D6","D27","D33","D35","D36","D37"]}
GET /predict/doge -> 404
{"detail":"asset 'doge' is not covered; covered: ['BTC', 'ETH', 'SOL']"}
```

## How to verify Phase 6a yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests, then only the new ones (test_contract.py reads the real CSVs; the others use hand-made fixtures)
python -m pytest ml -q
python -m pytest ml/tests/test_serving.py ml/tests/test_contract.py ml/tests/test_backtest_random_medians.py -q

# 2. The decisions written in this phase (appended after D34, in order)
Select-String -Path ml\docs\DECISIONS.md -Pattern '^\| D3[3-9] ' | ForEach-Object { $_.Line.Substring(0, 50) }

# 3. Step 0a: the two new random-baseline medians (trades median shown for comparison)
python -c "import json; [print(a, (r:=json.load(open(f'ml/reports/{a}/backtest.json'))['baselines']['random'])['trades_median'], r['max_drawdown_median'], r['hit_rate_median']) for a in ('btc','eth','sol')]"

# 4. The D36 check: re-run (about 10 s per asset), then n_effective, sign-flipped Spearman [CI], persistence [CI], match, cut rows, sealing
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.risk_mapping_check --asset $a; "$a exit: $LASTEXITCODE" }
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/risk_mapping_check.json')))['n_effective'], (s:=d['d36_sign_flipped'])['spearman'], s['spearman_ci95']['low'], s['spearman_ci95']['high'], (p:=d['persistence'])['spearman'], p['spearman_ci95']['low'], p['spearman_ci95']['high'], d['persistence_recomputed_matches'], d['pool']['rows_with_cut_pool'], d['metadata']['max_label_row_reached']) for a in ('btc','eth','sol')]"

# 5. The D36 rule by hand: 0.02 in [0.01, 0.03, 0.02, 0.02, 0.05, 0.04] -> 1 below, 2 tied -> p = 2/6
python -c "from ml.serving.responses import pooled_risk_score as f; print(f(0.02, [0.01, 0.03, 0.02, 0.02, 0.05, 0.04]))"

# 6. Start the service in the background, call every route, then stop it
$srv = Start-Process python -ArgumentList '-m','uvicorn','ml.api.service:app','--port','8001' -PassThru -WindowStyle Hidden
curl.exe -s --retry 20 --retry-connrefused --retry-delay 1 http://127.0.0.1:8001/health; ""
curl.exe -s http://127.0.0.1:8001/predict/btc; ""
curl.exe -s http://127.0.0.1:8001/risk/ETH; ""
curl.exe -s http://127.0.0.1:8001/debug/sol; ""
curl.exe -s -o NUL -w "doge: HTTP %{http_code}`n" http://127.0.0.1:8001/predict/doge
Stop-Process -Id $srv.Id
```

Expected (observed 2026-10-21; the service calls were stamped 2026-10-20T19:08Z UTC):

1. `160 passed`; the three new files show `24 passed`. If the raw CSVs are missing, test_contract.py shows as skipped.
2. Five lines starting `| D33 |`, `| D34 |`, `| D35 | Refines D28. Price fallback`, `| D36 | risk_score mapping`, `| D37 | sharpe_ratio on /risk`.
3. Output:
   - `btc 34.0 -0.591118 0.645161`
   - `eth 34.0 -0.645638 0.558824`
   - `sol 19.0 -0.56033 0.65`
4. `wrote ...risk_mapping_check.json` and `exit: 0` for each asset (plus a WARNING line if code is uncommitted), then:
   - `btc 67.7 0.287596 0.090986 0.46301 0.347215 0.161079 0.514323 True 0 2820`
   - `eth 67.7 0.506792 0.318042 0.655774 0.515039 0.332578 0.659126 True 0 2820`
   - `sol 36.8 0.204127 0.01536 0.452395 0.210949 0.020382 0.442397 True 133 1893`
5. `(66.66666666666667, 0.33333333333333326)`: risk_score 66.67 and p = 1/3.
6. Output:
   - `/health`: `{"status":"ok","model_version":{"price":"baseline-last-value","risk":"persistence-pooled-pct"},"data_last_bar":{"btc":"2026-10-17","eth":"2026-10-17","sol":"2026-10-17"}}`
   - `/predict/btc`: `"prediction_30d":0.0`, `"predicted_price":null`, `"signal":"UNCERTAIN"`, `"confidence":null`, `"risk_score":91.062366`, and a note ending `data stale: last bar 2026-10-17`.
   - `/risk/ETH`: `{"asset":"ETH","risk_score":86.190369,"volatility":0.432201,"sharpe_ratio":-0.764863,...}`, with the stale note.
   - `/debug/sol`: `"pool_size":8867`, `"p":0.35271230404872`, `"risk_score":64.728769595128`, `"stale":true`.
   - `doge: HTTP 404`.

- `timestamp` and `age_hours` change on every call. risk_score, volatility and sharpe_ratio change only when the CSVs are re-fetched. The stale note disappears once the latest bar closed less than 48 h ago.

## Merge of origin/main into ml-v2 (2026-10-20, local only, not pushed)

- `git fetch`: origin/main at a3a4a59. Fork point a584518; main was 94 commits ahead.
- Merge commit 341b6f3 (no rebase, since ml-v2 is already pushed).
  - Under ml/, the only change is the new `ml/Dockerfile`; every other change is in backend, frontend, db, sentiment_engine, aai_engine and the root Docker files.
  - `python -m pytest ml` -> `136 passed`; `python -c "import ml.config"` OK; `git_dirty` False after the merge.
- One conflict, `.gitignore`, resolved by keeping both sides:
  - main's sections plus ml-v2's `ml/data/raw/` (D13) and artifact rules;
  - `!ml/docs/` added after main's bare `docs/` rule, which would otherwise ignore any new file under ml/docs/.
  - Checked with `git check-ignore`: ml/docs, ml/data/*.py, ml/reports, ml/api and artifact metadata.json are tracked; raw CSVs, .pkl and PLANNER.md are ignored.
- Known issue for Phase 6 (VERIFIED): main's `ml/Dockerfile` and the compose `ml` service still start the v1 service (`uvicorn api.prediction_service:app`), copy data into the image, and assume Prophet/TensorFlow. v2 has no `ml/api/` yet, so that container would not start. Phase 6 replaces both; docker-compose.yml is shared, so Person B must be told.
- Not ML's to fix (for Person B): tracked files that match main's own ignore rules (`.env.example` via `.env.*`, two `db/__pycache__/*.pyc`). ml-v2 also carries an empty root `package-lock.json` from earlier history.
- Integration blanks, chosen by the user on 2026-10-20 (D-numbers to be written in Phase 6 Step 0; items 1, 2 and 6 also need Person B's confirmation):
  1. Price fallback: (c) `prediction_30d: 0`, `predicted_price` and bounds null, `model_version: "baseline-last-value"`, signal UNCERTAIN, confidence null, with a note.
  2. Integration: a daily backend pull of `/predict/{asset}` and `/risk/{asset}` at about 00:15 UTC, 10 s timeout, 3 retries. If ML is down, keep the last good row; add a stale note after 36 h.
  3. `risk_score` is always a number (agreed; D27's persistence fallback always gives one).
  4. Risk mapping: pooled percentile of today's `vol_30d` against the combined BTC+ETH+SOL history up to today; leakage-tested in Phase 6.
  5. SOL: agreed, no change.
  6. note/UNCERTAIN: pass `note` and `signal` through (fix `_map_prediction`), show the note, and rename or hide the AAI-derived "Signal" badge while ML says UNCERTAIN.

## Phase 5b: what ran (from repo root, 2026-10-20)

- Started from a clean tree: HEAD 0a80f92, `git_dirty` False. `python -c "import signal; print(signal.__file__)"` shows the stdlib module before and after creating `ml/signal/`. `test_stdlib_signal_not_shadowed` checks it inside pytest.
- Step 0: re-ran direction_mechanism once per asset. Only generated_at, git_commit and git_dirty (true -> false) changed. ETH last 40% unchanged: check 1 -0.5274 [-0.6658, -0.3105], check 2 -0.0455 [-0.2460, 0.2096], check 3 0.0148 [-0.1549, 0.1378].
- config.py: `SIGNALS`, `DIRECTION_SERVED` (all False, D33), `BACKTEST_FEE_PER_SIDE` 0.001, `RANDOM_BASELINE_RUNS` 1000, plus `RANDOM_BASELINE_P_BUY` 0.5 and `RANDOM_BASELINE_SEED` 0 (D34 values, kept in config per AGENTS rule 6).
- New modules:
  - `ml/signal/signal_logic.py`: the ONE `generate_signal(asset, direction_probs=None, serve=None)`.
  - `ml/evaluation/backtest.py`: pure accounting functions.
  - `ml/evaluation/run_backtest.py`: writes `ml/reports/{asset}/backtest.json` and calls `signal_logic.generate_signal` for every window.
  - No earlier module changed.
- Fee accounting (interpretation of D34, recorded in each report's `protocol`): the same rule applies to every strategy and baseline. Each starts in cash; a fee is charged on each change of position; there is no exit fee at the end. Buy-and-hold therefore pays one entry fee. The hit rate counts in-market windows where the asset rose, before fees.
- Tests: `ml/tests/test_signal_logic.py` (11) and `ml/tests/test_backtest.py` (8). `python -m pytest ml` -> `136 passed`.
- `python -m ml.evaluation.run_backtest --asset btc|eth|sol` -> exit 0. `git_dirty: true` with a stderr warning (code uncommitted; not re-run).
  - n_windows 68 / 68 / 37 = folds; `max_label_row_reached` 2820 / 2820 / 1893.
  - The served strategy has 0 trades and equals always-HOLD exactly (`checks`).
- STOP-AND-CHECK not triggered: the reference row does not beat buy-and-hold on any asset. Its paired CI is entirely below 0 for BTC and ETH, and contains 0 for SOL.

| backtest.json | BTC | ETH | SOL |
|---|---|---|---|
| windows | 68 (2019-10-16 to 2025-04-17) | 68 (2019-10-16 to 2025-04-17) | 37 (2022-10-10 to 2025-09-24) |
| served: cum return / Sharpe / max DD / trades / hit rate | 0 / null / 0 / 0 / null | 0 / null / 0 / 0 / null | 0 / null / 0 / 0 / null |
| reference: cum return / Sharpe / max DD / trades / hit rate | 1.108803 / 0.447052 / -0.49491 / 26 / 0.666667 | -0.113371 / 0.174753 / -0.544219 / 16 / 0.416667 | 1.75352 / 0.835992 / -0.273914 / 10 / 0.714286 |
| reference signals BUY / HOLD / SELL | 18 / 48 / 2 | 12 / 48 / 8 | 7 / 29 / 1 |
| buy-and-hold: cum return / Sharpe / max DD / trades / hit rate | 11.891251 / 0.930386 / -0.732185 / 1 / 0.647059 | 13.172092 / 0.92021 / -0.764578 / 1 / 0.558824 | 5.051202 / 1.074023 / -0.575206 / 1 / 0.648649 |
| always-HOLD: cum return / Sharpe / max DD / trades / hit rate | 0 / null / 0 / 0 / null | 0 / null / 0 / 0 / null | 0 / null / 0 / 0 / null |
| random median: cum return / Sharpe / trades (max DD, hit rate not computed) | 2.537104 / 0.652597 / 34 | 2.873809 / 0.64808 / 34 | 1.302658 / 0.728254 / 19 |
| reference percentile rank vs random: cum return / Sharpe | 29.3 / 22.5 | 9.0 / 5.6 | 57.3 / 59.0 |
| paired mean window return, reference - buy-and-hold [95% CI] (half-width) | -0.040236 [-0.079152, -0.000819] (0.039167) | -0.069422 [-0.133323, -0.012689] (0.060317) | -0.05078 [-0.136176, 0.025724] (0.08095) |
| paired mean window return, reference - always-HOLD [95% CI] (half-width) | 0.022052 [-0.014145, 0.067062] (0.040603) | 0.006082 [-0.021465, 0.034607] (0.028036) | 0.038024 [-0.006143, 0.09219] (0.049167) |

- Power: with 37-68 windows, a non-significant difference means "no demonstrated gain" (D29, D30). The reference row is evidence only and never served (D34).

## Phase 5a: what ran (from repo root, 2026-10-19 to 2026-10-20)

- Started from a clean tree: HEAD 3bd9090, `git_dirty` False.
- The task was split into 5a (Step 0 a-e plus its tests and docs) and 5b (Steps 1-5), following the review table in the task. The mechanism check runs once, in 0b. The `signal` shadowing check moves to 5b.
- 0a: re-ran run_walkforward_direction once per asset. Numbers are identical; only generated_at, git_commit and git_dirty (true -> false) changed. ETH approved, BTC and SOL not.
- 0b: new `ml/evaluation/direction_mechanism.py` writes `ml/reports/{asset}/direction_mechanism.json` (report only).
  - The recomputed confirmation log losses equal walkforward_direction.json, after rounding to 6 dp, within 1e-9.
  - `max_label_row_reached` 2820 / 2820 / 1893.
  - `git_dirty: true` (code uncommitted; not re-run).
- `ml/tests/test_direction_mechanism.py`: 2 tests. `python -m pytest ml` -> `117 passed`.
- 0c: D32 appended (numbers checked against walkforward_direction.json).

| direction_mechanism.json, last 40% [95% CI] | BTC | ETH | SOL |
|---|---|---|---|
| n_pooled / n_effective | 831 / 27.7 | 831 / 27.7 | 444 / 14.8 |
| 1. Spearman(P(FLAT), vol_30d) | -0.373706 [-0.584241, -0.129533] | -0.52739 [-0.66579, -0.3105] | 0.031874 [-0.236687, 0.210437] |
| 2. Spearman(P(FLAT), abs fwd_return_30d) | 0.094892 [-0.112403, 0.310917] | -0.045538 [-0.245999, 0.209584] | -0.051227 [-0.217209, 0.157597] |
| 3. Spearman(P(UP)-P(DOWN), fwd_return_30d) | -0.040797 [-0.298151, 0.17909] | 0.014782 [-0.154854, 0.137813] | -0.155432 [-0.487636, 0.159246] |
| mean P(FLAT) / observed FLAT share | 0.410172 / 0.561974 | 0.440101 / 0.602888 | 0.435216 / 0.542793 |

- STOP rule (ETH check 3 CI entirely above 0): not triggered. The CI contains 0.
- 5a paused before 0d: D33's draft reason ("is move-vs-no-move information") was not supported by ETH check 2 (CI contains 0). The user approved a reworded reason and a fix-3 sentence.
- 0d/0e: D33 and D34 appended after D32, in order. D33's final reason: "Reason: ETH's 4c gain shows no demonstrated up/down skill and no demonstrated row-level move-vs-no-move skill (direction_mechanism.json, ETH last 40%, n_effective 27.7, D29/D30: Spearman(P(UP)-P(DOWN), fwd_return_30d) = 0.0148 [-0.1549, 0.1378]; Spearman(P(FLAT), abs fwd_return_30d) = -0.0455 [-0.2460, 0.2096]). It coincides with P(FLAT) tracking trailing volatility (Spearman(P(FLAT), vol_30d) = -0.5274 [-0.6658, -0.3105]), so it cannot support BUY or SELL."
- Docs: `docs/phases/PHASE_5a_mechanism_check.md`, 2 glossary terms, AGENTS Docs list.

## How to verify Phase 5b yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. The stdlib signal module is not shadowed by ml/signal
python -c "import signal; print(signal.__file__)"

# 2. All tests, then only the new ones (hand-made fixtures, offline)
python -m pytest ml -q
python -m pytest ml/tests/test_signal_logic.py ml/tests/test_backtest.py -q

# 3. The served signal for every asset (D33)
python -c "from ml.signal.signal_logic import generate_signal; [print(a, generate_signal(a)['signal'], generate_signal(a)['confidence']) for a in ('btc','eth','sol')]"

# 4. Re-run (needs ml/data/raw/*.csv; about a minute per asset). WARNING appears only if code is uncommitted.
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.run_backtest --asset $a; "$a exit: $LASTEXITCODE" }

# 5. Windows, checks, served signals, reference vs buy-and-hold cumulative return, paired diff [CI], sealing
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/backtest.json')))['protocol']['n_windows'], d['checks'], d['strategies']['served']['signal_counts'], d['strategies']['reference']['cumulative_return'], d['baselines']['buy_and_hold']['cumulative_return'], (x:=d['paired_mean_window_return']['reference_minus_buy_and_hold'])['estimate'], x['low'], x['high'], d['metadata']['max_label_row_reached']) for a in ('btc','eth','sol')]"

# 6. Random baseline median cumulative return and the reference row's percentile rank
python -c "import json; [print(a, (r:=json.load(open(f'ml/reports/{a}/backtest.json'))['baselines']['random'])['cumulative_return_percentiles']['p50'], r['reference_percentile_rank']) for a in ('btc','eth','sol')]"
```

Expected (observed 2026-10-20):

1. A path ending in `Lib\signal.py` (the Python install), not `ml\signal`.
2. `136 passed`; the two new files show `19 passed`.
3. `btc UNCERTAIN None`, `eth UNCERTAIN None`, `sol UNCERTAIN None`.
4. `wrote ...backtest.json` and `exit: 0` for each asset.
5. Output:
   - `btc 68 {'served_trades': 0, 'served_equals_always_hold': True} {'UNCERTAIN': 68} 1.108803 11.891251 -0.040236 -0.079152 -0.000819 2820`
   - `eth 68 {'served_trades': 0, 'served_equals_always_hold': True} {'UNCERTAIN': 68} -0.113371 13.172092 -0.069422 -0.133323 -0.012689 2820`
   - `sol 37 {'served_trades': 0, 'served_equals_always_hold': True} {'UNCERTAIN': 37} 1.75352 5.051202 -0.05078 -0.136176 0.025724 1893`
6. Output:
   - `btc 2.537104 {'cumulative_return': 29.3, 'sharpe': 22.5}`
   - `eth 2.873809 {'cumulative_return': 9.0, 'sharpe': 5.6}`
   - `sol 1.302658 {'cumulative_return': 57.3, 'sharpe': 59.0}`

- Everything is deterministic (lbfgs fits; bootstrap and random baseline seeded with 0), so a re-run on the same data reproduces these values.

## How to verify Phase 5a (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest
python -m pytest ml/tests/test_direction_mechanism.py -q
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.direction_mechanism --asset $a; "$a exit: $LASTEXITCODE" }
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/direction_mechanism.json')))['consistency_check']['matches'], *[(k[:7], (b:=d['last_40pct'])[k]['spearman'], b[k]['spearman_ci95']['low'], b[k]['spearman_ci95']['high']) for k in ('check_1_pflat_vs_vol30d','check_2_pflat_vs_abs_fwd_return','check_3_up_minus_down_vs_fwd_return')], d['metadata']['max_label_row_reached']) for a in ('btc','eth','sol')]"
```

Expected (observed 2026-10-19):

1. `2 passed`.
2. `wrote ...direction_mechanism.json` and `exit: 0` for each asset (takes about a minute in total).
3. Output:
   - `btc {'logloss_prior': True, 'logloss_top': True} ('check_1', -0.373706, -0.584241, -0.129533) ('check_2', 0.094892, -0.112403, 0.310917) ('check_3', -0.040797, -0.298151, 0.17909) 2820`
   - `eth {'logloss_prior': True, 'logloss_top': True} ('check_1', -0.52739, -0.66579, -0.3105) ('check_2', -0.045538, -0.245999, 0.209584) ('check_3', 0.014782, -0.154854, 0.137813) 2820`
   - `sol {'logloss_prior': True, 'logloss_top': True} ('check_1', 0.031874, -0.236687, 0.210437) ('check_2', -0.051227, -0.217209, 0.157597) ('check_3', -0.155432, -0.487636, 0.159246) 1893`

## Phase 4c (direction model): what ran (from repo root, 2026-10-19)

- Started from a clean tree: HEAD 5b60be2, `git_dirty` False. scikit-learn 1.7.2. LogisticRegression default solver is lbfgs; on a hand-made 3-class array coef_ has shape (3, 2) and softmax(X @ coef_.T + intercept_) equals predict_proba.
- Step 0:
  - power_check re-run once per asset: numbers identical, git_dirty false; only generated_at, git_commit and git_dirty changed.
  - D30 appended.
  - `PHASE_<N>_<name>.md` restored in AGENTS rule 16 and STATUS.
- Step 1: D31 appended before any model code (DECISIONS.md diff: additions only).
- New modules:
  - `ml/models/direction.py`: 2 declared configs and the prior baseline; EPS = 1e-6; FitCache gives one fit per (fold, config) and counts ConvergenceWarnings.
  - `ml/evaluation/prob_metrics.py`: `log_loss_rows`, `ece`.
  - `ml/evaluation/run_walkforward_direction.py`: writes `ml/reports/{asset}/walkforward_direction.json`.
  - No earlier module changed.
- `ml/tests/test_direction_model.py`: 15 tests. `python -m pytest ml` -> `115 passed`.
  - First run: 1 failure in my ECE test from float rounding (3/10 vs 0.3 differ by 5.6e-17). Changed exact equality to an absolute tolerance of 1e-12; the miscalibrated case still checks its hand-computed values.
- `python -m ml.evaluation.run_walkforward_direction --asset btc|eth|sol` -> exit 0. `git_dirty: true` with a stderr warning (code not yet committed; not re-run).
- `max_label_row_reached` 2820 / 2820 / 1893; the ranking order contains only the 2 configs.
- STOP-AND-CHECK not triggered: max logloss(prior) - logloss(top) on the last 40% is 0.035904 (ETH, below 0.05), and max top-config balanced accuracy is 0.358599 (SOL, below 0.45).

| walkforward_direction.json (last 40% unless noted) | BTC | ETH | SOL |
|---|---|---|---|
| top config (first 60%) | logreg_c0.1 | logreg_c0.1 | logreg_c0.1 |
| n_pooled / n_effective | 831 / 27.7 | 831 / 27.7 | 444 / 14.8 |
| log loss prior / top | 1.017508 / 1.030682 | 1.03113 / 0.995226 | 1.055915 / 1.048813 |
| paired diff prior - top [95% CI] | -0.013174 [-0.045709, 0.017069] | 0.035904 [0.003531, 0.060357] | 0.007102 [-0.026359, 0.037926] |
| CI half-width | 0.031389 | 0.028413 | 0.032143 |
| balanced accuracy top / train_majority / momentum | 0.299088 / 0.333333 / 0.268803 | 0.358145 / 0.333333 / 0.416488 | 0.358599 / 0.333333 / 0.274997 |
| macro ECE top / prior | 0.118662 / 0.107982 | 0.11057 / 0.135259 | 0.07528 / 0.095195 |
| convergence warnings (c0.1, c1) | 0/68, 0/68 | 0/68, 0/68 | 0/37, 0/37 |
| verdict | not approved | APPROVED | not approved |

- Power: n_effective 27.7 / 27.7 / 14.8. "Not approved" means "no demonstrated gain" (D29, D30).
- Concerns about the ETH approval (all numbers from `ml/reports/eth/walkforward_direction.json`):
  - On the first 60% of folds, the top config's log loss (1.169426) is worse than the prior's (1.084441). Over all folds it is also worse (1.098151 vs 1.062628). The gain appears only on the last 40%.
  - Its CI lower bound is close to 0 (0.003531).
  - Three assets are tested, so the chance that at least one passes by luck is higher than 2.5%.

## Power check (2026-10-19, no new models)

- Started from a clean tree: HEAD 00d09a0. Re-ran run_walkforward_price once per asset; only generated_at, git_commit and git_dirty (true -> false) changed.
- `ml/evaluation/power_check.py` reads the paired 95% CIs already in walkforward_price.json and walkforward_risk.json and writes `ml/reports/{asset}/power_check.json`. It runs no models and no bootstrap. Its sources have `git_dirty` false.
- `ml/tests/test_power_check.py`: 3 tests. `python -m pytest ml` -> `100 passed`.
- D29 added. No decision on Prophet/LSTM.

| power_check.json (last-40% set)  | BTC      | ETH      | SOL       |
| -------------------------------- | -------- | -------- | --------- |
| n_effective                      | 27.7     | 27.7     | 14.8      |
| price CI half-width (return MAE) | 0.008646 | 0.009655 | 0.021625  |
| ... as % of last-value MAE       | 7.733277 | 7.074245 | 12.106436 |
| risk CI half-width (Spearman)    | 0.214335 | 0.152608 | 0.237515  |

- These are approximate: a true gain equal to the half-width is detected about half the time. About 80% power needs roughly 1.43x the half-width (price 11.0 / 10.1 / 17.3% of MAE; risk 0.31 / 0.22 / 0.34 Spearman).

## Phase 4b-1 (price model): what ran (from repo root, 2026-10-19)

- Started from a clean tree: HEAD 88d4a79, `git_dirty` False.
- Step 0a: re-ran run_walkforward_risk once per asset. Only generated_at, git_commit and git_dirty (true -> false) changed.
- Step 0b: D27 (risk fallback = persistence) and D28 (price target, approval rule) added to DECISIONS.md. PLAN.md 4b/4c "Done when" now says walk-forward (D21).
- New modules:
  - `ml/models/price.py`: the 3 declared configs and 2 declared baselines; target fwd_return_30d; features standardised on train-fold mean/std.
  - `ml/evaluation/run_walkforward_price.py`: writes `ml/reports/{asset}/walkforward_price.json`.
- No changes to earlier modules. Reused: harness, `load_dev`, `run_metadata`, `split_folds`, `price_metrics` (USDT view), `paired_bootstrap_ci`.
- `ml/tests/test_price_model.py`: 12 tests. `python -m pytest ml` -> `97 passed`.
- `python -m ml.evaluation.run_walkforward_price --asset btc|eth|sol` -> exit 0. `git_dirty: true` with a stderr warning (code not yet committed; not re-run).
- Test rows untouched: `rows_built` [0, b2) and `max_label_row_reached` b2-1, as in Phase 4.0.
- Cross-check: last-value USDT MAE equals the Phase 4.0 report (BTC 5456.61, ETH 346.78, SOL 22.56).
- Last-value was the best baseline on the first 60% for every asset (`best_baseline`), so comparing against it is consistent with D22.

| walkforward_price.json                     | BTC                           | ETH                             | SOL                             |
| ------------------------------------------ | ----------------------------- | ------------------------------- | ------------------------------- |
| top config (first 60%)                     | ridge_all_a1000               | hgb_d2                          | ridge_all_a1000                 |
| last-40% n_pooled / n_effective            | 831 / 27.7                    | 831 / 27.7                      | 444 / 14.8                      |
| paired MAE(last-value) - MAE(top) [95% CI] | 0.001055 [-0.00794, 0.009353] | -0.000785 [-0.010447, 0.008863] | -0.004377 [-0.023187, 0.020063] |
| verdict                                    | not approved                  | not approved                    | not approved                    |

- The confirmation sets are small (n_effective 27.7, 27.7, 14.8), so "not approved" reflects limited statistical power as well as possible lack of skill.
- Price API fallback is open for Person B (D28).

## Phase 4a (risk model): what ran (from repo root, 2026-10-19)

- Started from a clean tree: HEAD aeddd75, `git_dirty` False. Step 0 and Step 1 were not redone.
- Approved plan changes applied:
  - The blocking test was replaced by tests (i) and (ii).
  - PLAN.md table renamed (4a risk, 4b price, 4c direction), plus D26.
  - Class metrics use exp(prediction) with each fold's thresholds; Spearman uses the raw predicted log-vol.
- New modules:
  - `ml/models/risk.py`: the 4 declared configs; features standardised on train-fold mean/std; target log(fwd_vol_30d).
  - `ml/evaluation/run_walkforward_risk.py`: writes `ml/reports/{asset}/walkforward_risk.json`.
- Reuse change: `run_walkforward.py` gained `run_metadata()`, pulled out of `run()`. In-memory output is unchanged vs the committed reports (generated_at and git fields excluded) for all three assets.
- `ml/tests/test_risk_model.py`: 16 tests (config count, scaling on train only, (i), (ii), never an index >= b2, 60/40 split, fold-threshold classes). `python -m pytest ml` -> `85 passed`.
- `python -m ml.evaluation.run_walkforward_risk --asset btc|eth|sol` -> exit 0. `git_dirty: true` with a stderr warning (Phase 4a code not yet committed; not re-run, as instructed).
- Test rows untouched: `rows_built` [0, b2) and `max_label_row_reached` b2-1, the same as Phase 4.0.

| walkforward_risk.json                        | BTC                      | ETH                     | SOL                      |
| -------------------------------------------- | ------------------------ | ----------------------- | ------------------------ |
| top config (first 60%)                       | ridge_all_a10            | hgb_d3                  | ridge_all_a10            |
| last-40% n_pooled / n_effective              | 831 / 27.7               | 831 / 27.7              | 444 / 14.8               |
| paired Spearman diff vs persistence [95% CI] | 0.0562 [-0.1805, 0.2482] | -0.1376 [-0.24, 0.0652] | -0.221 [-0.4605, 0.0145] |
| verdict                                      | not approved             | not approved            | not approved             |

- The confirmation sets are small (n_effective 27.7, 27.7, 14.8), so "not approved" reflects limited statistical power as well as possible lack of skill.

## Phase 4a (risk model): stopped at pre-flight (2026-10-19, resolved the same day)

- Done before the stop:
  - Step 0a: re-ran run_baselines and run_walkforward once each from clean HEAD 8763086. All 6 reports changed only in generated_at, git_commit and git_dirty (true -> false); `git_dirty` False.
  - Step 0b: D23, D24, D25 added to DECISIONS.md.
  - Step 1: `paired_bootstrap_ci` in metrics.py plus 3 tests (`test_metrics.py`: 22 passed).
- Blocking problem: the required test "predictions for a fold do not change when rows at or after the origin are altered" cannot pass for a correct model. The fold predicts rows [t, t+30), and each row's features are trailing windows ending at that row's own price. So altering prices at or after t changes the predicted rows' inputs, and their predictions must change.
- Proposed replacement (needs approval): (i) the model fitted for fold k is unchanged when raw rows at or after origin_k are altered (compare its predictions on the original inputs); (ii) the prediction at any row r is unchanged when only rows after r are altered.
- Not started: ml/models/risk.py, run_walkforward_risk.py, test_risk_model.py, runs, phase doc.
  Done: branch ml-v2, v1 archived at tag archive/ml-v1, docs, Phase 0 scaffold, Phase 1 (BTC), Phase 1b (ETH, SOL), Phase 2, Phase 3, Phase 4.0.
  Blocked: nothing.

## Phase 4.0 (walk-forward harness): what ran (from repo root, 2026-10-19)

- Started from a clean tree: HEAD a934f10, `git_dirty` False.
- Docs: D21 (walk-forward, sealed test) and D22 (selection rule) added to DECISIONS.md. config.py: `MIN_TRAIN_ROWS = 730`, `WALKFORWARD_STEP = 30`.
- Interpretation recorded in D21: first origin = MIN_TRAIN_ROWS + 30 = row 760, so the first fold trains on exactly 730 rows. The last fold is cut at b2-30 (BTC/ETH 21 rows, SOL 24 rows).
- New modules:
  - `ml/evaluation/walkforward.py`: `make_folds`, `run_folds`, `Spec(fit, predict)`, `SealedTestError`. Raises on any row >= b2, and on a data frame longer than b2. Predict inputs are features + close only (no labels).
  - `ml/evaluation/run_walkforward.py`: builds features/labels only from raw rows before the first test row, then writes `ml/reports/{asset}/walkforward_baselines.json`.
- Reuse changes to Phase 3 code (no output change: in-memory `run_baselines.run()` still equals the committed reports, metadata excluded, for all three assets):
  - `run_baselines.py`: extracted `price_metrics`, `class_metrics`, `ranking_metrics` (each gained a `block_size` argument, default 30) and `strategy_stats` from the section functions.
  - `baselines.py`: added `walkforward_specs()` adapters that call the existing rules unchanged.
- `ml/tests/test_walkforward.py`: 7 tests (required a-f plus "predict inputs have no labels"). `python -m pytest ml` -> `66 passed`.
- `python -m ml.evaluation.run_walkforward --asset btc|eth|sol` -> exit 0, all four sections. `git_dirty: true` with a stderr warning (Phase 4.0 code not yet committed).
- Test rows never touched (from each report's metadata): `rows_built` = [0, b2); `max_label_row_reached` = b2-1 (BTC/ETH 2820, SOL 1893); `sealed_test_first_date` (BTC/ETH 2025-06-07, SOL 2025-11-17) equals the Phase 2 test start. Phase 3's reports already contain test metrics; this phase did not read or recompute them.

| Pooled walk-forward                                 | BTC                       | ETH                       | SOL                       |
| --------------------------------------------------- | ------------------------- | ------------------------- | ------------------------- |
| n_folds / n_pooled / n_effective                    | 68 / 2031 / 67.7          | 68 / 2031 / 67.7          | 37 / 1104 / 36.8          |
| price MAE last-value / drift                        | 5456.61 / 5583.06         | 346.78 / 361.15           | 22.56 / 23.34             |
| direction bal. acc. majority / always-UP / momentum | 0.3333 / 0.3333 / 0.3162  | 0.3333 / 0.3333 / 0.3649  | 0.3333 / 0.3333 / 0.326   |
| risk persistence bal. acc.                          | 0.4378                    | 0.468                     | 0.329                     |
| risk persistence Spearman [95% CI]                  | 0.347215 [0.1611, 0.5143] | 0.515039 [0.3326, 0.6591] | 0.210949 [0.0204, 0.4424] |

## Phase 3 (baselines + metrics): what ran (from repo root, 2026-10-19)

- Docs: D20 (evaluation on unbalanced classes) added to DECISIONS.md.
- Small refactors, output unchanged (re-ran dataset_summary: only `generated_at` differed, reverted):
  - `labels.py`: `direction_class` / `risk_class` split out of `apply_thresholds`, so baselines use the exact same class rule.
  - `dataset_summary.py`: `prepare(asset)` and `require_validated(asset)`, reused by run_baselines.
- New modules:
  - `ml/evaluation/metrics.py`: price, classification, risk ranking, interval, calibration, strategy metrics and a moving-block bootstrap. Undefined values return None.
  - `ml/evaluation/baselines.py`: fixed rules fitted on train only.
  - `ml/evaluation/run_baselines.py`: writes `ml/reports/{asset}/baselines.json` (tracked; not git-ignored).
- `ml/tests/test_metrics.py`: 19 tests. `python -m pytest ml` -> `52 passed`.
- `python -m ml.evaluation.run_baselines --asset btc|eth|sol` -> exit 0; all four sections present for validation and test.
- Report details:
  - Majority classes fitted on train: direction FLAT, risk medium (all assets). Drift log return: BTC 0.030048, ETH 0.027303, SOL 0.086301.
  - Classification `brier_one_hot` treats hard predictions as one-hot probabilities. `roc_auc_ovr` and `calibration` are null with a note (no probabilities).
  - `accuracy_ci95` and `mae_price_ci95` use a block bootstrap (block 30, 1000 resamples, seed 0). Strategy `mean_window_return_ci95` uses block 1, since windows do not overlap.
  - SOL test has no high-risk rows: high recall/precision are null with a note; balanced accuracy averages over low and medium only.
  - `git_dirty: true` in metadata because Phase 3 was not committed when the reports ran. Re-run after committing to record a clean commit.
- Findings (all from `ml/reports/{asset}/baselines.json`):
  - Direction: train-majority (always FLAT) has the highest test accuracy (BTC 0.655983, ETH 0.5662, SOL 0.7049), but balanced accuracy 0.3333. Momentum has negative MCC on every split.
  - Risk: trailing vol barely ranks forward vol (test Spearman BTC 0.006854, ETH -0.113481, SOL -0.191428; every 95% CI contains 0).
  - Price: drift beats last-value only on BTC validation (skill 0.018417); last-value is the price baseline to beat elsewhere.
  - n_effective is only 15.6 (BTC, ETH) and about 10.1 (SOL) per split, so all CIs are wide.

## Phase 3 sanity check: risk persistence (2026-10-19, no new features or models)

- Std definitions match: both `vol_30d` (features.py:50) and `fwd_vol_30d` (labels.py:25) use pandas `.std()`, ddof=1. Windows: r[t-29..t] and r[t+1..t+30].
- New test `test_fwd_vol_shifted_equals_trailing_vol` (test_leakage.py): fwd_vol_30d.shift(30) == vol_30d, rtol 1e-12. Passes. `python -m pytest ml` -> `53 passed`.
  - First run failed on my own row-count line (expected n-60, correct is n-30: the shift fills the 30 unlabelled end rows). Corrected the count, still exact; the tolerance check was not changed.
  - On real BTC data the max difference is 1.05e-15 over 3289 rows (one-off console check).
- New `risk_persistence_check` block in `ml/reports/{asset}/baselines.json`. Re-ran all three assets: exit 0, `git_dirty: true` (this task is uncommitted; HEAD a78f98f).

| Spearman(vol_30d, fwd_vol_30d) [95% CI] | BTC                        | ETH                         | SOL                        |
| --------------------------------------- | -------------------------- | --------------------------- | -------------------------- |
| train                                   | 0.465702 [0.2883, 0.6063]  | 0.464212 [0.2702, 0.6199]   | 0.523997 [0.2979, 0.6695]  |
| validation                              | -0.167378 [-0.4355, 0.159] | 0.082533 [-0.447, 0.3315]   | 0.297256 [-0.1375, 0.5979] |
| test                                    | 0.006854 [-0.3887, 0.3615] | -0.113481 [-0.3712, 0.2169] | -0.191428 [-0.5972, 0.172] |
| full labelled (n)                       | 0.505931 (3289)            | 0.463487 (3289)             | 0.585925 (2199)            |
| non-overlapping every 30th row (points) | 0.520186 (110)             | 0.445547 (110)              | 0.563747 (74)              |

- VERIFIED: alignment is correct (identity test passes; train Spearman positive with CIs above 0).
- HYPOTHESIS: the near-zero/negative validation and test values reflect a regime effect (calmer, narrower-range volatility since 2024), plus small samples (n_effective 10-16). Not proven.
- Reproducibility fix: `ml/gitinfo.py` now holds the git metadata for every report writer. `git_dirty` ignores ml/reports/ and git-ignored files, and warns on stderr when true. `ml/tests/test_gitinfo.py` adds 6 tests on a temporary fixture repo. `python -m pytest ml` -> `59 passed`.
- Follow-up: added `fwd_vol_30d_spread` and `vol_30d_spread` (n, min, p5-p95, max, std, IQR per split, labelled rows) to baselines.json. VERIFIED: test std and IQR of fwd_vol_30d are 36-56% of train for all three assets (numbers in the verify block, step 6). The explanation stays a HYPOTHESIS.

## How to verify Phase 4c yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests, then only the direction model tests (hand-made fixtures, offline)
python -m pytest ml -q
python -m pytest ml/tests/test_direction_model.py -q

# 2. Re-run (needs ml/data/raw/*.csv). WARNING appears only if code outside ml/reports/ is uncommitted.
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.run_walkforward_direction --asset $a; "$a exit: $LASTEXITCODE" }

# 3. Config count, ranking order, top config, n_effective, log loss prior/top, paired diff and CI, half-width, verdict, sealing
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/walkforward_direction.json')))['configs_declared']['count'], d['ranking_first_60pct']['order'], (c:=d['confirmation_last_40pct'])['top_config'], c['n_effective'], c['logloss_prior'], c['logloss_top'], (x:=c['paired_diff_logloss_prior_minus_top'])['estimate'], x['low'], x['high'], c['ci_half_width'], d['verdict']['approved'], d['metadata']['max_label_row_reached']) for a in ('btc','eth','sol')]"

# 4. Convergence warnings per config (folds with a warning)
python -c "import json; [print(a, {k: v['folds_with_warning'] for k, v in json.load(open(f'ml/reports/{a}/walkforward_direction.json'))['configs_declared']['convergence_warnings'].items()}) for a in ('btc','eth','sol')]"
```

Expected (observed 2026-10-19):

1. `115 passed`; the direction model file shows `15 passed`.
2. `wrote ...walkforward_direction.json` and `exit: 0` for each asset.
3. Output:
   - `btc 2 ['logreg_c0.1', 'logreg_c1'] logreg_c0.1 27.7 1.017508 1.030682 -0.013174 -0.045709 0.017069 0.031389 False 2820`
   - `eth 2 ['logreg_c0.1', 'logreg_c1'] logreg_c0.1 27.7 1.03113 0.995226 0.035904 0.003531 0.060357 0.028413 True 2820`
   - `sol 2 ['logreg_c0.1', 'logreg_c1'] logreg_c0.1 14.8 1.055915 1.048813 0.007102 -0.026359 0.037926 0.032143 False 1893`
4. `{'logreg_c0.1': 0, 'logreg_c1': 0}` for each asset.

- LogisticRegression (lbfgs) is deterministic, so a re-run on the same data reproduces these values.

## How to verify the power check yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. Tests (hand-made numbers, offline)
python -m pytest ml/tests/test_power_check.py -q

# 2. Re-build (reads the existing walkforward_price.json and walkforward_risk.json; runs no models)
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.power_check --asset $a; "$a exit: $LASTEXITCODE" }

# 3. n_effective, price half-width and % of last-value MAE, risk half-width (Spearman)
python -c "import json; [print(a, (p:=(d:=json.load(open(f'ml/reports/{a}/power_check.json')))['price'])['n_effective'], p['ci_half_width'], p['half_width_pct_of_last_value_mae'], d['risk']['ci_half_width_spearman']) for a in ('btc','eth','sol')]"

# 4. Cross-check one value by hand from the source report: (high - low) / 2
python -c "import json; c=json.load(open('ml/reports/btc/walkforward_risk.json'))['confirmation_last_40pct']['paired_diff_spearman_top_minus_persistence']; print((c['high']-c['low'])/2)"
```

Expected (observed 2026-10-19):

1. `3 passed`.
2. `wrote ...power_check.json` and `exit: 0` for each asset.
3. Output:
   - `btc 27.7 0.008646 7.733277 0.214335`
   - `eth 27.7 0.009655 7.074245 0.152608`
   - `sol 14.8 0.021625 12.106436 0.237515`
4. `0.214335`, the same as the BTC risk half-width in step 3.

## How to verify Phase 4b-1 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests, then only the price model tests (hand-made fixtures, offline)
python -m pytest ml -q
python -m pytest ml/tests/test_price_model.py -q

# 2. Re-run (needs ml/data/raw/*.csv). WARNING appears only if code outside ml/reports/ is uncommitted.
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.run_walkforward_price --asset $a; "$a exit: $LASTEXITCODE" }

# 3. Config count, best baseline, top config, confirmation size, paired MAE difference, verdict, sealing
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/walkforward_price.json')))['configs_declared']['count'], d['ranking_first_60pct']['best_baseline'], (c:=d['confirmation_last_40pct'])['top_config'], c['n_effective'], round((x:=c['paired_diff_mae_last_value_minus_top'])['estimate'],6), round(x['low'],6), round(x['high'],6), d['verdict']['approved'], d['metadata']['max_label_row_reached']) for a in ('btc','eth','sol')]"

# 4. Pooled return MAE of every predictor on all folds
python -c "import json; [print(a, {k: v['return']['mae_return'] for k, v in json.load(open(f'ml/reports/{a}/walkforward_price.json'))['all_folds'].items()}) for a in ('btc','eth','sol')]"
```

Expected (observed 2026-10-19):

1. `97 passed`; the price model file shows `12 passed`.
2. `wrote ...walkforward_price.json` and `exit: 0` for each asset.
3. Output:
   - `btc 3 last_value ridge_all_a1000 27.7 0.001055 -0.00794 0.009353 False 2820`
   - `eth 3 last_value hgb_d2 27.7 -0.000785 -0.010447 0.008863 False 2820`
   - `sol 3 last_value ridge_all_a1000 14.8 -0.004377 -0.023187 0.020063 False 1893`
4. Output:
   - `btc {'ridge_all_a100': 0.153931, 'ridge_all_a1000': 0.151327, 'hgb_d2': 0.156496, 'last_value': 0.149519, 'drift': 0.149914}`
   - `eth {'ridge_all_a100': 0.202902, 'ridge_all_a1000': 0.198734, 'hgb_d2': 0.19767, 'last_value': 0.194302, 'drift': 0.197344}`
   - `sol {'ridge_all_a100': 0.245028, 'ridge_all_a1000': 0.239465, 'hgb_d2': 0.248905, 'last_value': 0.233252, 'drift': 0.235037}`

- Ridge and HGB are deterministic (random_state=0), so a re-run on the same data reproduces these values.

## How to verify Phase 4a yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests, then only the risk model tests (hand-made fixtures, offline)
python -m pytest ml -q
python -m pytest ml/tests/test_risk_model.py -q

# 2. Re-run (needs ml/data/raw/*.csv; takes under a minute per asset). WARNING appears only if code is uncommitted.
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.run_walkforward_risk --asset $a; "$a exit: $LASTEXITCODE" }

# 3. Config count, top config, confirmation size, paired difference and verdict
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/walkforward_risk.json')))['configs_declared']['count'], (c:=d['confirmation_last_40pct'])['top_config'], c['n_effective'], c['paired_diff_spearman_top_minus_persistence']['estimate'], round(c['paired_diff_spearman_top_minus_persistence']['low'],4), round(c['paired_diff_spearman_top_minus_persistence']['high'],4), d['verdict']['approved'], d['metadata']['max_label_row_reached']) for a in ('btc','eth','sol')]"

# 4. Pooled Spearman of every predictor on all folds
python -c "import json; [print(a, {k: v['spearman'] for k, v in json.load(open(f'ml/reports/{a}/walkforward_risk.json'))['all_folds'].items()}) for a in ('btc','eth','sol')]"
```

Expected (observed 2026-10-19):

1. `85 passed`; the risk model file shows `16 passed`.
2. `wrote ...walkforward_risk.json` and `exit: 0` for each asset.
3. Output:
   - `btc 4 ridge_all_a10 27.7 0.056201 -0.1805 0.2482 False 2820`
   - `eth 4 hgb_d3 27.7 -0.137621 -0.24 0.0652 False 2820`
   - `sol 4 ridge_all_a10 14.8 -0.221018 -0.4605 0.0145 False 1893`
4. Output:
   - `btc {'har_ridge_a1': 0.407905, 'ridge_all_a1': 0.457404, 'ridge_all_a10': 0.46241, 'hgb_d3': 0.383628, 'persistence': 0.347215}`
   - `eth {'har_ridge_a1': 0.522056, 'ridge_all_a1': 0.515135, 'ridge_all_a10': 0.517704, 'hgb_d3': 0.542037, 'persistence': 0.515039}`
   - `sol {'har_ridge_a1': 0.168541, 'ridge_all_a1': 0.211465, 'ridge_all_a10': 0.211227, 'hgb_d3': 0.082843, 'persistence': 0.210949}`

- HGB and Ridge are deterministic (random_state=0), so a re-run on the same data reproduces these values exactly.

## How to verify Phase 4.0 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests, then only the walk-forward tests (hand-made fixtures, offline)
python -m pytest ml -q
python -m pytest ml/tests/test_walkforward.py -v

# 2. Re-run (needs ml/data/raw/*.csv). A WARNING line appears only if code outside ml/reports/ is uncommitted.
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.run_walkforward --asset $a; "$a exit: $LASTEXITCODE" }

# 3. Counts, sealing evidence and key pooled numbers
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/walkforward_baselines.json')))['price']['pooled']['n_folds'], d['price']['pooled']['n_pooled'], d['metadata']['rows_built'], d['metadata']['max_label_row_reached'], d['metadata']['sealed_test_first_date'], round(d['price']['pooled']['last_value']['mae_price'],2), d['risk']['pooled']['persistence_ranking']['spearman']) for a in ('btc','eth','sol')]"

# 4. The fold geometry by hand (D21): BTC/ETH b2=2821 -> 68 folds, origins 760..2770
python -c "from ml.evaluation.walkforward import make_folds; f=make_folds(3319, 2821); print(len(f), f[0].origin, f[-1].origin, len(f[0].train), f[-1].predict)"
```

Expected (observed 2026-10-19):

1. `66 passed`; the walk-forward file shows 7 passed.
2. `wrote ...walkforward_baselines.json` and `exit: 0` for each asset.
3. Output:
   - `btc 68 2031 [0, 2821] 2820 2025-06-07 5456.61 0.347215`
   - `eth 68 2031 [0, 2821] 2820 2025-06-07 346.78 0.515039`
   - `sol 37 1104 [0, 1894] 1893 2025-11-17 22.56 0.210949`
4. `68 760 2770 730 range(2770, 2791)`

- `max_label_row_reached` must stay below the b2 shown in `rows_built`. If raw data is re-fetched, n and b2 grow and these numbers change.

## How to verify Phase 3 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests (offline, hand-made fixtures; test_gitinfo uses a temporary fixture git repo)
python -m pytest ml -q

# 2. Re-run the baselines (needs ml/data/raw/*.csv; rewrites generated_at and git fields only).
#    git_dirty = uncommitted changes OUTSIDE ml/reports/ (tracked or untracked, git-ignored files excluded).
#    Changed report files never make it true. If true, a one-line WARNING goes to stderr; the run still completes.
foreach ($a in 'btc','eth','sol') { python -m ml.evaluation.run_baselines --asset $a; "$a exit: $LASTEXITCODE" }

# 3. Sections present + key test numbers
python -c "import json; [print(a, all(set((d:=json.load(open(f'ml/reports/{a}/baselines.json')))[s])=={'validation','test'} for s in ('price','direction','risk','strategy')), round(d['price']['test']['last_value']['mae_price'],2), d['direction']['test']['train_majority']['accuracy'], d['risk']['test']['persistence_ranking']['spearman'], d['strategy']['test']['n_windows']) for a in ('btc','eth','sol')]"

# 4. A null with a note (SOL test has no high-risk rows)
python -c "import json; r=json.load(open('ml/reports/sol/baselines.json'))['risk']['test']['persistence']; print(r['per_class']['high']); print(r['note'][:60])"

# 5. Sanity check: identity test, then the risk persistence Spearman values
python -m pytest ml -q -k fwd_vol_shifted
python -c "import json; [print(a, *[(k, (c:=json.load(open(f'ml/reports/{a}/baselines.json'))['risk_persistence_check'])[k]['spearman']) for k in ('train','validation','test','full_labelled','full_non_overlapping')]) for a in ('btc','eth','sol')]"

# 6. Volatility spread per split (std and IQR of fwd_vol_30d), and the git state recorded in the report
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/{a}/baselines.json')))['metadata']['git_dirty'], *[(s, v['std'], v['iqr']) for s, v in d['fwd_vol_30d_spread'].items()]) for a in ('btc','eth','sol')]"
```

Expected (observed 2026-10-19):

1. `66 passed` (59 at the end of Phase 3; Phase 4.0 added 7).
2. `wrote ...baselines.json` and `exit: 0` for each asset, with no WARNING line on a committed tree.
3. Output:
   - `btc True 8095.51 0.655983 0.006854 16`
   - `eth True 439.12 0.566239 -0.113481 16`
   - `sol True 13.82 0.704918 -0.191428 11`
4. `{'precision': None, 'recall': None, 'support': 0, 'predicted': 0}`, then `class(es) ['high'] never occur in the actual labels: their r`.
5. `1 passed, 65 deselected`, then:
   - `btc ('train', 0.465702) ('validation', -0.167378) ('test', 0.006854) ('full_labelled', 0.505931) ('full_non_overlapping', 0.520186)`
   - `eth ('train', 0.464212) ('validation', 0.082533) ('test', -0.113481) ('full_labelled', 0.463487) ('full_non_overlapping', 0.445547)`
   - `sol ('train', 0.523997) ('validation', 0.297256) ('test', -0.191428) ('full_labelled', 0.585925) ('full_non_overlapping', 0.563747)`
6. Output (git_dirty is `False` when everything outside ml/reports/ is committed, even after step 2 rewrote the reports):
   - `btc False ('train', 0.015606, 0.015899) ('validation', 0.00643, 0.00882) ('test', 0.006979, 0.007573)`
   - `eth False ('train', 0.018985, 0.021384) ('validation', 0.009016, 0.013563) ('test', 0.009042, 0.01207)`
   - `sol False ('train', 0.024828, 0.027889) ('validation', 0.012379, 0.015975) ('test', 0.009178, 0.009948)`

- If raw data is re-fetched later, test numbers shift; validation numbers stay the same unless n changes the split boundaries.

## Phase 2 (features, labels, splits): what ran (from repo root, 2026-10-19)

- Docs: D18 (split n after warm-up) and D19 (train-only thresholds) added to DECISIONS.md.
- config.py: added `WARMUP_ROWS = 30`, `DIRECTION_FLAT_PERCENTILE = 40`, `RISK_PERCENTILES = (33, 67)`.
- New modules:
  - `ml/features/features.py`: `build_features(df)`, 10 trailing-window columns, first 30 rows dropped. Refuses data with gaps (row windows equal day windows only without gaps).
  - `ml/labels/labels.py`: `fwd_return_30d`, `fwd_vol_30d`, `build_labels`, `fit_thresholds` (D19), `apply_thresholds`. Direction: UP if r > t, DOWN if r < -t, else FLAT. Risk: low if vol <= p33, high if vol > p67, else medium.
  - `ml/evaluation/splits.py`: `make_splits(n)` (D18, exact fractions so 0.70n has no float error), `split_dates`.
  - `ml/data/dataset_summary.py`: refuses an asset whose validation report did not pass; writes `ml/reports/data/{asset}_dataset_summary.json`.
- `ml/tests/test_leakage.py`: required tests a-g plus thresholds-to-classes, warm-up/no-NaN and gap-refusal tests.
- `python -m pytest ml` -> `33 passed`.
  - First run: 1 failure in test d at n=200. Not leakage: n=200 gives b2-30 = b1 = 140, so validation is empty and `make_splits` correctly raises. Moved n=200 to the "too small raises" test and used n=250 in test d. No assertion was weakened.
- `python -m ml.data.dataset_summary --asset btc|eth|sol` -> exit 0 for all three; `feature_nan_count` 0.

|                                | BTC                                  | ETH                 | SOL                                  |
| ------------------------------ | ------------------------------------ | ------------------- | ------------------------------------ |
| feature rows n                 | 3319                                 | 3319                | 2229                                 |
| train rows (dates)             | 2293 (2017-09-16 to 2023-12-26)      | 2293 (same)         | 1530 (2020-09-10 to 2024-11-17)      |
| validation rows (dates)        | 468 (2024-01-26 to 2025-05-07)       | 468 (same)          | 304 (2024-12-18 to 2025-10-17)       |
| test rows / labelled (dates)   | 498 / 468 (2025-06-07 to 2026-10-17) | 498 / 468 (same)    | 335 / 305 (2025-11-17 to 2026-10-17) |
| direction flat threshold \|r\| | 0.108207                             | 0.134363            | 0.172938                             |
| risk vol thresholds p33 / p67  | 0.027831 / 0.037694                  | 0.035513 / 0.049568 | 0.04593 / 0.061528                   |

- Finding to carry into Phase 3: class balance shifts a lot after train, because recent markets were calmer than 2017-2023. Example: BTC test risk is 92.74% low, 6.2% high; SOL test risk has 0.0% high (all from `{asset}_dataset_summary.json`). This is expected with train-only thresholds (D19), not a bug, but accuracy on test must be compared against a majority-class baseline.

## How to verify Phase 2 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. All tests, then only the leakage tests (offline, hand-made fixtures)
python -m pytest ml -q
python -m pytest ml/tests/test_leakage.py -v

# 2. Re-build the summaries (needs ml/data/raw/*.csv; rewrites generated_at only)
foreach ($a in 'btc','eth','sol') { python -m ml.data.dataset_summary --asset $a | Out-Null; "$a exit: $LASTEXITCODE" }

# 3. Key numbers from the tracked reports
python -c "import json; [print(a, (d:=json.load(open(f'ml/reports/data/{a}_dataset_summary.json')))['n_feature_rows'], d['feature_nan_count'], {k: (s['rows'], s['labelled_rows'], s['first_date'][:10]) for k, s in d['splits'].items()}) for a in ('btc','eth','sol')]"

# 4. The split rule by hand (D18): n=3319 -> b1=2323, b2=2821
python -c "from ml.evaluation.splits import make_splits; print(make_splits(3319))"
```

Expected (observed 2026-10-19):

1. `33 passed`; the leakage file shows 23 passed test cases.
2. `btc exit: 0`, `eth exit: 0`, `sol exit: 0`.
3. Output:
   - `btc 3319 0 {'train': (2293, 2293, '2017-09-16'), 'validation': (468, 468, '2024-01-26'), 'test': (498, 468, '2025-06-07')}`
   - `eth 3319 0 {'train': (2293, 2293, '2017-09-16'), 'validation': (468, 468, '2024-01-26'), 'test': (498, 468, '2025-06-07')}`
   - `sol 2229 0 {'train': (1530, 1530, '2020-09-10'), 'validation': (304, 304, '2024-12-18'), 'test': (335, 305, '2025-11-17')}`
4. `{'train': range(0, 2293), 'validation': range(2323, 2791), 'test': range(2821, 3319)}`

- If you re-fetch raw data later, n grows and the test end date moves; thresholds and balances shift slightly.

## Phase 1b (ETH, SOL): what ran (from repo root, 2026-10-18)

- No code changed: fetch.py, loader.py and validate.py already take `--asset`.
- `python -m ml.data.fetch --asset eth`: 4 pages, 3350 bars received, 3349 written, 1 unclosed dropped.
- `python -m ml.data.fetch --asset sol`: 3 pages, 2260 bars received, 2259 written, 1 unclosed dropped.
- No HTTP 403/451 and no retries. Both `validate` runs exited 0 with `passed: true`.
- `python -m pytest ml` -> `10 passed` (no new tests).
- Reports: `ml/reports/data/eth_validation.json`, `sol_validation.json` (tracked, D15).

| Field                         | BTC        | ETH        | SOL        |
| ----------------------------- | ---------- | ---------- | ---------- |
| rows                          | 3349       | 3349       | 2259       |
| first bar                     | 2017-08-17 | 2017-08-17 | 2020-08-11 |
| last bar                      | 2026-10-17 | 2026-10-17 | 2026-10-17 |
| missing days                  | 0          | 0          | 0          |
| excess kurtosis (> 1)         | 16.0117    | 12.1349    | 8.4565     |
| lag-1 autocorr of \|r\| (> 0) | 0.1769     | 0.1689     | 0.2698     |

- Done-when met: pytest passes; both reports have kurtosis > 1 and autocorr > 0; missing days listed (none).
- BTC files untouched. Phase 1b explanation: docs/phases/PHASE_1b_eth_sol_data.md.

## How to verify Phase 1b yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. Unit tests (offline)
python -m pytest ml -q

# 2. The tracked evidence reports
Get-Content ml\reports\data\eth_validation.json
Get-Content ml\reports\data\sol_validation.json

# 3. The raw files
python -c "import pandas as pd; [print(a, len(d:=pd.read_csv(f'ml/data/raw/{a}_1d.csv')), d.timestamp.iloc[0], d.timestamp.iloc[-1]) for a in ('eth','sol')]"

# 4. Re-validate the same files: same numbers expected (this rewrites the report's validated_at only)
python -m ml.data.validate --asset eth | Select-String '"rows"|"excess_kurtosis"|"abs_return_lag1_autocorr"|"passed"'
python -m ml.data.validate --asset sol | Select-String '"rows"|"excess_kurtosis"|"abs_return_lag1_autocorr"|"passed"'
```

Expected (observed 2026-10-18):

1. `10 passed`.
2. ETH: `"rows": 3349`, `"missing_days": []`, `"excess_kurtosis": 12.1349`, `"abs_return_lag1_autocorr": 0.1689`, `"passed": true`. SOL: `"rows": 2259`, `"missing_days": []`, `"excess_kurtosis": 8.4565`, `"abs_return_lag1_autocorr": 0.2698`, `"passed": true`.
3. `eth 3349 2017-08-17T00:00:00Z 2026-10-17T00:00:00Z` and `sol 2259 2020-08-11T00:00:00Z 2026-10-17T00:00:00Z`.
4. The same rows, kurtosis, autocorr and `passed` values as in 2.

- If you re-fetch later, rows grow by one per day and kurtosis/autocorr move slightly (still > 1 and > 0).

## Phase 1 (BTC): what ran (from repo root)

- `python -m pytest ml` -> `10 passed`.
  - The tests use hand-made fixtures, not market data, and make no network calls.
- `python -m ml.data.fetch --asset btc`
  - Fetched at 2026-10-18T11:07:30Z: 4 pages, 3350 bars received, 3349 written.
  - 1 bar dropped because it had not closed yet.
  - No HTTP 403/451 and no retries needed.
- `python -m ml.data.validate --asset btc` -> exit 0, `passed: true`. Observed values:

  | Field                                | Value                   |
  | ------------------------------------ | ----------------------- |
  | rows                                 | 3349                    |
  | first / last bar                     | 2017-08-17 / 2026-10-17 |
  | missing days                         | 0                       |
  | duplicates                           | 0                       |
  | non-positive prices                  | 0                       |
  | OHLC-inconsistent rows               | 0                       |
  | close min                            | 3189.02 (2017-09-14)    |
  | close max                            | 124658.54 (2025-10-06)  |
  | excess kurtosis of daily log returns | 16.0117 (> 1)           |
  | lag-1 autocorr of \|log returns\|    | 0.1769 (> 0)            |

- Done-when met: pytest passes; kurtosis > 1; \|r\| autocorr > 0; missing days listed (none).

## Phase 1 (BTC): files

- `ml/data/__init__.py`
- `ml/data/loader.py`: the one raw loader (`load_raw`, path helpers).
- `ml/data/fetch.py`
  - Binance /api/v3/klines, 1d, startTime=0, limit=1000 pages.
  - Retries with backoff on network errors and 5xx; obeys Retry-After on 418/429.
  - Stops immediately on 403/451 (`FetchBlocked`).
  - Drops bars whose close_time has not passed.
  - Writes prices exactly as Binance returns them.
- `ml/data/validate.py`
  - Pure check functions plus `validate(df)`.
  - Writes `ml/reports/data/btc_validation.json`. Exits 1 if any check fails.
  - Log returns are computed only between consecutive calendar days, so a gap never becomes a fake 2-day return.
  - Too few returns gives `null` instead of NaN, so the JSON stays valid.
- `ml/tests/test_validate.py`: 9 tests.
- Data files:
  - `ml/data/raw/btc_1d.csv` and `btc_1d.fetch.json` (fetch time and source) are git-ignored.
  - `ml/reports/data/btc_validation.json` is tracked (D15).
- Extra checks beyond the task list, reported but not part of done-when: `ohlc_inconsistent_rows`, `n_returns`, `validated_at`.
- Docs:
  - D17 added.
  - AGENTS rule 15 added.
  - PLAN.md has a "How to verify" column.

## Documentation task (2026-10-18, docs only; no code, data or tests changed)

- AGENTS rule 16 and a Docs list added.
- Created docs/GLOSSARY.md, docs/phases/TEMPLATE.md, PHASE_0_scaffold.md, PHASE_1_btc_data.md.
- Open "UNCLEAR: ask the author" items are in section 7 of the Phase 0 and Phase 1 files.
- Phase 1b must also ship `docs/phases/PHASE_1b_<name>.md` before it counts as done.
- Restored PHASE_<N>_<name>.md in AGENTS rule 16 and STATUS. A Markdown formatter in 8e2a260 had escaped it. 8e2a260's edits to existing text were formatting only (verified by the planner with git word-diff); no D-number.

## How to verify Phase 0 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest
python -c "import ml.config as c; print(c.ASSETS, c.ASSET_SYMBOLS, c.HORIZON_DAYS, c.SPLIT_FRACTIONS, c.EMBARGO_DAYS, c.ANNUALISATION_DAYS)"
git check-ignore -q ml/data/raw/x.csv;               "data/raw ignored:          $($LASTEXITCODE -eq 0)"
git check-ignore -q ml/data/fetch.py;                "fetch.py ignored:          $($LASTEXITCODE -eq 0)"
git check-ignore -q ml/artifacts/btc/model.pkl;      "artifact model ignored:    $($LASTEXITCODE -eq 0)"
git check-ignore -q ml/artifacts/btc/metadata.json;  "artifact metadata ignored: $($LASTEXITCODE -eq 0)"
```

Expected:

- `('btc', 'eth', 'sol') {'btc': 'BTCUSDT', 'eth': 'ETHUSDT', 'sol': 'SOLUSDT'} 30 {'train': 0.7, 'validation': 0.15, 'test': 0.15} 30 365`
- Then `True`, `False`, `True`, `False`.

## How to verify Phase 1 yourself (PowerShell, from the repo root)

```powershell
Set-Location C:\Shail\Somaiya\LY-Project\AltInvest\AltInvest

# 1. Unit tests (offline)
python -m pytest ml -q

# 2. The tracked evidence report
Get-Content ml\reports\data\btc_validation.json

# 3. The raw file
python -c "import pandas as pd; d=pd.read_csv('ml/data/raw/btc_1d.csv'); print('rows', len(d)); print('first', d.timestamp.iloc[0], d.close.iloc[0]); print('last ', d.timestamp.iloc[-1], d.close.iloc[-1]); print('columns', list(d.columns))"

# 4. Re-validate the same file: must reproduce the same numbers
python -m ml.data.validate --asset btc | Select-String '"rows"|"excess_kurtosis"|"abs_return_lag1_autocorr"|"passed"'

# 5. Optional, needs network: re-fetch, then re-validate
python -m ml.data.fetch --asset btc
python -m ml.data.validate --asset btc; "exit code: $LASTEXITCODE"
```

Expected (observed 2026-10-18):

1. `10 passed`.
2. `"passed": true`, `"missing_days": []`, `"excess_kurtosis": 16.0117`, `"abs_return_lag1_autocorr": 0.1769`, `"rows": 3349`.
3. Output:
   - `rows 3349`
   - `first 2017-08-17T00:00:00Z 4285.08`
   - `last  2026-10-17T00:00:00Z 81491.04`
   - `columns ['asset', 'timestamp', 'open', 'high', 'low', 'close', 'volume']`
4. The same four values as in 2.
5. After a re-fetch:
   - `first` stays 2017-08-17 and the first close stays 4285.08.
   - rows = 3349 + one per day since 2026-10-17.
   - The last timestamp is yesterday (UTC); today's open bar is dropped.
   - Kurtosis and autocorr move only slightly (still > 1 and > 0).
   - `exit code: 0`.
   - If the exit code is 1, a check failed: look at `checks` in the JSON.

## Open questions for the user

1. Backend host/CORS needs for the ML service?
2. Does Person A's MongoDB need to be the live price source later? (loader stays swappable)
3. Which extra assets after BTC/ETH/SOL? (WBTC treated as BTC for now)
4. `ml/wbtc_validation_model.csv` is an untracked file in ml/, left over from v1. I did not touch it. Delete it or move it out of ml/?

## Resolved (2026-10-18)

- D14: Python 3.10-3.12.
- D15: validation reports tracked in reports/data/.
- D16 and D17: embargo cut from the end of the earlier split. Validation and labelled test each have about 0.15n-30 rows; only the test date range is exact.
- ASSET_SYMBOLS in config.py.
