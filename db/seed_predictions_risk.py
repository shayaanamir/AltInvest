"""
db/seed_predictions_risk.py
Seeds: predictions, risk_scores, risk_breakdown
Source: frontend/src/data/sample_data/assetDetail.json (aaiPanel/riskOverview/signalCard)
NOTE: once ml/api/prediction_service.py writes here directly on each run,
this seed only matters for assets the ML service hasn't produced yet.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from db.mongo_connection import get_db

NOW = datetime.now(timezone.utc)

PREDICTIONS = [
    {"asset": "BTC", "predicted_price": 78452.71, "prediction_30d": 9.8,
     "lower_bound": 75100.00, "upper_bound": 81900.00, "confidence": 0.81,
     "risk_score": 71.2, "trend": "Bullish", "agreement": True, "signal": "STRONG_BUY",
     "boosted_confidence": 0.95, "ensemble_price": 77716.5, "model_version": "seed-v1"},
    {"asset": "ETH", "predicted_price": 4080.00, "prediction_30d": 6.1,
     "lower_bound": 3920.00, "upper_bound": 4260.00, "confidence": 0.69,
     "risk_score": 62.5, "trend": "Bullish", "agreement": True, "signal": "STRONG_BUY",
     "boosted_confidence": 0.95, "ensemble_price": 4035.08, "model_version": "seed-v1"},
    {"asset": "SOL", "predicted_price": 174.63, "prediction_30d": -2.4,
     "lower_bound": 158.40, "upper_bound": 191.20, "confidence": 0.58,
     "risk_score": 38.4, "trend": "Neutral", "agreement": False, "signal": "UNCERTAIN",
     "boosted_confidence": 0.60, "ensemble_price": 171.42, "model_version": "seed-v1"},
]

RISK_SCORES = [
    {"asset": "BTC", "risk_score": 71.2, "volatility": 0.18, "sharpe_ratio": 1.62},
    {"asset": "ETH", "risk_score": 62.5, "volatility": 0.24, "sharpe_ratio": 1.18},
    {"asset": "SOL", "risk_score": 38.4, "volatility": 0.34, "sharpe_ratio": 0.74},
]

RISK_BREAKDOWN = [
    {"asset": "BTC", "volatility_index": 41, "liquidity_score": 96, "regulatory_risk": 30, "market_risk": 38},
    {"asset": "ETH", "volatility_index": 52, "liquidity_score": 93, "regulatory_risk": 34, "market_risk": 45},
    {"asset": "SOL", "volatility_index": 74, "liquidity_score": 84, "regulatory_risk": 41, "market_risk": 58},
    {"asset": "LINK", "volatility_index": 47, "liquidity_score": 78, "regulatory_risk": 28, "market_risk": 42},
    {"asset": "DOGE", "volatility_index": 81, "liquidity_score": 71, "regulatory_risk": 47, "market_risk": 66},
    {"asset": "ARB", "volatility_index": 55, "liquidity_score": 66, "regulatory_risk": 39, "market_risk": 55},
    {"asset": "DAI", "volatility_index": 3, "liquidity_score": 88, "regulatory_risk": 52, "market_risk": 12},
    {"asset": "UNI", "volatility_index": 58, "liquidity_score": 69, "regulatory_risk": 44, "market_risk": 57},
    {"asset": "BASE", "volatility_index": 49, "liquidity_score": 52, "regulatory_risk": 46, "market_risk": 50},
]


# ── Remaining covered assets, from the same sample JSON ──────────────────────
# The hand-written rows above cover BTC/ETH/SOL (predictions, risk_scores) and the
# first nine assets (risk_breakdown). The other assets come from assets.json.
# `agreement`, `signal`, `boosted_confidence` and `ensemble_price` only exist when
# the real ML service runs (Prophet + LSTM), so they are left None here.

def _trend(pct: float) -> str:
    return "Bullish" if pct > 5 else "Bearish" if pct < -5 else "Neutral"   # ml/api/prediction_service.py rule


def _add_remaining_from_sample():
    import json
    path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data",
                        "sample_data", "assets.json")
    with open(path, encoding="utf-8") as f:
        sample = json.load(f)["assets"]

    have_pred = {p["asset"] for p in PREDICTIONS}
    have_risk = {r["asset"] for r in RISK_SCORES}
    have_breakdown = {b["asset"] for b in RISK_BREAKDOWN}
    for s in sample:
        sym, pred, risk = s["symbol"], s.get("prediction"), s.get("risk")
        if pred and sym not in have_pred:
            PREDICTIONS.append({
                "asset": sym, "predicted_price": pred["prophetPrice30d"],
                "prediction_30d": pred["prediction30dPct"],
                "lower_bound": pred["lowerBound"], "upper_bound": pred["upperBound"],
                "confidence": s["aai"]["confidence"],
                "risk_score": risk["score"] if risk else None,
                "trend": _trend(pred["prediction30dPct"]),
                "agreement": None, "signal": None,
                "boosted_confidence": None, "ensemble_price": None,
                "model_version": "seed-v1",
            })
        if risk and sym not in have_risk:
            RISK_SCORES.append({
                "asset": sym, "risk_score": risk["score"],
                "volatility": risk["volatility"], "sharpe_ratio": risk["sharpeRatio"],
            })
        if risk and sym not in have_breakdown:
            RISK_BREAKDOWN.append({
                "asset": sym, "volatility_index": risk["volatilityIndex"],
                "liquidity_score": risk["liquidityScore"],
                "regulatory_risk": risk["regulatoryRisk"], "market_risk": risk["marketRisk"],
            })


_add_remaining_from_sample()



def _upsert_daily(collection, doc: dict) -> None:
    """One row per asset per day, so re-running the seed doesn't stack duplicates."""
    day = NOW.strftime("%Y-%m-%dT00:00:00Z")
    collection.update_one(
        {"asset": doc["asset"], "date": day},
        {"$set": {**doc, "date": day, "timestamp": NOW}},
        upsert=True,
    )


def seed():
    db = get_db()

    for p in PREDICTIONS:
        _upsert_daily(db.predictions, p)
    print(f"[predictions] inserted {len(PREDICTIONS)}")

    for r in RISK_SCORES:
        _upsert_daily(db.risk_scores, r)
    print(f"[risk_scores] inserted {len(RISK_SCORES)}")

    for rb in RISK_BREAKDOWN:
        _upsert_daily(db.risk_breakdown, rb)
    print(f"[risk_breakdown] inserted {len(RISK_BREAKDOWN)}")

    db.predictions.create_index([("asset", 1), ("timestamp", -1)])
    db.risk_scores.create_index([("asset", 1), ("timestamp", -1)])
    db.risk_breakdown.create_index([("asset", 1), ("timestamp", -1)])
    print("Indexes ensured.")


if __name__ == "__main__":
    seed()