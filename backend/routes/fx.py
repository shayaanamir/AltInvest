"""
routes/fx.py

GET /fx — the latest stored USD exchange rates, used by the frontend to show values in the
user's display currency. Rates are written by controllers/fx_controller.py's scheduler.
"""
import path_setup  # noqa: F401

from fastapi import APIRouter, HTTPException

from controllers.fx_controller import get_latest_rates, SUPPORTED_CURRENCIES
from models.schemas import FxRatesOut
from utils.http_errors import db_unavailable

router = APIRouter(tags=["FX"])


@router.get("/fx", response_model=FxRatesOut)
def get_fx_rates():
    try:
        doc = get_latest_rates()
    except Exception as exc:
        raise db_unavailable(exc)

    if not doc:
        raise HTTPException(status_code=503, detail="Exchange rates haven't been fetched yet.")

    return {
        "base": doc["base"],
        "rates": {c: doc["rates"][c] for c in SUPPORTED_CURRENCIES if c in doc.get("rates", {})},
        "as_of": doc["as_of"],
        "source": doc.get("source"),
        "supported": SUPPORTED_CURRENCIES,
    }
