# STATUS
Current phase: 2 DONE for BTC, ETH, SOL (2026-10-19). No models built.
Next: Phase 3 (baselines + metric functions). Not started; waiting on the user's go-ahead.
Done: branch ml-v2, v1 archived at tag archive/ml-v1, docs, Phase 0 scaffold, Phase 1 (BTC), Phase 1b (ETH, SOL), Phase 2.
Blocked: nothing.

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

| | BTC | ETH | SOL |
|---|---|---|---|
| feature rows n | 3319 | 3319 | 2229 |
| train rows (dates) | 2293 (2017-09-16 to 2023-12-26) | 2293 (same) | 1530 (2020-09-10 to 2024-11-17) |
| validation rows (dates) | 468 (2024-01-26 to 2025-05-07) | 468 (same) | 304 (2024-12-18 to 2025-10-17) |
| test rows / labelled (dates) | 498 / 468 (2025-06-07 to 2026-10-17) | 498 / 468 (same) | 335 / 305 (2025-11-17 to 2026-10-17) |
| direction flat threshold \|r\| | 0.108207 | 0.134363 | 0.172938 |
| risk vol thresholds p33 / p67 | 0.027831 / 0.037694 | 0.035513 / 0.049568 | 0.04593 / 0.061528 |

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

| Field | BTC | ETH | SOL |
|---|---|---|---|
| rows | 3349 | 3349 | 2259 |
| first bar | 2017-08-17 | 2017-08-17 | 2020-08-11 |
| last bar | 2026-10-17 | 2026-10-17 | 2026-10-17 |
| missing days | 0 | 0 | 0 |
| excess kurtosis (> 1) | 16.0117 | 12.1349 | 8.4565 |
| lag-1 autocorr of \|r\| (> 0) | 0.1769 | 0.1689 | 0.2698 |

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

  | Field | Value |
  |---|---|
  | rows | 3349 |
  | first / last bar | 2017-08-17 / 2026-10-17 |
  | missing days | 0 |
  | duplicates | 0 |
  | non-positive prices | 0 |
  | OHLC-inconsistent rows | 0 |
  | close min | 3189.02 (2017-09-14) |
  | close max | 124658.54 (2025-10-06) |
  | excess kurtosis of daily log returns | 16.0117 (> 1) |
  | lag-1 autocorr of \|log returns\| | 0.1769 (> 0) |

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
- Phase 1b must also ship docs/phases/PHASE_1b_<name>.md before it counts as done.

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
