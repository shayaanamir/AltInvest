"""Phase 10 step 10.7 (ml/docs/DECISIONS.md D78): item value pull, the item lookup route and holdings estimates.
Mocked HTTP and mocked database calls; no network, no Mongo."""
from datetime import datetime, timezone

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import db.queries as queries
from controllers import ml_pull_controller as pull
from controllers import nft_items
from routes import nft as nft_route
from routes import portfolio as portfolio_route

NOW = datetime(2026, 11, 14, 0, 16, tzinfo=timezone.utc)
REAL_CLIENT = httpx.Client


ACC = "Median error in testing (Feb-Nov 2026): 2.0%"
RARE = "Rarest items: about 9%"


def _item(slug, token, value=1.25, method="model", rare=None):
    return {"rarity_accuracy_note": rare, "slug": slug, "token_id": token, "estimated_value_eth": value, "method": method, "last_floor_eth": 1.0,
            "last_floor_time": "2026-11-13T22:00:00Z", "last_sale": {"price_eth": 1.1, "timestamp": "2026-06-01T10:00:00Z"},
            "no_prior_sale": False, "rarity_rank": 120, "rarity_ranked_tokens": 8888,
            "accuracy_note": ACC, "model_version": "nft-fv-pooled-l1-nl15-refit-2026-11-14",
            "note": None, "as_of": "2026-11-14T00:16:00Z", "timestamp": "2026-11-14T00:16:00Z"}


def _client(handler):
    return REAL_CLIENT(transport=httpx.MockTransport(handler))


@pytest.fixture
def stored(monkeypatch):
    rows = {}
    monkeypatch.setattr(queries, "upsert_nft_item_value", lambda r: rows.__setitem__((r["slug"], r["token_id"]), r))
    monkeypatch.setattr(queries, "get_nft_item_value", lambda s, t: rows.get((s, str(t))))
    return rows


def test_pull_stores_every_holding_token_in_batches_of_50(stored):
    tokens = [("azuki", str(i)) for i in range(60)]
    calls = []

    def handler(req):
        items = req.url.params["items"].split(",")
        calls.append(len(items))
        return httpx.Response(200, json={"items": [_item(*x.split(":")) for x in items], "timestamp": "2026-11-14T00:16:00Z"})
    out = nft_items.pull_item_values(_client(handler), pull.fetch, lambda _: None, now=NOW, tokens=tokens)
    assert calls == [50, 10] and out == {"batch 1": "stored 50", "batch 2": "stored 10"} and len(stored) == 60
    r = stored[("azuki", "7")]
    assert r["as_of_ts"] == NOW and r["source"] == "ml-service" and r["estimated_value_eth"] == 1.25
    assert not any("usd" in k for k in r)                       # ETH only


def test_a_failed_or_bad_batch_writes_nothing(stored):
    out = nft_items.pull_item_values(_client(lambda req: httpx.Response(503)), pull.fetch, lambda _: None, now=NOW,
                                     tokens=[("azuki", "1")])
    assert out["batch 1"].startswith("failed") and stored == {}
    bad = {"items": [{**_item("azuki", "1"), "estimated_value_eth": -2}], "timestamp": "x"}
    out = nft_items.pull_item_values(_client(lambda req: httpx.Response(200, json=bad)), pull.fetch, lambda _: None,
                                     now=NOW, tokens=[("azuki", "1")])
    assert "bad body" in out["batch 1"] and stored == {}


def _app(monkeypatch, handler):
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: REAL_CLIENT(transport=httpx.MockTransport(handler)))
    app = FastAPI()
    app.include_router(nft_route.router)
    return TestClient(app)


def test_item_route_live_then_stale_then_errors(monkeypatch, stored):
    c = _app(monkeypatch, lambda req: httpx.Response(200, json=_item("pudgypenguins", "7862")))
    body = c.get("/nft/collections/pudgypenguins/items/7862/value").json()
    assert body["estimated_value_eth"] == 1.25 and body["stale"] is False and body["accuracy_note"] == ACC
    assert "lower_eth" not in body and "drivers" not in body
    c = _app(monkeypatch, lambda req: httpx.Response(503))
    body = c.get("/nft/collections/pudgypenguins/items/7862/value").json()
    assert body["stale"] is True and body["estimated_value_eth"] == 1.25          # the stored row
    assert c.get("/nft/collections/pudgypenguins/items/1/value").status_code == 503  # nothing stored
    c = _app(monkeypatch, lambda req: httpx.Response(404))
    assert c.get("/nft/collections/pudgypenguins/items/1/value").status_code == 404
    assert c.get("/nft/collections/pudgypenguins/items/abc/value").status_code == 422


def test_holdings_get_the_stored_estimate_without_changing_value(monkeypatch):
    monkeypatch.setattr(queries, "get_nft_item_values",
                        lambda pairs: {("azuki", "8604"): _item("azuki", "8604", 0.9, "model", RARE)})
    hs = [{"asset_type": "nft", "nft_collection_slug": "azuki", "nft_token_id": "8604", "current_value_usd": 900.0},
          {"asset_type": "crypto", "symbol": "BTC", "current_value_usd": 10.0}]
    out = portfolio_route.with_item_estimates(hs)
    assert out[0]["estimated_value_eth"] == 0.9 and out[0]["estimated_value_accuracy_note"] == ACC
    assert out[0]["estimated_value_rarity_accuracy_note"] == RARE                       # D84
    assert out[0]["current_value_usd"] == 900.0 and "estimated_value_eth" not in out[1]
    monkeypatch.setattr(queries, "get_nft_item_values", lambda pairs: (_ for _ in ()).throw(RuntimeError("db down")))
    assert portfolio_route.with_item_estimates(hs)[0].get("estimated_value_eth") is None   # never fails the list


def test_pull_all_includes_the_item_values(monkeypatch):
    monkeypatch.setattr(queries, "ML_COVERED_ASSETS", ())
    monkeypatch.setattr("controllers.nft_pull.pull_nft", lambda c, f, s: {"collections": "skipped"})
    monkeypatch.setattr(nft_items, "pull_item_values", lambda c, f, s: {"items": "no NFT holdings; nothing to pull"})
    out = pull.pull_all(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404))))
    assert out["NFT items"] == {"items": "no NFT holdings; nothing to pull"}


def test_rarity_accuracy_note_is_stored_and_optional_for_older_ml_bodies():
    """D84: the rarest-10% line is passed through; an ML body from before 10.9 (no such field) still stores."""
    row = nft_items.item_row(_item("azuki", "1", rare=RARE), NOW)
    assert row["rarity_accuracy_note"] == RARE and row["accuracy_note"] == ACC
    old = {k: v for k, v in _item("azuki", "1").items() if k != "rarity_accuracy_note"}
    assert nft_items.item_row(old, NOW)["rarity_accuracy_note"] is None
