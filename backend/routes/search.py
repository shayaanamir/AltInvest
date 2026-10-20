"""
routes/search.py

Cross-collection text search (assets, nft_collections, market_insights).
Logs the query to user_search_history when the caller is authenticated;
search itself works unauthenticated (search bar shouldn't require login).
"""
import path_setup  # noqa: F401

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from utils.http_errors import db_unavailable

from auth.dependencies import get_optional_user_id
from models.schemas import SearchResults
from db.queries import search_all, log_search

router = APIRouter(tags=["Search"])


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
        raise db_unavailable(exc)

    user_id = get_optional_user_id(authorization)
    if user_id:
        try:
            log_search(user_id, q.strip())
        except Exception as exc:
            print(f"[search] failed to log search history: {exc}")

    return results