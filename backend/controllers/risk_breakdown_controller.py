"""
Measured risk breakdown for the coins the ML service serves (ml/docs/DECISIONS.md D96, D94 Stage 2).

Three metrics per coin, each a 0-100 SAFETY score (higher = safer, like the D36 risk score) from ranking a measured
value across the covered coins:

  volatility   the served 30-day volatility (ML /risk `volatility`, persistence, D82)   lower is safer
  liquidity    24h volume / market cap (latest CoinGecko snapshot)                    higher is safer
  market_risk  maximum drawdown over the last 90 days of daily closes (`prices`)       shallower is safer

Every metric keeps its raw value, source and as_of. An input that is missing, unreadable or older than its limit
gives value null and status "not available" (never a default) and is left out of that metric's ranking. There is
no regulatory-risk metric (no data source). DAI and BASE (not covered, D94) get no rows.

Runs right after the daily ML pull (ml_pull_controller), under claim_run("risk-breakdown").
"""
import logging
from datetime import datetime, timedelta, timezone

from controllers.aai_controller import INPUT_MAX_AGE

_log = logging.getLogger("risk_breakdown")

SOURCE = "measured-d96"
ML_MAX_AGE = INPUT_MAX_AGE                 # 3 days: the ML pull is daily (same limit as the AAI, G-20)
MARKET_MAX_AGE = timedelta(days=1)         # the CoinGecko snapshot refreshes every 2 minutes
PRICE_MAX_AGE = timedelta(days=3)          # the last hourly price must be this recent
DRAWDOWN_DAYS = 90
MIN_DRAWDOWN_DAYS = 60                     # at least this many of the 90 daily closes, else not available
CLAIM_GAP_SECONDS = 6 * 3600

NOT_AVAILABLE = "not available"
OK = "ok"

# metric -> (label, raw-value description, source description, riskier when the raw value is higher?)
METRICS = {
    "volatility": ("Volatility", "30-day volatility, annualised", "ML service /risk (30-day volatility, D82)", True),
    "liquidity": ("Liquidity", "24h volume / market cap", "CoinGecko 24h volume and market cap", False),
    "market_risk": ("Market risk", f"maximum drawdown over {DRAWDOWN_DAYS} days", "daily closes from Binance / CoinGecko prices", True),
}


