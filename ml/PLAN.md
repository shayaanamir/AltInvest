# AltInvest ML Pipeline — Evolution Plan (v2)
### From "Predict a Price" -> "Risk-Aware, Backtested Trading Signal"

> **Status**: Planning only — no code changes have been made.
> **Revision**: v2 — fixes threshold data-leakage, unifies signal logic, verifies ma_cross
>   semantics, reorders phases to build-then-backtest, and fully specifies volatility output.
> **Implementation order**: Steps are listed in true dependency order.

---

## Current State (Baseline)

The pipeline currently:
- Loads hourly price CSVs -> `feature_engineering.py` -> 9 features
- Trains `ProphetForecaster` (30-day price) + `RiskClassifier` (7-day volatility risk, 3-class)
- Trains `Conv1D+LSTM` separately, caches report JSON
- Serves via FastAPI on port 8001 with these **live endpoints**:
  - `GET /prediction/{asset}` -> price + risk + STRONG_BUY/STRONG_SELL/UNCERTAIN signal
  - `GET /risk/{asset}` -> risk_score + volatility + sharpe_ratio
  - `GET /models/{asset}` -> Prophet vs LSTM A/B comparison
  - `GET /metrics/{asset}` -> evaluation metrics
  - `POST /retrain/{asset}` -> hot-reload

**Key constraint**: All endpoints above must remain backward-compatible throughout.

---

## Implementation Priority Order (Revised)

> **Design principle**: Build the live-serving signal function first; backtest that exact
> function second. A backtest is only meaningful if it tests the identical logic being served.

| Step | Phase | Title | Effort | Dependency |
|---|---|---|---|---|
| **1** | Phase 1 | Direction Classifier | M | None — independent |
| **2** | Phase 2 | Regime Detector | S | None — independent |
| **3** | Phase 3 (new) | Unified Signal Function | S | Requires Phase 1 + 2 outputs |
| **4** | Phase 4 | Walk-forward Backtest | M | Requires Phase 3 (backtests that exact function) |
| **5** | Phase 5 | Calibration Check | S | Requires Phase 1 model |
| **6** | Phase 6 | API Response Schema Update | M | Requires Phases 1+2+3+4 |
| **7** | Phase 7 (CONDITIONAL) | Continuous Volatility Forecast | M | See scheduling gate below |

**Recommended first implementation: Phase 1 (Direction Classifier)**
- Directly mirrors `RiskClassifier` structure — same leakage-prevention pattern, zero new deps
- Produces `prob_up_30d` / `prob_down_30d` which feed Phase 3 (signal function)
- No new raw data, no new pip deps, lowest risk to existing endpoints

**Phase 7 scheduling gate (CONDITIONAL)**:
Phase 7 (GARCH/EWMA volatility) is NOT a default deliverable. Only schedule it if, after
completing Phase 6, there is a concrete demonstrable gap — e.g. the calibration check (Phase 5)
reveals that `risk_score` and `prob_up_30d` are uncorrelated with short-term volatility
movement, or the backtest (Phase 4) shows poor performance in low-regime-signal periods where
a continuous vol forecast would provide an additional gate. Without such evidence, the existing
`risk_score` already covers this slot.

---

## Pre-Implementation Step 0: Distribution Analysis

> **Run before writing ANY labeling code.** This step's outputs are inputs to Phase 1.
> Its purpose is to fix the direction dead-zone threshold using a pre-committed rule,
> NOT to choose whichever threshold produces the best-looking backtest after the fact.

### What to Run

