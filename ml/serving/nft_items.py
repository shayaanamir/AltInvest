"""Item value responses (Phase 10 step 10.7, D78). No FastAPI here.

For a token at request time t: features of a hypothetical sale at t (ml.nft.fv_serving, the training code),
then per collection (config.NFT_FV_SERVE): "model" -> the fitted fv_pooled_l1_nl15 artifact, "b2" -> the B2
baseline (the 90-day same-decile median premium, 0 with fewer than 5 sales). estimated_value_eth = the last floor
point before t x exp(predicted premium). ETH only, point estimate only: no range for any collection (D77), no
feature-importance drivers. Tokens with no earlier sale get the training's missing-value handling and
no_prior_sale = true. The accuracy note comes from the artifact metadata ('Accuracy check pending' until 10.9).
Tables are rebuilt only when a source file changes; serving refuses (503) if the live traits differ from the
ones the model was trained with (hashes in metadata.json).
"""

import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.data.serving_gate import NotServable
from ml.nft import fv_artifact, fv_serving, store
from ml.serving.responses import iso_utc

SOURCE_FILES = ("floor_points.csv", "sales_raw.csv", "tx_payments.csv", "traits_fill.csv", "tokens_fill.csv")
_CACHE: dict = {}


def _num(x, digits: int = 6):
    return None if x is None or not math.isfinite(float(x)) else round(float(x), digits)


def _signature() -> tuple:
    d = config.ML_NFT_DIR
    files = [d / f for f in SOURCE_FILES] + sorted((d / "traits").glob("*.csv")) + sorted((d / "tokens").glob("*.csv"))
    return (str(d),) + tuple(f.stat().st_mtime_ns if f.exists() else None for f in files)


def tables(now: datetime) -> dict:
    """{h, points, items, booster, meta}, cached on the source files' modification times."""
    sig = _signature()
    if _CACHE.get("sig") == sig:
        return _CACHE["tables"]
    d = config.ML_NFT_DIR
    if not (store.has_table(d, "sales_raw") and store.has_table(d, "floor_points") and store.has_table(d, "traits")):
        raise NotServable(f"NFT item data missing in {d}; run python -m ml.nft.refresh")
    try:
        booster, meta = fv_artifact.load()
    except (OSError, ImportError) as e:
        raise NotServable(f"fair-value model artifact unavailable: {type(e).__name__}") from None
    items = fv_serving.items(d)
    if fv_serving.trait_pairs_hash(items["traits"]) != meta["trait_pairs_sha256"] or \
            fv_serving.static_hash(items["static"]) != meta["static_sha256"]:
        raise NotServable("item traits differ from the ones the fair-value model was trained with")
    hist = fv_serving.history_asof(d, int(now.timestamp()))
    out = {"h": hist["h"], "points": hist["points"], "items": items, "booster": booster, "meta": meta}
    _CACHE.update(sig=sig, tables=out)
    return out


def _check(slug: str, token_id: str, items: dict) -> tuple[str, str]:
    s = slug.lower()
    if s not in config.NFT_SLUGS:
        raise KeyError(f"collection '{slug}' is not covered; covered: {list(config.NFT_SLUGS)}")
    tok = str(token_id)
    if not ((items["tokens"]["slug"] == s) & (items["tokens"]["token_id"] == tok)).any():
        raise KeyError(f"token '{tok}' not found in collection '{s}'")
    return s, tok


def values(pairs: list[tuple[str, str]], now: datetime) -> list[dict]:
    """One NftItemValue body per (slug, token_id), in order."""
    t = tables(now)
    ts = int(now.timestamp())
    pairs = [_check(s, k, t["items"]) for s, k in pairs]
    known = set(map(tuple, t["items"]["static"][["slug", "token_id"]].astype(str).to_numpy()))
    ok = [p for p in pairs if p in known]
    feats = fv_serving.query_features(t["h"], t["points"], t["items"]["static"], t["items"]["traits"], ok, ts) \
        if ok else None
    pred_model = fv_artifact.predict(t["booster"], t["meta"], feats) if ok else []
    by_pair = {p: i for i, p in enumerate(ok)}
    tokens = t["items"]["tokens"].set_index(["slug", "token_id"])
    out = []
    for slug, tok in pairs:
        info = tokens.loc[(slug, tok)]
        method = config.NFT_FV_SERVE[slug]
        floor = fv_serving.floor_before(t["points"], slug, ts)
        sale = fv_serving.last_sale(t["h"], slug, tok)
        i = by_pair.get((slug, tok))
        notes = []
        if i is None:
            y_hat, no_prior = None, sale is None
            notes.append("No trait data for this item, so no estimate.")
        else:
            row = feats.iloc[i]
            y_hat = float(pred_model[i]) if method == "model" else float(np.nan_to_num(row["decile_prem_med_90d"]))
            no_prior = bool(row["no_prior_sale"])
        if floor is None:
            y_hat = None
            notes.append("No floor price before now, so no estimate.")
        elif (ts - floor["time"]) / 3600 > config.STALE_DATA_HOURS:
            notes.append(f"data stale: last floor {iso_utc(datetime.fromtimestamp(floor['time'], tz=timezone.utc))}")
        if no_prior and i is not None:
            notes.append("This item has no earlier sale in the data, so the estimate leans on similar items.")
        rank = info.get("rarity_rank")
        out.append({
            "slug": slug, "token_id": tok,
            "estimated_value_eth": None if y_hat is None else _num(floor["floor_eth"] * math.exp(y_hat)),
            "method": "model" if method == "model" else "baseline_b2",
            "last_floor_eth": None if floor is None else _num(floor["floor_eth"]),
            "last_floor_time": None if floor is None else iso_utc(datetime.fromtimestamp(floor["time"], tz=timezone.utc)),
            "last_sale": None if sale is None else {
                "price_eth": _num(sale["price_eth"]),
                "timestamp": iso_utc(datetime.fromtimestamp(sale["timestamp"], tz=timezone.utc))},
            "no_prior_sale": bool(no_prior),
            "rarity_rank": None if pd.isna(rank) else int(rank),
            "rarity_ranked_tokens": int(t["items"]["tokens"].query("slug == @slug")["rarity_rank"].notna().sum()),
            "accuracy_note": t["meta"].get("accuracy_note") or config.NFT_FV_ACCURACY_NOTE,
            "model_version": t["meta"]["model_version"] if method == "model" else "nft-fv-baseline-b2",
            "note": " ".join(notes) or None, "as_of": iso_utc(now)})
    return out


def value(slug: str, token_id: str, now: datetime) -> dict:
    """NftItemValueResponse."""
    return {**values([(slug, token_id)], now)[0], "timestamp": iso_utc(now)}


def batch(items: str, now: datetime) -> dict:
    """NftItemValuesResponse for 'slug:token,slug:token,...' (at most config.NFT_FV_MAX_BATCH)."""
    pairs = [tuple(x.split(":", 1)) for x in items.split(",") if x.strip()]
    if not pairs or any(len(p) != 2 for p in pairs) or len(pairs) > config.NFT_FV_MAX_BATCH:
        raise ValueError(f"items must be 1-{config.NFT_FV_MAX_BATCH} entries 'slug:token_id', comma separated")
    return {"items": values([(s.strip(), k.strip()) for s, k in pairs], now), "timestamp": iso_utc(now)}
