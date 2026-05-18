from fastapi import APIRouter
from typing import List
from models.schemas import AssetItem
from shared.mock_data import SUPPORTED_ASSETS

router = APIRouter(tags=["Assets"])


@router.get("/assets", response_model=List[AssetItem])
def get_assets():
    """Returns the list of assets supported by the platform."""
    return [{"asset": k, "name": v} for k, v in SUPPORTED_ASSETS.items()]
