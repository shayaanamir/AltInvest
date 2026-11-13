"""Leakage and forbidden-column checks for the fair-value features (Phase 10 step 10.6a, D76). No model is fitted.

    python -m ml.nft.fv_leakage          (writes ml/reports/nft/fv_leakage_check.json)

CHECK 1 (every feature, N_SAMPLE >= 2,000 clean development sales, seed 0): an independent per-sale reference
implementation is given ONLY the data cut at the sale timestamp (history rows and floor points with time < t, and
the static traits) and must reproduce the pipeline value (both null, or |difference| <= TOL).
CHECK 2 (N_PIPELINE sales of the same sample): the pipeline itself (fv_features.build) is re-run on that sale's
collection cut at t (later rows and other rows at the same timestamp removed) with the sale's own price
multiplied by 1000; its features for the sale must equal the full-data run.
CHECK 3: no forbidden column (fv_features.FORBIDDEN, the ID-like trait columns) reaches any model matrix of any
candidate, and fv_features.matrix refuses each of them.
"""

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ml import config
from ml.data.validate import ML_ROOT
from ml.evaluation import nft_fv_protocol as proto
from ml.gitinfo import git_metadata
from ml.models import nft_fair_value as fvm
from ml.nft import fv_features as fv
from ml.nft import item_data, snapshot
from ml.nft import traits as tr

REPORT = ML_ROOT / "reports" / "nft" / "fv_leakage_check.json"
N_SAMPLE = 2000
N_PIPELINE = 70
SEED = 0
TOL = 1e-9
DAY = fv.DAY


def prepare() -> dict:
    """Development data only (load_dev); H, the full-data feature frame and the static tables."""
    d = item_data.load_dev(include_flagged=True)
    h = fv.history(d["sales"])
    static, tcols = fv.static_features(d["tokens"], d["traits"])
    feats = fv.build(h, d["floor_points"], static, d["traits"])
    return {"dev": d, "h": h, "static": static, "trait_cols": tcols, "features": feats}


def static_reference(tokens: pd.DataFrame, traits: pd.DataFrame, slug: str, token: str) -> dict:
    """STATIC features of one token recomputed directly from the traits table (independent of the pipeline).
    `tokens` and `traits` may be pre-filtered to the collection."""
    keep = traits[(traits["slug"] == slug) & ~traits["id_like"]]
    known = tokens[(tokens["slug"] == slug) & tokens["rarity_score"].notna()]
    n = len(known)
    mine = dict(zip(keep.loc[keep["token_id"] == token, "trait_type"], keep.loc[keep["token_id"] == token, "value"]))
    shares, out = [], {}
    for c in sorted(keep["trait_type"].unique()):
        col = keep[(keep["trait_type"] == c) & keep["token_id"].isin(known["token_id"])]
        v = mine.get(c, tr.NONE)
        count = (col["value"] == v).sum() if v != tr.NONE else n - len(col)
        shares.append(count / n)
        values = sorted(set(col["value"]) | ({tr.NONE} if len(col) < n else set()))
        out[fv.trait_column(slug, c)] = float(values.index(v))
    row = known[known["token_id"] == token].iloc[0]
    return {**out, "collection": float(config.NFT_SLUGS.index(slug)), "rarity_score": float(row["rarity_score"]),
            "rarity_pct": float(row["rarity_pct"]), "n_traits": float(len(mine)),
            "trait_share_min": float(min(shares)), "trait_share_mean": float(np.mean(shares))}


