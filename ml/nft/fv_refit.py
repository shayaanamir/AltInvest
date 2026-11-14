"""Serving refits of the fair-value model (Phase 10 step 10.9, D83). Runs where the live data is (the ML image).

    python -m ml.nft.fv_refit --refit [--date YYYY-MM-DD]     refit now (or as of a refit date), serve it
    python -m ml.nft.fv_refit --sanity                         refit vs development model on a fixed token sample
    python -m ml.nft.fv_refit --accuracy                       (host) write accuracy.json from the 10.8 report

PROCEDURE (exactly the D79 monthly refit, used for every serving refit): refit date R (a UTC date), cutoff
C = R 00:00 UTC - 7 days. The feature history is rebuilt from the live data directory (config.ML_NFT_DIR) with the
request-time code (ml.nft.fv_serving.history_asof: dedupe, C1-C3, W1 removed), cut at C; the training rows are
all sales before C that are clean as of C (W1/W2 decided from sales before C only, fv_features.clean_mask).
fv_pooled_l1_nl15 is fitted with its declared parameters (ml/models/nft_fair_value.py); B2 has no fitted
parameters (its premium is computed from the history at request time), so nothing is refitted for lilpudgys.
GUARD: the parameters, the number of rounds and the feature columns must equal those of the development artifact
(D76/D78); otherwise the refit refuses and the served model stays. No hyperparameter or feature changes outside a
declared phase.

LAYOUT (config.NFT_FV_ARTIFACT_DIR): the development artifact (D78) stays at the top level; each refit is written to
refits/<R>/ (model.txt + metadata.json, written to a temporary folder first and renamed), then the pointer file
CURRENT (relative folder) is replaced atomically, and one line is appended to refit_log.jsonl (date, cutoff, rows,
artifact hash). Serving follows CURRENT (fv_artifact.load).
"""

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ml import config
from ml.models import nft_fair_value as fvm
from ml.nft import fv_artifact, fv_serving
from ml.nft import fv_features as fv

EMBARGO_DAYS = 7
REFITS = "refits"
LOG = "refit_log.jsonl"
ACCURACY = "accuracy.json"
SANITY_PER_COLLECTION = 30
SANITY_SEED = 0


class RefitRefused(RuntimeError):
    """The refit would change the declared parameters or features (D83 guard)."""


def cutoff_for(refit_date: str) -> pd.Timestamp:
    return pd.Timestamp(refit_date, tz="UTC") - pd.Timedelta(days=EMBARGO_DAYS)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def training_rows(directory: Path, cutoff: pd.Timestamp) -> dict:
    """{train, items, id_like}: the D79 training rows as of `cutoff` from a live data directory."""
    cut = int(cutoff.timestamp())
    hist = fv_serving.history_asof(directory, cut)
    items = fv_serving.items(directory)
    feats = fv.build(hist["h"], hist["points"], items["static"], items["traits"])
    feats["y"] = feats["premium"]
    keep = (feats["timestamp"].to_numpy() < cut) & fv.clean_mask(feats, hist["rows"], cut)
    traits = items["traits"]
    id_like = {s: list(v) for s, v in traits[traits["id_like"]].groupby("slug")["trait_type"].unique().items()}
    return {"train": feats[keep].reset_index(drop=True), "items": items, "id_like": id_like}


def guard(cols: list[str], dev_meta: dict) -> None:
    p = fvm.params(config.NFT_FV_CANDIDATE)
    if dev_meta["candidate"] != config.NFT_FV_CANDIDATE or dev_meta["params"] != json.loads(json.dumps(p)) or \
            dev_meta["n_rounds"] != fvm.N_ROUNDS:
        raise RefitRefused("the declared candidate, parameters or rounds differ from the development artifact")
    if cols != dev_meta["columns"]:
        raise RefitRefused(f"the feature columns differ from the development artifact "
                           f"({len(cols)} vs {len(dev_meta['columns'])}); a feature change needs a declared phase")


