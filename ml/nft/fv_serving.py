"""Request-time fair-value inputs (Phase 10 step 10.7, D78): the SAME code as training, as of a time t.

history_asof(directory, t): the feature history H as it was at t. Raw sales and floor points with time < t are
read from a data directory (the live/serving ML_NFT_DIR) and cut immediately; then exactly the training cleaning
runs: dedupe (sales.dedupe, as the snapshot did), C1 pass-throughs, C2 multi-token rule with the stored transaction
payments (D74; a transaction without a payment record is dropped, as in v3), the floor point strictly before each
sale, C3 (< 1% of the floor point), and W1 rows removed (fv_features.history). No W2 (it is never a feature).
items(directory): traits and tokens with the D68 fills, ID-like categories marked and rarity over known tokens,
exactly as the v3 item snapshot (item_data._items).
query_features(...): fv_features.build run on H plus one hypothetical sale per queried token at t (premium unknown),
restricted to the rows that can enter the queried rows' features (every window is <= 90 days, so rows with time
>= t - 91 days, plus every earlier row of the queried tokens for prev_*). Tested to equal the training pipeline's
features for a hypothetical sale at t (ml/tests/test_nft_fv_serving.py).
"""

from pathlib import Path

import numpy as np
import pandas as pd

from ml.nft import fv_features as fv
from ml.nft import item_clean as ic
from ml.nft import item_data, item_snapshot, sales as sl, store

DAY = fv.DAY
SUBSET_DAYS = 91


def _payments(directory: Path) -> pd.DataFrame:
    path = Path(directory) / "tx_payments.csv"
    pay = store.read_csv(path) if path.exists() else pd.DataFrame(columns=["tx", "ok", "value_eth", "weth", "beth"])
    pay = pay.drop_duplicates("tx", keep="last").copy()
    pay["ok"] = pay["ok"].astype(str).str.lower().isin(("true", "1"))
    return pay


def clean_rows(raw: pd.DataFrame, points: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
    """C1-C3 exactly as item_clean.clean (the v3 rule), without the W1/W2 flags."""
    collapsed = {slug: ic.collapse_passthroughs(g)[0] for slug, g in raw.groupby("slug", sort=True)}
    all_rows = pd.concat(collapsed.values(), ignore_index=True)
    out = []
    for slug, g0 in collapsed.items():
        g1, _ = ic.classify_multi_token(g0, all_rows, payments)
        g3, _ = ic.drop_below_floor(ic.join_floor_point(g1, points))
        out.append(g3)
    return pd.concat(out, ignore_index=True)


def history_asof(directory: Path, t: int) -> dict:
    """{h, points, rows}: the feature history and floor points known at Unix time t (everything at or after t
    is dropped right after reading)."""
    d = Path(directory)
    points = store.read_table(d, "floor_points")
    points = points[points["time"] < t].reset_index(drop=True)
    raw = store.read_table(d, "sales_raw")
    raw = raw[raw["timestamp"] < t]
    raw = sl.dedupe(raw)[sl.SALE_COLUMNS]
    rows = clean_rows(raw, points, _payments(d))
    return {"h": fv.history(rows), "points": points, "rows": rows}


def items(directory: Path) -> dict:
    """{tokens, traits, static, trait_cols} from a data directory, with the D68 fills (as the v3 item snapshot)."""
    d = Path(directory)
    base_tokens, base_traits = store.read_table(d, "tokens"), store.read_table(d, "traits")
    fill_tok = d / item_snapshot.FILL_TOKENS
    fill_trt = d / item_snapshot.FILL_TRAITS
    ftok = store.read_csv(fill_tok) if fill_tok.exists() else base_tokens.iloc[0:0]
    ftrt = store.read_csv(fill_trt) if fill_trt.exists() else base_traits.iloc[0:0]
    traits, tokens = item_snapshot.merge(base_tokens, base_traits, ftok, ftrt)
    traits, tokens, _ = item_data._items(tokens, traits)
    static, tcols = fv.static_features(tokens, traits)
    return {"tokens": tokens, "traits": traits, "static": static, "trait_cols": tcols}


def query_features(h: pd.DataFrame, points: pd.DataFrame, static: pd.DataFrame, traits: pd.DataFrame,
                   queries: list[tuple[str, str]], t: int) -> pd.DataFrame:
    """Features of a hypothetical sale of each (slug, token_id) at Unix time t, one row per query (same order),
    with no_prior_sale = the token has no earlier sale in H."""
    h = h[h["timestamp"] < t]
    p = points[points["time"] < t]
    q = pd.DataFrame(queries, columns=["slug", "token_id"]).astype(str)
    keep = (h["timestamp"] >= t - SUBSET_DAYS * DAY) | h.set_index(["slug", "token_id"]).index.isin(
        list(map(tuple, q.to_numpy())))
    sub = h.loc[keep & h["slug"].isin(q["slug"]).to_numpy(), ["slug", "token_id", "timestamp", "date", "tx",
                                                               "premium"]]
    date = pd.Timestamp(t, unit="s", tz="UTC").strftime("%Y-%m-%d")
    pseudo = q.assign(timestamp=t, date=date, tx=[f"~query-{i}" for i in range(len(q))], premium=np.nan)
    frame = pd.concat([sub, pseudo], ignore_index=True).sort_values(["slug", "timestamp", "tx", "token_id"],
                                                                     kind="stable").reset_index(drop=True)
    frame["hid"] = np.arange(len(frame))
    frame["ts"] = pd.to_datetime(frame["timestamp"], unit="s")
    out = fv.build(frame, p, static, traits)
    out = out[out["tx"].str.startswith("~query-")].copy()
    out["query"] = out["tx"].str.slice(len("~query-")).astype(int)
    out = out.sort_values("query").reset_index(drop=True)
    out["no_prior_sale"] = out["prev_n"].to_numpy() == 0
    return out


def last_sale(h: pd.DataFrame, slug: str, token_id: str) -> dict | None:
    """The token's latest sale in H (W1 excluded), or None."""
    g = h[(h["slug"] == slug) & (h["token_id"] == str(token_id))]
    if g.empty:
        return None
    r = g.sort_values(["timestamp", "hid"]).iloc[-1]
    return {"price_eth": float(r["price_eth"]), "timestamp": int(r["timestamp"]), "date": r["date"]}


def floor_before(points: pd.DataFrame, slug: str, t: int) -> dict | None:
    """The last OpenSea floor point strictly before t (the floor the premium is relative to, D70)."""
    p = points[(points["slug"] == slug) & (points["time"] < t)]
    if p.empty:
        return None
    r = p.sort_values("time").iloc[-1]
    return {"floor_eth": float(r["token_unit"]), "time": float(r["time"])}


def trait_pairs_hash(traits: pd.DataFrame) -> str:
    """Hash of the non-ID-like (slug, token_id, trait_type, value) rows, order-free: serving refuses to use a model
    when the live traits differ from the ones it was trained with."""
    import hashlib
    t = traits.loc[~traits["id_like"], ["slug", "token_id", "trait_type", "value"]].astype(str)
    t = t.sort_values(list(t.columns)).to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def static_hash(static: pd.DataFrame) -> str:
    import hashlib
    s = static.sort_values(["slug", "token_id"]).reset_index(drop=True)
    s = s[sorted(s.columns)].round(10).to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
