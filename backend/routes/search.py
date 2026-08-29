"""
routes/search.py

Cross-collection text search (assets, nft_collections, market_insights).
Logs the query to user_search_history when the caller is authenticated;
search itself works unauthenticated (search bar shouldn't require login).
"""
import path_setup  # noqa: F401

from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Header, HTTPException, Query

from auth.security import decode_access_token
from models.schemas import SearchResults
from db.queries import search_all, log_search

router = APIRouter(tags=["Search"])


def _optional_user_id(authorization: Optional[str] = Header(None)) -> Optional[ObjectId]:
    """
    Best-effort auth: if a valid Bearer token is present, return the user_id
    so the search can be logged. If absent or invalid, return None rather
    than raising — search is public.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    payload = decode_access_token(authorization.split(" ", 1)[1])
    if not payload:
        return None
    try:
        return ObjectId(payload.get("sub"))
    except Exception:
        return None


# ── GET /search ──────────────────────────────────────────────────────────────

@router.get("/search", response_model=SearchResults)
def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=25),
    authorization: Optional[str] = Header(None),
):
    if not q.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty.")

    try:
        results = search_all(q.strip(), limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Unable to reach the database: {exc}")

    user_id = _optional_user_id(authorization)
    if user_id:
        try:
            log_search(user_id, q.strip())
        except Exception as exc:
            print(f"[search] failed to log search history: {exc}")

    return results