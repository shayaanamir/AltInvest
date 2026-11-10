"""Item-level sale cleaning for fair value (D70; C2 revised by D74, currency by D75). Pure functions, no I/O.

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
ATTRIBUTION_TOLERANCE = 1.01                 # D74: rows may sum to at most 1% more than the tx paid
NOT_FEATURES = ("sale_type", "payment_currency", "marketplace", "payment_symbol", "buyer", "seller", "tx",
                "protocol_address",
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
    """Original D70 C2, kept only so the frozen v2 snapshot stays reproducible (superseded by D74): a tx with >= 2 distinct tokens of one collection between the same seller and buyer."""
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


def payment_currency(symbol: pd.Series) -> pd.Series:
    """D75: ETH, WETH and BETH are the same currency, 1:1. NOT a model feature."""
    return symbol.map({"ETH": "ETH", "WETH": "ETH", "BETH": "ETH"})


def classify_multi_token(s: pd.DataFrame, all_rows: pd.DataFrame, payments: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """D74 (replaces C2): keep a multi-token group (one tx, seller, buyer, >= 2 tokens) when its prices are per-token,
    i.e. S <= 1.01 x P for its payment token, where P = what the transaction paid in that token (payments: tx, ok,
    value_eth, weth, beth) and S = the sum of ALL rows of that transaction (all_rows, every collection) in that token.
    Otherwise drop it as a true bundle / not attributable; a transaction without a payment record is dropped too."""
    key = ["slug", "tx", "seller", "buyer"]
    multi = (s.groupby(key)["token_id"].transform("nunique") >= 2).to_numpy()
    sums = all_rows.groupby(["tx", "payment_symbol"])["price_eth"].sum().rename("tx_rows_sum").reset_index()
    m = s.loc[multi, key + ["payment_symbol", "price_eth"]].reset_index()
    m = m.merge(sums, on=["tx", "payment_symbol"], how="left").merge(payments, on="tx", how="left")
    paid = np.select([m["payment_symbol"] == "ETH", m["payment_symbol"] == "WETH", m["payment_symbol"] == "BETH"],
                     [m["value_eth"], m["weth"], m["beth"]], np.nan).astype(float)
    ok = m["ok"].fillna(False).astype(bool).to_numpy()
    row_status = np.where(~ok, "rpc_missing", np.where(m["tx_rows_sum"].to_numpy() <= ATTRIBUTION_TOLERANCE * paid,
                                                        "attributable", "not_attributable"))
    m["status"] = row_status
    order = {"attributable": 0, "not_attributable": 1, "rpc_missing": 2}
    m["rank"] = m["status"].map(order)
    m["group_status"] = m.groupby(key)["rank"].transform("max").map({v: k for k, v in order.items()})
    drop_idx = m.loc[m["group_status"] != "attributable", "index"]
    counts = {}
    for status in order:
        sub = m[m["group_status"] == status]
        counts[f"C2_{status}_groups"] = int(sub[key].drop_duplicates().shape[0])
        counts[f"C2_{status}_rows"] = len(sub)
    return s.drop(index=drop_idx), counts


def clean(sales: pd.DataFrame, points: pd.DataFrame, payments: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """(rows after C1-C3 with floor_point_eth, wash_flag (''/W1/W2), clean, sale_type, payment_currency; counts per
    collection). With `payments` (v3), C2 is the D74 classification; without them, the original D70 C2 (v2)."""
    counts, collapsed = {}, {}
    for slug, g in sales.groupby("slug", sort=True):
        collapsed[slug], c1 = collapse_passthroughs(g)
        counts[slug] = {"before": len(g), **c1}
    all_rows = pd.concat(collapsed.values(), ignore_index=True)
    out = []
    for slug, g0 in collapsed.items():
        if payments is None:
            g1, n_b = drop_bundles(g0)
            counts[slug]["C2_bundle_rows_dropped"] = n_b
        else:
            g1, c2 = classify_multi_token(g0, all_rows, payments)
            counts[slug].update(c2)
        g2 = join_floor_point(g1, points)
        g3, n_c3 = drop_below_floor(g2)
        g3 = g3.sort_values(["slug", "token_id", "timestamp"]).reset_index(drop=True)
        w1 = (g3["buyer"] == g3["seller"]).to_numpy()
        w2 = return_flags(g3)
        g3["wash_flag"] = np.select([w1, w2], ["W1", "W2"], "")
        g3["clean"] = g3["wash_flag"] == ""
        g3["sale_type"] = sale_type(g3["payment_symbol"])
        if payments is not None:
            g3["payment_currency"] = payment_currency(g3["payment_symbol"])
        counts[slug].update({"C3_below_1pct_floor_dropped": n_c3, "W1_flagged": int(w1.sum()),
                             "W2_flagged": int((w2 & ~w1).sum()), "clean": int(g3["clean"].sum())})
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
