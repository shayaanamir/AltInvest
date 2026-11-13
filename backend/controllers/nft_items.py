"""
backend/controllers/nft_items.py

Fair-value item values from the ML service (Phase 10 step 10.7, ml/docs/DECISIONS.md D78; contract
ml/docs/CONTRACT_NFT.md NftItemValueResponse / NftItemValuesResponse). ETH only, point estimate only: no range,
no drivers, no USD conversion of the estimate.
  pull_item_values   daily (from ml_pull_controller.pull_all): every NFT portfolio holding's token, in batches
                     of 50, upserted into nft_item_values on (slug, token_id); a failed batch writes nothing.
  live_item_value    the collection page's item lookup: one live call; stored on success. On failure the last
                     stored row is returned with stale = true, or nothing.
"""
import path_setup  # noqa: F401

from datetime import datetime, timezone

BATCH = 50
ITEM_TIMEOUT_SECONDS = 60.0         # the ML service builds its item history once per data refresh
FIELDS = ("estimated_value_eth", "method", "last_floor_eth", "last_floor_time", "last_sale", "no_prior_sale",
          "rarity_rank", "rarity_ranked_tokens", "accuracy_note", "model_version", "note", "as_of")


def item_row(body: dict, now: datetime) -> dict:
    """An ML item body as a Mongo row; raises ValueError if it can't be stored."""
    from controllers.ml_pull_controller import _parse_ts
    missing = [k for k in ("slug", "token_id") + FIELDS if k not in body]
    if missing:
        raise ValueError(f"missing fields {missing}")
    v = body["estimated_value_eth"]
    if v is not None and (not isinstance(v, (int, float)) or v <= 0):
        raise ValueError("estimated_value_eth is not a positive number or null")
    return {"slug": body["slug"], "token_id": str(body["token_id"]), **{k: body[k] for k in FIELDS},
            "as_of_ts": _parse_ts(body["as_of"]), "source": "ml-service", "pulled_at": now}


def pull_item_values(client, fetch, sleep, now: datetime | None = None, tokens: list | None = None) -> dict:
    """{batch: outcome}. Never raises for HTTP errors."""
    import db.queries as q
    now = now or datetime.now(timezone.utc)
    tokens = q.get_nft_holding_tokens() if tokens is None else tokens
    if not tokens:
        return {"items": "no NFT holdings; nothing to pull"}
    out = {}
    for i in range(0, len(tokens), BATCH):
        chunk = tokens[i:i + BATCH]
        key = f"batch {i // BATCH + 1}"
        st, body, why = fetch(client, "/nft/items/value?items=" + ",".join(f"{s}:{t}" for s, t in chunk), sleep=sleep,
                              timeout=ITEM_TIMEOUT_SECONDS)
        if st != "ok":
            out[key] = f"failed: {why}; nothing written"
            continue
        try:
            rows = [item_row(b, now) for b in body.get("items") or []]
            if len(rows) != len(chunk):
                raise ValueError(f"asked for {len(chunk)} items, got {len(rows)}")
        except (KeyError, TypeError, ValueError) as exc:
            out[key] = f"failed: bad body ({exc}); nothing written"
            continue
        for r in rows:
            q.upsert_nft_item_value(r)
        out[key] = f"stored {len(rows)}"
    return out


def live_item_value(client, fetch, slug: str, token_id: str, now: datetime | None = None) -> tuple[str, dict | None]:
    """("ok" | "stale" | "not_found" | "failed", row). One live call, then the stored row as a fallback."""
    import db.queries as q
    now = now or datetime.now(timezone.utc)
    st, body, why = fetch(client, f"/nft/{slug}/items/{token_id}/value", sleep=lambda s: None,
                          timeout=ITEM_TIMEOUT_SECONDS, retries=0)
    if st == "not_covered":
        return "not_found", None
    if st == "ok":
        try:
            row = item_row(body, now)
            q.upsert_nft_item_value(row)
            return "ok", row
        except (KeyError, TypeError, ValueError):
            pass
    stored = q.get_nft_item_value(slug, token_id)
    return ("stale", stored) if stored else ("failed", None)
