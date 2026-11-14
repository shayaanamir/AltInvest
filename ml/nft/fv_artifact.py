"""The served fair-value model artifact (Phase 10 step 10.7, D78).

    python -m ml.nft.fv_artifact --train      (training venv: lightgbm + pyarrow; DEVELOPMENT data only)

Fits config.NFT_FV_CANDIDATE (fv_pooled_l1_nl15, exactly as declared in ml/models/nft_fair_value.py) on the
clean development sales before config.NFT_FV_TRAIN_CUTOFF (2025-12-25, the last walk-forward fold's training
cutoff), with W1/W2 decided from sales before that cutoff (D76 amended), i.e. the fold-9 fit of 10.6. Writes
model.txt (LightGBM text) and metadata.json (AGENTS rule 10) to config.NFT_FV_ARTIFACT_DIR. Since step 10.9 the
served model is a refit on the live data (ml.nft.fv_refit, D83) in the folder that the pointer file CURRENT names;
CURRENT and the refits live in config.NFT_FV_REFIT_DIR (the serving data volume, 10.9b), never in this folder, which
containers mount read-only. This development fit stays as the reference. Serving loads the served one with load()
(lightgbm only).
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ml import config
from ml.models import nft_fair_value as fvm
from ml.nft import fv_features as fv
from ml.nft import fv_serving

MODEL, META, CURRENT = "model.txt", "metadata.json", "CURRENT"


def cutoff_ts() -> int:
    return int(pd.Timestamp(config.NFT_FV_TRAIN_CUTOFF, tz="UTC").timestamp())


def training_frame() -> dict:
    """Development rows only (item_data.load_dev); the training rows of the served fit."""
    from ml.nft import fv_leakage
    p = fv_leakage.prepare()
    feats = p["features"].assign(y=p["features"]["premium"])
    cut = cutoff_ts()
    train = (feats["timestamp"] < cut).to_numpy() & fv.clean_mask(feats, p["dev"]["sales"], cut)
    return {**p, "train": feats[train].reset_index(drop=True)}


def train() -> dict:
    import lightgbm as lgb  # noqa: F401  (training venv)
    from ml.gitinfo import git_metadata
    from ml.nft import item_data, snapshot
    git = git_metadata()
    p = training_frame()
    tr = p["train"]
    traits = p["dev"]["traits"]
    id_like = {s: list(v) for s, v in traits[traits["id_like"]].groupby("slug")["trait_type"].unique().items()}
    cols = fvm.columns_for(config.NFT_FV_CANDIDATE, None, p["trait_cols"])
    booster = fvm._fit(fvm.params(config.NFT_FV_CANDIDATE), fv.matrix(tr, cols, id_like), tr["y"].to_numpy())
    out = config.NFT_FV_ARTIFACT_DIR
    out.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(out / MODEL))
    from ml.nft.snapshot import sha256
    meta = {"model_version": config.MODEL_VERSION_NFT_FV, "model_sha256": sha256(out / MODEL),
            "candidate": config.NFT_FV_CANDIDATE,
            "params": fvm.params(config.NFT_FV_CANDIDATE), "n_rounds": fvm.N_ROUNDS, "columns": cols,
            "categorical": [c for c in cols if c == "collection" or c.startswith("trait__")],
            "id_like": id_like, "train_cutoff_exclusive": config.NFT_FV_TRAIN_CUTOFF,
            "train_rows": len(tr), "train_dates": [tr["date"].min(), tr["date"].max()],
            "train_rows_by_collection": tr.groupby("slug").size().astype(int).to_dict(),
            "data": "development rows only (item_data.load_dev); W1/W2 as of the training cutoff (D76 amended)",
            "item_snapshot": config.NFT_ITEM_SNAPSHOT_V3, "item_manifest_sha256": item_data.require(),
            "base_manifest_sha256": snapshot.require_snapshot("floor_points", "eth_usd"),
            "static_sha256": fv_serving.static_hash(p["static"]),
            "trait_pairs_sha256": fv_serving.trait_pairs_hash(traits),
            "serve": dict(config.NFT_FV_SERVE), "range": None,
            "decisions": "D76, D77 (walk-forward approval), D78 (serving)", "walkforward_report":
                "ml/reports/nft/walkforward_fair_value.json", "trial_count": fvm.TRIAL_COUNT,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **git}
    (out / META).write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    return meta


def served_dir(directory=None, follow_current: bool = True, refit_dir=None) -> Path:
    """The served artifact folder: the refit that refit_dir/CURRENT points to (D83), else the development artifact
    (D78) in `directory`. refit_dir defaults to config.NFT_FV_REFIT_DIR (the volume); the pointer must stay inside it."""
    d = Path(directory or config.NFT_FV_ARTIFACT_DIR)
    r = Path(refit_dir or config.NFT_FV_REFIT_DIR)
    pointer = r / CURRENT
    if follow_current and pointer.exists():
        rel = pointer.read_text(encoding="utf-8").strip()
        target = (r / rel).resolve()
        if r.resolve() not in target.parents:
            raise OSError("CURRENT points outside the refit folder")
        return target
    return d


def has_served_model(refit_dir=None) -> bool:
    """True when refit_dir/CURRENT names a refit with a model file (10.9b MINOR 9: else the startup refit runs)."""
    r = Path(refit_dir or config.NFT_FV_REFIT_DIR)
    if not (r / CURRENT).exists():
        return False
    try:
        return (served_dir(None, True, r) / MODEL).exists()
    except OSError:
        return False


def load(directory=None, follow_current: bool = True, refit_dir=None) -> tuple:
    """(booster, metadata) of the served artifact (CURRENT's refit if present, D83; else the development fit)."""
    import lightgbm as lgb
    d = served_dir(directory, follow_current, refit_dir)
    meta = json.loads((d / META).read_text(encoding="utf-8"))
    import hashlib
    if hashlib.sha256((d / MODEL).read_bytes()).hexdigest() != meta["model_sha256"]:
        raise OSError("model.txt does not match the sha256 in metadata.json")
    return lgb.Booster(model_file=str(d / MODEL)), meta


def predict(booster, meta: dict, feats: pd.DataFrame) -> np.ndarray:
    return booster.predict(fv.matrix(feats, meta["columns"], meta["id_like"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the served fair-value artifact on development data (D78)")
    parser.add_argument("--train", action="store_true", required=True)
    parser.parse_args()
    meta = train()
    print(json.dumps({k: meta[k] for k in ("model_version", "train_rows", "train_dates", "git_commit", "git_dirty")}))


if __name__ == "__main__":
    main()