def dynamic_reference(t: int, token: str, hist: pd.DataFrame, pts: pd.DataFrame, decile_of: dict,
                      pairs: list, members: dict) -> dict:
    """DYNAMIC features from cut data only: `hist` = the collection's H rows with timestamp < t, `pts` = its floor
    points with time < t (sorted)."""
    assert (hist["timestamp"] < t).all() and (pts["time"] < t).all()
    pt, pv = pts["time"].to_numpy(dtype=float), pts["token_unit"].to_numpy(dtype=float)

    def asof(s):
        sel = pt < s
        return (pv[sel][-1], pt[sel][-1]) if sel.any() else (np.nan, np.nan)
    f = {}
    f0, t0 = asof(t)
    f["floor_age_hours"] = (t - t0) / 3600
    for k in fv.FLOOR_RET_DAYS:
        f[f"floor_ret_{k}d"] = np.log(f0 / asof(t - k * DAY)[0])
    daily = np.array([asof(t - j * DAY)[0] for j in range(max(fv.FLOOR_VOL_DAYS) + 1)])
    r = np.log(daily[:-1] / daily[1:])
    for k in fv.FLOOR_VOL_DAYS:
        f[f"floor_vol_{k}d"] = float(np.std(r[:k], ddof=1))
    same = hist[hist["token_id"].to_numpy() == token]                    # all earlier sales of the token
    win = hist[hist["timestamp"].to_numpy() >= t - max(fv.DECILE_DAYS, fv.TRAIT_DAYS, *fv.COLL_MED_DAYS) * DAY]
    ts, prem, tok = win["timestamp"].to_numpy(), win["premium"].to_numpy(), win["token_id"].to_numpy()
    med = lambda sel: float(np.median(prem[sel])) if sel.sum() >= fv.MIN_ROWS else np.nan   # noqa: E731
    for k in fv.COUNT_DAYS:
        f[f"coll_sales_{k}d"] = float((ts >= t - k * DAY).sum())
    for k in fv.COLL_MED_DAYS:
        f[f"coll_prem_med_{k}d"] = med(ts >= t - k * DAY)
    w90 = ts >= t - fv.DECILE_DAYS * DAY
    dec = np.array([decile_of.get(x, np.nan) for x in tok])
    f["decile_prem_med_90d"] = med(w90 & (dec == decile_of[token]))
    tw = ts >= t - fv.TRAIT_DAYS * DAY
    has = lambda p: np.fromiter((x in members[p] for x in tok), bool, len(tok))   # noqa: E731
    kept = [m for m in (med(tw & has(p)) for p in pairs) if not np.isnan(m)]
    f.update({"trait_prem_max": max(kept) if kept else np.nan, "trait_prem_mean": float(np.mean(kept)) if kept else np.nan,
              "trait_prem_min": min(kept) if kept else np.nan, "trait_prem_n": float(len(kept))})
    if len(same):
        last = same[same["timestamp"] == same["timestamp"].max()].sort_values("hid").iloc[-1]
        f.update(prev_prem=last["premium"], prev_days=(t - last["timestamp"]) / DAY)
    else:
        f.update(prev_prem=np.nan, prev_days=np.nan)
    f["prev_n"] = float(len(same))
    when = datetime.fromtimestamp(t, tz=timezone.utc)
    f.update(dow=float(when.weekday()), hour=float(when.hour))
    return f


def _compare(a: dict, b: dict, cols: list[str]) -> dict:
    out = {}
    for c in cols:
        x, y = float(a[c]), float(b[c])
        both_nan = np.isnan(x) and np.isnan(y)
        diff = 0.0 if both_nan else abs(x - y)
        out[c] = (both_nan or diff <= TOL, diff, not np.isnan(x))
    return out


def _tally(results: list[dict], cols: list[str]) -> dict:
    return {c: {"n": len(results), "n_equal": int(sum(r[c][0] for r in results)),
                "n_non_null": int(sum(r[c][2] for r in results)),
                "max_abs_diff": float(np.nanmax([r[c][1] for r in results]))} for c in cols}


def check_reference(p: dict, sample: pd.DataFrame) -> dict:
    d, h, feats = p["dev"], p["h"], p["features"].set_index("hid")
    decile_of = {s: dict(zip(g["token_id"], g["rarity_decile"])) for s, g in p["static"].groupby("slug")}
    pairs_long = d["traits"][~d["traits"]["id_like"]]
    members = {k: set(g["token_id"]) for k, g in pairs_long.groupby(["slug", "trait_type", "value"])}
    pairs_of = {k: list(zip(g["trait_type"], g["value"])) for k, g in pairs_long.groupby(["slug", "token_id"])}
    by_slug = {s: g for s, g in h.groupby("slug")}
    pts = {s: g.sort_values("time") for s, g in d["floor_points"].groupby("slug")}
    stat_cols = fv.STATIC + [c for c in p["trait_cols"]]
    tok_by = {s: g for s, g in d["tokens"].groupby("slug")}
    trt_by = {s: g for s, g in d["traits"].groupby("slug")}
    res = []
    for q in sample.itertuples():
        hs, t = by_slug[q.slug], int(q.timestamp)
        ref = dynamic_reference(t, q.token_id, hs[hs["timestamp"] < t], pts[q.slug][pts[q.slug]["time"] < t],
                                decile_of[q.slug], [(q.slug, *x) for x in pairs_of.get((q.slug, q.token_id), [])],
                                members)
        ref.update(static_reference(tok_by[q.slug], trt_by[q.slug], q.slug, q.token_id))
        row = feats.loc[q.hid]
        own = [c for c in p["trait_cols"] if c.startswith(fv.trait_column(q.slug, ""))]
        res.append(_compare(ref, row, fv.DYNAMIC + fv.STATIC + own))
    per = _tally(res, fv.DYNAMIC + fv.STATIC)
    trait = [r for r in res]
    own_ok = sum(all(v[0] for k, v in r.items() if k.startswith("trait__")) for r in trait)
    per["trait__<slug>__<category> (all of the sale's own collection)"] = {"n": len(res), "n_equal": int(own_ok)}
    return {"n_sales": len(sample), "per_feature": per, "static_columns_checked": len(stat_cols)}


