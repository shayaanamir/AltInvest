# DATA

## Source (training phase)
Binance public klines API (no key). Symbols BTCUSDT, ETHUSDT, SOLUSDT. Interval 1d. Close = price.
Later: live updates via the same API, or Person A's MongoDB. The loader must be swappable (one function in data/loader.py).

## Schema (data/raw/{asset}_1d.csv)
`asset, timestamp (UTC ISO-8601, bar open), open, high, low, close, volume`

## Rules
- Real data only. No forward-fill, no interpolation. Gaps are reported, not hidden.
- Only fully closed bars (drop the current partial day).
- Paginate (limit 1000), retry with backoff, respect rate limits.
- Files are git-ignored; `fetch.py` is tracked so anyone can regenerate.

## Validation (data/validate.py -> reports/data/{asset}_validation.json, tracked; D15)
Row count, date range, missing days, duplicates, min/max, non-positive prices,
excess kurtosis of daily log returns, lag-1 autocorrelation of |returns|.
Real crypto shows heavy tails (kurtosis well above 0) and volatility clustering (positive autocorr).
If a series looks Gaussian with no clustering: STOP and report. It's probably synthetic or broken.

## Splits (config.py)
Chronological. Train first ~70%, validation ~15%, test last ~15%.
Embargo of 30 days between each split (equal to the horizon), cut from the END of the earlier split (D16). The test set is touched only for final reports.

## Known limits
BTC/ETH since 2017-08, SOL since 2020-08. This gives roughly 75-100 non-overlapping 30-day windows per asset, so results are noisy: report confidence intervals.
