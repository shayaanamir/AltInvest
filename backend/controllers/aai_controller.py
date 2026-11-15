"""
AAI controller — orchestrates calls to all three modules and assembles the response.

Inputs come only from the database (`predictions`, `risk_scores`) and the sentiment engine;
nothing is made up. A missing prediction or risk score leaves that component null and the AAI
score null (with `missing_inputs` / `note` saying why). Sentiment is the one component with a
stand-in (a neutral 50 at zero confidence), and the response flags when that happened.
"""

import time
import logging
from datetime import datetime, timezone
from aai_engine.aai import compute_aai, normalise_sentiment, normalise_expected_return

# ML's "no model beat no-change" fallback (ml/docs/DECISIONS.md D35): prediction_30d is 0 %.
# Decision C5 (2026-11-02, Phase 7): keep it as a neutral pred_score of 50, and say so in the note.
BASELINE_MODEL_VERSION = "baseline-last-value"
BASELINE_NOTE = (
    "The prediction part is ML's no-change baseline (prediction_30d 0 %, model_version "
    "baseline-last-value): no model beat it, so it counts as a neutral 50, not as a forecast."
)

# NFT AAI (decision C6, 2026-11-15; same rule as C5): there is no NFT floor forecast, so the
# prediction part is a neutral 50. Risk is the ML NFT risk score (higher = safer, but ranked
# against the tracked NFT collections only, ml/docs/DECISIONS.md D59). Sentiment comes from the
# sentiment engine under asset_id = the collection slug; until it is there no NFT AAI is stored.
NFT_AAI_MODEL_VERSION = "nft-aai-neutral-pred-v1"
NFT_AAI_NOTE = (
    "There is no NFT price forecast, so the prediction part counts as a neutral 50, not as a forecast. "
    "The risk part is ranked against the tracked NFT collections only, so this score is not "
    "comparable to a crypto AAI score."
)


def _get_real_prediction(asset: str) -> dict | None:
    """Latest row in `predictions`, or None. Database errors propagate (503 via main.py)."""
    from db.queries import get_latest_prediction
    return get_latest_prediction(asset)


def _get_real_risk(asset: str) -> dict | None:
    """Latest row in `risk_scores`, or None. Database errors propagate (503 via main.py)."""
    from db.queries import get_latest_risk
    return get_latest_risk(asset)


def _get_real_sentiment(asset: str) -> dict:
    """
    A fresh sentiment reading from the engine: the stored one if it is recent, otherwise a
    refreshed one (same cache, locking and time budget as GET /sentiment/{asset}).

    Never substitutes made-up data. If there is no usable reading — engine missing, pipeline
    failed, nothing to read — it returns confidence 0.0, which makes compute_aai_response use
    a neutral 50 for the sentiment component, and available=False so the response says so.
    """
    try:
        from routes.sentiment import current_sentiment
        record = current_sentiment(asset.lower())
    except Exception as exc:
        print(f"[aai_controller] Sentiment engine unavailable ({exc})")
        record = None

    if record is None:
        return {"sentiment_score": 0.0, "confidence": 0.0, "available": False}
    return {
        "sentiment_score": record["sentiment_score"],
        "confidence": record["confidence"],
        "available": True,
    }


def _expected_return_pct(pred: dict, asset: str) -> float | None:
    """
    The prediction's expected 30-day move in percent: the stored `prediction_30d`, or worked out
    from `predicted_price` against the latest stored price. None if neither is possible.
    """
    pct = pred.get("prediction_30d")
    if isinstance(pct, (int, float)):
        return float(pct)
    target = pred.get("predicted_price")
    if not isinstance(target, (int, float)):
        return None
    from db.queries import get_latest_price
    price = (get_latest_price(asset) or {}).get("price")
    if not isinstance(price, (int, float)) or price <= 0:
        return None
    return (target / price - 1.0) * 100.0


