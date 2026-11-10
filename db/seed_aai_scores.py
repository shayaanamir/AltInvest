"""
db/seed_aai_scores.py
Seeds: aai_scores
Source: db/seed_data/{assets,nftCollections,assetDetail}.json (seed input only)

Only targets that already exist in `assets` / `nft_collections` get a row, so
run this after seed_assets and seed_nft (seed_all.py does). Once the AAI
engine writes here on its own (routes/assets.py caches /intelligence results),
these rows are just the starting point and are superseded by newer timestamps.
"""
import json, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from db.mongo_connection import get_db
from db.queries import upsert_aai_score_generalized

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "seed_data")


def _load(name: str) -> dict:
    with open(os.path.join(SAMPLE_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def _doc(target_type: str, target_id: str, item: dict, components: dict | None) -> dict:
    sent = item.get("sentiment") or {}
    aai = item["aai"]
    return {
        "target_type": target_type,
        "target_id": target_id,
        "aai_score": aai["score"],
        "confidence": aai.get("confidence"),
        "regime": aai.get("regime"),
        "pred_score": (components or {}).get("predScore"),
        "sentiment_score": sent.get("score"),
        "sentiment_confidence": sent.get("confidence"),
        "sentiment_trend": sent.get("trend"),
        "risk_score": (components or {}).get("riskScore"),
        "model_version": "seed-v1",
        "timestamp": datetime.now(timezone.utc),
    }


def seed():
    db = get_db()
    assets = {a["asset_id"] for a in db.assets.find({}, {"asset_id": 1})}
    slugs = {c["slug"] for c in db.nft_collections.find({}, {"slug": 1})}
    detail = _load("assetDetail.json")

    n_crypto = n_nft = 0
    for a in _load("assets.json")["assets"]:
        if a["symbol"] not in assets:
            print(f"[aai_scores] skip {a['symbol']} (not in `assets` collection)")
            continue
        comps = (detail.get(a["symbol"]) or {}).get("aaiPanel", {}).get("componentScores")
        upsert_aai_score_generalized("crypto", a["symbol"], _doc("crypto", a["symbol"], a, comps))
        n_crypto += 1
    # No AAI rows for NFT collections (ml/docs/DECISIONS.md D67): the old seed's NFT AAI values were made up.
    # AAI for NFTs is future backend work; the collections' ML risk and liquidity come from the ML pull.
    del slugs

    db.aai_scores.create_index([("target_type", 1), ("target_id", 1), ("timestamp", -1)])
    print(f"[aai_scores] upserted {n_crypto} crypto + {n_nft} nft. Indexes ensured.")


if __name__ == "__main__":
    from db.seed_guard import require_local_target
    require_local_target()          # local MongoDB only, unless --allow-remote (D69)
    seed()
