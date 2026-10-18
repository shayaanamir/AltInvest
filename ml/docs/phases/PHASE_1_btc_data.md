# Phase 1: BTC data

## 1. Goal
Download Bitcoin's full daily price history from Binance and prove it is real before building on it. v1 used synthetic data, so its metrics meant nothing (D1, D2). Real prices have two fingerprints: extreme days happen far more often than a bell curve predicts, and big moves cluster together. If the data lacks them, the project stops (docs/DATA.md).

## 2. What we did
1. `fetch.py` downloads daily bars from Binance (1000 per page), drops the unfinished current day, and saves `ml/data/raw/btc_1d.csv`.
2. `validate.py` checks the data and writes `ml/reports/data/btc_validation.json`.
3. 9 offline tests cover the validation logic.
4. Ran on 2026-10-18: 3350 bars received, 3349 kept (ml/docs/STATUS.md).

## 3. Files
- `ml/data/fetch.py`: downloads, retries on errors, waits on rate limits, stops on HTTP 403/451 (region block).
- `ml/data/loader.py`: the single place that reads the raw CSV (`load_raw`).
- `ml/data/validate.py`: runs the checks; exits with code 1 if any fail.
- `ml/tests/test_validate.py`: the 9 tests.
- `ml/reports/data/btc_validation.json`: tracked evidence (D15).

## 4. How the check works
Prices become **log returns**, ln(today / yesterday), e.g. 100 to 110 gives 0.095. Returns are not computed across missing days. Two numbers decide pass or fail:
- **Excess kurtosis** (0 for a bell curve): must be > 1, meaning heavy tails.
- **Lag-1 autocorrelation of absolute returns**: must be > 0, meaning volatility clustering.

Also checked: no duplicate days, no zero or negative prices, and each bar's high/low must enclose its open and close. Gaps are reported, never filled.

## 5. Results (from btc_validation.json)
| Check | Result | Meaning |
|---|---|---|
| Rows | 3349 (2017-08-17 to 2026-10-17) | every calendar day present, 0 missing |
| Duplicates / bad prices / bad OHLC | 0 / 0 / 0 | clean |
| Close range | 3189.02 to 124658.54 | plausible Bitcoin history |
| Excess kurtosis | 16.01 (needs > 1) | heavy tails, looks real |
| Abs-return autocorrelation | 0.177 (needs > 0) | volatility clusters, looks real |
| `passed` | true | |

## 6. Decisions
- D2: Binance public klines, real data only.
- D3: daily bars, 30-bar horizon.
- D10: train on downloaded files, live fetch later.
- D13/D15: raw data git-ignored, validation report tracked.
- UNCLEAR: why the thresholds are exactly kurtosis > 1 and autocorrelation > 0 (DATA.md says only "well above 0" and "positive").
- UNCLEAR: why USDT pairs stand in for dollar prices.

## 7. Limits
- Raw CSV is git-ignored: a clone must re-run fetch, and new days shift the numbers slightly.
- The checks show the data looks real, not that Binance's numbers are correct. `volume` is not validated.
- Tests never touch the network; the live fetch is verified only by the one recorded run.
- Only BTC is done. ETH and SOL come in Phase 1b.

## 8. Verify and next
- Verify: see "How to verify Phase 1 yourself" in ml/docs/STATUS.md.
- Next: Phase 1b repeats this for ETH and SOL. Phase 2 uses the validated CSV via `load_raw` to build features, labels and 70/15/15 splits with a 30-day embargo.
- Terms are defined in docs/GLOSSARY.md.
