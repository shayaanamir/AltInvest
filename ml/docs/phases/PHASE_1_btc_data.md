# Phase 1: BTC data

## 1. Goal
Phase 1 downloads Bitcoin's full daily price history from Binance and proves it is real market data before anything is built on it. The v1 project used synthetic data, so all its metrics meant nothing (D1, D2). Real prices have two fingerprints: extreme days are far more common than a bell curve predicts, and big moves cluster together. If the data lacks them, it is probably fake or broken, and the project must stop (docs/DATA.md). This is why it comes right after the scaffold and before features or models.

## 2. Big picture
```
Phase 0 config -> [Phase 1: fetch.py -> raw CSV -> validate.py -> btc_validation.json] -> Phase 1b ETH/SOL -> Phase 2 features, labels, splits
```
Phase 1 uses `ASSET_SYMBOLS` from Phase 0. Phase 2 will read the CSV through `loader.py`, and nothing downstream may use data that failed validation (AGENTS rule 4).

## 3. What we did, step by step
1. Wrote `fetch.py`, which asks Binance for daily bars in pages of 1000 until the history runs out.
2. Dropped the bar for the current, unfinished day.
3. Saved the bars as `ml/data/raw/btc_1d.csv`, plus a small file recording when and where they came from.
4. Wrote `validate.py` to measure the data and write `ml/reports/data/btc_validation.json`.
5. Wrote 9 tests for the validation logic, using tiny made-up inputs.
6. Ran everything on 2026-10-18 (ml/docs/STATUS.md): 4 pages, 3350 bars received, 3349 kept, no blocking or retries.

## 4. What each new file does
- `ml/data/fetch.py`: downloads, retries on errors, waits when rate-limited, stops at HTTP 403/451 (region block) rather than working around it.
- `ml/data/loader.py`: the one function that reads the raw CSV (`load_raw`), so the source can be swapped later.
- `ml/data/validate.py`: runs the checks and writes the report; exits with code 1 if any check fails.
- `ml/tests/test_validate.py`: 9 offline tests of those checks.
- `ml/reports/data/btc_validation.json`: tracked evidence (D15).

Flow: `fetch.py` writes the CSV, `loader.py` reads it, `validate.py` turns it into the JSON.

## 5. How it works
Core idea: turn prices into **log returns**, then look at their shape. A log return is ln(today / yesterday). Example (made-up): 100 to 110 gives ln(1.1) = 0.095. If a day is missing, `validate.py` skips the return across the gap instead of treating a 2-day move as a 1-day move (test `test_log_returns_skip_gaps`). Two numbers are then computed:
- **Excess kurtosis**: 0 for a bell curve; above 1 means heavy tails. Required: > 1.
- **Lag-1 autocorrelation of absolute returns**: above 0 means volatility clustering. Required: > 0.
Other checks: no duplicate days, no zero or negative prices, and each bar's high/low must enclose its open and close. Gaps are listed, not fixed (no forward-fill).

## 6. What the results mean
All values from `ml/reports/data/btc_validation.json`:
- `rows` 3349, from 2017-08-17 to 2026-10-17; `expected_days` 3349; `missing_days_count` 0. Every calendar day has a bar. Bad would be a non-empty `missing_days` list.
- `duplicate_count` 0, `non_positive_price_rows` 0, `ohlc_inconsistent_rows` 0. Bad would be any value above 0.
- `close_min` 3189.02 (2017-09-14), `close_max` 124658.54 (2025-10-06): plausible Bitcoin history, a 39x range.
- `excess_kurtosis` 16.0117: a bell curve gives 0, so extreme days are much more common than normal. Good (> 1). A value near 0 would suggest synthetic data.
- `abs_return_lag1_autocorr` 0.1769: positive, so big moves tend to follow big moves. Good (> 0). Near 0 or negative would be suspicious.
- `passed`: true.
Test count `10 passed` (this phase adds 9 to Phase 0's 1) comes from ml/docs/STATUS.md.

## 7. Decisions and alternatives
- D2: Binance public klines, real data only. Alternative: keep v1's data, which failed provenance.
- D3: daily bars, 30-bar horizon. Alternative: hourly, maybe later for risk only.
- D10: train on downloaded files; live fetching later.
- D13/D15: raw data git-ignored, validation report tracked.
- D17 sets up the split rule Phase 2 will use.
- UNCLEAR: ask the author why the thresholds are exactly kurtosis > 1 and autocorr > 0 (docs/DATA.md says only "well above 0" and "positive").
- UNCLEAR: ask the author why USDT pairs stand in for dollar prices (docs/DATA.md says "Close = price").

## 8. Mistakes avoided
- "Synthetic data makes every metric meaningless. Validate real data first": the whole phase.
- "Hand-typed metrics appeared in no artifact": the numbers in section 6 are written by `validate.py` as JSON.
- Real data only, gaps reported, not hidden: no forward-fill or interpolation.
- Only fully closed bars are kept, so a half-finished day never enters.

## 9. What could still go wrong
- The raw CSV is git-ignored, so a clone must run `fetch` again; re-fetching adds new days and shifts kurtosis and autocorrelation slightly (ml/docs/STATUS.md).
- The checks only prove the data has real-looking statistics. They cannot prove Binance's numbers are correct.
- Prices are stored as Binance returns them; `volume` is not validated at all.
- Binance may block some regions (HTTP 451); the fetch then stops by design.
- Tests use made-up inputs and never touch the network, so the live fetch is verified only by the one run recorded in STATUS.md.
- ETH and SOL are not done; the claim holds for BTC only.

## 10. How to verify yourself
See "How to verify Phase 1 yourself" in ml/docs/STATUS.md.

## 11. What happens next
Phase 1b repeats this for ETH and SOL (same checks, PLAN.md). Phase 2 needs from this phase: a validated, gap-free CSV per asset and `load_raw`, to build features, labels and the 70/15/15 splits with a 30-day embargo.

## 12. New terms
Kline, OHLCV, daily bar, closed bar, UTC, gap, forward-fill, pagination, rate limit, return, log return, kurtosis, excess kurtosis, heavy tails, volatility clustering, autocorrelation, exit code, fixture (all in docs/GLOSSARY.md).
