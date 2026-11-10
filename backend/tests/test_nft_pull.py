"""Phase 10 (ml/docs/DECISIONS.md D61, D67): the NFT pull, the collection detail route and the NFT seed.
Mocked HTTP and mocked database calls; no network, no Mongo."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import db.queries as queries
from controllers import ml_pull_controller as pull
from controllers import nft_pull
from routes import nft as nft_route

NOW = datetime(2026, 11, 11, 0, 16, tzinfo=timezone.utc)
LISTING = {"collections": [{"slug": "azuki", "name": "Azuki", "symbol": "AZUKI", "contract": "0xed5a",
                            "total_supply": 10000, "image_url": None, "verified": True, "description": None,
                            "last_floor_date": "2026-11-11", "floor_eth": 0.45, "floor_usd": 960.0,
                            "change_24h": 1.0, "change_7d": -2.0, "volume_1d_eth": 3.5, "sales_1d": 8}],
           "marketplaces_counted": "Sales on OpenSea and Blur, as reported by OpenSea",
           "timestamp": "2026-11-11T00:16:00Z"}
FLOOR = {"slug": "azuki", "timestamp": "2026-11-11T00:16:00Z", "note": None, "rows": [
    {"date": f"2026-11-{d:02d}", "floor_eth": 0.40 + 0.01 * d, "floor_usd": 2000 * (0.40 + 0.01 * d), "eth_usd": 2000.0,
     "floor_source": "opensea_floor", "floor_age_hours": 9.5, "floor_intraday_median_eth": None}
    for d in range(1, 12)]}
RISK = {"slug": "azuki", "volatility": 1.12, "risk_score": 18.06, "as_of": "2026-11-11",
        "liquidity": {"sales_7d": 55.0, "sales_30d": 525.0, "volume_7d_eth": 29.6, "volume_30d_eth": 307.4,
                      "liquidity_score": 12.6, "label": "Low", "is_illiquid": False, "wash_removed_share_30d": 0.02,
                      "marketplaces_counted": "Sales on OpenSea and Blur, as reported by OpenSea"},
        "model_version": "nft-ewma-pooled-pct",
        "note": "Risk model: EWMA floor volatility ... relative to the other tracked NFT collections ... not comparable "
                "to crypto risk scores.", "timestamp": "2026-11-11T00:16:00Z"}
SALES = {"slug": "azuki", "marketplaces_counted": "x", "timestamp": "2026-11-11T00:16:00Z", "rows": [
    {"token_id": "4052", "timestamp": "2026-11-08T04:27:59Z", "price_eth": 0.452, "price_usd": 1012.59,
     "marketplace": "opensea", "buyer": "0xb", "seller": "0xs", "tx": "0xt"}]}


@pytest.fixture
def stored(monkeypatch):
    rows = {"meta": [], "market": [], "liq": [], "risk": [], "sales": []}
    monkeypatch.setattr(queries, "upsert_nft_collection_meta", lambda s, f, d: rows["meta"].append((s, f, d)))
    monkeypatch.setattr(queries, "upsert_nft_market_rows", lambda r: rows["market"].extend(r))
    monkeypatch.setattr(queries, "upsert_nft_liquidity_row", lambda r: rows["liq"].append(r))
    monkeypatch.setattr(queries, "upsert_nft_risk_row", lambda r: rows["risk"].append(r))
    monkeypatch.setattr(queries, "upsert_nft_sale_rows", lambda r: rows["sales"].extend(r))
    return rows


def _client(bodies: dict, fail: str | None = None):
    def handler(req):
        path = req.url.path
        if fail and fail in path:
            return httpx.Response(503, json={"detail": "down"})
        for key, body in bodies.items():
            if path.endswith(key):
                return httpx.Response(200, json=body)
        return httpx.Response(404, json={"detail": "not covered"})
    return httpx.Client(transport=httpx.MockTransport(handler))


BODIES = {"/nft/collections": LISTING, "/nft/azuki/floor": FLOOR, "/nft/azuki/risk": RISK, "/nft/azuki/sales": SALES}


def test_pull_writes_every_table_with_the_right_keys(stored):
    out = nft_pull.pull_nft(_client(BODIES), pull.fetch, lambda _: None, now=NOW)
    assert out == {"azuki": "stored"}
    slug, meta, defaults = stored["meta"][0]
    assert slug == "azuki" and meta["supply"] == 10000 and meta["symbol"] == "AZUKI" and "subcategory" in defaults
    m = stored["market"]
    assert [r["date"] for r in m] == [f"2026-11-{d:02d}" for d in range(1, 12)]
    assert m[-1]["timestamp"] == datetime(2026, 11, 11, tzinfo=timezone.utc) and m[-1]["source"] == "ml-service"
    assert m[-1]["change_24h"] == pytest.approx((0.51 / 0.50 - 1) * 100, abs=1e-4)
    assert m[-1]["change_7d"] == pytest.approx((0.51 / 0.44 - 1) * 100, abs=1e-4) and m[0]["change_24h"] is None
    assert m[-1]["volume_24h_eth"] == 3.5 and "volume_24h_eth" not in m[0] and m[0]["floor_age_hours"] == 9.5
    liq, risk = stored["liq"][0], stored["risk"][0]
    assert liq["date"] == risk["date"] == "2026-11-11" and liq["sell_through_rate"] == 0.0525
    assert risk["risk_score"] == 18.06 and risk["floor_volatility_30d"] == 1.12 and risk["holder_concentration"] is None
    assert isinstance(risk["timestamp"], datetime) and stored["sales"][0]["timestamp"].tzinfo is not None


def test_a_failed_endpoint_writes_nothing_for_that_collection(stored):
    out = nft_pull.pull_nft(_client(BODIES, fail="/risk"), pull.fetch, lambda _: None, now=NOW)
    assert out["azuki"].startswith("failed: risk HTTP 503") and out["azuki"].endswith("nothing written")
    assert all(not v for v in stored.values())
    assert pull.has_failures({"NFT": out})


def test_bad_body_and_missing_listing(stored):
    bad = {**BODIES, "/nft/azuki/risk": {**RISK, "slug": "milady"}}
    assert nft_pull.pull_nft(_client(bad), pull.fetch, lambda _: None, now=NOW)["azuki"].startswith("failed: bad body")
    assert all(not v for v in stored.values())
    out = nft_pull.pull_nft(_client({}), pull.fetch, lambda _: None, now=NOW)
    assert out == {"collections": "skipped: 404; nothing written"} and not pull.has_failures({"NFT": out})


def _detail_client(monkeypatch, risk_age_hours: float):
    ts = (datetime.now(timezone.utc) - timedelta(hours=risk_age_hours)).replace(tzinfo=None)   # as Mongo returns
    risk_row = {"slug": "azuki", "date": "2026-11-11", "timestamp": ts, "source": "ml-service",
                "floor_volatility_30d": 1.12, "risk_score": 18.06, "model_version": "nft-ewma-pooled-pct",
                "note": RISK["note"]}
    fns = {"get_nft_collection": lambda s: {"slug": s, "name": "Azuki", "symbol": "AZUKI", "verified": True,
                                            "supply": 10000},
           "get_nft_market_data_latest": lambda s: None, "get_nft_holder_stats": lambda s: None,
           "get_nft_liquidity": lambda s: None, "get_nft_risk_breakdown": lambda s: dict(risk_row),
           "get_nft_traits": lambda s: None, "get_nft_sales": lambda s, limit=10: [],
           "get_latest_aai_score": lambda t, s: None,
           "get_nft_floor_history": lambda s: [{"date": "2026-11-10", "floor_eth": 0.45, "floor_usd": 960.0,
                                                "floor_age_hours": 80.0}]}
    for name, fn in fns.items():
        monkeypatch.setattr(nft_route, name, fn)
    app = FastAPI()
    app.include_router(nft_route.router)
    return TestClient(app)


def test_detail_returns_floor_history_and_ml_risk(monkeypatch):
    d = _detail_client(monkeypatch, 1).get("/nft/collections/azuki").json()
    assert d["floor_history"] == [{"date": "2026-11-10", "floor_eth": 0.45, "floor_usd": 960.0, "floor_age_hours": 80.0}]
    assert d["volatility"] == 1.12 and d["risk_score"] == 18.06 and d["risk_model_version"] == "nft-ewma-pooled-pct"
    assert d["risk_as_of"] == "2026-11-11" and "not comparable to crypto" in d["risk_note"]
    assert "data stale" not in d["risk_note"] and d["last_updated"].endswith("Z")


def test_detail_marks_a_risk_row_older_than_36_hours_stale(monkeypatch):
    d = _detail_client(monkeypatch, 37).get("/nft/collections/azuki").json()
    assert "data stale: the newest stored row is 37 h old" in d["risk_note"]


def test_seed_holds_exactly_the_ml_collections_and_no_fictional_ones():
    from db import seed_nft, seed_user_data
    root = Path(__file__).resolve().parents[2]
    seeded = {c["slug"] for c in seed_nft.COLLECTIONS}
    assert len(seeded) == 7
    cfg_path = root / "ml" / "config.py"               # not mounted in the backend container; checked on the host
    if cfg_path.exists():
        ml_slugs = cfg_path.read_text(encoding="utf-8").split("NFT_SLUGS = (")[1].split(")")[0]
        assert seeded == {s.strip().strip('"') for s in ml_slugs.replace("\n", " ").split(",") if s.strip()}
    assert all(c["verified"] and isinstance(c["supply"], int) for c in seed_nft.COLLECTIONS)
    js = json.loads((root / "db" / "seed_data" / "nftCollections.json").read_text(encoding="utf-8"))
    assert {c["slug"] for c in js["collections"]} == seeded and not any("aai" in c for c in js["collections"])
    src = Path(seed_user_data.__file__).read_text(encoding="utf-8")
    assert not any(s in src for s in seed_nft.FICTIONAL_SLUGS)
    assert '"pudgypenguins"' in src and '"azuki"' in src and "14.2 ETH" not in src
