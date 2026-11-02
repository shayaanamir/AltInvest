"""
db/seed_predictions_risk.py
Seeds: predictions, risk_scores, risk_breakdown
Source: db/seed_data/assetDetail.json and assets.json (seed input only)
NOTE: predictions and risk_scores for the ML-covered assets (db.queries.ML_COVERED_ASSETS:
BTC, ETH, SOL) are NOT seeded. They come only from the ML service, pulled daily by
backend/controllers/ml_pull_controller.py; a seed row here would overwrite that day's real row.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from db.mongo_connection import get_db
from db.queries import ML_COVERED_ASSETS

NOW = datetime.now(timezone.utc)

# Filled from the sample JSON below, without the ML-covered assets.
PREDICTIONS = []
RISK_SCORES = []

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
# The hand-written rows above cover the first nine assets (risk_breakdown). The rest,
# and every predictions / risk_scores row, come from assets.json, skipping the ML-covered
# assets for predictions and risk_scores. `agreement`, `signal`, `boosted_confidence` and
# `ensemble_price` are left None here.

def _trend(pct: float) -> str:
    return "Bullish" if pct > 5 else "Bearish" if pct < -5 else "Neutral"   # +/-5 % bands


def _add_remaining_from_sample():
    import json
    path = os.path.join(os.path.dirname(__file__), "seed_data", "assets.json")
    with open(path, encoding="utf-8") as f:
        sample = json.load(f)["assets"]

    have_pred = {p["asset"] for p in PREDICTIONS} | set(ML_COVERED_ASSETS)
    have_risk = {r["asset"] for r in RISK_SCORES} | set(ML_COVERED_ASSETS)
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