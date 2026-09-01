# lightweight_backtest.py
# WBTC Lightweight Historical Evaluation over the held-out test split.
#
# Purpose:
#   Measure whether the trained combined signal (BUY/SELL/HOLD) has useful
#   behaviour over the held-out test period WITHOUT retraining any model.
#   This is NOT a walk-forward retraining backtest.
#
# Risk proxy:
#   The WBTC pipeline does not include the BTC/ETH/SOL RiskClassifier.
#   risk_score is approximated as the percentile rank of volatility_14d
#   in the test set (scaled 0-100). This is documented clearly.
#
# Return calculation:
#   BUY  -> strategy_return = +target_return_30d  (long)
#   SELL -> strategy_return = -target_return_30d  (short)
#   HOLD -> strategy_return = 0
#
# Usage:
#   cd ml/
#   python training/lightweight_backtest.py
#   python training/lightweight_backtest.py --up-thresh 0.55 --down-thresh 0.55

import sys
import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

_ML_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ML_ROOT))

from models.direction_classifier import DirectionClassifier, DIRECTION_FEATURES
from training.wbtc_signal import generate_signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s -- %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("lightweight_backtest")

DATA_DIR      = _ML_ROOT / "data"
ARTIFACTS_DIR = _ML_ROOT / "models" / "artifacts"
TEST_CSV      = DATA_DIR / "wbtc_test_model.csv"
ARTIFACT_PATH = ARTIFACTS_DIR / "wbtc_direction_clf.pkl"


def run_backtest(up_threshold=0.50, down_threshold=0.50, risk_threshold=70.0):
    sep = "=" * 62
    print()
    print(sep)
    print("  AltInvest -- WBTC Lightweight Backtest (Test Split)")
    print(sep)

    # 1. Load model artifact
    if not ARTIFACT_PATH.exists():
        raise FileNotFoundError(
            "Model artifact not found: " + str(ARTIFACT_PATH) +
            "\n  -> Run: python training/train_wbtc_direction.py"
        )
    log.info("Loading DirectionClassifier from %s ...", ARTIFACT_PATH)
    clf = DirectionClassifier.load(ARTIFACT_PATH)

    # 2. Load test split (never used during training or threshold decisions)
    log.info("Loading test split from %s ...", TEST_CSV)
    test_df = pd.read_csv(TEST_CSV)
    test_df["timestamp"] = pd.to_datetime(test_df["timestamp"])
    test_df = test_df.sort_values("timestamp").reset_index(drop=True)
    log.info("Test rows: %d  |  date range: %s -> %s",
             len(test_df),
             test_df["timestamp"].iloc[0].date(),
             test_df["timestamp"].iloc[-1].date())

    # 3. Approximate risk_score from volatility_14d (percentile rank 0-100)
    risk_proxy = (test_df["volatility_14d"].rank(pct=True) * 100).values

    # 4. Generate signals
    X_test      = test_df[DIRECTION_FEATURES].values
    proba       = clf._model.predict_proba(X_test)
    class_names = list(clf._encoder.classes_)   # DOWN, FLAT, UP
    up_idx      = class_names.index("UP")
    down_idx    = class_names.index("DOWN")

    signals = []
    for i in range(len(test_df)):
        sig = generate_signal(
            prob_up=float(proba[i, up_idx]),
            prob_down=float(proba[i, down_idx]),
            trend_return=float(test_df["return_30d"].iloc[i]),
            risk_score=float(risk_proxy[i]),
            up_threshold=up_threshold,
            down_threshold=down_threshold,
            risk_threshold=risk_threshold,
        )
        signals.append(sig)

    test_df["signal"]    = signals
    test_df["prob_up"]   = proba[:, up_idx]
    test_df["prob_down"] = proba[:, down_idx]

    # 5. Strategy returns
    def strat_ret(row):
        if row["signal"] == "BUY":
            return row["target_return_30d"]
        elif row["signal"] == "SELL":
            return -row["target_return_30d"]
        return 0.0

    test_df["strategy_return"] = test_df.apply(strat_ret, axis=1)
    test_df["bnh_return"]      = test_df["target_return_30d"]

    # 6. Hit rate
    active = test_df[test_df["signal"] != "HOLD"]
    if len(active) > 0:
        hit = (
            ((active["signal"] == "BUY")  & (active["target_return_30d"] > 0)) |
            ((active["signal"] == "SELL") & (active["target_return_30d"] < 0))
        )
        hit_rate = hit.mean()
    else:
        hit_rate = float("nan")

    # 7. Cumulative returns
    cum_strategy = float(np.exp(test_df["strategy_return"].sum()) - 1)
    cum_bnh      = float(np.exp(test_df["bnh_return"].sum()) - 1)

    # 8. Sharpe (annualised from hourly returns)
    nz = test_df["strategy_return"][test_df["signal"] != "HOLD"]
    sharpe = float((nz.mean() / nz.std()) * np.sqrt(8760)) if (len(nz) > 1 and nz.std() > 0) else float("nan")

    # 9. Max drawdown
    cum_log  = test_df["strategy_return"].cumsum()
    roll_max = cum_log.cummax()
    max_dd   = float(np.exp((cum_log - roll_max).min()) - 1)

    # 10. Signal distribution
    sig_counts = test_df["signal"].value_counts().to_dict()

    # Print report
    print()
    print("  Thresholds: up={:.2f}  down={:.2f}  risk_max={:.0f}".format(
        up_threshold, down_threshold, risk_threshold))
    print()
    print("  [Signal Distribution]")
    total = len(test_df)
    for sig in ["BUY", "SELL", "HOLD"]:
        n = sig_counts.get(sig, 0)
        print("    {:4s} : {:5d}  ({:.1f}%)".format(sig, n, n / total * 100))

    print()
    print("  [Performance vs Buy-and-Hold]")
    print("    Strategy cumulative return : {:+.2%}".format(cum_strategy))
    print("    Buy-and-hold return        : {:+.2%}".format(cum_bnh))
    if not np.isnan(hit_rate):
        print("    Hit rate (active signals)  : {:.2%}  (n={} active trades)".format(
            hit_rate, len(active)))
    else:
        print("    Hit rate (active signals)  : N/A (no active signals)")
    if not np.isnan(sharpe):
        print("    Annualised Sharpe          : {:.3f}".format(sharpe))
    print("    Max drawdown (strategy)    : {:.2%}".format(max_dd))

    print()
    print("  [Note on risk_score proxy]")
    print("    risk_score is approximated as percentile rank of volatility_14d")
    print("    in the test set (0-100 scale). Replace with RiskClassifier output")
    print("    for production use.")
    print()
    print(sep)

    return {
        "test_rows":        len(test_df),
        "signal_counts":    sig_counts,
        "hit_rate":         round(hit_rate, 4) if not np.isnan(hit_rate) else None,
        "cum_strategy_pct": round(cum_strategy * 100, 2),
        "cum_bnh_pct":      round(cum_bnh * 100, 2),
        "sharpe":           round(sharpe, 3) if not np.isnan(sharpe) else None,
        "max_drawdown_pct": round(max_dd * 100, 2),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="WBTC Lightweight Backtest")
    p.add_argument("--up-thresh",   type=float, default=0.50)
    p.add_argument("--down-thresh", type=float, default=0.50)
    p.add_argument("--risk-thresh", type=float, default=70.0)
    a = p.parse_args()
    run_backtest(up_threshold=a.up_thresh, down_threshold=a.down_thresh,
                 risk_threshold=a.risk_thresh)
