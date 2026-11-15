"""D91 seed cleanup, D92 migration check, and hidden assets; in-memory database only (no Mongo)."""
from datetime import datetime

import pytest

import db.mongo_connection as conn
import db.queries as queries
from db import cleanup_seed_data as cl
from db import migration_check as mc
from db.seed_insights import INSIGHTS
from tests.fake_mongo import FakeDB

ATLAS = "mongodb+srv://user:secret@cluster0.abcde.mongodb.net/?retryWrites=true"
T = datetime(2026, 11, 15, 0, 15)


def seeded_db() -> FakeDB:
    """Seed rows (no source / seed-v1 / fictional) next to real rows and user data."""
    return FakeDB(
        prices=[{"asset": "BTC", "price": 42000.0, "timestamp": T},                              # simulated
                {"asset": "DOGE", "price": 0.09, "timestamp": T},                                # simulated
                {"asset": "BTC", "price": 64150.0, "timestamp": T, "source": "binance-klines-1h"}],
        asset_market_data=[{"asset_id": "BTC", "price": 71450.3}, {"asset_id": "DOGE", "price": 0.1},
                           {"asset_id": "BTC", "price": 64974.47, "source": "binance-ticker"}],
        predictions=[{"asset": "BTC", "model_version": "seed-v1"}, {"asset": "ADA"},
                     {"asset": "BTC", "model_version": "baseline-last-value", "source": "ml-service"}],
        risk_scores=[{"asset": "DOGE"}, {"asset": "BTC", "source": "ml-service"}],
        risk_breakdown=[{"asset": "BTC", "volatility_index": 40}],
        aai_scores=[{"asset": "BTC", "model_version": "seed-v1"},
                    {"asset": "BTC", "model_version": "baseline-last-value"}],             # real: no source
        market_insights=[{"title": INSIGHTS[0]["title"]}, {"title": "A real headline from a feed"}],
        sentiment_themes=[{"label": "Spot ETF inflows"}],
        nft_collections=[{"slug": "azuki"}, {"slug": "astralcats"}, {"slug": "genesispunks"}],
        nft_market_data=[{"slug": "azuki", "floor_eth": 9.9}, {"slug": "astralcats"},
                         {"slug": "azuki", "floor_eth": 0.9, "source": "ml-service"}],
        nft_tokens=[{"slug": "boredapeyachtclub", "token_id": "4271"}],
        assets=[{"asset_id": a} for a in ("BTC", "ETH", "SOL", "DOGE", "BASE")],
        watchlists=[{"name": "w", "items": [{"type": "crypto", "symbol_or_slug": "DOGE"},
                                            {"type": "nft", "symbol_or_slug": "astralcats"},
                                            {"type": "crypto", "symbol_or_slug": "BTC"}]}],
        portfolio_holdings=[{"symbol": "BASE"}, {"symbol": "BTC"}],
        portfolio_transactions=[{"symbol": "BASE"}],
        alerts=[{"target_symbol": "DOGE"}],
        users=[{"email": "demo@example.com"}],
    )


def counts(rep):
    return {r["collection"]: r["matched"] for r in rep["rules"] if r["matched"]}


def test_dry_run_counts_only_seed_rows():
    db = seeded_db()
    rep = cl.report(db)
    assert counts(rep) == {"prices": 2, "asset_market_data": 2, "predictions": 2, "risk_scores": 1,
                           "risk_breakdown": 1, "aai_scores": 1, "market_insights": 1, "sentiment_themes": 1,
                           "nft_collections": 2, "nft_market_data": 2, "nft_tokens": 1}
    doge = next(u for u in rep["unsourced_assets"] if u["asset_id"] == "DOGE")
    assert (doge["watchlist_items"], doge["alerts"]) == (1, 1)
    base = next(u for u in rep["unsourced_assets"] if u["asset_id"] == "BASE")
    assert (base["holdings"], base["transactions"]) == (1, 1)
    assert [u["asset_id"] for u in rep["unsourced_assets"]] == ["BASE", "DOGE"]
    assert rep["fictional_collection_watchlist_items"] == {"astralcats": 1}


def test_apply_keeps_every_real_row_and_all_user_data():
    db = seeded_db()
    cl.apply(db)
    assert [d.get("source") for d in db.prices.docs] == ["binance-klines-1h"]
    assert [d["source"] for d in db.asset_market_data.docs] == ["binance-ticker"]
    assert [d["model_version"] for d in db.aai_scores.docs] == ["baseline-last-value"]
    assert [d["title"] for d in db.market_insights.docs] == ["A real headline from a feed"]
    assert [d["slug"] for d in db.nft_collections.docs] == ["azuki"]
    assert db.nft_market_data.docs == [{"slug": "azuki", "floor_eth": 0.9, "source": "ml-service"}]
    assert len(db.assets.docs) == 5 and len(db.watchlists.docs[0]["items"]) == 3          # keep mode: untouched
    assert len(db.portfolio_holdings.docs) == 2 and len(db.users.docs) == 1 and len(db.alerts.docs) == 1
    assert cl.report(db)["rules"] and not counts(cl.report(db))                           # idempotent: nothing left


