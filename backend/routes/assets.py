# backend/routes/assets.py
import path_setup  # noqa
from fastapi import APIRouter
from models.schemas import AssetItem
from typing import List

router = APIRouter(tags=["Assets"])

@router.get("/assets", response_model=List[AssetItem])
def get_assets():
    try:
        from db.queries import get_supported_assets
        results = get_supported_assets()
        if results:
            return [{"asset": r["asset_id"], "name": r["name"]} for r in results]
    except Exception:
        pass
    # Fallback if MongoDB isn't up yet
    print("MongoDB not available, returning mock assets")
    return [{"asset": "BTC", "name": "Bitcoin"}, {"asset": "ETH", "name": "Ethereum"}]