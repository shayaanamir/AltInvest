"""
backend/controllers/nft_pull.py

Daily pull of the ML service's NFT endpoints into the existing nft_* tables (ml/docs/DECISIONS.md D61, D67;
contract: ml/docs/CONTRACT_NFT.md). Called from controllers/ml_pull_controller.pull_all, so it runs at
startup and daily at 00:15 UTC with the same retry and timeout rules as /predict and /risk.

Per collection, all three calls (floor, risk, sales) must succeed and parse before anything is written for
it; otherwise nothing is written and the last good rows stay the newest.
  nft_collections     ML metadata; subcategory and banner_color are only set on insert (kept from the seed)
  nft_market_data     one row per (slug, date): floor in ETH and USD, change_24h / change_7d from the series
  nft_liquidity       one row per (slug, as_of): the D58 fields, sell_through_rate = sales_30d / supply
  nft_risk_breakdown  one row per (slug, as_of): volatility, risk_score, model_version, note
  nft_sales           wash-filtered sales of the last 30 days, upserted on (slug, tx, token, seller, buyer)
"""
import path_setup  # noqa: F401

from datetime import datetime, timezone

FLOOR_DAYS = 400
SALES_DAYS = 30
STATIC_DEFAULTS = {"subcategory": "PFP", "banner_color": "#1b1f2e"}


def _date_ts(date: str) -> datetime:
    return datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _pct(new, old):
    if not isinstance(new, (int, float)) or not isinstance(old, (int, float)) or not old:
        return None
    return round((new / old - 1) * 100, 4)


def market_rows(slug: str, floor: dict, latest: dict, now: datetime) -> list:
    """nft_market_data rows from /nft/{slug}/floor; the newest row also gets the 1-day volume and sales."""
    rows = floor.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("floor has no rows")
    by_date = {r["date"]: r.get("floor_eth") for r in rows}
    out = []
    for r in rows:
        d = _date_ts(r["date"])
        prev = by_date.get(datetime.fromtimestamp(d.timestamp() - 86400, tz=timezone.utc).strftime("%Y-%m-%d"))
        week = by_date.get(datetime.fromtimestamp(d.timestamp() - 7 * 86400, tz=timezone.utc).strftime("%Y-%m-%d"))
        out.append({"slug": slug, "date": r["date"], "timestamp": d, "floor_eth": r.get("floor_eth"),
                    "floor_usd": r.get("floor_usd"), "eth_usd": r.get("eth_usd"), "floor_source": r.get("floor_source"),
                    "floor_intraday_median_eth": r.get("floor_intraday_median_eth"),
                    "change_24h": _pct(r.get("floor_eth"), prev), "change_7d": _pct(r.get("floor_eth"), week),
                    "holders_count": None, "source": "ml-service", "pulled_at": now})
    out[-1].update({"volume_24h_eth": latest.get("volume_1d_eth"), "sales_24h": latest.get("sales_1d")})
    return out


def risk_rows(slug: str, risk: dict, supply, now: datetime) -> tuple[dict, dict]:
    """(nft_liquidity row, nft_risk_breakdown row) from /nft/{slug}/risk."""
    from controllers.ml_pull_controller import _parse_ts
    if risk.get("slug") != slug or not isinstance(risk.get("liquidity"), dict) or not risk.get("as_of"):
        raise ValueError("risk body is not for this collection or has no liquidity / as_of")
    ts = _parse_ts(risk["timestamp"])
    liq = risk["liquidity"]
    s30 = liq.get("sales_30d")
    common = {"slug": slug, "date": risk["as_of"], "timestamp": ts, "source": "ml-service", "pulled_at": now}
    liquidity = {**common, **liq,
                 "sell_through_rate": round(s30 / supply, 6) if isinstance(s30, (int, float)) and supply else None}
    breakdown = {**common, "floor_volatility_30d": risk.get("volatility"), "risk_score": risk.get("risk_score"),
                 "model_version": risk.get("model_version"), "note": risk.get("note"),
                 "holder_concentration": None, "liquidity_depth": None}
    return liquidity, breakdown


def sale_rows(slug: str, sales: dict, now: datetime) -> list:
    from controllers.ml_pull_controller import _parse_ts
    rows = sales.get("rows")
    if not isinstance(rows, list):
        raise ValueError("sales has no rows list")
    return [{"slug": slug, "token_id": str(r["token_id"]), "timestamp": _parse_ts(r["timestamp"]),
             "price_eth": r["price_eth"], "price_usd": r.get("price_usd"), "marketplace": r.get("marketplace"),
             "buyer": r.get("buyer") or "", "seller": r.get("seller") or "", "tx": r.get("tx") or "",
             "source": "ml-service", "pulled_at": now} for r in rows]


def pull_nft(client, fetch, sleep, now: datetime | None = None) -> dict:
    """{slug: outcome} for every collection ML lists, or {"collections": failure} if the list fails."""
    import db.queries as q

    now = now or datetime.now(timezone.utc)
    status, listing, reason = fetch(client, "/nft/collections", sleep=sleep)
    if status != "ok":
        return {"collections": f"{'skipped' if status == 'not_covered' else 'failed'}: {reason}; nothing written"}
    out = {}
    for c in listing.get("collections") or []:
        slug = c.get("slug")
        bodies = {}
        for name, path in (("floor", f"/nft/{slug}/floor?days={FLOOR_DAYS}"), ("risk", f"/nft/{slug}/risk"),
                           ("sales", f"/nft/{slug}/sales?days={SALES_DAYS}")):
            st, body, why = fetch(client, path, sleep=sleep)
            if st != "ok":
                bodies = None
                out[slug] = f"failed: {name} {why}; nothing written"
                break
            bodies[name] = body
        if bodies is None:
            continue
        try:
            supply = c.get("total_supply")
            market = market_rows(slug, bodies["floor"], c, now)
            liquidity, breakdown = risk_rows(slug, bodies["risk"], supply, now)
            sales = sale_rows(slug, bodies["sales"], now)
        except (KeyError, TypeError, ValueError) as exc:
            out[slug] = f"failed: bad body ({exc}); nothing written"
            continue
        meta = {k: v for k, v in {"name": c.get("name"), "symbol": c.get("symbol") or slug.upper(),
                                  "supply": supply, "verified": bool(c.get("verified")),
                                  "description": c.get("description"), "image_url": c.get("image_url"),
                                  "contract": c.get("contract")}.items() if v is not None}
        q.upsert_nft_collection_meta(slug, {**meta, "updated_at": now}, {**STATIC_DEFAULTS, "created_at": now})
        q.upsert_nft_market_rows(market)
        q.upsert_nft_liquidity_row(liquidity)
        q.upsert_nft_risk_row(breakdown)
        q.upsert_nft_sale_rows(sales)
        out[slug] = "stored"
    return out
