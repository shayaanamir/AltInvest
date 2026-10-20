"""
utils/asset_gate.py

One definition of "an asset the platform knows about" for the per-asset endpoints
(/prediction, /risk, /aai): it is whatever is in the `assets` collection, not a list
kept in code. Adding an asset to the database is all it takes for these routes to accept it.
"""

from fastapi import HTTPException

from utils.http_errors import db_unavailable


def require_known_asset(asset: str) -> str:
    """
    Returns the asset's canonical (upper-case) symbol if it is in the `assets` collection.
    Raises 404 for an unknown asset and 503 if the database can't be reached.
    """
    from db.queries import get_asset

    symbol = asset.upper()
    try:
        doc = get_asset(symbol)
    except Exception as exc:
        raise db_unavailable(exc)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Asset '{symbol}' not found.")
    return symbol
