# Phase 1b: ETH and SOL data

## 1. Goal
Repeat the Phase 1 data download and "is it real?" check for Ethereum and Solana, so every asset has validated data before Phase 2 builds on it. The Phase 1 code already worked for any asset, so no code changed.

## 2. What we did
1. Ran `python -m ml.data.fetch --asset eth` and `--asset sol` (ml/data/raw/*.fetch.json).
2. Ran `python -m ml.data.validate --asset eth` and `--asset sol`, which wrote the two reports below.
3. Ran `python -m pytest ml`: 10 passed (ml/docs/STATUS.md). No new tests were needed.
4. No HTTP 403/451, no retries, no failed checks.

## 3. Files
- `ml/reports/data/eth_validation.json`: tracked evidence for ETH (D15).
- `ml/reports/data/sol_validation.json`: tracked evidence for SOL (D15).
- `ml/data/raw/eth_1d.csv`, `sol_1d.csv`: the data itself, git-ignored.

## 4. How it works
Same two checks as Phase 1 (see PHASE_1_btc_data.md): excess kurtosis must be > 1 (heavy tails) and lag-1 autocorrelation of absolute returns must be > 0 (volatility clustering).

## 5. Results
Numbers from `ml/reports/data/{btc,eth,sol}_validation.json`:

| | BTC | ETH | SOL |
|---|---|---|---|
| Rows | 3349 | 3349 | 2259 |
| First date | 2017-08-17 | 2017-08-17 | 2020-08-11 |
| Last date | 2026-10-17 | 2026-10-17 | 2026-10-17 |
| Missing days | 0 | 0 | 0 |
| Excess kurtosis (needs > 1) | 16.0117 | 12.1349 | 8.4565 |
| Abs-return autocorr (needs > 0) | 0.1769 | 0.1689 | 0.2698 |
| Passed | true | true | true |

- All three assets show heavy tails and volatility clustering, so the data looks real.
- SOL has fewer rows because it only started trading on Binance in August 2020 (about 6 years against 9 for BTC and ETH).
- Duplicates, non-positive prices and inconsistent high/low bars are 0 for both new assets.

## 6. Decisions
- D2: Binance public klines, real data only.
- D13/D15: raw data git-ignored, validation reports tracked.
- No code change: `fetch.py`, `loader.py` and `validate.py` already take `--asset`.

## 7. Limits
- Same as Phase 1: the checks show the data looks real, not that Binance's numbers are correct. `volume` is not validated.
- SOL's shorter history means less data to train and test on in Phase 2.
- Raw CSVs are git-ignored, so a clone must re-run fetch and the numbers shift slightly.

## 8. Verify and next
- Verify: see "How to verify Phase 1b yourself" in ml/docs/STATUS.md.
- Next: Phase 2 (features, labels, splits) uses the validated CSVs for BTC, ETH and SOL via `load_raw`.
