"""Phase 10 step 10.7 (D78): request-time fair-value features and item value serving. Development dates only."""

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.api.contract import check
from ml.nft import fv_artifact, fv_features as fv, fv_serving
from ml.nft import snapshot

TOL = 1e-9
DAY = 86400


def _need_dev():
    if not (snapshot.snapshot_dir(config.NFT_ITEM_SNAPSHOT_V3) / "sales.parquet").exists():
        pytest.skip("v3 item snapshot files are local only (D64)")


@pytest.fixture(scope="module")
def dev():
    _need_dev()
    from ml.nft import fv_leakage
    return fv_leakage.prepare()


def _equal(a: pd.DataFrame, b: pd.DataFrame, cols: list) -> list:
    bad = []
    for c in cols:
        x, y = a[c].to_numpy(dtype=float), b[c].to_numpy(dtype=float)
        ok = (np.isnan(x) & np.isnan(y)) | (np.abs(x - y) <= TOL)
        if not ok.all():
            bad.append((c, int((~ok).sum())))
    return bad


def _reference(dev, queries, t):
    """The training pipeline (fv.build on the FULL development history) with hypothetical sales at t."""
    h = dev["h"][["slug", "token_id", "timestamp", "date", "tx", "premium"]]
    q = pd.DataFrame(queries, columns=["slug", "token_id"])
    date = pd.Timestamp(t, unit="s", tz="UTC").strftime("%Y-%m-%d")
    frame = pd.concat([h, q.assign(timestamp=t, date=date, tx=[f"~ref-{i}" for i in range(len(q))], premium=np.nan)],
                      ignore_index=True).sort_values(["slug", "timestamp", "tx", "token_id"]).reset_index(drop=True)
    frame["hid"] = np.arange(len(frame))
    frame["ts"] = pd.to_datetime(frame["timestamp"], unit="s")
    out = fv.build(frame, dev["dev"]["floor_points"], dev["static"], dev["dev"]["traits"])
    out = out[out["tx"].str.startswith("~ref-")].copy()
    out["i"] = out["tx"].str.slice(5).astype(int)
    return out.sort_values("i").reset_index(drop=True)


def test_request_time_features_equal_the_training_pipeline_for_hypothetical_sales(dev):
    rng = np.random.default_rng(0)
    static = dev["static"]
    sold = set(map(tuple, dev["h"][["slug", "token_id"]].to_numpy()))
    lo, hi = int(pd.Timestamp("2025-03-01", tz="UTC").timestamp()), int(pd.Timestamp("2026-01-24", tz="UTC").timestamp())
    cols = fv.DYNAMIC + fv.STATIC + dev["trait_cols"]
    n_pairs, n_never = 0, 0
    for t in rng.integers(lo, hi, size=20):
        idx = rng.choice(len(static), size=10, replace=False)
        queries = [tuple(x) for x in static.iloc[idx][["slug", "token_id"]].to_numpy()]
        got = fv_serving.query_features(dev["h"], dev["dev"]["floor_points"], static, dev["dev"]["traits"],
                                        queries, int(t))
        ref = _reference(dev, queries, int(t))
        assert _equal(got, ref, cols) == []
        assert (got["no_prior_sale"] == (got["prev_n"] == 0)).all() and got.loc[got["no_prior_sale"], "prev_prem"].isna().all()
        n_pairs += len(queries)
        n_never += sum(q not in sold for q in queries)
    assert n_pairs == 200 and n_never > 0            # tokens never sold get the training's missing values


def test_request_time_features_at_a_real_sale_time_equal_that_sale_s_training_features(dev):
    clean = dev["features"][dev["features"]["clean"]].sample(n=100, random_state=0)
    cols = fv.DYNAMIC + fv.STATIC + dev["trait_cols"]
    for _, r in clean.iterrows():
        got = fv_serving.query_features(dev["h"], dev["dev"]["floor_points"], dev["static"], dev["dev"]["traits"],
                                        [(r["slug"], r["token_id"])], int(r["timestamp"]))
        assert _equal(got, r.to_frame().T.reset_index(drop=True), cols) == []


def test_request_time_inputs_ignore_everything_at_or_after_t(dev):
    t = int(pd.Timestamp("2025-09-15 12:00", tz="UTC").timestamp())
    q = [tuple(dev["static"].iloc[5][["slug", "token_id"]])]
    a = fv_serving.query_features(dev["h"], dev["dev"]["floor_points"], dev["static"], dev["dev"]["traits"], q, t)
    h2 = dev["h"].copy()
    h2.loc[h2["timestamp"] >= t, "premium"] += 3.0                      # change every later price
    b = fv_serving.query_features(h2, dev["dev"]["floor_points"], dev["static"], dev["dev"]["traits"], q, t)
    assert _equal(a, b, fv.DYNAMIC) == []