```python
import numpy as np
import pandas as pd
from features.feature_engineering import load_raw_csv, build_features

asset = "btc"   # repeat for eth, sol
df = build_features(load_raw_csv(asset))

# Compute forward 30d log-return (exact formula DirectionClassifier will use)
fwd_return = np.log(df["price"].shift(-720) / df["price"])
fwd_return = fwd_return.dropna()

print(f"Observations: {len(fwd_return)}")
print(f"Std:  {fwd_return.std():.4f}")
print(f"P10:  {fwd_return.quantile(0.10):.4f}")
print(f"P40:  {fwd_return.quantile(0.40):.4f}")
print(f"P60:  {fwd_return.quantile(0.60):.4f}")
print(f"P90:  {fwd_return.quantile(0.90):.4f}")

# Class balance for candidate thresholds
for thresh in [0.01, 0.02, 0.05]:
    up   = (fwd_return >  thresh).sum()
    flat = ((fwd_return >= -thresh) & (fwd_return <= thresh)).sum()
    down = (fwd_return < -thresh).sum()
    n    = len(fwd_return)
    print(f"thresh=+-{thresh:.0%}: UP={up/n:.1%}  FLAT={flat/n:.1%}  DOWN={down/n:.1%}")
```

### Pre-Committed Decision Rule

The following rule is stated HERE, before the distribution is inspected. It cannot be changed
after seeing results.

```
IF   +-2% dead-zone produces FLAT class >= 15% of training labels:
     -> USE +-2% threshold  (3-class: UP / FLAT / DOWN)

ELSE IF +-2% produces FLAT < 15%:
     -> OPTION A: use |fwd_return| 40th-percentile as threshold
        (computed on training split only; stored in artifact)
     -> OPTION B: fall back to binary UP / DOWN (no FLAT class)
     -> PREFER A unless 40th-percentile of |fwd_return| < 0.005

DO NOT choose the threshold that maximizes backtest Sharpe after the fact.
```

### Results Table (fill in after running Step 0)

| Asset | P40 of abs(fwd_ret) | +-2% FLAT% | Chosen threshold | Schema |
|---|---|---|---|---|
| btc | 0.0984 | 9.0% | **0.0984** (~9.8%) | 3-class (Option A) |
| eth | 0.0892 | 9.4% | **0.0892** (~8.9%) | 3-class (Option A) |
| sol | 0.1355 | 4.9% | **0.1355** (~13.6%) | 3-class (Option A) |

> **Decision**: All assets use Option A (P40 of |fwd_return| on training split).
> ±2% dead-zone produced FLAT < 15% for every asset (4.9–9.4%), and all P40 values
> are >> 0.005 minimum, so Option A applies. Per-asset thresholds are stored in each
> artifact — NOT shared across assets.

---

## Phase 1 — Direction Classifier

> **"What is the probability this asset goes up over 30 days?"**

### Labeling

3-class (or binary if decision rule selects it) schema from Step 0 analysis. Threshold `THRESH`
is filled in from Step 0.

```
target_direction_30d:
  +1 (UP)   if target_return_30d >  +THRESH
   0 (FLAT) if target_return_30d in [-THRESH, +THRESH]   (omitted if binary)
  -1 (DOWN) if target_return_30d <  -THRESH

target_return_30d_t = ln(price_{t+720} / price_t)    [720 hours = 30 days forward]
```

This is computed inside `DirectionClassifier.fit()` ONLY — never stored in the CSV.
The existing `return_30d` column is a TRAILING log-return (backward-looking) and is safe
as an input feature.

### Files Changed

#### [NEW] models/direction_classifier.py

**Class**: `DirectionClassifier` — mirrors `RiskClassifier` in structure, docstrings, CLI, and
save/load pattern. Only the target label changes.

```
DirectionClassifier
    .fit(df)             — label + train RandomForest (direction)
    .predict(df)         — classify direction for latest row
    .predict_latest(df)  — alias for predict(df)
    .save(path)          — persist to models/artifacts/{asset}_direction_clf.pkl
    .load(path)          — restore from disk
    .feature_importances — dict of feature -> importance
    .is_fitted           — bool property
```

**Features** (same as `CLASSIFIER_FEATURES` in `classifier.py`, already leakage-free):

```python
DIRECTION_FEATURES = [
    "return_1h", "return_1d", "return_7d", "return_30d",
    "volatility_14d", "ma_cross", "volume_change_pct",
]
```

