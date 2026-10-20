"""
backend/controllers/portfolio_intelligence.py

GET /portfolio/intelligence: a read across everything the user holds, weighted by current value.

  diversification  - from the Herfindahl index of position weights: score = (1 - sum(w^2)) x 100.
                     One position scores 0; four equal positions 75; ten equal positions 90.
  concentration    - the largest position's share; over 40% counts as concentrated.
  aggregate risk   - value-weighted average of each crypto position's stored risk_score
                     (same 0-100 scale as Discover; NFTs have no risk score).
  sentiment        - value-weighted average of live sentiment (falls back to the stored AAI row).
  signal mix       - count of positions per BUY / HOLD / SELL signal from each AAI score.

Holdings that can't be valued (no price) are left out of every weighting and counted separately.
"""
from controllers.portfolio_controller import get_valued_holdings
from controllers.market_controller import aai_signal, live_sentiment_by_symbol
from db.queries import get_all_latest_aai_scores, get_all_latest_risk_scores

CONCENTRATION_THRESHOLD = 0.40


def _label(score: float | None) -> str:
    if score is None:
        return "No priced holdings"
    if score < 40:
        return "Concentrated"
    if score < 70:
        return "Moderately diversified"
    return "Well diversified"


def _weighted(pairs):
    pairs = [(v, w) for v, w in pairs if v is not None and w > 0]
    total = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total if total else None


def build_intelligence(user_id) -> dict:
    valued = get_valued_holdings(user_id)
    priced = [h for h in valued if h.get("valuation_status") == "ok" and (h.get("current_value_usd") or 0) > 0]

    # Group by asset so two rows of the same thing don't count as diversification.
    positions: dict[str, dict] = {}
    for h in priced:
        key = (h.get("symbol") or "").upper() if h.get("asset_type") == "crypto" else h.get("nft_collection_slug")
        p = positions.setdefault(key, {"key": key, "type": h.get("asset_type"), "name": h.get("name") or key, "value": 0.0})
        p["value"] += h["current_value_usd"]
    total = sum(p["value"] for p in positions.values())

    crypto_aai = get_all_latest_aai_scores("crypto")
    nft_aai = get_all_latest_aai_scores("nft")
    risk = get_all_latest_risk_scores()
    live = live_sentiment_by_symbol()

    signal_mix: dict[str, int] = {}
    risk_pairs, sent_pairs = [], []
    for p in positions.values():
        p["weight"] = p["value"] / total if total else 0.0
        aai = (crypto_aai if p["type"] == "crypto" else nft_aai).get(p["key"]) or {}
        signal = aai_signal(aai.get("aai_score"))
        if signal:
            signal_mix[signal] = signal_mix.get(signal, 0) + 1
        if p["type"] == "crypto":
            risk_pairs.append(((risk.get(p["key"]) or {}).get("risk_score"), p["value"]))
            sent = (live.get(p["key"]) or {}).get("score", aai.get("sentiment_score"))
            sent_pairs.append((sent, p["value"]))

    hhi = sum(p["weight"] ** 2 for p in positions.values()) if positions else None
    diversification = round((1 - hhi) * 100) if hhi is not None else None
    top = max(positions.values(), key=lambda p: p["value"], default=None)
    concentrated = bool(top and len(positions) > 1 and top["weight"] > CONCENTRATION_THRESHOLD) or len(positions) == 1

    agg_risk = _weighted(risk_pairs)
    sentiment = _weighted(sent_pairs)

    suggestions = []
    unpriced = len(valued) - len(priced)
    if not valued:
        suggestions.append("No holdings yet. Add what you own to see risk, sentiment and signals across it.")
    else:
        if top and len(positions) == 1:
            suggestions.append(f"Everything is in {top['name']}. A single position has no diversification.")
        elif top and top["weight"] > CONCENTRATION_THRESHOLD:
            suggestions.append(f"{top['name']} is {round(top['weight'] * 100)}% of your portfolio's value.")
        sells = signal_mix.get("SELL", 0)
        if sells:
            suggestions.append(f"{sells} position{'s' if sells > 1 else ''} currently read SELL on the AAI score.")
        if sentiment is not None and sentiment < -0.15:
            suggestions.append("News sentiment on what you hold is negative overall.")
        if unpriced:
            suggestions.append(f"{unpriced} holding{'s' if unpriced > 1 else ''} had no current price and {'were' if unpriced > 1 else 'was'} left out.")

    return {
        "position_count": len(positions),
        "priced_value_usd": round(total, 2),
        "unpriced_holding_count": unpriced,
        "diversification_score": diversification,
        "diversification_label": _label(diversification),
        "concentrated": concentrated,
        "largest_position": {"name": top["name"], "weight_pct": round(top["weight"] * 100, 1)} if top else None,
        "aggregate_risk_score": round(agg_risk) if agg_risk is not None else None,
        "sentiment_exposure": round(sentiment, 3) if sentiment is not None else None,
        "signal_mix": signal_mix,
        "suggestions": suggestions,
    }
