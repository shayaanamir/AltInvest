# GLOSSARY (plain English; add new terms whenever a phase introduces them)

Terms marked *(not used yet)* appear in the plan docs but no code uses them so far.

## Market data
- **Kline / candlestick**: one time slice of trading summarised as open, high, low, close and volume. Binance calls its API record a "kline".
- **OHLCV**: Open, High, Low, Close, Volume of one bar. Open/close are the first/last price of the slice, high/low the extremes, volume the amount traded.
- **Daily bar**: one kline covering one UTC day (00:00 to 24:00). We use the close as "the price of that day" (docs/DATA.md).
- **Closed bar**: a bar whose time slice is over. The current day's bar is still changing, so `fetch.py` drops it.
- **UTC**: the world time standard, used for all timestamps so day boundaries are the same everywhere.
- **Spot symbol (BTCUSDT)**: Binance's name for the market that trades BTC against USDT, a coin pegged to the US dollar.
- **Gap / missing day**: a calendar day inside the date range with no bar. We report gaps; we never fill them.
- **Forward-fill / interpolation**: inventing a missing value by copying the last one or drawing a line between neighbours. Forbidden here (AGENTS rule 4, docs/DATA.md).
- **Synthetic data**: numbers produced by a program instead of the market. v1 used it, which made its metrics meaningless (docs/LEARNINGS.md).
- **Pagination**: an API returns at most 1000 bars per request, so we ask repeatedly, each time starting after the last bar received.
- **Rate limit / backoff**: the server refuses too many requests per minute; backoff means waiting longer after each failed try.

## Returns and risk
- **Return**: how much the price changed, as a fraction. 100 to 110 is +10%.
- **Log return**: ln(today's close / yesterday's close). Close to the ordinary return for small moves, and daily log returns can be added up over time.
- **Volatility**: how violently returns swing, usually the standard deviation of returns.
- **Annualised volatility**: daily volatility scaled to a year: daily std x sqrt(365) for crypto, which trades every day (docs/EVALUATION.md rule 5). *(not used yet)*
- **Sharpe ratio**: average return divided by volatility, a "return per unit of risk" score. Annualised with sqrt(365). *(not used yet)*
- **Kurtosis**: a number describing how fat the extreme ends of a distribution are.
- **Excess kurtosis**: kurtosis minus 3, so a normal (bell-curve) distribution scores 0. Positive means more extreme days than a bell curve predicts.
- **Heavy tails**: extreme moves (crashes, spikes) happen far more often than a bell curve would allow. Real crypto has them; high excess kurtosis is the symptom.
- **Volatility clustering**: big moves tend to be followed by big moves, calm by calm. Measured here by the autocorrelation of absolute returns.
- **Autocorrelation (lag-1)**: how strongly a series resembles itself shifted by one step. +1 same, 0 unrelated, -1 opposite.

## Modelling and evaluation
- **Horizon**: how far ahead we predict: 30 daily bars (D3).
- **Label**: the answer a model is trained to predict, built from the future (for example the price 30 days later).
- **Feature**: an input to a model, built only from the past.
- **Leakage**: information from the future getting into training or features, which makes results look better than they could be in real use.
- **Train / validation / test split**: three chronological pieces of the data. Train teaches the model, validation is for choosing between options, test is a final exam used once.
- **Embargo**: a gap (30 days) left between splits so labels, which look 30 days ahead, in one piece cannot overlap the next piece (D16).
- **Baseline**: a deliberately simple predictor (for example "price stays the same"). A model is only worth shipping if it beats it.
- **Walk-forward**: testing by repeatedly training on the past and predicting the next stretch, moving forward in time. *(not used yet)*
- **Non-overlapping windows**: evaluating 30-day periods that do not share days, because daily steps with a 30-day horizon overlap 29/30 (docs/LEARNINGS.md). *(not used yet)*
- **Backtest**: replaying a strategy on past data to see how it would have done. *(not used yet)*

## Engineering
- **Unit test**: a tiny automatic check of one function using small made-up inputs (here, hand-made fixtures, not market data).
- **Fixture**: the small made-up input a test uses.
- **Git-ignored**: a file Git does not track, so it is not committed. Raw data files are ignored; reports are tracked (D13, D15).
- **Artifact**: a saved model file. Each gets a `metadata.json` (AGENTS rule 10). *(not used yet)*
- **Pickle**: Python's way of saving objects to a file; it breaks if saved from a script run as `python file.py` (AGENTS rule 9). *(not used yet)*
- **Exit code**: the number a command returns: 0 means success, 1 means failure. `validate` returns 1 if any check fails.