def check_pipeline(p: dict, sample: pd.DataFrame) -> dict:
    d, h, full = p["dev"], p["h"], p["features"].set_index("hid")
    cols = fv.DYNAMIC + fv.STATIC
    res = []
    for q in sample.itertuples():
        t = int(q.timestamp)
        cut = h[(h["slug"] == q.slug) & ((h["timestamp"] < t) | (h["hid"] == q.hid))].copy()
        cut.loc[cut["hid"] == q.hid, "premium"] += np.log(1000.0)          # the sale's own price x 1000
        pts = d["floor_points"][(d["floor_points"]["slug"] == q.slug) & (d["floor_points"]["time"] < t)]
        out = fv.build(cut, pts, p["static"], d["traits"]).set_index("hid")
        res.append(_compare(out.loc[q.hid], full.loc[q.hid], cols))
    return {"n_sales": len(sample), "per_feature": _tally(res, cols)}


def check_forbidden(p: dict) -> dict:
    id_like = p["dev"]["traits"].loc[p["dev"]["traits"]["id_like"]].groupby("slug")["trait_type"].unique()
    id_like = {s: list(v) for s, v in id_like.items()}
    banned = set(fv.FORBIDDEN) | {fv.trait_column(s, c) for s, cs in id_like.items() for c in cs}
    mats = {n: fvm.columns_for(n, s, p["trait_cols"]) for n in fvm.NAMES
            for s in ([None] if fvm.model_type(n) == "pooled" else config.NFT_SLUGS[:1])}
    per_coll = {s: fvm.columns_for("fv_percoll_l2_nl15", s, p["trait_cols"]) for s in config.NFT_SLUGS}
    leaks = sorted({c for cols in list(mats.values()) + list(per_coll.values()) for c in cols if c in banned})
    refused = []
    for c in sorted(banned):
        frame = p["features"].assign(**{c: 0.0}) if c not in p["features"] else p["features"]
        try:
            fv.matrix(frame, fv.feature_columns(p["trait_cols"]) + [c], id_like)
        except ValueError:
            refused.append(c)
    return {"banned_columns": sorted(banned), "id_like_categories": id_like, "leaks_into_any_matrix": leaks,
            "matrix_refuses_each_banned_column": len(refused) == len(banned), "n_refused": len(refused),
            "pooled_matrix_columns": len(fv.feature_columns(p["trait_cols"])),
            "per_collection_matrix_columns": {s: len(c) for s, c in per_coll.items()}}


def fold_table(feats: pd.DataFrame) -> list[dict]:
    clean = feats[feats["clean"]]
    rows = []
    for f in proto.folds():
        train, test = proto.fold_rows(clean, f)
        rows.append({"fold": f["fold"], "part": f["part"], "train_end_exclusive": str(f["train_end"].date()),
                     "embargo": [str(f["train_end"].date()), str(f["test_start"].date())],
                     "test": [str(f["test_start"].date()), str(f["test_end"].date())],
                     "n_train": int(train.sum()), "n_test": int(test.sum()),
                     "n_test_by_collection": clean[test].groupby("slug").size().astype(int).to_dict()})
    return rows


def main() -> None:
    git = git_metadata()
    p = prepare()
    clean = p["features"][p["features"]["clean"]]
    sample = clean.sample(n=N_SAMPLE, random_state=SEED)
    report = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git,
              "item_snapshot": config.NFT_ITEM_SNAPSHOT_V3, "item_manifest_sha256": item_data.require(),
              "base_manifest_sha256": snapshot.require_snapshot("floor_points", "eth_usd"),
              "dev_rows": {"history_H": len(p["h"]), "clean_targets": len(clean),
                           "last_date": str(p["h"]["date"].max()), "floor_points": len(p["dev"]["floor_points"])},
              "sample": {"n": N_SAMPLE, "seed": SEED, "by_collection": sample.groupby("slug").size().to_dict(),
                         "tolerance": TOL},
              "check1_reference_on_cut_data": check_reference(p, sample),
              "check2_pipeline_on_cut_data": check_pipeline(p, sample.head(N_PIPELINE)),
              "check3_forbidden_columns": check_forbidden(p), "folds": fold_table(p["features"])}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
