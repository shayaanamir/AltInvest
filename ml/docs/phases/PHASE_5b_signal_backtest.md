# Phase 5b: Signal logic and backtest

## 1. Goal
Write the one function that turns model output into the API's BUY/HOLD/SELL/UNCERTAIN signal (`generate_signal`), and replay simple trading rules on past data to see what they would have earned (a **backtest**). By the serving rule (D33), every asset gets UNCERTAIN, so the backtest is evidence only. Nothing here approves a model (D32, D34).

## 2. What we did
1. Re-ran the 5a mechanism check on a clean commit: the numbers were identical.
2. Wrote `generate_signal()` and the backtest, both following D33 and D34.
3. Wrote 19 tests on hand-made fixtures (not market data). `python -m pytest ml` gives 136 passed (ml/docs/STATUS.md).
4. Ran the backtest for BTC, ETH and SOL on the walk-forward fold origins only (before the sealed test split).

## 3. Files
- `ml/signal/signal_logic.py`: the one `generate_signal()`; no price inputs, never STRONG_*.
- `ml/evaluation/backtest.py`: positions, fees, returns, hit rate, random baseline.
- `ml/evaluation/run_backtest.py`: calls `generate_signal` for every window and writes the report.
- `ml/reports/{btc,eth,sol}/backtest.json`: tracked evidence.

## 4. How it works
- **Windows**: one 30-day window per fold origin, so windows never overlap (68 for BTC/ETH, 37 for SOL).
- **Long-only**: BUY means holding the coin for the window; HOLD, SELL and UNCERTAIN mean cash (0 return).
- **Transaction cost**: 0.1% each time the position changes (buy or sell).
- **Served**: what the API would do (D33): always UNCERTAIN, so always in cash.
- **Reference row**: the 4c direction model with serving forced on; it picks the most likely class (UP -> BUY, DOWN -> SELL, FLAT -> HOLD). Evidence only, never served.
- **Baselines**: buy-and-hold, always-HOLD, and a random signal (BUY with 50% chance, 1000 seeded runs).

## 5. Results
From `ml/reports/{asset}/backtest.json`:

| | BTC | ETH | SOL |
|---|---|---|---|
| Cumulative return: reference / buy-and-hold | 1.108803 / 11.891251 | -0.113371 / 13.172092 | 1.75352 / 5.051202 |
| Reference windows in cash (%) | 73.53 | 82.35 | 81.08 |
| Reference rank among random runs (cumulative return, %) | 29.3 | 9.0 | 57.3 |
| Mean window return, reference - buy-and-hold [95% CI] | -0.040236 [-0.079152, -0.000819] | -0.069422 [-0.133323, -0.012689] | -0.05078 [-0.136176, 0.025724] |

- The reference row mostly says HOLD (FLAT is the most likely class), so it sits in cash during a strong bull market. It is clearly worse than buy-and-hold for BTC and ETH, and not better than random.
- The served policy equals always-HOLD exactly: 0 trades, 0 return.

## 6. Decisions
- D33: direction is served UNCERTAIN with confidence null for all assets.
- D34: the backtest protocol (windows, long-only, fee, baselines, CIs) was fixed before this code was written.
- D32: nothing here is an approval.

## 7. Limits
- 37-68 windows only: a difference smaller than the CI half-width (0.039-0.081 in mean window return) cannot be confirmed; "no demonstrated gain" (D29, D30).
- The test period was not used; the backtest covers 2019-2025 (BTC/ETH) and 2022-2025 (SOL) only.
- Price fields are blocked on Person B (D28).

## 8. Verify and next
- Verify: see "How to verify Phase 5b yourself" in ml/docs/STATUS.md.
- Next: Phase 6 (API), once the price-field question (D28) is answered.
