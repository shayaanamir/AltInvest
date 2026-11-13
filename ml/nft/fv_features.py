"""Fair-value features (Phase 10 step 10.6a, D76): every column with its as-of definition. Pure functions, no I/O.

Notation. t = the sale's timestamp (Unix seconds, UTC). HISTORY H = the development rows of the v3 item snapshot
(ml.nft.item_data.load_dev(include_flagged=True): C1-C3 applied, dated before 2026-01-25) WITHOUT the W1 rows
(buyer == seller, known at the sale). W2-flagged rows STAY in H: W2 is decided with up to 30 days of look-ahead,
so at time t a later-flagged sale looked like any other sale. The `clean` flag is never a feature.
Which rows are training or test targets ('clean') is recomputed by clean_as_of(cutoff) from sales before the
cutoff only (D76 amended): never the snapshot's stored flags, whose W2 used sales after 2026-01-24.
premium(sale) = log(price_eth / floor_point_eth), floor_point_eth = the last OpenSea floor point strictly before
that sale (D70). The target y of a clean row is its premium. A window [t - w days, t) is strictly before t:
rows at timestamp t (the same transaction or the same block) never enter it. Points: the base snapshot's floor
points with time < 2026-01-25 (load_dev); floor_asof(s) = token_unit of the last point with time < s.

STATIC (traits are static metadata revealed before the sales window, D60; per collection over its tokens with
known traits; ID-like categories (traits.id_like, D70: milady Number) excluded everywhere):
  collection          code of the slug in config.NFT_SLUGS (categorical)
  rarity_score        sum over categories of -log(share of the token's value), 'none' counted as a value (v3)
  rarity_pct          rarity_rank / tokens ranked x 100 (rank 1 = rarest, v3)
  n_traits            categories where the token has a value other than 'none'
  trait_share_min     min over categories of the share of supply of the token's value ('none' included)
  trait_share_mean    mean of the same shares
  trait__<slug>__<category>   code of the token's value ('none' is a value) in that category (categorical);
                      null for rows of other collections
FLOOR (points with time < t):
  floor_age_hours     (t - time of the last point before t) / 3600
  floor_ret_{1,7,30}d log(floor_asof(t) / floor_asof(t - k days))
  floor_vol_{7,30}d   std (ddof 1) of r_j = log(floor_asof(t - j days) / floor_asof(t - (j + 1) days)), j < k
TRAILING SALES (rows of H in the same collection, inside [t - w, t)):
  coll_sales_{1,7}d   count
  coll_prem_med_{7,30}d   median premium, null with fewer than 5 rows
  decile_prem_med_90d median premium of rows whose token is in the same rarity decile, null with < 5 rows
  trait_prem_{max,mean,min}, trait_prem_n   for each of the token's (category, value) pairs (not 'none', not
                      ID-like): the median premium over 90 days of rows whose token has that pair, kept with >= 5
                      rows; max / mean / min over the kept pairs and their number (null / 0 when none is kept)
SAME TOKEN (rows of H of the same token with timestamp < t):
  prev_prem, prev_days    premium of the latest one and (t - its timestamp) / 86400 (ties: the last in H order)
  prev_n              how many there are
CALENDAR: dow (0 = Monday), hour (UTC) of t.
"""

import re

import numpy as np
import pandas as pd

from ml import config
from ml.nft import item_clean as ic
from ml.nft import traits as tr

DAY = 86400
MIN_ROWS = 5
FLOOR_RET_DAYS = (1, 7, 30)
FLOOR_VOL_DAYS = (7, 30)
COUNT_DAYS = (1, 7)
COLL_MED_DAYS = (7, 30)
DECILE_DAYS = 90
TRAIT_DAYS = 90

