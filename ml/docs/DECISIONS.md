# DECISIONS (append only; don't re-debate without a new reason)

| # | Decision | Why |
|---|---|---|
| D1 | Restart as ml-v2; v1 archived at tag archive/ml-v1 | v1 used synthetic data; 3 signal functions; stale artifacts |
| D2 | Real data only (Binance public klines) | v1 metrics were meaningless on GBM data |
| D3 | Daily bars, horizon = 30 rows | Matches Murray 2023 and McNally 2016; avoids v1's "30 days = 30 hours" bug. Hourly may return later for risk only. |
| D4 | Assets: BTC, ETH, SOL; WBTC dropped for now | WBTC tracks BTC; v1 WBTC data was scaled, gapped, unsourced |
| D5 | ML owns only /predict and /risk | AAI is backend |
| D6 | No extra top-level response fields | CONTRACT has additionalProperties:false; extras go to /debug |
| D7 | signal values BUY/HOLD/SELL/UNCERTAIN first | Direction accuracy expected near 50-55%; STRONG_* needs evidence |
| D8 | Ensembling only if it beats the best single model on validation | Murray 2023: averaging with weaker models hurt |
| D9 | Risk = forward 30d realised vol terciles (thresholds from train), score = 100 - P(high)*100 | Forward-looking, no circularity with features |
| D10 | Training uses downloaded historical files; live fetching comes later | User decision |
