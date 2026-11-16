"""Asset profiles from CoinGecko (controllers/asset_profile_controller.py). HTTP and Mongo are faked.
The category lists are CoinGecko's real tags for these coins (fetched 2026-11-16)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from controllers import asset_profile_controller as ap
from controllers.asset_detail_controller import related_and_similar

NOW = datetime(2026, 11, 16, 7, 0, tzinfo=timezone.utc)

BTC = ["Smart Contract Platform", "Layer 1 (L1)", "FTX Holdings", "Proof of Work (PoW)", "Bitcoin Ecosystem",
       "GMCI 30 Index", "GMCI Index", "Coinbase 50 Index"]
ETH = ["Smart Contract Platform", "Layer 1 (L1)", "Ethereum Ecosystem", "FTX Holdings", "Multicoin Capital Portfolio",
       "Proof of Stake (PoS)", "GMCI Layer 1 Index", "Coinbase 50 Index"]
BNB = ["Smart Contract Platform", "Exchange-based Tokens", "BNB Chain Ecosystem", "Centralized Exchange (CEX) Token",
       "Layer 1 (L1)", "Ethereum Ecosystem", "Alleged SEC Securities", "FTX Holdings", "Proof of Stake (PoS)"]
DAI = ["Stablecoins", "Decentralized Finance (DeFi)", "USD Stablecoin", "Ethereum Ecosystem", "Crypto-backed Stablecoin"]
UNI = ["Decentralized Exchange (DEX)", "Decentralized Finance (DeFi)", "Ethereum Ecosystem", "Andreessen Horowitz (a16z) Portfolio"]


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(ap, "_sleep", lambda s: None)


def test_subcategory_follows_the_coingecko_tags():
    assert ap.subcategory_of(BTC) == "Layer 1"
    assert ap.subcategory_of(BNB) == "Exchange token"          # more specific than its Layer 1 tag
    assert ap.subcategory_of(DAI) == "Stablecoin"              # before DeFi
    assert ap.subcategory_of(UNI) == "DEX"
    assert ap.subcategory_of(["Layer 2 (L2)", "Ethereum Ecosystem"]) == "Layer 2"
    assert ap.subcategory_of(["Meme", "Dog-Themed"]) == "Meme"
    assert ap.subcategory_of(["Something new"]) is None and ap.subcategory_of([]) is None


def test_profile_fields_from_a_coin():
    coin = {"id": "bitcoin", "categories": BTC + [None],
            "links": {"homepage": ["", "http://www.bitcoin.org"]},
            "description": {"en": "Bitcoin is the first <a href='x'>decentralized</a> currency. It is mined. It has a cap. Fourth."}}
    f = ap.profile_fields(coin)
    assert f["description"] == "Bitcoin is the first decentralized currency. It is mined. It has a cap."
    assert f["website"] == "http://www.bitcoin.org" and f["subcategory"] == "Layer 1"
    assert f["categories"] == BTC and f["profile_source"] == "coingecko" and f["coingecko_id"] == "bitcoin"
    assert ap.profile_fields({"id": "x", "description": {"en": ""}})["description"] is None


def test_related_assets_share_specific_tags_not_portfolios_or_ubiquitous_ones():
    cats = {"BTC": BTC, "ETH": ETH, "BNB": BNB, "DAI": DAI, "UNI": UNI}
    rel = ap.related_from_categories(cats, {"ETH": 2e11, "BNB": 7e10, "DAI": 4e9, "UNI": 3e9})
    related, basis = rel["DAI"]
    # 4 of these 5 carry "Ethereum Ecosystem", so it is too common to mean anything; DeFi is not.
    assert related == ["UNI"] and basis["UNI"] == ["Decentralized Finance (DeFi)"]
    assert rel["BTC"] == ([], {})                            # Layer 1 / FTX Holdings / indices don't count
    assert "Alleged SEC Securities" not in str(rel["BNB"][1])


def _db(assets, caps=()):
    class Coll:
        def __init__(self, rows):
            self.rows, self.updates = rows, []

        def find(self, flt=None, proj=None):
            return [dict(r) for r in self.rows]

        def update_one(self, flt, update):
            self.updates.append((flt["asset_id"], update["$set"]))
    return SimpleNamespace(assets=Coll(assets), asset_market_data=Coll([{"asset_id": a, "market_cap": c} for a, c in caps]))


def _coin_handler(seen, rate_limit_after=None):
    def handler(req):
        cg = req.url.path.rsplit("/", 1)[-1]
        seen.append(cg)
        if rate_limit_after is not None and len(seen) > rate_limit_after:
            return httpx.Response(429, headers={"retry-after": "60"})
        cats = {"bitcoin": BTC, "ethereum": ETH, "dai": DAI, "uniswap": UNI}.get(cg, [])
        return httpx.Response(200, json={"id": cg, "categories": cats, "links": {"homepage": [f"https://{cg}.org"]},
                                         "description": {"en": f"{cg} is a coin."}})
    return handler


def test_refresh_fills_missing_profiles_first_and_recomputes_related():
    fresh = NOW - timedelta(days=1)
    db = _db([{"asset_id": "BTC", "profile_updated_at": fresh, "categories": BTC},
              {"asset_id": "ETH"}, {"asset_id": "DAI"}, {"asset_id": "UNI", "profile_updated_at": NOW - timedelta(days=9)}])
    seen = []
    out = ap.refresh_profiles(client=httpx.Client(transport=httpx.MockTransport(_coin_handler(seen))), db=db, now=NOW, limit=3)
    assert seen == ["ethereum", "dai", "uniswap"]            # missing ones first, BTC is fresh
    assert out["refreshed"] == ["ETH", "DAI", "UNI"] and out["stopped"] is None
    profile = next(u for a, u in db.assets.updates if a == "DAI" and "subcategory" in u)
    assert profile["subcategory"] == "Stablecoin" and profile["website"] == "https://dai.org" and profile["profile_updated_at"] == NOW
    related = {a: u for a, u in db.assets.updates if "related_assets" in u}
    assert set(related) == {"BTC", "ETH", "DAI", "UNI"} and "UNI" in related["DAI"]["related_assets"]


def test_refresh_stops_at_a_rate_limit_and_leaves_the_rest_for_later():
    db = _db([{"asset_id": "ETH"}, {"asset_id": "DAI"}, {"asset_id": "UNI"}])
    seen = []
    out = ap.refresh_profiles(client=httpx.Client(transport=httpx.MockTransport(_coin_handler(seen, rate_limit_after=1))),
                              db=db, now=NOW, limit=3)
    assert out["refreshed"] == ["ETH"] and out["stopped"] == "rate limited" and out["due_left"] == 2
    assert len(seen) == 2                                     # no call after the 429


def test_related_reason_names_the_shared_tag():
    universe = [{"id": "DAI", "market_cap": 4e9}, {"id": "UNI", "market_cap": 3e9}]
    asset = {"asset_id": "DAI", "related_assets": ["UNI"], "related_basis": {"UNI": ["Decentralized Finance (DeFi)"]}}
    related, _ = related_and_similar(asset, universe)
    assert related[0]["reason"] == "Both tagged “Decentralized Finance (DeFi)” on CoinGecko"