def compute_aai_response(asset: str, sentiment: dict | None = None) -> dict:
    """
    `sentiment` lets a caller pass a reading it already has ({sentiment_score, confidence,
    available}); without it the engine is asked, which may refresh a stale reading.
    """
    pred = _get_real_prediction(asset)
    sent = sentiment if sentiment is not None else _get_real_sentiment(asset)
    risk = _get_real_risk(asset)

    expected = _expected_return_pct(pred, asset) if pred else None
    pred_score = normalise_expected_return(expected) if expected is not None else None

    raw_sent_score = normalise_sentiment(sent.get("sentiment_score", 0.0))
    confidence = float(sent.get("confidence", 0.0))
    sent_score = round(confidence * raw_sent_score + (1 - confidence) * 50.0, 2)

    risk_value = (risk or {}).get("risk_score")
    risk_score = float(risk_value) if isinstance(risk_value, (int, float)) else None

    aai_score = (
        compute_aai(pred_score, sent_score, risk_score)
        if pred_score is not None and risk_score is not None else None
    )
    sentiment_available = bool(sent.get("available", True))
    missing = [name for name, v in (("prediction", pred_score), ("risk score", risk_score)) if v is None]
    notes = []
    if missing:
        notes.append(f"No {' or '.join(missing)} is stored for {asset} yet, so the AAI score can't be computed.")
    if pred_score is not None and (pred or {}).get("model_version") == BASELINE_MODEL_VERSION:
        notes.append(BASELINE_NOTE)

    return {
        "asset": asset,
        "aai_score": aai_score,
        "pred_score": pred_score,
        "expected_return_30d": round(expected, 2) if expected is not None else None,
        "sentiment_score": round(sent_score, 2),
        "sentiment_confidence": round(confidence, 2),
        "sentiment_available": sentiment_available,
        "sentiment_note": None if sentiment_available else (
            "No recent sentiment reading was available, so a neutral value was used for the sentiment component."
        ),
        "risk_score": round(risk_score, 2) if risk_score is not None else None,
        "missing_inputs": missing,
        "note": " ".join(notes) or None,
        "model_version": (pred or {}).get("model_version"),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _get_nft_risk(slug: str) -> dict | None:
    """Latest ML NFT risk row (source ml-service), or None. Seeded or other rows don't count."""
    from db.queries import get_nft_risk_breakdown
    row = get_nft_risk_breakdown(slug)
    return row if (row or {}).get("source") == "ml-service" else None


def compute_nft_aai_response(slug: str, sentiment: dict) -> dict:
    """
    AAI for one NFT collection (C6): 0.4 x neutral 50 + 0.3 x sentiment + 0.3 x ML NFT risk.
    `sentiment` is {sentiment_score, confidence, available} as for crypto. Same response shape
    as compute_aai_response, so is_complete() and the aai_scores readers work unchanged.
    """
    pred_score = 50.0
    raw_sent_score = normalise_sentiment(sentiment.get("sentiment_score", 0.0))
    confidence = float(sentiment.get("confidence", 0.0))
    sent_score = round(confidence * raw_sent_score + (1 - confidence) * 50.0, 2)

    risk_value = (_get_nft_risk(slug) or {}).get("risk_score")
    risk_score = float(risk_value) if isinstance(risk_value, (int, float)) else None

    sentiment_available = bool(sentiment.get("available", True))
    missing = [] if risk_score is not None else ["risk score"]
    notes = [f"No ML risk score is stored for {slug} yet, so the AAI score can't be computed."] if missing else []
    notes.append(NFT_AAI_NOTE)
    return {
        "asset": slug,
        "aai_score": compute_aai(pred_score, sent_score, risk_score) if risk_score is not None else None,
        "pred_score": pred_score,
        "expected_return_30d": None,
        "sentiment_score": round(sent_score, 2),
        "sentiment_confidence": round(confidence, 2),
        "sentiment_available": sentiment_available,
        "sentiment_note": None if sentiment_available else (
            "No recent sentiment reading was available, so a neutral value was used for the sentiment component."
        ),
        "risk_score": round(risk_score, 2) if risk_score is not None else None,
        "missing_inputs": missing,
        "note": " ".join(notes),
        "model_version": NFT_AAI_MODEL_VERSION,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def is_complete(result: dict) -> bool:
    """True when every input was real (prediction, risk and sentiment): only then may it be cached."""
    return result.get("aai_score") is not None and result.get("sentiment_available") is not False


# ── Background refresh ───────────────────────────────────────────────────────
# Discover, Watchlists, Compare and Trending read AAI from `aai_scores`. Without this job a score
# only appeared after someone opened that asset's intelligence panel.

_log = logging.getLogger("aai_refresh")
AAI_REFRESH_SECONDS = 30 * 60   # well inside the 60-minute freshness window the intelligence route uses


def refresh_all_aai_scores() -> dict:
    """
    Computes and stores the AAI for every covered crypto asset and NFT collection. Uses only stored sentiment
    readings (never runs the sentiment pipeline), and stores only complete scores; an asset
    missing a prediction, risk score or recent sentiment keeps its previous row.
    Returns {"stored": [...], "skipped": {asset: reason}}.
    """
    from db.queries import get_supported_assets, upsert_aai_score_generalized
    from controllers.market_controller import live_sentiment_by_symbol

    live = live_sentiment_by_symbol()
    stored, skipped = [], {}
    for a in get_supported_assets():
        symbol = a["asset_id"].upper()
        reading = live.get(symbol)
        sentiment = (
            {"sentiment_score": reading["score"], "confidence": reading["confidence"], "available": True}
            if reading else {"sentiment_score": 0.0, "confidence": 0.0, "available": False}
        )
        result = compute_aai_response(symbol, sentiment=sentiment)
        if not is_complete(result):
            skipped[symbol] = ", ".join(result["missing_inputs"] + ([] if reading else ["recent sentiment"]))
            continue
        upsert_aai_score_generalized(
            "crypto", symbol,
            {**result, "target_type": "crypto", "target_id": symbol, "sentiment_trend": reading.get("trend"),
             "timestamp": datetime.now(timezone.utc)},
        )
        stored.append(symbol)

    # NFT collections (C6). The sentiment engine keys them by slug; live_sentiment_by_symbol
    # upper-cases ids. Nothing is stored until a usable reading for the slug exists, so the
    # NFT AAI appears on its own once the engine covers the collections.
    from db.queries import get_nft_collections
    for c in get_nft_collections():
        slug = c.get("slug")
        if not slug:
            continue
        reading = live.get(slug.upper())
        if not reading:
            skipped[f"nft:{slug}"] = "recent sentiment"
            continue
        sentiment = {"sentiment_score": reading["score"], "confidence": reading["confidence"], "available": True}
        result = compute_nft_aai_response(slug, sentiment)
        if not is_complete(result):
            skipped[f"nft:{slug}"] = ", ".join(result["missing_inputs"])
            continue
        upsert_aai_score_generalized(
            "nft", slug,
            {**result, "target_type": "nft", "target_id": slug, "sentiment_trend": reading.get("trend"),
             "timestamp": datetime.now(timezone.utc)},
        )
        stored.append(f"nft:{slug}")
    return {"stored": stored, "skipped": skipped}


def run_aai_refresh_scheduler(initial_delay_seconds: int = 120) -> None:
    """Daemon-thread loop: first run shortly after startup (sentiment readings load first), then every 30 min."""
    time.sleep(initial_delay_seconds)
    while True:
        try:
            outcome = refresh_all_aai_scores()
            _log.info("[aai] stored %d score(s); skipped %s", len(outcome["stored"]), outcome["skipped"] or "none")
        except Exception as exc:
            from utils.http_errors import redact
            _log.error("[aai] refresh failed: %s: %s", type(exc).__name__, redact(exc))
        time.sleep(AAI_REFRESH_SECONDS)