**Leakage-prevention** (identical discipline to `RiskClassifier.fit()`):
1. Compute `_target_return_30d` via reverse-rolling trick on price series, 720h horizon
2. Drop final 720 rows (no forward label)
3. Chronological 80/20 split with **720-hour embargo** (horizon-matched; `classifier.py` uses 168h for its 7-day horizon)
4. Compute THRESH from training split only if using Option A
5. Label both splits using that fixed THRESH
6. `TimeSeriesSplit(n_splits=5, gap=720)` CV on training data only

**Stored state in artifact**: fitted `RandomForestClassifier`, `LabelEncoder`, `_thresh`,
`_schema` ("3-class" or "binary"), `_eval_report`.

**Output from `.predict(df)`**:

```python
{
    "asset":         "BTC",
    "prob_up_30d":   0.72,
    "prob_flat_30d": 0.18,   # 0.0 if binary schema
    "prob_down_30d": 0.10,
    "direction":     "UP",
}
```

**Artifact**: `models/artifacts/{asset}_direction_clf.pkl`

**New pip dependency**: None

**Risk to existing endpoints**: None

**Effort**: M

---

#### [MODIFY] training/train.py

Add `step_direction()` as Step 5 (after `step_classify`). Add `--skip-direction` flag.

Training order:
```
LOAD -> BUILD features -> FIT RegimeDetector -> FIT Prophet
     -> FIT RiskClassifier -> FIT DirectionClassifier
     -> (Backtest if --run-backtest) -> WRITE report
```

Extend training report JSON:
```json
{
  "direction": {
    "asset": "btc", "prob_up_30d": 0.72, "direction": "UP",
    "cv_accuracy": 0.68, "thresh": 0.02, "schema": "3-class", "duration_sec": 9.4
  }
}
```

**Risk to existing endpoints**: None

---

#### [MODIFY] api/prediction_service.py

Load `DirectionClassifier` in `ModelCache.load_asset()`. Add `prob_up_30d`, `prob_down_30d`
to `PredictionResponse` (additive only — no fields removed).

---

### Training Data Schema Impact (Phase 1)

| Column | Stored in CSV? | Where Computed |
|---|---|---|
| `target_return_30d` | No — ephemeral | Inside `DirectionClassifier.fit()` only |
| `target_direction_30d` | No — ephemeral | From above + pre-committed THRESH |

**No CSV regeneration needed.**

---

## Phase 2 — Regime Detector

> **"What market state are we in? TRENDING / CHOPPY / CRISIS"**

### ma_cross Semantics — Verified from Source

Before finalising any regime rule referencing `ma_cross`, verify its value space against
`features/feature_engineering.py` lines 140-149:

```python
# Exact code in _add_moving_averages():
conditions = [
    (df["price"] > df["ma_7d"]) & (df["ma_7d"] > df["ma_30d"]),   # fully bullish
    (df["price"] < df["ma_7d"]) & (df["ma_7d"] < df["ma_30d"]),   # fully bearish
]
choices = [1, -1]
df["ma_cross"] = np.select(conditions, choices, default=0)
```

**Confirmed**: `ma_cross` is a **3-value integer: {-1, 0, +1}**
- `+1` = price > ma_7d > ma_30d (fully bullish stack)
- `-1` = price < ma_7d < ma_30d (fully bearish stack)
- ` 0` = mixed / indeterminate (partial crossover or price between MAs)

**Implication**: `ma_cross != 0` correctly selects fully-aligned trending states. It is
NOT a momentum measure and `0` is NOT equivalent to "flat price" — it includes all partial
crossover states. The regime rule "TRENDING requires ma_cross != 0" is semantically valid
given this definition.

### Design Decision: Rule-Based (not GMM)

Rule-based is preferred: fully interpretable, stable across retraining, easy to present.
GMM on 3 features with 16,801 rows would not provide meaningful additional value and
complicates explanation.

### Regime Rules — With Threshold Provenance

Every numeric threshold is labeled as either **engineering heuristic** or
**empirically checked**. Heuristics are identified explicitly so they can be revisited if
Phase 4 backtest shows regime labels are decorrelated with forward returns.

