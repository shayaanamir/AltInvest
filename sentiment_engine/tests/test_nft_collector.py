"""NFT collector: per-target search feeds, broad-feed matching, dates, dedup. No network: feeds are parsed from strings."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from urllib.parse import parse_qs, urlparse

import feedparser

from nft_sentiment import collector
from nft_sentiment import config as cfg

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def _rss(items):
    body = ""
    for it in items:
        source = f'<source url="https://x.example">{it["source"]}</source>' if it.get("source") else ""
        date = f"<pubDate>{format_datetime(NOW - timedelta(hours=it['age']))}</pubDate>" if "age" in it else ""
        body += (f"<item><title>{it['title']}</title><link>https://x.example/{abs(hash(it['title']))}</link>"
                 f"<description>{it.get('summary', '')}</description>{date}{source}</item>")
    return feedparser.parse(f'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>{body}</channel></rss>')


def _search(target, items, name="Google News"):
    return ({"name": name, "kind": "search", "target": target, "url": "u"}, _rss(items))


def _broad(items, name="CoinDesk", trust=1.0):
    return ({"name": name, "kind": "broad", "url": "b", "trust_weight": trust}, _rss(items))


def _build(feeds, slugs=("boredapeyachtclub", "mutant-ape-yacht-club", "azuki")):
    return collector.build_articles(feeds, collector.targets_for(list(slugs)), now=NOW)


def test_search_entry_goes_only_to_its_target_with_publisher_and_trust():
    out = _build([_search("azuki", [
        {"title": "Azuki floor jumps after anime deal - CoinDesk", "source": "CoinDesk", "age": 5},
        {"title": "Bored Ape and Azuki holders meet - Unknown Blog", "source": "Unknown Blog", "age": 6},
    ])])
    titles = [a["title"] for a in out["azuki"]]
    assert titles == ["Azuki floor jumps after anime deal", "Bored Ape and Azuki holders meet"]  # suffix stripped
    assert out["boredapeyachtclub"] == []        # the Azuki search feed is not matched against other targets
    first = out["azuki"][0]
    assert first["source"] == "CoinDesk" and first["via"] == "Google News"
    assert first["trust_weight"] == cfg.SOURCE_TRUST["CoinDesk"]
    assert out["azuki"][1]["trust_weight"] == cfg.SEARCH_TRUST_DEFAULT


def test_search_hit_that_does_not_name_the_collection_is_dropped():
    out = _build([_search("azuki", [{"title": "Ethereum Foundation dispute widens", "source": "KuCoin", "age": 3}])])
    assert out["azuki"] == []


def test_broad_feed_is_matched_against_every_target():
    out = _build([_broad([{"title": "Yuga Labs announces Otherside update", "age": 2}])])
    assert len(out["boredapeyachtclub"]) == 1 and len(out["mutant-ape-yacht-club"]) == 1
    assert out["azuki"] == []
    assert out["boredapeyachtclub"][0]["source"] == "CoinDesk" and out["boredapeyachtclub"][0]["via"] is None


def test_bored_ape_does_not_match_mutant_ape():
    out = _build([_broad([{"title": "Mutant Ape floor slides 10%", "age": 2}])])
    assert out["boredapeyachtclub"] == [] and len(out["mutant-ape-yacht-club"]) == 1


def test_pengu_the_game_character_is_not_the_pengu_token():
    out = _build([_broad([
        {"title": "TFT Prismatic Tour Set Revealed With Pengu's All-Star Lineup", "age": 2},
        {"title": "PENGU rallies 12% as Pudgy toys hit Walmart", "age": 3},
        {"title": "Whales accumulate $PENGU", "age": 4},
    ])], slugs=("pudgypenguins",))
    assert [a["title"] for a in out["pudgypenguins"]] == ["PENGU rallies 12% as Pudgy toys hit Walmart",
                                                         "Whales accumulate $PENGU"]


def test_old_and_undated_entries_are_dropped():
    out = _build([_search("azuki", [
        {"title": "Azuki news from last month - X", "source": "X", "age": cfg.NFT_MAX_ARTICLE_AGE_HOURS + 1},
        {"title": "Azuki undated story - X", "source": "X"},
        {"title": "Azuki fresh story - X", "source": "X", "age": 1},
    ])])
    assert [a["title"] for a in out["azuki"]] == ["Azuki fresh story"]


def test_age_is_computed_in_utc():
    out = _build([_search("azuki", [{"title": "Azuki story - X", "source": "X", "age": 30}])])
    assert abs(out["azuki"][0]["age_hours"] - 30) < 0.01


def test_same_story_from_google_and_bing_is_kept_once():
    item = {"title": "Azuki launches new anime series", "age": 4}
    out = _build([
        _search("azuki", [{**item, "title": item["title"] + " - Decrypt", "source": "Decrypt"}]),
        _search("azuki", [item], name="Bing News"),
    ])
    assert len(out["azuki"]) == 1


def test_market_needs_a_headline_mention():
    feeds = [_broad([
        {"title": "OpenSea volume doubles as NFT market wakes up", "age": 2},
        {"title": "Bitcoin slides below 67k", "summary": "Elsewhere, NFT traders were quiet.", "age": 2},
    ])]
    out = collector.build_articles(feeds, collector.targets_for([], include_market=True), now=NOW)
    assert [a["title"] for a in out[cfg.NFT_MARKET_ID]] == ["OpenSea volume doubles as NFT market wakes up"]


def test_search_feed_urls():
    feeds = collector.search_feeds("pudgypenguins", cfg.NFT_COLLECTIONS["pudgypenguins"])
    google = [f for f in feeds if f["name"] == "Google News"][0]
    q = parse_qs(urlparse(google["url"]).query)["q"][0]
    assert q.endswith(f"when:{cfg.SEARCH_WINDOW}") and '"Pudgy Penguins"' in q
    bing = [f for f in feeds if f["name"] == "Bing News"][0]
    assert parse_qs(urlparse(bing["url"]).query)["format"] == ["rss"]
    assert all(f["target"] == "pudgypenguins" and f["kind"] == "search" for f in feeds)


def test_bing_queries_have_no_or():
    """Bing's RSS returns nothing for OR queries (checked live 2026-11-16)."""
    for target in [*cfg.NFT_COLLECTIONS.values(), cfg.NFT_MARKET]:
        assert all(" OR " not in q for q in target.get("bing_queries", []))


def test_targets_cover_the_ml_collections():
    import ast
    import pathlib

    import pytest
    path = pathlib.Path(__file__).resolve().parents[2] / "ml" / "config.py"
    if not path.exists():
        pytest.skip("ml/ is not present (e.g. inside the backend container)")
    src = path.read_text(encoding="utf-8")
    node = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Assign)
                and any(getattr(t, "id", None) == "NFT_SLUGS" for t in n.targets))
    assert set(ast.literal_eval(node.value)) == set(cfg.NFT_COLLECTIONS)