STATIC = ["collection", "rarity_score", "rarity_pct", "n_traits", "trait_share_min", "trait_share_mean"]
FLOOR = (["floor_age_hours"] + [f"floor_ret_{k}d" for k in FLOOR_RET_DAYS] + [f"floor_vol_{k}d" for k in FLOOR_VOL_DAYS])
TRAILING = ([f"coll_sales_{k}d" for k in COUNT_DAYS] + [f"coll_prem_med_{k}d" for k in COLL_MED_DAYS]
            + ["decile_prem_med_90d", "trait_prem_max", "trait_prem_mean", "trait_prem_min", "trait_prem_n"])
TOKEN = ["prev_prem", "prev_days", "prev_n"]
CALENDAR = ["dow", "hour"]
DYNAMIC = FLOOR + TRAILING + TOKEN + CALENDAR
# Never in a model matrix (user rule 10.6a and D70/D75): descriptive, identifying, same-transaction or label columns
FORBIDDEN = tuple(ic.NOT_FEATURES) + ("token_id", "name", "image_url", "price_eth", "price_usd", "eth_usd", "premium",
                                      "y", "timestamp", "date", "ts", "hid", "floor_point_eth", "rarity_rank",
                                      "rarity_decile", "slug")


def _safe(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "_", s)


def trait_column(slug: str, category: str) -> str:
    return f"trait__{_safe(slug)}__{_safe(category)}"