def test_served_artifact_is_the_fold_9_fit_of_the_walk_forward(dev):
    from ml.evaluation.run_nft_fair_value import ROWS
    if not (config.NFT_FV_ARTIFACT_DIR / fv_artifact.MODEL).exists() or not ROWS.exists():
        pytest.skip("artifact or walk-forward rows not present")
    booster, meta = fv_artifact.load(follow_current=False)              # the development fit (D78)
    assert meta["train_cutoff_exclusive"] == "2025-12-25" and meta["train_dates"][1] < "2025-12-25"
    assert meta["range"] is None and "accuracy_note" not in meta        # removed in 10.9b (MINOR 4)
    rows = pd.read_parquet(ROWS)
    f9 = rows[rows["fold"] == 9]
    feats = dev["features"].set_index("hid").loc[f9["hid"]].reset_index()
    pred = fv_artifact.predict(booster, meta, feats)
    assert np.allclose(pred, f9[f"pred:{config.NFT_FV_CANDIDATE}"].to_numpy(), atol=1e-12)
    assert meta["static_sha256"] == fv_serving.static_hash(dev["static"])
    assert meta["trait_pairs_sha256"] == fv_serving.trait_pairs_hash(dev["dev"]["traits"])


# ---- responses, with the request time inside development dates (no live data) ----

NOW = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def served(dev, monkeypatch):
    from ml.serving import nft_items
    if not (config.NFT_FV_ARTIFACT_DIR / fv_artifact.MODEL).exists():
        pytest.skip("artifact not trained")
    from ml.nft import fv_refit
    booster, meta = fv_artifact.load(follow_current=False)
    meta = {**meta, "accuracy": fv_refit.accuracy_block(config.NFT_FV_ARTIFACT_DIR)}   # the D84 lines
    tokens = dev["dev"]["tokens"]
    t = {"h": dev["h"], "points": dev["dev"]["floor_points"], "booster": booster, "meta": meta,
         "items": {"tokens": tokens, "traits": dev["dev"]["traits"], "static": dev["static"],
                   "trait_cols": dev["trait_cols"]}}
    monkeypatch.setattr(nft_items, "tables", lambda now: t)
    return nft_items


def test_item_values_follow_the_per_collection_serving_config(served, dev, monkeypatch):
    pairs = [("pudgypenguins", "7862"), ("azuki", "8604"), ("lilpudgys", str(dev["h"].query("slug == 'lilpudgys'")["token_id"].iloc[0]))]
    body = served.batch(",".join(f"{s}:{k}" for s, k in pairs), NOW)
    check("NftItemValuesResponse", body)
    by = {i["slug"]: i for i in body["items"]}
    assert by["pudgypenguins"]["method"] == "model" and by["lilpudgys"]["method"] == "baseline_b2"
    assert all("usd" not in k for i in body["items"] for k in i)          # ETH only
    assert by["pudgypenguins"]["accuracy_note"] == "Median error in testing (Feb-Nov 2026): 2.0%"
    assert by["lilpudgys"]["accuracy_note"] == "Median error in testing (Feb-Nov 2026): 2.8%"    # B2's (D80)
    st = dev["static"].set_index(["slug", "token_id"])["rarity_decile"]
    for i in body["items"]:
        rare = st.get((i["slug"], i["token_id"])) == 1
        assert i["rarity_accuracy_note"] == ("Rarest items: about 9%" if rare else None)
    feats = fv_serving.query_features(dev["h"], dev["dev"]["floor_points"], dev["static"], dev["dev"]["traits"],
                                      [pairs[2]], int(NOW.timestamp()))
    b2 = float(np.nan_to_num(feats["decile_prem_med_90d"].iloc[0]))
    assert by["lilpudgys"]["estimated_value_eth"] == pytest.approx(by["lilpudgys"]["last_floor_eth"] * np.exp(b2), rel=1e-5)
    monkeypatch.setattr(config, "NFT_FV_SERVE", {s: "b2" for s in config.NFT_SLUGS})   # the 10.9 switch
    assert all(i["method"] == "baseline_b2" for i in served.batch("pudgypenguins:7862,azuki:8604", NOW)["items"])


