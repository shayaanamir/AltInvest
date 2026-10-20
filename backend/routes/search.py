"""
routes/search.py

Cross-collection text search (assets, nft_collections, market_insights).
Logs the query to user_search_history when the caller is authenticated;
search itself works unauthenticated (search bar shouldn't require login).

/search/history: the signed-in user's recent searches (read, record, clear). The history is
de-duplicated, capped at 20 per user and expires after 90 days (db/queries.py, db/indexes.py).
"""
import path_setup  # noqa: F401

from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from utils.http_errors import db_unavailable

from auth.security import decode_access_token
from models.schemas import SearchResults
from auth.dependencies import get_current_user_id
from db.queries import search_all, log_search, get_search_history, clear_search_history
from utils.serialization import serialize_dates

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
        raise db_unavailable(exc)

    user_id = _optional_user_id(authorization)
    if user_id:
        try:
            log_search(user_id, q.strip())
        except Exception as exc:
            print(f"[search] failed to log search history: {exc}")

    return results


# ── /search/history ──────────────────────────────────────────────────────────

class SearchHistoryIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)


@router.get("/search/history")
def list_search_history(limit: int = Query(8, ge=1, le=20), user_id: ObjectId = Depends(get_current_user_id)):
    return [serialize_dates(d) for d in get_search_history(user_id, limit)]


@router.post("/search/history", status_code=204)
def record_search(payload: SearchHistoryIn, user_id: ObjectId = Depends(get_current_user_id)):
    if not payload.query.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty.")
    log_search(user_id, payload.query)
    return None


@router.delete("/search/history", status_code=204)
def delete_search_history(user_id: ObjectId = Depends(get_current_user_id)):
    clear_search_history(user_id)
    return None
