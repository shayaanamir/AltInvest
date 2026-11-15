# CONTRACT_PAST_RANGES: ML past-range endpoint (Phase 11, D87)

The ML service (:8001) validates this response against the schema below before returning it, as it does for CONTRACT.md (AGENTS rule 14, `additionalProperties: false`). The backend pulls it daily at 00:15 UTC with the other ML endpoints and stores it in `ml_past_ranges`.
- Errors: an asset not in `ml/config.py` ASSETS gives 404. Data that fails the serving gate (D40) gives 503.
- `days` (query, optional, integer >= 0): only the last `days` points; omitted = the full history.
- Every price field is a price in USD (never a percentage, AGENTS rule 12). `volatility` is annualised (daily std x sqrt(365)), as on /risk.

## GET /past-ranges/{asset} -> PastRangesResponse

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PastRangesResponse",
  "type": "object",
  "required": ["asset", "timestamp", "lag_days", "volatility_measure", "note", "points"],
  "properties": {
    "asset": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"},
    "lag_days": {"type": "integer", "description": "Days between the day a range was drawn (made_on) and the day it is shown for (date)"},
    "volatility_measure": {"type": "string", "description": "The served volatility column (ml/config.py RISK_VOL_COLUMN)"},
    "note": {"type": "string"},
    "points": {"type": "array", "items": {
      "type": "object",
      "required": ["date", "made_on", "centre", "volatility", "inner_lower", "inner_upper", "outer_lower", "outer_upper", "close"],
      "properties": {
        "date": {"type": "string", "format": "date", "description": "The day the range is shown for (bar open date, UTC)"},
        "made_on": {"type": "string", "format": "date", "description": "date - lag_days: the day the range was drawn"},
        "centre": {"type": "number", "description": "Close of the made_on bar, USD"},
        "volatility": {"type": "number", "description": "Served annualised volatility as known on made_on"},
        "inner_lower": {"type": "number", "description": "50% range, lower edge, USD"},
        "inner_upper": {"type": "number", "description": "50% range, upper edge, USD"},
        "outer_lower": {"type": "number", "description": "80% range, lower edge, USD"},
        "outer_upper": {"type": "number", "description": "80% range, upper edge, USD"},
        "close": {"type": "number", "description": "Close of the date bar, USD (the outcome; used only for the calibration line)"}
      },
      "additionalProperties": false
    }}
  },
  "additionalProperties": false
}
```
Example (one point shown):
```json
{"asset":"BTC","timestamp":"2026-11-16T09:00:00Z","lag_days":30,"volatility_measure":"vol_30d","note":"Each day's range is ...","points":[{"date":"2026-10-17","made_on":"2026-09-17","centre":76417.01,"volatility":0.488582,"inner_lower":69527.80,"inner_upper":83988.84,"outer_lower":63859.73,"outer_upper":91443.54,"close":81491.04}]}
```
