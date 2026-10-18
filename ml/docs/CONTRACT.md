# CONTRACT — source of truth (copied verbatim from the backend team). Do not change without approval.
Both schemas have `additionalProperties: false`: NO extra fields in responses.
Internal extras (regime, probabilities, etc.) may only be exposed on a separate `/debug/...` route.

## GET /predict/{asset} -> PredictionResponse
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PredictionResponse",
  "type": "object",
  "required": ["asset", "predicted_price", "prediction_30d", "confidence", "model_version", "timestamp"],
  "properties": {
    "asset": {"type": "string", "description": "Uppercase asset symbol", "example": "BTC"},
    "predicted_price": {"type": ["number","null"], "description": "Ensemble-weighted predicted price 30 days out"},
    "prediction_30d": {"type": ["number","null"], "description": "Predicted 30-day percentage change"},
    "confidence": {"type": ["number","null"], "minimum": 0, "maximum": 1, "description": "Model confidence, blended across ensemble members"},
    "model_version": {"type": ["string","null"], "example": "ensemble-v1.2.0"},
    "timestamp": {"type": "string", "format": "date-time", "description": "ISO-8601 UTC, when this prediction was generated"},
    "lower_bound": {"type": ["number","null"], "description": "Lower bound of the confidence interval"},
    "upper_bound": {"type": ["number","null"], "description": "Upper bound of the confidence interval"},
    "risk_score": {"type": ["number","null"], "minimum": 0, "maximum": 100, "description": "Convenience copy of the risk score, higher = safer"},
    "trend": {"type": ["string","null"], "enum": ["Bullish","Bearish","Neutral",null]},
    "agreement": {"type": ["boolean","null"], "description": "Whether Prophet and LSTM/RandomForest agree on direction"},
    "signal": {"type": ["string","null"], "enum": ["STRONG_BUY","BUY","HOLD","SELL","STRONG_SELL","UNCERTAIN",null]},
    "boosted_confidence": {"type": ["number","null"], "minimum": 0, "maximum": 1, "description": "Confidence after ensemble-agreement boosting"},
    "ensemble_price": {"type": ["number","null"], "description": "Raw weighted-average price across Prophet/LSTM/RandomForest before rounding"},
    "note": {"type": ["string","null"], "description": "Present only on fallback/mock responses"}
  },
  "additionalProperties": false
}
```
Example:
```json
{"asset":"BTC","predicted_price":78452.71,"prediction_30d":9.8,"confidence":0.81,"model_version":"ensemble-v1.2.0",
 "timestamp":"2026-09-03T14:00:00Z","lower_bound":75100.00,"upper_bound":81900.00,"risk_score":71.2,"trend":"Bullish",
 "agreement":true,"signal":"STRONG_BUY","boosted_confidence":0.95,"ensemble_price":77716.5,"note":null}
```

## GET /risk/{asset} -> RiskResponse
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "RiskResponse",
  "type": "object",
  "required": ["asset", "risk_score", "timestamp"],
  "properties": {
    "asset": {"type": "string", "example": "BTC"},
    "risk_score": {"type": "number", "minimum": 0, "maximum": 100, "description": "Normalised risk score — higher = safer, per aai_engine contract"},
    "volatility": {"type": ["number","null"], "description": "Annualised volatility, e.g. 0.18 = 18%"},
    "sharpe_ratio": {"type": ["number","null"], "description": "Risk-adjusted return metric"},
    "timestamp": {"type": "string", "format": "date-time"},
    "note": {"type": ["string","null"], "description": "Present only on fallback/mock responses"}
  },
  "additionalProperties": false
}
```
Example:
```json
{"asset":"BTC","risk_score":71.2,"volatility":0.18,"sharpe_ratio":1.62,"timestamp":"2026-09-03T14:00:00Z","note":null}
```

## Notes
- risk_score here is a single ML number. It is NOT the 4-part risk_breakdown (separate contract, no ML).
- AAIResponse is the backend's own output. Out of scope for ML.
- Our rules on top of this contract:
  - `/predict/btc` and `/risk/btc` must return the SAME risk_score.
  - prediction_30d is a percent; predicted_price a price. Never mix.
  - volatility is annualised (daily std * sqrt(365)).
  - signal emitted values: BUY, HOLD, SELL, UNCERTAIN (STRONG_* only if justified by docs/EVALUATION.md).
  - `agreement` compares the models actually used; null if only one model is served.
  - `note` is set when the model does not beat baselines, or data is stale.
