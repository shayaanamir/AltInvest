"""Phase 10 step 10.5: item metadata fill, rarity over known tokens, and the item data checks (D68).
Hand-made frames, no network, no snapshot files. The wash rules themselves are tested in test_nft_data.py."""

import numpy as np
import pandas as pd
import pytest

from ml.nft import item_snapshot as its
from ml.nft import item_summary as isum
from ml.nft import sales as sl
from ml.nft import traits as tr


def _tokens(ids, n_traits):
    return pd.DataFrame({"slug": "c", "token_id": ids, "name": [f"C #{i}" if n else "" for i, n in zip(ids, n_traits)],
                         "image_url": "", "n_traits": n_traits})


def _traits(rows):
    return pd.DataFrame(rows, columns=tr.TRAIT_COLUMNS)


BASE_TRAITS = _traits([("c", "1", "Fur", "Gold"), ("c", "2", "Fur", "Brown"), ("c", "3", "Fur", "Brown")])


def test_known_only_rarity_does_not_rank_unread_metadata_as_rare():
    tokens = _tokens(["1", "2", "3", "4"], [1, 1, 1, 0])
    old = tr.rarity_all(tokens, BASE_TRAITS).set_index("token_id")
    assert old.loc["4", "rarity_rank"] == 1                       # 'none' (1 of 4) looks as rare as Gold
    new = tr.rarity_all(tokens, BASE_TRAITS, known_only=True).set_index("token_id")
    assert pd.isna(new.loc["4", "rarity_rank"]) and np.isnan(new.loc["4", "rarity_score"])
    assert new.loc["1", "rarity_score"] == pytest.approx(-np.log(1 / 3))             # shares over 3 known tokens
    assert new.loc["1", "rarity_rank"] == 1 and new.loc["2", "rarity_rank"] == 2


def test_opensea_item_parses_like_alchemy_metadata():
    nft = {"identifier": "4", "name": "C #4", "image_url": "u", "traits": [{"trait_type": "Fur", "value": "Gold"}]}
    token, rows = tr.parse_token(tr.from_opensea(nft), "c")
    assert token == {"slug": "c", "token_id": "4", "name": "C #4", "image_url": "u", "n_traits": 1}
    assert rows == [{"slug": "c", "token_id": "4", "trait_type": "Fur", "value": "Gold"}]


def test_merge_fills_only_missing_tokens_and_keeps_the_base_rows():
    base_tokens = _tokens(["1", "2", "3", "4", "5"], [1, 1, 1, 0, 0])
    fill_tokens = _tokens(["4", "5", "1"], [1, 0, 1])               # 5 stays unread; 1 already had traits
    fill_traits = _traits([("c", "4", "Fur", "Gold"), ("c", "1", "Fur", "SHOULD-NOT-REPLACE")])
    traits, tokens = its.merge(base_tokens, BASE_TRAITS, fill_tokens, fill_traits)
    assert traits[traits["token_id"] == "1"]["value"].tolist() == ["Gold"]          # base rows win
    assert traits[traits["token_id"] == "4"]["value"].tolist() == ["Gold"]
    t = tokens.set_index("token_id")
    assert t.loc["4", "n_traits"] == 1 and not t.loc["4", "traits_missing"] and t.loc["4", "name"] == "C #4"
    assert t.loc["5", "traits_missing"] and pd.isna(t.loc["5", "rarity_rank"])
    assert t.loc["2", "rarity_score"] == pytest.approx(-np.log(2 / 4))               # Brown: 2 of 4 known tokens
    assert its.missing_tokens(base_tokens)["token_id"].tolist() == ["4", "5"]


def _sale(token, date, buyer="b", seller="s", tx=None, price=1.0):
    ts = int(pd.Timestamp(date, tz="UTC").timestamp()) + 60
    return {"slug": "c", "token_id": token, "timestamp": ts, "date": date, "price_eth": price, "payment_symbol": "ETH",
            "buyer": buyer, "seller": seller, "tx": tx or f"t{token}{date}", "protocol_address": "",
            "marketplace": "unknown"}


def test_checks_count_each_problem_and_pass_on_clean_data():
    floor = pd.DataFrame({"slug": "c", "date": ["2025-01-01", "2025-01-02"]})
    eth = pd.DataFrame({"date": ["2025-01-01", "2025-01-02"], "eth_usd": [2000.0, 2100.0]})
    tokens = _tokens(["1", "2"], [1, 1]).assign(traits_missing=False)
    raw = pd.DataFrame([_sale("1", "2025-01-01"), _sale("2", "2025-01-02")])
    clean = isum.checks(raw, raw, floor, eth, tokens, BASE_TRAITS)
    assert not any(clean.values())
    bad = pd.DataFrame([_sale("1", "2025-01-01"), _sale("1", "2025-01-01"), _sale("9", "2025-01-03", buyer="")])
    tokens2 = tokens.assign(traits_missing=[True, False])
    c = isum.checks(bad, bad, floor, eth, tokens2, pd.concat([BASE_TRAITS, BASE_TRAITS.iloc[:1]]))
    assert c == {"duplicate_sales": 1, "sales_without_floor_for_their_date": 1, "sales_without_eth_usd_for_their_date": 1,
                 "sales_with_empty_buyer_or_seller": 1, "sold_tokens_without_metadata": 1,
                 "sold_tokens_without_traits": 1, "duplicate_trait_rows": 1}
    assert isum.with_usd(raw, eth)["price_usd"].tolist() == [2000.0, 2100.0]
    assert sl.KEY == ["slug", "tx", "token_id", "seller", "buyer"]