def test_hide_and_prune():
    db = seeded_db()
    done = cl.apply(db, "hide", prune_watchlists=True)
    assert done["assets hidden"] == 2
    assert {d["asset_id"] for d in db.assets.docs if d.get("hidden")} == {"DOGE", "BASE"}
    assert [i["symbol_or_slug"] for i in db.watchlists.docs[0]["items"]] == ["DOGE", "BTC"]   # only the fictional NFT


def test_delete_mode_never_touches_holdings_or_transactions():
    db = seeded_db()
    cl.apply(db, "delete", prune_watchlists=True)
    assert [d["asset_id"] for d in db.assets.docs] == ["BTC", "ETH", "SOL"]
    assert [i["symbol_or_slug"] for i in db.watchlists.docs[0]["items"]] == ["BTC"]
    assert len(db.portfolio_holdings.docs) == 2 and len(db.portfolio_transactions.docs) == 1


@pytest.fixture
def cli_db(monkeypatch):
    db = seeded_db()
    monkeypatch.setattr(conn, "get_db", lambda: db)
    monkeypatch.setenv("MONGO_URI", ATLAS)
    monkeypatch.setenv("MONGO_DB_NAME", "altinvest_db")
    return db


def test_cli_is_a_dry_run_by_default_and_prints_no_credentials(cli_db, capsys):
    before = sum(len(c.docs) for c in cli_db._c.values())
    assert cl.main([]) == 0
    assert sum(len(c.docs) for c in cli_db._c.values()) == before
    out = capsys.readouterr().out
    assert "dry run" in out and "cluster0.abcde.mongodb.net" in out and "secret" not in out


def test_cli_on_atlas_needs_allow_remote_and_confirm(cli_db):
    with pytest.raises(SystemExit, match="refusing to clean up a non-local MongoDB"):
        cl.main(["--confirm"])                                       # remote without --allow-remote
    assert len(cli_db.prices.docs) == 3                              # nothing deleted
    assert cl.main(["--allow-remote"]) == 0                          # still a dry run without --confirm
    assert len(cli_db.prices.docs) == 3
    assert cl.main(["--confirm", "--allow-remote"]) == 0
    assert len(cli_db.prices.docs) == 1


def test_cleanup_script_is_not_a_seed_entry_point():
    """test_seed_guard checks every db/seed*.py; this script deletes, so it has its own name and guard call."""
    assert not cl.__file__.endswith(("seed.py",)) and "require_local_target" in open(cl.__file__).read()


def test_migration_check_finds_missing_and_newer_real_rows():
    src = FakeDB(
        ml_past_ranges=[{"asset": "BTC", "source": "ml-service", "pulled_at": T}],
        risk_scores=[{"asset": "BTC", "date": "2026-11-15", "source": "ml-service", "pulled_at": datetime(2026, 11, 15, 9)},
                     {"asset": "BTC", "date": "2026-11-14", "source": "ml-service", "pulled_at": T},
                     {"asset": "DOGE", "date": "2026-11-14"}],                              # no source: ignored
        fx_rates=[{"base": "USD", "as_of": "2026-11-14", "source": "frankfurter"}],
        odd=[{"x": 1, "source": "something"}],
    )
    dst = FakeDB(risk_scores=[{"asset": "BTC", "date": "2026-11-15", "source": "ml-service", "pulled_at": T}],
                 fx_rates=[{"base": "USD", "as_of": "2026-11-14"}])
    rep = mc.build(src, dst)
    r = rep["collections"]["risk_scores"]
    assert (r["real_rows_in_source"], r["missing_in_target"], r["newer_in_source"]) == (2, 1, 1)
    assert r["missing_from"] == "2026-11-14" and r["proposal"] == "COPY"
    assert rep["collections"]["ml_past_ranges"]["missing_in_target"] == 1
    assert rep["collections"]["ml_past_ranges"]["proposal"] == "RE-PULL"
    assert rep["collections"]["fx_rates"]["missing_in_target"] == 0
    assert rep["real_collections_without_a_rule"] == ["odd"]
    assert dst.risk_scores.docs[0]["pulled_at"] == T and len(src.risk_scores.docs) == 3       # read-only


def test_hidden_assets_leave_lists_search_and_detail_but_not_holdings(monkeypatch):
    db = FakeDB(assets=[{"asset_id": "BTC", "name": "Bitcoin", "symbol": "BTC"},
                        {"asset_id": "DOGE", "name": "Dogecoin", "symbol": "DOGE", "hidden": True}])
    monkeypatch.setattr(queries, "get_db", lambda: db)
    assert [a["asset_id"] for a in queries.get_supported_assets()] == ["BTC"]
    assert queries.get_asset("DOGE") is None and queries.get_asset("btc")["name"] == "Bitcoin"
    assert set(queries.get_assets_by_id(["BTC", "DOGE"])) == {"BTC", "DOGE"}