```
CRISIS   if volatility_14d > crisis_vol_threshold
          OR return_7d < -0.15

TRENDING if |return_7d| > 0.05
          AND ma_cross != 0

CHOPPY   otherwise (default)
```

| Threshold | Value | Provenance |
|---|---|---|
| `crisis_vol_threshold` | 99th pct of training `volatility_14d` | **Empirically checked** — computed in `RegimeDetector.fit()` from training split, stored in artifact |
| `return_7d < -0.15` | -15% in 7 days | **Engineering heuristic** — extreme crash detection. Not independently backtested against forward returns. |
| `|return_7d| > 0.05` | 5% move in 7 days | **Engineering heuristic** — separates signal from noise (~1.5x typical 7d log-return std on crypto). Not independently backtested. |
| `ma_cross != 0` | {-1, +1} | **Derived from source** — verified against feature_engineering.py above |

> ⚠️ If Phase 4 backtest shows regime labels are decorrelated with forward returns,
> revisit the two heuristic thresholds first using Step 0 distribution outputs.

### Files Changed

#### [NEW] features/regime.py

**Class**: `RegimeDetector`

```
RegimeDetector
    .fit(df)            — compute crisis_vol_threshold from training data
    .predict(df)        — return regime Series per row (vectorised, no model call)
    .predict_latest(df) — regime string for most recent row
    .save(path)         — persist threshold to {asset}_regime.pkl
    .load(path)         — restore
    .is_fitted          — bool property
```

Only stored state: `_crisis_vol_threshold` (one float from training split). All other rules
are deterministic from feature values — inference is pure threshold application.

**Artifact**: `models/artifacts/{asset}_regime.pkl`

**New pip dependency**: None

**Risk to existing endpoints**: None

**Effort**: S

---

#### [MODIFY] training/train.py

`step_regime()` runs after feature engineering, before all model steps.
Add `--skip-regime` flag. Add `regime` sub-dict to training report.

---

#### [MODIFY] api/prediction_service.py

Load `RegimeDetector` in `ModelCache.load_asset()`. Add `regime: str` to `PredictionResponse`
(additive — backward-compatible).

---

### Training Data Schema Impact (Phase 2)

`regime_label` is derived at inference time only from existing features. **No CSV regeneration needed.**

---

## Phase 3 — Unified Signal Function

> **"One function that generates the trading signal — called identically by the API and the backtest."**

This is a NEW phase. It must come BEFORE the backtest (Phase 4).

**Core principle**: The backtest is only academically valid if it simulates exactly the signal
that would have been served live. If the backtest uses different logic than the API, the
Sharpe / drawdown figures measure a phantom strategy, not the deployed one.

The old plan had two different signal definitions:
- Phase 4 backtest: `BUY if prob_up > 0.60 AND trend == Bullish AND risk_score > 50`
- Phase 6 API: `HOLD if regime == CRISIS elif prob_up > 0.60 and trend == Bullish: BUY`

Both are replaced by a single function.

### Files Changed

#### [NEW] api/signal_logic.py

Pure Python — no FastAPI import. Importable from both `prediction_service.py` and `backtest.py`.

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class Signal:
    signal:            Literal["BUY", "SELL", "HOLD"]
    signal_confidence: float   # 0.0-1.0
    rationale:         str     # human-readable explanation of which rule fired


def generate_signal(
    prob_up_30d:         float,
    prob_down_30d:       float,
    trend:               str,    # "Bullish" | "Bearish" | "Neutral"
    regime:              str,    # "TRENDING" | "CHOPPY" | "CRISIS"
    risk_score:          float,  # CONTRACT score 0-100 (higher = lower risk)
    direction_threshold: float = 0.60,
    risk_gate:           float = 50.0,
) -> Signal:
    """
    Canonical signal function. Called identically by:
        api/prediction_service.py  (live serving)
        training/backtest.py       (historical walk-forward)

    Rules (evaluated in order):
      1. CRISIS regime           -> HOLD (no directional bet)
      2. risk_score <= risk_gate -> HOLD (risk too high)
      3. prob_up > threshold AND trend == Bullish  -> BUY
      4. prob_down > threshold AND trend == Bearish -> SELL
      5. otherwise                                 -> HOLD

    Confidence:
      base = max(prob_up_30d, prob_down_30d)
      multiplier = 0.9 if TRENDING, 0.7 if CHOPPY, 0.0 if CRISIS
      signal_confidence = base * multiplier
    """
