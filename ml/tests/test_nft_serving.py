"""Phase 10 step 10.4: the ML NFT endpoints (D59, D61, D66, D67). Hand-made live directories, no network.
A last test validates the real live data against CONTRACT_NFT.md when it exists (git-ignored, like the CSVs)."""

import json
import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from ml import config
from ml.api.contract import CONTRACT_NFT_MD, load_schemas, validator
from ml.api.service import app
from ml.data.validate import ML_ROOT
from ml.models import risk_v2
from ml.nft import risk_data, store
from ml.serving import nft_responses as nr

SLUGS = ("aa", "bb")
DAY = 86400
LAST = "2025-01-20"


def _live(tmp_path, days=120, spike=False):
    """Floor points for 2 collections ending 00:00 of LAST, ETH bars, a few sales and the metadata file."""
    live = tmp_path / "live"
    end = int(pd.Timestamp(LAST, tz="UTC").timestamp())
    rng = np.random.default_rng(0)
    rows = []
    for i, slug in enumerate(SLUGS):
        level = (1.0 + i) * np.exp(np.cumsum(rng.normal(0, 0.03 * (1 + i), days)))
        if spike:
            level[days // 2] *= 0.1
        rows += [(slug, end - (days - 1 - k) * DAY + 3600 * 5, float(level[k]), "1") for k in range(days)]
    store.write_csv(pd.DataFrame(rows, columns=["slug", "time", "token_unit", "usd_price"]), live / "floor_points.csv")
    ts = pd.date_range(pd.Timestamp(LAST) - pd.Timedelta(days=days + 5), periods=days + 5, freq="D", tz="UTC")
    pd.DataFrame({"asset": "eth", "timestamp": ts, "open": 2000.0, "high": 0.0, "low": 0.0, "close": 2001.0,
                  "volume": 1.0}).to_csv(live / "eth_1d.csv", index=False)
    s0 = end - 40 * DAY
    sales = [{"slug": slug, "token_id": str(k), "timestamp": s0 + k * DAY + 7, "price_eth": 1.0 + i,
              "payment_symbol": "ETH", "buyer": f"b{k}", "seller": f"s{k}", "tx": f"t{slug}{k}",
              "protocol_address": "", "marketplace": "unknown"} for i, slug in enumerate(SLUGS) for k in range(40)]
    sales = pd.DataFrame(sales)
    sales["date"] = pd.to_datetime(sales["timestamp"], unit="s", utc=True).dt.strftime("%Y-%m-%d")
    store.write_csv(sales, live / "sales_raw.csv")
    (live / "collections.json").write_text(json.dumps({s: {"name": s.upper(), "symbol": s.upper(), "total_supply": 9,
                                                           "verified": True} for s in SLUGS}))
    return live


@pytest.fixture
def live(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ML_NFT_DIR", _live(tmp_path))
    monkeypatch.setattr(config, "NFT_SLUGS", SLUGS)
    nr._CACHE.clear()
    yield config.ML_NFT_DIR
    nr._CACHE.clear()


NOW = datetime(2025, 1, 20, 12, tzinfo=timezone.utc)
SCHEMAS = load_schemas(CONTRACT_NFT_MD)


def _errors(title, body):
    return [f"{list(e.path)}: {e.message}" for e in validator(SCHEMAS[title]).iter_errors(body)]


def test_schemas_are_closed_and_separate_from_the_crypto_contract():
    assert set(SCHEMAS) == {"NftCollectionsResponse", "NftFloorResponse", "NftRiskResponse", "NftSalesResponse",
                            "NftItemValueResponse", "NftItemValuesResponse"}          # 10.7 item values (D78)
    assert all(s["additionalProperties"] is False for s in SCHEMAS.values())
    ok = {"slug": "aa", "rows": [], "timestamp": "2025-01-20T00:00:00Z"}
    assert _errors("NftFloorResponse", ok) == [] and _errors("NftFloorResponse", {**ok, "extra": 1})


@pytest.mark.usefixtures("live")
def test_every_response_validates_and_unknown_or_missing_give_404_and_503(monkeypatch, tmp_path):
    for title, body in (("NftCollectionsResponse", nr.collections(NOW)), ("NftFloorResponse", nr.floor("aa", NOW)),
                        ("NftRiskResponse", nr.risk("bb", NOW)), ("NftSalesResponse", nr.sales("aa", NOW))):
        assert _errors(title, body) == [], title
    c = TestClient(app)
    assert c.get("/nft/aa/risk").status_code == 200 and c.get("/nft/zz/risk").status_code == 404
    monkeypatch.setattr(config, "ML_NFT_DIR", tmp_path / "empty")
    nr._CACHE.clear()
    assert c.get("/nft/aa/risk").status_code == 503


@pytest.mark.usefixtures("live")
def test_served_volatility_is_the_evaluation_persistence_on_the_raw_floor():
    floor = nr.tables()["floor"]
    g = floor[floor["slug"] == "aa"]
    hist = risk_data.features(risk_data.floor_series(g, "floor_eth_asof"))
    expected = risk_v2.persistence_predict(None, hist, range(len(hist)))  # the 10.3 evaluation baseline
    np.testing.assert_allclose(nr.served_vol(g).to_numpy(), expected, equal_nan=True)
    body = nr.risk("aa", NOW)
    assert body["volatility"] == pytest.approx(expected[-1] * math.sqrt(365), rel=1e-6)
    assert config.NFT_RISK_VOL_COLUMN == "vol_30d" and config.NFT_MODEL_FLOOR_COLUMN == "floor_eth_asof"
    assert body["model_version"] == config.MODEL_VERSION_NFT_RISK == "nft-persistence-pooled-pct"
    assert "No model is served" in body["note"] and "D73" in body["note"]


@pytest.mark.usefixtures("live")
def test_risk_score_is_the_pooled_nft_percentile_and_the_note_says_it_is_not_comparable():
    t = nr.tables()
    today = t["floor"]["date"].max()
    pool = np.concatenate([s[s.index <= today].dropna().to_numpy() for s in t["vol"].values()])
    x = nr.risk_inputs("bb", NOW)
    assert x["pool_size"] == len(pool) and x["pool_collections"] == list(SLUGS)
    p = ((pool < x["daily_vol"]).sum() + 0.5 * (pool == x["daily_vol"]).sum()) / len(pool)
    assert nr.risk("bb", NOW)["risk_score"] == pytest.approx(100 * (1 - p), abs=1e-6)
    note = nr.risk("bb", NOW)["note"]
    assert "relative to the other tracked NFT collections" in note and "not comparable to crypto" in note
    assert "data stale" not in note


@pytest.mark.usefixtures("live")
def test_stale_after_48_hours_from_the_last_floor_date():
    assert "data stale: last floor 2025-01-20" not in nr.risk("aa", NOW + timedelta(hours=35))["note"]
    assert "data stale: last floor 2025-01-20" in nr.risk("aa", NOW + timedelta(hours=37))["note"]   # 49 h
    assert nr.floor("aa", NOW + timedelta(hours=37))["note"] == "data stale: last floor 2025-01-20"


def test_no_volatility_with_fewer_than_60_days(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ML_NFT_DIR", _live(tmp_path, days=55))
    monkeypatch.setattr(config, "NFT_SLUGS", SLUGS)
    nr._CACHE.clear()
    body = nr.risk("aa", NOW)
    nr._CACHE.clear()
    assert body["volatility"] is None and body["risk_score"] is None and "fewer than 60 days" in body["note"]


@pytest.mark.usefixtures("live")
def test_floor_and_sales_rows_and_the_cache_follow_the_files():
    f = nr.floor("aa", NOW, days=5)
    assert [r["date"] for r in f["rows"]][-1] == LAST and len(f["rows"]) == 5
    assert all(r["floor_usd"] == pytest.approx(r["floor_eth"] * r["eth_usd"], abs=0.01) for r in f["rows"])
    assert [r["eth_usd"] for r in f["rows"]] == [2000.0] * 4 + [2001.0]     # last date: previous bar's close (D63)
    s = nr.sales("aa", NOW, days=10)["rows"]
    assert len(s) == 10 and all(r["price_usd"] == 2000.0 for r in s)        # 1 ETH x the open of the date
    first = nr.tables()
    assert nr.tables() is first                                             # cached
    p = config.ML_NFT_DIR / "collections.json"
    p.write_text(p.read_text().replace('"AA"', '"AAX"'))
    import os
    os.utime(p, ns=(p.stat().st_atime_ns, p.stat().st_mtime_ns + 10 ** 9))
    assert nr.tables() is not first and nr.collections(NOW)["collections"][0]["name"] == "AAX"


def test_served_measure_follows_the_10_3_report_and_the_d72_check():
    report = ML_ROOT / "reports" / "nft" / "walkforward_risk.json"
    served = json.loads(report.read_text(encoding="utf-8"))["served_volatility"]
    check = json.loads((ML_ROOT / "reports" / "nft" / "item_data_v2.json").read_text(encoding="utf-8"))
    withdrawn = check["d66_sales_check"]["ewma_approval_withdrawn"]
    expected = "vol_30d" if withdrawn else {"ewma": "ewma_vol", "persistence_vol30": "vol_30d"}[served]
    assert expected == config.NFT_RISK_VOL_COLUMN                          # D73


@pytest.mark.skipif(not (config.ML_NFT_DIR / "floor_points.csv").exists(), reason="no live NFT data (git-ignored)")
def test_real_live_data_validates_against_the_contract():
    nr._CACHE.clear()
    c = TestClient(app)
    bodies = {"NftCollectionsResponse": c.get("/nft/collections").json()}
    for slug in config.NFT_SLUGS:
        bodies[f"NftFloorResponse {slug}"] = c.get(f"/nft/{slug}/floor?days=30").json()
        bodies[f"NftRiskResponse {slug}"] = c.get(f"/nft/{slug}/risk").json()
    bodies["NftSalesResponse"] = c.get(f"/nft/{config.NFT_SLUGS[0]}/sales?days=3").json()
    for name, body in bodies.items():
        assert _errors(name.split()[0], body) == [], name
    nr._CACHE.clear()
