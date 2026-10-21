# Phase 0: Scaffold

## 1. Goal
Phase 0 builds the empty frame of ML v2 before any data or model exists: one file of project constants, pinned dependencies, a working test runner, and git rules for what is and is not tracked. It comes first because every later phase imports the same constants and runs under the same test setup. The "done when" in docs/PLAN.md is: `pytest` runs and `python -c "import ml.config"` works.

## 2. Big picture
```
[Phase 0 scaffold] -> Phase 1 data -> 2 features/labels/splits -> 3 baselines -> 4 models -> 5 signal -> 6 API -> 7 backend
```
Before it: the v1 code was archived at git tag `archive/ml-v1` (D1, commit aeeffd2) and the planning docs were written (commit bf5161f). After it: every phase reads `ml/config.py` and is tested with `python -m pytest ml`.

## 3. What we did, step by step
1. Archived v1 and started branch `ml-v2` (D1), because v1 used synthetic data (docs/LEARNINGS.md).
2. Wrote planning docs: requirements, architecture, data, evaluation, plan, contract, decisions, learnings (commit bf5161f).
3. Created `ml/config.py` with the shared constants (commit 7c08785).
4. Created `ml/requirements.txt`, `ml/pytest.ini`, and `ml/tests/test_config.py`.
5. Changed `.gitignore` from ignoring all of `ml/data/` to only `ml/data/raw/`, and added rules for model files (D13).
6. Recorded decisions D11 to D16 (Python version, split rules, where reports live).

## 4. What each new file does
- `ml/config.py`: the only place for constants (AGENTS rule 6).
- `ml/__init__.py`: makes `ml` a Python package so `python -m ml.x.y` works (D12).
- `ml/requirements.txt`: library versions pinned to the dev machine's (Python 3.12.10, per its header comment).
- `ml/pytest.ini`: tells pytest to look in `tests/` and to put the repo root on the import path.
- `ml/tests/test_config.py`: one test that the split fractions sum to 1.
- `.gitignore`: keeps raw data and model files out of git but keeps `metadata.json` and reports in.

Connection: tests and every later module import `ml.config`; `pytest.ini` is what lets tests import `ml.*`.

## 5. How it works
`config.py` is just named values. The split fractions are stored as fractions, not dates (D11), because the assets start on different dates (BTC 2017, SOL 2020; docs/DATA.md "Known limits"). Example (made-up row count): a series of 1000 rows gives a 700/150/150 split; the dates are worked out per asset later, in Phase 2.

## 6. What the results mean
- `python -c "import ml.config ..."` prints, per ml/docs/STATUS.md: assets `btc, eth, sol`, horizon `30`, split `0.7/0.15/0.15`, embargo `30`, annualisation `365`. Good: exactly those values. Bad: an ImportError or different values.
- `python -m pytest ml` gives `10 passed` in total (ml/docs/STATUS.md), of which 1 is `test_config.py`; the other 9 belong to Phase 1.
- The four `git check-ignore` lines should print `True, False, True, False` (ml/docs/STATUS.md): raw data and model files ignored, `fetch.py` and `metadata.json` not.

## 7. Decisions and alternatives
- D11: store split fractions, not fixed dates. Alternative: fixed dates, which would leave SOL with a tiny training set.
- D12: repo root is the working directory and `ml` is a package. Alternative: run from inside `ml/`, which collects other teams' tests.
- D13: ignore only `ml/data/raw/`. v1's rule ignored all of `ml/data/` and would have hidden `fetch.py`.
- D14: Python 3.10 to 3.12; heavy libraries (TensorFlow, Prophet) only if they beat baselines.
- D16/D17: embargo cut from the end of the earlier split (config only stores the 30; the cutting is Phase 2).
- UNCLEAR: ask the author why these exact library versions beyond "the dev machine's".

## 8. Mistakes avoided
- "Triplicated signal logic drifts" and one source of truth: one config file (docs/LEARNINGS.md).
- "`python models/x.py` pickles as `__main__.X`": the package layout forces `python -m` (D12).
- "Gitignored artifacts with no metadata": `.gitignore` keeps `metadata.json` tracked.
- Annualisation sqrt(365), not 252: stored as `ANNUALISATION_DAYS = 365`.

## 9. What could still go wrong
Nothing here is tested beyond the constants and the one test, so the phase proves the setup works, not that the constants are right. The 30-day horizon and 70/15/15 split are decisions (D3, D11), not facts; they can only be judged once models exist. Ignore rules are checked only for four sample paths.

## 10. How to verify yourself
See "How to verify Phase 0 yourself" in ml/docs/STATUS.md.

## 11. What happens next
Phase 1 (real BTC data) needs `ASSET_SYMBOLS` and `ASSETS` from `config.py` and the test setup from this phase. Phase 2 will need `SPLIT_FRACTIONS`, `EMBARGO_DAYS` and `HORIZON_DAYS`.

## 12. New terms
Horizon, embargo, annualised volatility, Sharpe ratio, baseline, synthetic data, git-ignored, unit test (all in docs/GLOSSARY.md).