```

Default thresholds (`direction_threshold=0.60`, `risk_gate=50.0`) are parameters — the
backtest can sweep them to assess sensitivity without changing the function logic.

**New pip dependency**: None

**Risk to existing endpoints**: None

**Effort**: S

---

## Phase 4 — Walk-Forward Backtest

> **"How would `generate_signal()` have performed historically, exactly as served?"**

**Hard dependency on Phase 3**: Do not start Phase 4 until `signal_logic.generate_signal()`
is committed and stable. The backtest result is meaningless if it tests a different function
than what is served.

### Design

Walk-forward at daily (24h) steps. At each step `t`:
- Use `asset_df.iloc[:t]` only (strict no-look-ahead)
- Call `.predict_latest()` on the pre-fitted model artifacts (same as live inference)
- Call `generate_signal()` with identical arguments as the API handler
- Record realized 30-day forward return = `ln(price_{t+720} / price_t)`

The models are NOT re-fitted at each step — they use the same artifacts as the API.
This is the only valid simulation of what would have been served live.

### Files Changed

#### [NEW] training/backtest.py

```python
def run_backtest(
    asset_df:            pd.DataFrame,
    direction_clf:       DirectionClassifier,
    classifier:          RiskClassifier,
    regime_det:          RegimeDetector,
    forecaster:          ProphetForecaster,
    asset:               str,
    step_hours:          int   = 24,
    direction_threshold: float = 0.60,
    risk_gate:           float = 50.0,
) -> dict:
    """Walk-forward backtest. Calls signal_logic.generate_signal() — identical to API."""
```

Walk-forward loop (pseudocode):
```
for t in range(warmup, len(asset_df) - 720, step_hours):
    sub    = asset_df.iloc[:t]
    d      = direction_clf.predict_latest(sub)
    r      = classifier.predict_latest(sub)
    regime = regime_det.predict_latest(sub)
    trend  = derive_trend_from_forecaster(forecaster, sub)
    sig    = generate_signal(d["prob_up_30d"], d["prob_down_30d"],
                             trend, regime, r["risk_score"],
                             direction_threshold, risk_gate)
    fwd    = log(price[t+720] / price[t])
    record(sig.signal, fwd)
```

**Metrics output**:
```python
{
    "asset": "btc", "step_hours": 24,
    "direction_threshold": 0.60, "risk_gate": 50.0,
    "n_periods": int, "n_buy": int, "n_sell": int, "n_hold": int,
    "hit_rate":   float,   # % of BUY/SELL where direction was correct
    "cum_return": float,   # cumulative log-return of strategy
    "sharpe":     float,   # annualised: mean(daily_ret)/std(daily_ret)*sqrt(252)
    "max_drawdown":       float,
    "buy_and_hold_return": float,
    "generated_at": str,
}
```

**Output file**: `models/artifacts/{asset}_backtest_report.json`

**CLI**:
```bash
python training/backtest.py --asset btc
python training/backtest.py --asset btc --step 48 --direction-threshold 0.65
```

**Integration with train.py**: `step_backtest()` behind `--run-backtest` flag (off by default).

**New pip dependency**: None

**Risk to existing endpoints**: None

**Effort**: M

---

#### [MODIFY] api/prediction_service.py

Add `GET /backtest/{asset}` (reads pre-computed report JSON):

```python
@app.get("/backtest/{asset}", tags=["Backtest"])
async def get_backtest_report(asset: str) -> dict:
    """Returns the pre-computed walk-forward backtest report."""
