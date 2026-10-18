# STATUS
Current phase: 0 DONE (2026-10-18). Next: Phase 1 (data/fetch.py + validate.py for BTC), not started; waiting on user go-ahead.
Done: branch ml-v2 created, v1 archived at tag archive/ml-v1, docs drafted, Phase 0 scaffold.
Blocked: nothing.

## Phase 0: what ran (from repo root)
- `python -m pytest ml` -> `1 passed in 0.02s` (exit 0). Also passes from inside ml/ (`python -m pytest`).
- `python -c "import ml.config"` -> OK. ASSETS=('btc','eth','sol'), HORIZON_DAYS=30, SPLIT_FRACTIONS={train 0.70, validation 0.15, test 0.15}, EMBARGO_DAYS=30, ANNUALISATION_DAYS=365.
- `git check-ignore` results:
  - ignored: ml/data/raw/*, ml/artifacts/<asset>/<model files> (pkl, keras, joblib, ...)
  - tracked: ml/data/fetch.py, ml/artifacts/<asset>/metadata.json, ml/reports/**

## Phase 0: files
- New: ml/__init__.py, ml/config.py, ml/requirements.txt (pinned to the dev machine's versions), ml/pytest.ini (testpaths=tests, pythonpath=..), ml/tests/test_config.py.
- .gitignore:
  - `ml/data/` changed to `ml/data/raw/` (D13).
  - Added `*.keras`, `ml/artifacts/*/*` and `!ml/artifacts/*/metadata.json`.
- Docs refined:
  - AGENTS.md: added a Commands section.
  - ARCHITECTURE.md: "split dates" changed to "split fractions".
  - DECISIONS.md: appended D11-D13.

## Resolved by the user (2026-10-18)
- Python 3.10-3.12 accepted (D14). REQUIREMENTS.md updated.
- Validation reports tracked at ml/reports/data/{asset}_validation.json (D15). DATA.md and ARCHITECTURE.md updated; `git check-ignore` confirms the path is tracked.
- Embargo cut from the end of the earlier split; last 30 rows unlabelled (D16). DATA.md updated.
- `ASSET_SYMBOLS = {"btc": "BTCUSDT", "eth": "ETHUSDT", "sol": "SOLUSDT"}` added to config.py; `ASSETS` is derived from it. `python -m pytest ml` -> 1 passed.

## Open questions for the user
1. Backend host/CORS needs for the ML service?
2. Does Person A's MongoDB need to be the live price source later? (loader stays swappable)
3. Which extra assets after BTC/ETH/SOL? (WBTC treated as BTC for now)
4. D16 wording check, as recorded:
   - train = [0, b1-30), validation = [b1, b2-30), test = [b2, n).
   - Under this, validation ends up with 0.15n-30 rows, not exactly 0.15n.
   - The labelled part of test has 0.15n-30 rows, because the last 30 rows have no label.
   - Only test's date range (start b2, ends at the latest data) is exact.
   - Is that what you meant by "validation and test keep their exact sizes"? Phase 2 tests will encode this rule.