def test_rarest_decile_item_gets_the_rarest_items_line(served, dev):
    st = dev["static"]
    rare = st[(st["slug"] == "azuki") & (st["rarity_decile"] == 1)]["token_id"].iloc[0]
    common = st[(st["slug"] == "azuki") & (st["rarity_decile"] == 10)]["token_id"].iloc[0]
    a = check("NftItemValueResponse", served.value("azuki", rare, NOW))
    b = check("NftItemValueResponse", served.value("azuki", common, NOW))
    assert a["rarity_accuracy_note"] == "Rarest items: about 9%" and b["rarity_accuracy_note"] is None
    assert a["accuracy_note"] == b["accuracy_note"] == "Median error in testing (Feb-Nov 2026): 3.8%"


def test_item_without_an_earlier_sale_is_flagged(served, dev):
    sold = set(dev["h"]["token_id"][dev["h"]["slug"] == "azuki"])
    never = next(k for k in dev["static"].query("slug == 'azuki'")["token_id"] if k not in sold)
    body = check("NftItemValueResponse", served.value("azuki", never, NOW))
    assert body["no_prior_sale"] and body["last_sale"] is None and body["estimated_value_eth"] > 0
    assert "no earlier sale" in body["note"]


def test_endpoints_validate_and_map_errors(served, monkeypatch):
    from fastapi.testclient import TestClient
    from ml.api import service

    class Clock(datetime):                                                # request time inside development dates
        @classmethod
        def now(cls, tz=None):
            return NOW
    monkeypatch.setattr(service, "datetime", Clock)
    c = TestClient(service.app)
    r = c.get("/nft/pudgypenguins/items/7862/value")
    assert r.status_code == 200 and r.json()["slug"] == "pudgypenguins"
    assert c.get("/nft/pudgypenguins/items/99999999/value").status_code == 404
    assert c.get("/nft/nope/items/1/value").status_code == 404
    assert c.get("/nft/items/value", params={"items": "pudgypenguins"}).status_code == 422
    r = c.get("/nft/items/value", params={"items": "pudgypenguins:7862,azuki:8604"})
    assert r.status_code == 200 and len(r.json()["items"]) == 2


def test_live_directory_cut_at_the_development_end_rebuilds_the_training_history():
    """The serving loader on the live data directory, cut at 2026-01-25, equals the development history (D78)."""
    _need_dev()
    from ml.nft import item_data
    if not fv_serving.store.has_table(config.ML_NFT_DIR, "sales_raw"):
        pytest.skip("no live NFT data directory")
    a = fv_serving.history_asof(config.ML_NFT_DIR, item_data.dev_end_timestamp())["h"]
    b = fv.history(item_data.load_dev(include_flagged=True)["sales"])
    cols = ["slug", "token_id", "timestamp", "tx", "price_eth", "floor_point_eth", "premium"]
    pd.testing.assert_frame_equal(a[cols].reset_index(drop=True), b[cols].reset_index(drop=True))
    if (config.NFT_FV_ARTIFACT_DIR / fv_artifact.META).exists():
        meta = fv_artifact.load(follow_current=False)[1]
        it = fv_serving.items(config.ML_NFT_DIR)
        assert fv_serving.static_hash(it["static"]) == meta["static_sha256"]
        assert fv_serving.trait_pairs_hash(it["traits"]) == meta["trait_pairs_sha256"]


def test_live_accuracy_log_records_exactly_the_served_values(served, dev, tmp_path, monkeypatch):
    """D85: the daily log uses the API's own estimates() code; its values equal the item value responses."""
    import gzip

    from ml.nft import live_accuracy
    t = served.tables(NOW)
    st = dev["static"]
    small = st[st["token_id"].isin(["7862", "8604", "1", "2", "3"])].reset_index(drop=True)
    monkeypatch.setattr(served, "tables", lambda now: {**t, "items": {**t["items"], "static": small}})
    rec = live_accuracy.record(NOW, tmp_path)
    with gzip.open(rec["file"], "rt", encoding="utf-8") as f:
        logged = pd.read_csv(f, dtype={"token_id": str})
    assert rec["rows"] == len(small) == len(logged) and (logged["logged_at"] == int(NOW.timestamp())).all()
    pairs = list(zip(logged["slug"], logged["token_id"]))
    api = {(i["slug"], i["token_id"]): i for i in served.values(pairs, NOW)}
    for r in logged.itertuples():
        a = api[(r.slug, r.token_id)]
        assert r.estimated_value_eth == pytest.approx(a["estimated_value_eth"], rel=1e-6, abs=1e-6)
        assert r.floor_eth == pytest.approx(a["last_floor_eth"], rel=1e-6)          # the API rounds to 6 digits
        assert ("model" if r.method == "model" else "baseline_b2") == a["method"]