```

Returns 404 with generation instructions if report not found. New endpoint — no existing
endpoints modified.

---

### Training Data Schema Impact (Phase 4)

No new CSV columns. **No CSV regeneration needed.**

---

## Phase 5 — Calibration Check

> **"When our model says 70% probability, does it actually win ~70% of the time?"**

**Dependency**: Requires Phase 1 (`DirectionClassifier`) to be committed.

### Files Changed

#### [MODIFY] models/classifier.py

Add private `_compute_calibration(y_true_bin, y_proba, n_bins=10)` function.
Call after test evaluation in `RiskClassifier.fit()`. Store result in `self._calibration`:

```python
{
    "bins":              [0.0, 0.1, ..., 1.0],
    "mean_predicted":    [...],
    "fraction_positive": [...],
    "brier_score":       float,   # mean((y_true - y_pred)^2); lower is better
}
```

#### [MODIFY] models/direction_classifier.py

Same calibration step, treating UP=1, FLAT+DOWN=0 for binary calibration of `prob_up_30d`.

#### [MODIFY] training/train.py

Add calibration sub-dict to training report for both classifiers:
```json
{
  "classify":  { "calibration": { "brier_score": 0.143 } },
  "direction": { "calibration": { "brier_score": 0.211 } }
}
```

**New pip dependency**: None (`sklearn.calibration.calibration_curve` in scikit-learn >= 1.0)

**Risk to existing endpoints**: None — training-time only

**Effort**: S

---

## Phase 6 — API Response Schema Update

> **"Wire `generate_signal()` into the live API; add `signal_v2` headline; expose backtest endpoint."**

**Dependency**: Phases 1+2+3+4 must be complete. Phase 3 (`generate_signal`) must be stable
before this phase wires it into the API handler.

### Backward Compatibility

**Keep all existing fields. Add `signal_v2` as a new nested object.**

Person B's backend consumes `signal`, `trend`, `agreement`, `boosted_confidence`, `ensemble_price`
from the live contract. No removals. New consumers use `signal_v2`.

### Files Changed

#### [MODIFY] api/prediction_service.py

New Pydantic models:

```python
class DirectionOutput(BaseModel):
    prob_up_30d:   float
    prob_flat_30d: float
    prob_down_30d: float
    direction:     str    # "UP" | "FLAT" | "DOWN"

class PriceReference(BaseModel):
    prophet_price:  float
    lstm_price:     Optional[float]
    ensemble_price: float
    lower_bound:    float
    upper_bound:    float

class SignalV2(BaseModel):
    """Risk-aware, regime-gated trading signal (v2 headline)."""
    signal:            str    # "BUY" | "SELL" | "HOLD"
    signal_confidence: float  # 0.0-1.0
    rationale:         str    # from Signal.rationale field
    regime:            str    # "TRENDING" | "CHOPPY" | "CRISIS"
    direction:         DirectionOutput
    price_reference:   PriceReference
```

Updated `PredictionResponse` (additive only — no removals):

```python
class PredictionResponse(BaseModel):
    # === ALL EXISTING FIELDS PRESERVED ===
    asset: str; predicted_price: float; prediction_30d: float
    lower_bound: float; upper_bound: float; confidence: float
    risk_score: float; timestamp: str; trend: str; agreement: bool
    signal: str; boosted_confidence: float; ensemble_price: float
    # === Phase 1 additions ===
    prob_up_30d: float
    prob_down_30d: float
    # === Phase 2 addition ===
    regime: str
    # === Phase 6: v2 headline ===
    signal_v2: SignalV2
