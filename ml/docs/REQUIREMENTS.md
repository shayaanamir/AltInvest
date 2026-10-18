# REQUIREMENTS

## Purpose
AltInvest is an analytics platform for crypto (later NFTs). It predicts and scores risk. It does NOT trade.

## ML service must provide
- `GET /predict/{asset}` -> PredictionResponse (docs/CONTRACT.md)
- `GET /risk/{asset}` -> RiskResponse (docs/CONTRACT.md)
- Port 8001. Consumed by the backend (Person B), which calls over HTTP.

## Assets
- Phase 1-7: BTC, ETH, SOL (spot vs USDT). More added later via config only.
- WBTC: not a separate asset for now (tracks BTC). Revisit later.
- NFTs: separate plan, only after crypto is finished end to end.

## Outputs per asset
- 30-day-ahead predicted price, % change, interval, measured confidence
- Risk score 0-100, higher = safer; annualised volatility; Sharpe
- Signal in {BUY, HOLD, SELL, UNCERTAIN}; STRONG_* only if backtests justify it

## Non-goals
- AAI composite score, risk_breakdown (4 bars), sentiment, order execution.

## Honesty requirement
If a model does not beat the naive baselines (docs/EVALUATION.md) on held-out data, the API must say so:
signal = UNCERTAIN or HOLD, low confidence, and a `note`. Expected accuracy is modest (papers: ~52% direction).

## Constraints
- Python 3.10/3.11, FastAPI, scikit-learn. Heavy libs (TensorFlow, Prophet) only if they earn their place vs baselines.
- Retraining must be reproducible from the fetch script + config.