def accuracy_block(base: Path) -> dict | None:
    path = base / ACCURACY
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def refit(refit_date: str | None = None, directory: Path | None = None, base: Path | None = None) -> dict:
    """Fit, write refits/<R>/, point CURRENT at it, log it. Returns the new metadata."""
    d = Path(directory or config.ML_NFT_DIR)
    base = Path(base or config.NFT_FV_ARTIFACT_DIR)
    now = datetime.now(timezone.utc)
    r = refit_date or now.strftime("%Y-%m-%d")
    cutoff = cutoff_for(r)
    dev_meta = json.loads((base / fv_artifact.META).read_text(encoding="utf-8"))
    rows = training_rows(d, cutoff)
    tr, items = rows["train"], rows["items"]
    cols = fvm.columns_for(config.NFT_FV_CANDIDATE, None, items["trait_cols"])
    guard(cols, dev_meta)
    booster = fvm._fit(fvm.params(config.NFT_FV_CANDIDATE), fv.matrix(tr, cols, rows["id_like"]), tr["y"].to_numpy())
    final = base / REFITS / r
    tmp = base / REFITS / f".{r}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    booster.save_model(str(tmp / fv_artifact.MODEL))
    meta = {"model_version": f"nft-fv-pooled-l1-nl15-refit-{r}", "model_sha256": _sha(tmp / fv_artifact.MODEL),
            "candidate": config.NFT_FV_CANDIDATE, "params": fvm.params(config.NFT_FV_CANDIDATE),
            "n_rounds": fvm.N_ROUNDS, "columns": cols,
            "categorical": [c for c in cols if c == "collection" or c.startswith("trait__")],
            "id_like": rows["id_like"], "refit_date": r, "train_cutoff_exclusive": cutoff.strftime("%Y-%m-%d"),
            "train_rows": len(tr), "train_dates": [tr["date"].min(), tr["date"].max()],
            "train_rows_by_collection": tr.groupby("slug").size().astype(int).to_dict(),
            "data": f"live data directory {d} (all clean sales before the cutoff; W1/W2 as of the cutoff; D79/D83)",
            "static_sha256": fv_serving.static_hash(items["static"]),
            "trait_pairs_sha256": fv_serving.trait_pairs_hash(items["traits"]),
            "serve": dict(config.NFT_FV_SERVE), "range": None, "accuracy": accuracy_block(base),
            "accuracy_note": config.NFT_FV_ACCURACY_NOTE, "development_model_sha256": dev_meta["model_sha256"],
            "decisions": "D79 (procedure), D80 (lilpudgys B2), D83 (refit), D84 (accuracy line)",
            "trial_count": fvm.TRIAL_COUNT, "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run_on": os.environ.get("HOSTNAME", "host")}
    (tmp / fv_artifact.META).write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    shutil.rmtree(final, ignore_errors=True)
    os.replace(tmp, final)
    pointer = base / f".{fv_artifact.CURRENT}.tmp"
    pointer.write_text(f"{REFITS}/{r}\n", encoding="utf-8")
    os.replace(pointer, base / fv_artifact.CURRENT)
    entry = {"refit_date": r, "cutoff": meta["train_cutoff_exclusive"], "train_rows": len(tr),
             "train_rows_by_collection": meta["train_rows_by_collection"], "model_sha256": meta["model_sha256"],
             "model_version": meta["model_version"], "created_at": meta["created_at"]}
    with (base / LOG).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return meta


def due(now: datetime, base: Path | None = None) -> bool:
    """A refit is due on the first refresh of a calendar month in which no refit has been made yet (D83: the 1st;
    a later day of the month only if the job could not run on the 1st)."""
    base = Path(base or config.NFT_FV_ARTIFACT_DIR)
    path = base / LOG
    if not path.exists():
        return True
    month = now.strftime("%Y-%m")
    return not any(json.loads(x)["refit_date"].startswith(month) for x in path.read_text(encoding="utf-8").splitlines()
                   if x.strip())