```

**Handler update**: Replace the inline signal logic in `GET /prediction/{asset}` with a call
to `signal_logic.generate_signal()`. The old top-level `signal` field retains its existing
STRONG_BUY / STRONG_SELL / UNCERTAIN logic for backward compatibility. New consumers read
`signal_v2.signal`.

**API version**: `"1.0.0"` -> `"1.1.0"`

**Risk to existing endpoints**: Zero — no fields removed

**Effort**: M

---

### Training Data Schema Impact (Phase 6)

None — API layer only. **No CSV regeneration needed.**

---

## Phase 7 — Continuous Volatility Forecast (CONDITIONAL)

> **Status: CONDITIONAL — do not schedule by default. See Phase 7 scheduling gate above.**

### Output Specification (Exact Formulas)

Two options are fully specified here. One must be chosen before any implementation begins.

#### Option A — EWMA (Recommended Default)

RiskMetrics exponentially weighted moving average of variance:

```
sigma^2_t = alpha * r^2_{t-1} + (1 - alpha) * sigma^2_{t-1}
alpha = 0.06  (lambda = 0.94, standard RiskMetrics daily; use same for hourly)
```

**7-day (168-hour) forecast**: EWMA gives the current conditional variance. Under EWMA,
the h-step-ahead variance equals the current variance (no mean-reversion term). So:

```
sigma^2_{t+1:t+168} = 168 * sigma^2_t_hourly    (sum of 168 equal hourly variances)
sigma_7d_hourly     = sqrt(168 * sigma^2_t)
```

**Annualised** (converting from hourly to annual):
```
sigma_7d_annualised = sigma_t_hourly * sqrt(168) * sqrt(365 * 24 / 168)
                    = sigma_t_hourly * sqrt(365 * 24)
                    = sigma_t_hourly * sqrt(8760)
                    = sigma_t_hourly * 93.57
```

**Exact implementation formula**:
```python
hourly_ewm_var      = df["return_1h"].ewm(alpha=0.06).var().iloc[-1]
volatility_forecast_7d = float(np.sqrt(hourly_ewm_var * 8760))
```

Interpretation: annualised volatility (fraction, e.g. 0.85 = 85% annualised vol)
implied by the current EWMA conditional variance.

**New pip dependency**: None

---

#### Option B — GARCH(1,1)

```
sigma^2_t = omega + alpha * r^2_{t-1} + beta * sigma^2_{t-1}
```

**h-step-ahead conditional variance**:
```
sigma^2_{t+h} = omega/(1-alpha-beta)
              + (alpha+beta)^h * (sigma^2_t - omega/(1-alpha-beta))
```

**7-day forecast**: sum conditional variances h=1..168, then annualise:
```
var_7d = sum_{h=1}^{168} sigma^2_{t+h}
sigma_7d_annualised = sqrt(var_7d) * sqrt(8760 / 168)
```

Simplified implementation:
```python
from arch import arch_model
res   = arch_model(df["return_1h"] * 100, vol='Garch', p=1, q=1).fit(disp='off')
fcast = res.forecast(horizon=168).variance.iloc[-1]        # 168 hourly forecasts in %^2
var_7d_pct_sq = fcast.sum()
volatility_forecast_7d = float(np.sqrt(var_7d_pct_sq) / 100 * np.sqrt(8760 / 168))
```

**New pip dependency**: `arch>=5.3`

---

**Recommendation**: Default to **EWMA (Option A)**. Revisit GARCH only if Phase 5
calibration shows the existing `risk_score` is poorly calibrated AND EWMA is also
uncorrelated with realized vol. Document the chosen method in the artifact metadata.

### Files Changed (if activated)

#### [NEW] models/volatility_forecaster.py

**Class**: `VolatilityForecaster`

```
VolatilityForecaster
    .fit(df)     — EWMA: stateless (no-op); GARCH: fit and store params
    .predict(df) — return volatility_forecast_7d (annualised, using chosen formula)
    .save(path)  — persist config/params to {asset}_vol_forecaster.pkl
    .load(path)  — restore
