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
| D11 | config.py stores split FRACTIONS (0.70/0.15/0.15), not dates; dates are derived per asset and written to metadata.json | Assets start on different dates (SOL 2020 vs BTC 2017); fixed dates would give SOL a tiny train set |
| D12 | Repo root is the working directory; `ml` is a package (`ml/__init__.py`); tests run as `python -m pytest ml` | Matches `python -m ml.x.y` (AGENTS rule 9); avoids collecting other teams' tests |
| D13 | Only `ml/data/raw/` is git-ignored, not `ml/data/` | DATA.md requires fetch.py/validate.py to be tracked; v1's `ml/data/` rule would have ignored them |
| D14 | Python 3.10-3.12 supported; dev machine runs 3.12.10 | scikit-learn/FastAPI fine on 3.12; TensorFlow/Prophet optional, only if they beat baselines |
| D15 | Validation reports tracked at ml/reports/data/{asset}_validation.json; data/raw/ stays ignored | Small files, and they are the evidence the data is real |
| D16 | Split boundaries from 70/15/15 of the full series (n rows): b1=floor(0.70n), b2=floor(0.85n). train=[0, b1-30), validation=[b1, b2-30), test=[b2, n). The last 30 rows of the series have no forward label and are excluded from labelled data | Embargo cut from the end of the earlier split, so test ends at the latest data |