def sanity(directory: Path | None = None, base: Path | None = None, t: int | None = None) -> dict:
    """Refit vs development model on a fixed token sample (30 per model collection, seed 0) at the same time t:
    the difference in predicted premium and in estimated value. Reported only; selects nothing."""
    d = Path(directory or config.ML_NFT_DIR)
    base = Path(base or config.NFT_FV_ARTIFACT_DIR)
    t = t or int(datetime.now(timezone.utc).timestamp())
    dev_booster, dev_meta = fv_artifact.load(base, follow_current=False)
    new_booster, new_meta = fv_artifact.load(base)
    items = fv_serving.items(d)
    hist = fv_serving.history_asof(d, t)
    rng = np.random.default_rng(SANITY_SEED)
    sample = []
    static = items["static"]
    for slug in sorted(s for s, m in config.NFT_FV_SERVE.items() if m == "model"):
        toks = np.sort(static.loc[static["slug"] == slug, "token_id"].astype(str).unique())
        sample += [(slug, str(x)) for x in rng.choice(toks, size=min(SANITY_PER_COLLECTION, len(toks)), replace=False)]
    feats = fv_serving.query_features(hist["h"], hist["points"], static, items["traits"], sample, t)
    a = fv_artifact.predict(dev_booster, dev_meta, feats)
    b = fv_artifact.predict(new_booster, new_meta, feats)
    df = pd.DataFrame({"slug": [s for s, _ in sample], "dev": a, "refit": b})
    df["abs_diff_premium"] = (df["refit"] - df["dev"]).abs()
    df["abs_rel_diff_value"] = np.abs(np.exp(df["refit"] - df["dev"]) - 1)

    def summ(g):
        return {"n": len(g), "median_abs_rel_diff_value": float(g["abs_rel_diff_value"].median()),
                "p90_abs_rel_diff_value": float(g["abs_rel_diff_value"].quantile(0.9)),
                "max_abs_rel_diff_value": float(g["abs_rel_diff_value"].max()),
                "spearman_dev_vs_refit": float(g[["dev", "refit"]].corr(method="spearman").iloc[0, 1])}

    return {"t": datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "dev_model": dev_meta["model_version"], "refit_model": new_meta["model_version"],
            "sample": f"{SANITY_PER_COLLECTION} tokens per model collection, numpy seed {SANITY_SEED}",
            "pooled": summ(df), "by_collection": {s: summ(g) for s, g in df.groupby("slug")},
            "note": "Sanity check only (D83): no selection, no threshold, nothing changes on its result."}


def write_accuracy(report: Path | None = None, base: Path | None = None) -> dict:
    """accuracy.json for the item card's error line (D84), from the 10.8 report: the served method's sealed MdAPE
    per collection (lilpudgys: B2's) and the served setup's MdAPE on the rarest decile (pooled)."""
    from ml.data.validate import ML_ROOT
    report = Path(report or ML_ROOT / "reports" / "nft" / "sealed_fair_value.json")
    base = Path(base or config.NFT_FV_ARTIFACT_DIR)
    r = json.loads(report.read_text(encoding="utf-8"))
    if r.get("mode") != "sealed" or not r["verdict"]["pass"]:
        raise ValueError("accuracy.json needs the passed sealed report (D79)")
    by = r["descriptive"]["by_collection"]
    out = {"source": "ml/reports/nft/sealed_fair_value.json", "source_sha256": _sha(report),
           "source_git_commit": r["git_commit"], "window": r["window"], "window_label": "Feb-Nov 2026",
           "metric": "MdAPE on price (median absolute percentage error)",
           "by_collection": {s: {"method": "model" if m == "model" else "b2",
                                 "mdape": by[s]["served"], "n": by[s]["n"]} for s, m in r["serve"].items()},
           "rarest_decile": {"decile": 1, "mdape": r["descriptive"]["by_rarity_decile"]["1.0"]["served"],
                             "n": r["descriptive"]["by_rarity_decile"]["1.0"]["n"],
                             "scope": "served setup, pooled over the 7 collections"},
           "decision": "D84"}
    (base / ACCURACY).write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Fair-value serving refits (D83)")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--refit", action="store_true")
    g.add_argument("--sanity", action="store_true")
    g.add_argument("--accuracy", action="store_true")
    parser.add_argument("--date", help="refit date YYYY-MM-DD (default: today, UTC)")
    args = parser.parse_args()
    if args.refit:
        meta = refit(args.date)
        print(json.dumps({k: meta[k] for k in ("model_version", "refit_date", "train_cutoff_exclusive", "train_rows",
                                               "model_sha256")}))
    elif args.sanity:
        print(json.dumps(sanity(), indent=1))
    else:
        print(json.dumps(write_accuracy(), indent=1))


if __name__ == "__main__":
    main()
