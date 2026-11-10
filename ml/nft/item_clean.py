"""Item-level sale cleaning for fair value (D70). Pure functions, no I/O.

Order: C1 collapse pass-throughs, C2 drop bundles, floor join, C3 drop price < 1% of the floor, then flags W1 and
W2. Dropped rows leave the table; flagged rows stay with wash_flag set. clean = not flagged. Every count is per
collection. sale_type is descriptive only: it is NOT a model feature (NOT_FEATURES lists every such column).
"""

import numpy as np
import pandas as pd

from ml import config

FLOOR_FRACTION_MIN = 0.01                   # C3
RETURN_WINDOW_DAYS = config.NFT_WASH_ROUNDTRIP_DAYS   # W2: 30 days
ID_LIKE_SHARE = 0.5                         # D70: distinct values > 50% of tokens
NOT_FEATURES = ("sale_type", "buyer", "seller", "tx", "marketplace", "payment_symbol", "protocol_address",
                "wash_flag", "clean")       # D70: never model inputs


def collapse_passthroughs(s: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """C1: one row per (slug, tx, token): the final buyer's leg. Ambiguous groups are dropped."""
    key = ["slug", "tx", "token_id"]
    size = s.groupby(key)["seller"].transform("size")
    single, multi = s[size == 1], s[size > 1]
    keep, ambiguous = [], 0
    for _, g in multi.groupby(key, sort=False):
        final = g[~g["buyer"].isin(set(g["seller"]))]
        if len(final) == 1:
            keep.append(final)
        else:
            ambiguous += len(g)
    out = pd.concat([single] + keep, ignore_index=True)
    return out, {"C1_rows_collapsed": int(len(multi) - sum(len(k) for k in keep) - ambiguous),
                 "C1_ambiguous_rows_dropped": int(ambiguous)}


def drop_bundles(s: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """C2: a tx with >= 2 distinct tokens of one collection between the same seller and buyer."""
    n = s.groupby(["slug", "tx", "seller", "buyer"])["token_id"].transform("nunique")
    return s[n < 2].copy(), int((n >= 2).sum())


def join_floor_point(s: pd.DataFrame, points: pd.DataFrame) -> pd.DataFrame:
    """floor_point_eth = the last floor point with time strictly BEFORE the sale timestamp, and its age in hours."""
    out = s.copy()
    out["floor_point_eth"], out["floor_point_age_hours"] = np.nan, np.nan
    for slug, idx in out.groupby("slug").groups.items():
        p = points[points["slug"] == slug].sort_values("time")
        t, v = p["time"].to_numpy(dtype=float), p["token_unit"].to_numpy(dtype=float)
        ts = out.loc[idx, "timestamp"].to_numpy(dtype=float)
        j = np.searchsorted(t, ts, side="left") - 1            # strictly before: equal times are not used
        ok = j >= 0
        out.loc[idx, "floor_point_eth"] = np.where(ok, v[np.clip(j, 0, None)], np.nan)
        out.loc[idx, "floor_point_age_hours"] = np.where(ok, (ts - t[np.clip(j, 0, None)]) / 3600, np.nan)
    return out


def drop_below_floor(s: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """C3: price below 1% of floor_point_eth, or no floor point before the sale."""
    bad = ~(s["price_eth"] >= FLOOR_FRACTION_MIN * s["floor_point_eth"])
    return s[~bad].copy(), int(bad.sum())


def return_flags(s: pd.DataFrame) -> np.ndarray:
    """W2: for a sale whose buyer X sold the same token at most 30 days earlier, flag every leg from X's sale up to
    and including X's purchase. `s` must be sorted by (slug, token_id, timestamp)."""
    flag = np.zeros(len(s), dtype=bool)
    win = RETURN_WINDOW_DAYS * 86400
    pos = 0
    for _, g in s.groupby(["slug", "token_id"], sort=False):
        n = len(g)
        if n > 1:
            sellers, buyers, ts = g["seller"].to_numpy(), g["buyer"].to_numpy(), g["timestamp"].to_numpy()
            for j in range(1, n):
                for i in range(j):
                    if sellers[i] == buyers[j] and ts[j] - ts[i] <= win:
                        flag[pos + i:pos + j + 1] = True
                        break
        pos += n
    return flag


def sale_type(symbol: pd.Series) -> pd.Series:
    """Descriptive only, NOT a model feature (D70): WETH (OpenSea offers) or BETH (Blur bids) -> bid_accept,
    ETH -> listing_fill. An inference from the payment token; the API gives no order side."""
    return symbol.map({"WETH": "bid_accept", "BETH": "bid_accept", "ETH": "listing_fill"}).fillna("unknown")


def clean(sales: pd.DataFrame, points: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """(rows after C1-C3 with floor_point_eth, wash_flag (''/W1/W2), clean, sale_type; counts per collection)."""
    counts, out = {}, []
    for slug, g in sales.groupby("slug", sort=True):
        g0, c1 = collapse_passthroughs(g)
        counts[slug] = {"before": len(g), **c1}
        g1, n_b = drop_bundles(g0)
        g2 = join_floor_point(g1, points)
        g3, n_c3 = drop_below_floor(g2)
        g3 = g3.sort_values(["slug", "token_id", "timestamp"]).reset_index(drop=True)
        w1 = (g3["buyer"] == g3["seller"]).to_numpy()
        w2 = return_flags(g3)
        g3["wash_flag"] = np.select([w1, w2], ["W1", "W2"], "")
        g3["clean"] = g3["wash_flag"] == ""
        g3["sale_type"] = sale_type(g3["payment_symbol"])
        counts[slug].update({"C2_bundle_rows_dropped": n_b, "C3_below_1pct_floor_dropped": n_c3,
                             "W1_flagged": int(w1.sum()), "W2_flagged": int((w2 & ~w1).sum()),
                             "clean": int(g3["clean"].sum())})
        out.append(g3)
    rows = pd.concat(out, ignore_index=True).sort_values(["slug", "timestamp", "tx", "token_id"])
    return rows.reset_index(drop=True), counts


def id_like_categories(tokens: pd.DataFrame, traits: pd.DataFrame) -> dict:
    """{slug: [categories with distinct values > 50% of the collection's tokens]} (D70)."""
    out = {}
    for slug, tr in traits.groupby("slug"):
        n_tokens = int((tokens["slug"] == slug).sum())
        nun = tr.groupby("trait_type")["value"].nunique()
        out[slug] = sorted(nun[nun > ID_LIKE_SHARE * n_tokens].index.tolist())
    return out
