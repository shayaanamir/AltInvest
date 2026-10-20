"""
routes/search.py

Cross-collection text search (assets, nft_collections, market_insights).
Search itself is public (the search bar shouldn't require login) and doesn't record anything:
the top bar searches as you type, so a search is only saved to history (POST /search/history)
when the user actually picks a result.

/search/history: the signed-in user's recent searches (read, record, clear). The history is
de-duplicated, capped at 20 per user and expires after 90 days (db/queries.py, db/indexes.py).
"""
import path_setup  # noqa: F401

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from utils.http_errors import db_unavailable

from models.schemas import SearchResults
from auth.dependencies import get_current_user_id
from db.queries import search_all, log_search, get_search_history, clear_search_history
from utils.serialization import serialize_dates

router = APIRouter(tags=["Search"])


# ── GET /search ──────────────────────────────────────────────────────────────

@router.get("/search", response_model=SearchResults)
def search(
    q: str = Query(..., min_length=1, max_length=64),
    limit: int = Query(10, ge=1, le=25),
):
    if not q.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty.")

    try:
        results = search_all(q.strip(), limit=limit)
    except Exception as exc:
        raise db_unavailable(exc)
    for row in results["insights"]:
        row.pop("score", None)
        if hasattr(row.get("published_at"), "strftime"):
            row["published_at"] = row["published_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
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