def _aware(ts):
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(ts, datetime):
        return None
    return (ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v else None


def _measured(value, as_of, why=None):
    return {"value": value, "as_of": _iso(as_of), "status": OK if value is not None else NOT_AVAILABLE, "why": why}


def max_drawdown(closes: list[float]) -> float | None:
    """The deepest fall from a running peak, as a positive fraction (0.35 = 35 % below the peak). None if empty."""
    if not closes:
        return None
    peak, worst = closes[0], 0.0
    for p in closes:
        peak = max(peak, p)
        if peak > 0:
            worst = max(worst, 1.0 - p / peak)
    return worst


def daily_closes(rows: list) -> list[float]:
    """Last price of each UTC day, oldest first, from oldest-first [(timestamp, price)]."""
    by_day = {}
    for ts, price in rows:
        ts = _aware(ts)
        p = _num(price)
        if ts is not None and p is not None and p > 0:
            by_day[ts.strftime("%Y-%m-%d")] = p
    return [by_day[d] for d in sorted(by_day)]


def safety_scores(values: dict, riskier_when_higher: bool) -> dict:
    """
    {asset: 0-100 safety score} over the assets with a value: 100 x (other assets that are riskier + half the ties)
    / (n - 1). Assets without a value get None; fewer than two values give every asset None.
    """
    have = {a: v for a, v in values.items() if v is not None}
    out = {a: None for a in values}
    n = len(have)
    if n < 2:
        return out
    for a, v in have.items():
        riskier = sum(1 for b, w in have.items() if b != a and (w > v if riskier_when_higher else w < v))
        ties = sum(1 for b, w in have.items() if b != a and w == v)
        out[a] = round(100.0 * (riskier + 0.5 * ties) / (n - 1), 1)
    return out


def gather_inputs(assets, now: datetime) -> dict:
    """{asset: {metric: measured}} from the database: the newest rows, each checked against its age limit."""
    from db.queries import get_all_latest_risk_scores, get_asset_market_data_all_latest, get_prices_since

    risk_rows = get_all_latest_risk_scores()
    market_rows = {m.get("asset_id"): m for m in get_asset_market_data_all_latest()}
    out = {}
    for asset in assets:
        # Volatility: only the ML service's own rows (D94 removed the seeded ones).
        r = risk_rows.get(asset) or {}
        r_at = _aware(r.get("timestamp"))
        vol = _num(r.get("volatility"))
        if r.get("source") != "ml-service" or vol is None:
            vol_m = _measured(None, r_at, "no volatility from the ML service")
        elif r_at is None or now - r_at > ML_MAX_AGE:
            vol_m = _measured(None, r_at, f"ML risk row older than {ML_MAX_AGE.days} days")
        else:
            vol_m = _measured(vol, r_at)

        # Liquidity: 24h volume / market cap from the same CoinGecko snapshot.
        m = market_rows.get(asset) or {}
        m_at = _aware(m.get("timestamp"))
        volume, cap = _num(m.get("volume_24h")), _num(m.get("market_cap"))
        if volume is None or cap is None or cap <= 0 or volume < 0:
            liq_m = _measured(None, m_at, "no 24h volume or market cap")
        elif m_at is None or now - m_at > MARKET_MAX_AGE:
            liq_m = _measured(None, m_at, f"market snapshot older than {MARKET_MAX_AGE.days} day")
        else:
            liq_m = _measured(volume / cap, m_at)

        # Market risk: 90-day maximum drawdown of daily closes.
        rows = get_prices_since(asset, now - timedelta(days=DRAWDOWN_DAYS))
        closes = daily_closes(rows)
        p_at = _aware(rows[-1][0]) if rows else None
        if len(closes) < MIN_DRAWDOWN_DAYS:
            dd_m = _measured(None, p_at, f"only {len(closes)} of {DRAWDOWN_DAYS} daily closes")
        elif p_at is None or now - p_at > PRICE_MAX_AGE:
            dd_m = _measured(None, p_at, f"last price older than {PRICE_MAX_AGE.days} days")
        else:
            dd_m = _measured(round(max_drawdown(closes), 6), p_at)

        out[asset] = {"volatility": vol_m, "liquidity": liq_m, "market_risk": dd_m}
    return out


def build_rows(inputs: dict, now: datetime) -> list[dict]:
    """One risk_breakdown row per asset: every metric with raw value, rank score, source, as_of and status."""
    scores = {
        metric: safety_scores({a: inputs[a][metric]["value"] for a in inputs}, riskier_when_higher)
        for metric, (_, _, _, riskier_when_higher) in METRICS.items()
    }
    ranked = {metric: sum(1 for s in per.values() if s is not None) for metric, per in scores.items()}
    rows = []
    for asset, measured in inputs.items():
        metrics = {}
        for metric, (label, raw_label, source, _) in METRICS.items():
            m = measured[metric]
            score = scores[metric][asset]
            metrics[metric] = {
                "label": label,
                "score": score,                         # 0-100, higher = safer; None when not available
                "raw": m["value"],
                "raw_label": raw_label,
                "source": source,
                "as_of": m["as_of"],
                "status": OK if score is not None else NOT_AVAILABLE,
                "why": m["why"] if score is None else None,
                "ranked_among": ranked[metric],
            }
        rows.append({"asset": asset, "timestamp": now, "source": SOURCE, "direction": "higher = safer",
                     "metrics": metrics})
    return rows


def refresh_risk_breakdowns(now: datetime | None = None, write: bool = True) -> dict:
    """Measures, ranks and (with write) stores today's breakdown for every covered coin. Returns the rows."""
    from db.queries import ML_COVERED_ASSETS, upsert_risk_breakdown

    now = now or datetime.now(timezone.utc)
    rows = build_rows(gather_inputs(sorted(ML_COVERED_ASSETS), now), now)
    if write:
        for row in rows:
            upsert_risk_breakdown(row)
    missing = {r["asset"]: [k for k, v in r["metrics"].items() if v["status"] != OK] for r in rows}
    return {"rows": rows, "not_available": {a: m for a, m in missing.items() if m}}


def run_after_ml_pull() -> None:
    """Called by the ML pull scheduler after each pull; one worker per CLAIM_GAP_SECONDS. Never raises."""
    from utils.scheduler_gate import claim_run
    try:
        if claim_run("risk-breakdown", CLAIM_GAP_SECONDS):
            out = refresh_risk_breakdowns()
            _log.info("[risk-breakdown] stored %d row(s); not available: %s", len(out["rows"]),
                      out["not_available"] or "none")
    except Exception as exc:
        from utils.http_errors import redact
        _log.error("[risk-breakdown] failed: %s: %s", type(exc).__name__, redact(exc))


if __name__ == "__main__":
    # Dry run: prints what would be stored, writes nothing.
    import json
    import sys
    write = "--write" in sys.argv
    result = refresh_risk_breakdowns(write=write)
    print(json.dumps([{**r, "timestamp": _iso(r["timestamp"])} for r in result["rows"]], indent=1))
    print("written" if write else "dry run: nothing written", "| not available:", result["not_available"] or "none")