```

**Output**:
```python
{
    "asset":                  "BTC",
    "method":                 "ewma",        # or "garch"
    "volatility_forecast_7d": 0.847,         # annualised fraction
    "formula":                "sqrt(ewm_var(alpha=0.06) * 8760)",
    "timestamp":              "2026-05-18T14:00:00Z",
}
```

#### [MODIFY] api/prediction_service.py

Add `volatility_forecast_7d: Optional[float]` to `RiskResponse`.

**Risk to existing endpoints**: Zero — Optional field with None default

---

### Training Data Schema Impact (Phase 7)

No new CSV columns. **No CSV regeneration needed.**

---

## Schema Reference — All New Columns

| New Column | Stored in CSV? | Where Computed | Phase |
|---|---|---|---|
| `target_return_30d` | No — ephemeral | Inside `DirectionClassifier.fit()` | 1 |
| `target_direction_30d` | No — ephemeral | From above + pre-committed THRESH | 1 |
| `regime_label` | No — inference only | `RegimeDetector.predict()` from existing features | 2 |
| `prob_up_30d` | No — inference only | `DirectionClassifier.predict()` | 1 |
| `prob_down_30d` | No — inference only | `DirectionClassifier.predict()` | 1 |
| `volatility_forecast_7d` | No — inference only | `VolatilityForecaster.predict()` | 7 (cond.) |

**No raw CSV regeneration is required for any phase.**

---

## New Artifacts Reference

| File | Phase | Description |
|---|---|---|
| `{asset}_direction_clf.pkl` | 1 | Trained DirectionClassifier (RandomForest) |
| `{asset}_regime.pkl` | 2 | RegimeDetector (crisis_vol_threshold) |
| `{asset}_backtest_report.json` | 4 | Walk-forward backtest metrics |
| `{asset}_vol_forecaster.pkl` | 7 (cond.) | VolatilityForecaster (EWMA config or GARCH params) |

---

## New pip Dependencies

| Package | Version | Phase | Condition |
|---|---|---|---|
| `arch` | `>=5.3` | 7 — GARCH path only | Only if EWMA rejected in favour of GARCH |

All Steps 1-6 use existing packages in `requirements.txt`.

---

## Endpoint Compatibility Summary

| Endpoint | Ph1 | Ph2 | Ph3 | Ph4 | Ph5 | Ph6 | Ph7 |
|---|---|---|---|---|---|---|---|
| `GET /prediction/{asset}` | Additive | Additive | — | — | — | Additive | — |
| `GET /risk/{asset}` | — | — | — | — | — | — | Additive (Optional) |
| `GET /models/{asset}` | — | — | — | — | — | — | — |
| `GET /metrics/{asset}` | — | — | — | — | — | — | — |
| `POST /retrain/{asset}` | New artifact | New artifact | — | Optional | — | — | New artifact |
| `GET /backtest/{asset}` | — | — | — | **NEW** | — | — | — |

**No existing endpoint is modified in a breaking way. All changes are additive.**

---

## File Change Index

| File | Action | Phase(s) |
|---|---|---|
| `models/direction_classifier.py` | **NEW** | 1 |
| `features/regime.py` | **NEW** | 2 |
| `api/signal_logic.py` | **NEW** | 3 |
| `training/backtest.py` | **NEW** | 4 |
| `models/volatility_forecaster.py` | **NEW** | 7 (conditional) |
| `models/classifier.py` | **MODIFY** — add calibration to `.fit()` | 5 |
| `models/direction_classifier.py` | **MODIFY** — add calibration to `.fit()` | 5 |
| `training/train.py` | **MODIFY** — add Steps 2,5,6; new CLI flags | 1, 2, 4, 5 |
| `api/prediction_service.py` | **MODIFY** — new fields, new models in cache, new endpoint | 1, 2, 4, 6, 7 |
| `requirements.txt` | **MODIFY** — add `arch>=5.3` if GARCH path chosen | 7 (conditional) |
| `FLOW.md` | **MODIFY** — update architecture diagram | After Phase 6 |
| `README.md` | **MODIFY** — update endpoint table, add new artifacts | After Phase 6 |

---

*Plan v2 — 2026-08-28 | Author: ML Engineer (Person C) — dev-shail branch*
*Revisions: data-driven threshold rule, unified signal function, ma_cross verification,*
*build-then-backtest ordering, GARCH/EWMA full specification with exact formulas.*
