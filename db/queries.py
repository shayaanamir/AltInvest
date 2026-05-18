from db.mongo_connection import get_db
from datetime import datetime, timezone

def get_latest_price(asset: str) -> dict | None:
    db = get_db()
    return db.prices.find_one(
        {"asset": asset.upper()},
        sort=[("date", -1)],
        projection={"_id": 0}
    )

def get_price_history(asset: str, days: int = 365) -> list:
    db = get_db()
    cursor = db.prices.find(
        {"asset": asset.upper()},
        sort=[("date", -1)],
        limit=days,
        projection={"_id": 0}
    )
    return list(cursor)

def get_latest_sentiment(asset: str) -> dict | None:
    db = get_db()
    return db.sentiment.find_one(
        {"asset": asset.upper()},
        sort=[("date", -1)],
        projection={"_id": 0}
    )

def get_latest_prediction(asset: str) -> dict | None:
    db = get_db()
    return db.predictions.find_one(
        {"asset": asset.upper()},
        sort=[("date", -1)],
        projection={"_id": 0}
    )

def get_latest_risk(asset: str) -> dict | None:
    db = get_db()
    return db.risk_scores.find_one(
        {"asset": asset.upper()},
        sort=[("date", -1)],
        projection={"_id": 0}
    )

def get_supported_assets() -> list:
    db = get_db()
    return list(db.assets.find({}, projection={"_id": 0}))

def upsert_aai_score(asset: str, payload: dict) -> None:
    db = get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
    db.aai_scores.update_one(
        {"asset": asset.upper(), "date": today},
        {"$set": payload},
        upsert=True
    )