def static_features(tokens: pd.DataFrame, traits: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """(one row per token with known traits: slug, token_id, rarity_decile and the STATIC + trait columns,
    the trait column names). rarity_decile = ceil(10 x rarity_rank / tokens ranked), 1 = rarest 10% (B1, D76)."""
    keep = traits[~traits["id_like"]]
    known = tokens[tokens["rarity_score"].notna()]
    parts, tcols = [], []
    for code, slug in enumerate(config.NFT_SLUGS):
        tk = known[known["slug"] == slug]
        if tk.empty:
            continue
        m = tr.trait_matrix(tk, keep[keep["slug"] == slug])
        sh = tr.shares(m)
        r = tk.set_index("token_id").loc[m.index]
        df = pd.DataFrame({"slug": slug, "token_id": m.index.to_numpy(), "collection": float(code),
                           "rarity_score": r["rarity_score"].to_numpy(dtype=float),
                           "rarity_pct": r["rarity_pct"].to_numpy(dtype=float),
                           "n_traits": (m != tr.NONE).sum(axis=1).to_numpy(dtype=float),
                           "trait_share_min": sh.min(axis=1).to_numpy(), "trait_share_mean": sh.mean(axis=1).to_numpy(),
                           "rarity_decile": np.clip(np.ceil(10 * r["rarity_rank"].to_numpy(dtype=float) / len(tk)), 1, 10)})
        for c in sorted(m.columns):
            name = trait_column(slug, c)
            codes = {v: float(i) for i, v in enumerate(sorted(m[c].unique()))}
            df[name] = m[c].map(codes).to_numpy(dtype=float)
            tcols.append(name)
        parts.append(df)
    if len(set(tcols)) != len(tcols):
        raise ValueError("trait column names collide after sanitising")
    return pd.concat(parts, ignore_index=True), tcols


def history(sales: pd.DataFrame) -> pd.DataFrame:
    """H: development rows without W1 (buyer == seller), sorted (slug, timestamp, tx, token_id), with hid (row id),
    ts and premium. The snapshot's stored wash_flag / clean are NOT carried (their W2 used later sales, D76 amended)."""
    w1 = sales["buyer"] == sales["seller"]
    h = sales[~w1].sort_values(["slug", "timestamp", "tx", "token_id"]).reset_index(drop=True)
    h = h[["slug", "token_id", "timestamp", "date", "tx", "price_eth", "floor_point_eth"]].copy()
    h["hid"] = np.arange(len(h))
    h["ts"] = pd.to_datetime(h["timestamp"], unit="s")
    h["premium"] = np.log(h["price_eth"] / h["floor_point_eth"])
    return h


def clean_as_of(sales: pd.DataFrame, cutoff: int) -> pd.DataFrame:
    """(slug, tx, token_id, clean) for the rows with timestamp < cutoff, with W1 (buyer == seller) and W2
    (item_clean.return_flags) computed from THOSE rows only, so no flag depends on a sale at or after the cutoff
    (D76 amended). `sales` = development rows after C1-C3 (load_dev(include_flagged=True))."""
    s = sales[sales["timestamp"] < cutoff].sort_values(["slug", "token_id", "timestamp", "tx"], kind="stable")
    s = s.reset_index(drop=True)
    w1 = (s["buyer"] == s["seller"]).to_numpy()
    w2 = ic.return_flags(s)
    return s[["slug", "tx", "token_id"]].assign(clean=~w1 & ~w2)


def clean_mask(frame: pd.DataFrame, sales: pd.DataFrame, cutoff: int) -> np.ndarray:
    """Per row of `frame` (slug, tx, token_id): clean as of `cutoff` (False for rows at or after the cutoff)."""
    c = clean_as_of(sales, cutoff)
    if c.duplicated(["slug", "tx", "token_id"]).any():
        raise ValueError("(slug, tx, token_id) is not unique")
    m = frame[["slug", "tx", "token_id"]].merge(c, on=["slug", "tx", "token_id"], how="left")
    return m["clean"].eq(True).to_numpy(dtype=bool)


def _rolling(df: pd.DataFrame, keys: list[str], days: int, stat: str) -> np.ndarray:
    """Per group of `keys` (df sorted by keys then ts): count, or median with >= MIN_ROWS, of premium in [t - days, t)."""
    vals = pd.Series(df["premium"].to_numpy(), index=pd.DatetimeIndex(df["ts"]))
    out = np.full(len(df), np.nan)
    for pos in df.groupby(keys, sort=False).indices.values():
        roll = vals.iloc[pos].rolling(f"{days}D", closed="left", min_periods=0 if stat == "count" else MIN_ROWS)
        out[pos] = (roll.count() if stat == "count" else roll.median()).to_numpy()
    return out


def _floor(h: pd.DataFrame, points: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=h.index, columns=FLOOR, dtype=float)
    for slug, idx in h.groupby("slug").groups.items():
        p = points[points["slug"] == slug].sort_values("time")
        pt, pv = p["time"].to_numpy(dtype=float), p["token_unit"].to_numpy(dtype=float)
        t = h.loc[idx, "timestamp"].to_numpy(dtype=float)

        def asof(s):
            j = np.searchsorted(pt, s, side="left") - 1                  # strictly before s
            return np.where(j >= 0, pv[np.clip(j, 0, None)], np.nan), np.where(j >= 0, pt[np.clip(j, 0, None)], np.nan)
        f0, t0 = asof(t)
        out.loc[idx, "floor_age_hours"] = (t - t0) / 3600
        for k in FLOOR_RET_DAYS:
            out.loc[idx, f"floor_ret_{k}d"] = np.log(f0 / asof(t - k * DAY)[0])
        daily = np.column_stack([asof(t - j * DAY)[0] for j in range(max(FLOOR_VOL_DAYS) + 1)])
        rets = np.log(daily[:, :-1] / daily[:, 1:])                       # r_j, j = 0 .. 29
        for k in FLOOR_VOL_DAYS:
            out.loc[idx, f"floor_vol_{k}d"] = np.std(rets[:, :k], axis=1, ddof=1)
    return out


def _trait_premia(h: pd.DataFrame, traits: pd.DataFrame) -> pd.DataFrame:
    pairs = traits.loc[~traits["id_like"], ["slug", "token_id", "trait_type", "value"]]
    ex = h[["hid", "slug", "token_id", "ts", "premium"]].merge(pairs, on=["slug", "token_id"])
    ex = ex.sort_values(["slug", "trait_type", "value", "ts", "hid"]).reset_index(drop=True)
    ex["tp"] = _rolling(ex, ["slug", "trait_type", "value"], TRAIT_DAYS, "median")
    g = ex.groupby("hid")["tp"]
    agg = pd.DataFrame({"trait_prem_max": g.max(), "trait_prem_mean": g.mean(), "trait_prem_min": g.min(),
                        "trait_prem_n": g.count().astype(float)})
    return agg.reindex(h["hid"]).fillna({"trait_prem_n": 0.0}).reset_index(drop=True)


def _previous(h: pd.DataFrame) -> pd.DataFrame:
    left = h[["hid", "slug", "token_id", "timestamp"]].sort_values(["timestamp", "hid"])
    right = (h[["slug", "token_id", "timestamp", "hid", "premium"]]
             .rename(columns={"timestamp": "prev_ts", "hid": "prev_hid", "premium": "prev_prem"})
             .sort_values(["prev_ts", "prev_hid"]))
    m = pd.merge_asof(left, right, left_on="timestamp", right_on="prev_ts", by=["slug", "token_id"],
                      allow_exact_matches=False, direction="backward").set_index("hid").reindex(h["hid"])
    prev_n = h.groupby(["slug", "token_id"])["timestamp"].rank(method="min") - 1
    return pd.DataFrame({"prev_prem": m["prev_prem"].to_numpy(),
                         "prev_days": (m["timestamp"] - m["prev_ts"]).to_numpy() / DAY,
                         "prev_n": prev_n.to_numpy(dtype=float)})


def build(h: pd.DataFrame, points: pd.DataFrame, static: pd.DataFrame, traits: pd.DataFrame) -> pd.DataFrame:
    """Features for EVERY row of H (index = hid order), plus hid, slug, token_id, tx, date, timestamp, premium and
    rarity_decile (identifiers and the label; never in a model matrix). Which rows are clean is decided per cutoff
    by clean_as_of."""
    h = h.merge(static[["slug", "token_id", "rarity_decile"]], on=["slug", "token_id"], how="left")
    out = h[["hid", "slug", "token_id", "tx", "date", "timestamp", "premium", "rarity_decile"]].copy()
    for k in COUNT_DAYS:
        out[f"coll_sales_{k}d"] = _rolling(h, ["slug"], k, "count")
    for k in COLL_MED_DAYS:
        out[f"coll_prem_med_{k}d"] = _rolling(h, ["slug"], k, "median")
    hd = h.sort_values(["slug", "rarity_decile", "ts", "hid"])
    out.loc[hd.index, "decile_prem_med_90d"] = _rolling(hd, ["slug", "rarity_decile"], DECILE_DAYS, "median")
    out = pd.concat([out, _floor(h, points), _trait_premia(h, traits), _previous(h)], axis=1)
    out["dow"] = h["ts"].dt.dayofweek.astype(float)
    out["hour"] = h["ts"].dt.hour.astype(float)
    static_cols = [c for c in static.columns if c not in ("rarity_decile",)]
    return out.merge(static[static_cols], on=["slug", "token_id"], how="left")


def feature_columns(trait_cols: list[str]) -> list[str]:
    return STATIC + list(trait_cols) + DYNAMIC


def matrix(frame: pd.DataFrame, columns: list[str], id_like: dict) -> pd.DataFrame:
    """The model matrix: exactly `columns`, refusing any forbidden or ID-like trait column (user rule 10.6a)."""
    banned = set(FORBIDDEN) | {trait_column(s, c) for s, cs in id_like.items() for c in cs}
    bad = [c for c in columns if c in banned or c.lower() in banned]
    if bad:
        raise ValueError(f"forbidden columns in the model matrix: {bad}")
    allowed = set(STATIC) | set(DYNAMIC) | {c for c in columns if c.startswith("trait__")}
    if set(columns) - allowed:
        raise ValueError(f"columns outside the declared feature list: {sorted(set(columns) - allowed)}")
    return frame[columns].astype(float)
