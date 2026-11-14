"""Phase 10 step 10.5b: D70 item cleaning and the D71 sealed cutoff and loaders. Hand-made frames, no network."""

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.nft import item_clean as ic
from ml.nft import item_data as idt
from ml.nft import snapshot

T0 = int(pd.Timestamp("2025-03-01", tz="UTC").timestamp())
DAY = 86400


def _s(token, t, seller, buyer, tx, price=1.0, symbol="ETH", slug="c"):
    ts = T0 + int(t * DAY)
    return {"slug": slug, "token_id": token, "timestamp": ts,
            "date": pd.Timestamp(ts, unit="s", tz="UTC").strftime("%Y-%m-%d"), "price_eth": price,
            "payment_symbol": symbol, "buyer": buyer, "seller": seller, "tx": tx, "protocol_address": "",
            "marketplace": "unknown"}


POINTS = pd.DataFrame({"slug": "c", "time": [T0 - DAY, T0 + 5 * DAY, T0 + 5 * DAY + 3600], "token_unit": [1.0, 2.0, 50.0]})


def test_floor_point_is_strictly_before_the_sale():
    s = pd.DataFrame([_s("1", 0, "a", "b", "t1"), _s("2", 5, "a", "b", "t2"), _s("3", 5 + 1 / 24, "a", "b", "t3"),
                      _s("4", 5 + 2 / 24, "a", "b", "t4")])
    j = ic.join_floor_point(s, POINTS)
    # sale 2 is at exactly the point's time: that point is NOT used; sale 3 too (equal to the second point's time)
    assert j["floor_point_eth"].tolist() == [1.0, 1.0, 2.0, 50.0]
    assert j["floor_point_age_hours"].tolist() == [24.0, 144.0, 1.0, 1.0]
    early = ic.join_floor_point(pd.DataFrame([_s("9", -2, "a", "b", "t9")]), POINTS)
    assert np.isnan(early["floor_point_eth"].iloc[0])
    assert ic.drop_below_floor(early)[1] == 1                     # no floor before the sale: dropped by C3


def test_passthroughs_collapse_to_the_final_buyer_and_ambiguous_groups_drop():
    s = pd.DataFrame([_s("1", 1, "a", "m", "t1", 1.0), _s("1", 1, "m", "z", "t1", 1.2),   # a -> m -> z: keep m -> z
                      _s("2", 1, "a", "b", "t2"), _s("2", 1, "c", "d", "t2"),              # two finals: ambiguous
                      _s("3", 1, "a", "b", "t3")])
    out, c = ic.collapse_passthroughs(s)
    assert sorted(zip(out["token_id"], out["buyer"])) == [("1", "z"), ("3", "b")]
    assert c == {"C1_rows_collapsed": 1, "C1_ambiguous_rows_dropped": 2}


def test_bundles_drop_but_sweeps_from_different_sellers_stay():
    s = pd.DataFrame([_s("1", 1, "a", "b", "tb"), _s("2", 1, "a", "b", "tb"),               # bundle a -> b
                      _s("3", 1, "x", "b", "ts"), _s("4", 1, "y", "b", "ts")])              # sweep: two sellers
    out, n = ic.drop_bundles(s)
    assert n == 2 and sorted(out["token_id"]) == ["3", "4"]


def test_below_one_percent_of_the_floor_is_dropped():
    s = ic.join_floor_point(pd.DataFrame([_s("1", 1, "a", "b", "t1", 0.0099), _s("2", 1, "a", "b", "t2", 0.01)]),
                            POINTS)
    out, n = ic.drop_below_floor(s)
    assert n == 1 and out["token_id"].tolist() == ["2"]


def test_wash_flags_buyer_equals_seller_and_returns_within_30_days():
    s = pd.DataFrame([
        _s("1", 1, "a", "a", "t1"),                                            # W1
        _s("2", 1, "x", "y", "t2"), _s("2", 10, "y", "z", "t3"), _s("2", 31, "z", "x", "t4"),  # back to x in 30 d
        _s("3", 1, "x", "y", "t5"), _s("3", 31.5, "y", "x", "t6"),            # back after 30.5 days: kept
        _s("4", 1, "x", "y", "t7"), _s("4", 2, "y", "w", "t8"),               # never returns: kept
    ])
    out, counts = ic.clean(s, POINTS)
    flags = dict(zip(zip(out["token_id"], out["tx"]), out["wash_flag"]))
    assert flags[("1", "t1")] == "W1"
    assert [flags[("2", t)] for t in ("t2", "t3", "t4")] == ["W2", "W2", "W2"]
    assert flags[("3", "t5")] == "" and flags[("3", "t6")] == "" and flags[("4", "t8")] == ""
    assert counts["c"]["W1_flagged"] == 1 and counts["c"]["W2_flagged"] == 3 and counts["c"]["clean"] == 4
    assert out["clean"].sum() == 4 and set(out.columns) >= {"floor_point_eth", "sale_type", "wash_flag"}


def test_sale_type_is_descriptive_and_never_a_feature():
    assert ic.sale_type(pd.Series(["WETH", "BETH", "ETH", "USDC"])).tolist() == \
        ["bid_accept", "bid_accept", "listing_fill", "unknown"]
    assert "sale_type" in ic.NOT_FEATURES and "wash_flag" in ic.NOT_FEATURES


def test_id_like_categories_are_those_with_values_over_half_the_tokens():
    tokens = pd.DataFrame({"slug": "c", "token_id": [str(i) for i in range(10)]})
    traits = pd.concat([pd.DataFrame({"slug": "c", "token_id": tokens["token_id"], "trait_type": "Number",
                                      "value": tokens["token_id"]}),
                        pd.DataFrame({"slug": "c", "token_id": tokens["token_id"], "trait_type": "Fur",
                                      "value": ["a", "b"] * 5}),
                        pd.DataFrame({"slug": "c", "token_id": tokens["token_id"][:5], "trait_type": "Half",
                                      "value": [str(i) for i in range(5)]})])          # exactly 50%: not ID-like
    assert ic.id_like_categories(tokens, traits) == {"c": ["Number"]}


def test_sealed_cutoff_and_the_split_with_its_embargo():
    dates = pd.Series(["2025-01-05"] * 50 + ["2025-02-10"] * 30 + ["2025-03-02"] * 15 + ["2025-03-20"] * 5)
    assert idt.sealed_cutoff(dates) == "2025-03-01"              # March holds exactly 20%: the latest month that does
    assert idt.sealed_cutoff(dates, share=0.5) == "2025-02-01" and idt.sealed_cutoff(dates, share=0.51) == "2025-01-01"
    sales = pd.DataFrame({"date": ["2025-01-24", "2025-01-25", "2025-01-31", "2025-02-01", "2025-02-02"]})
    parts = idt.split(sales, "2025-02-01")
    assert parts["dev"]["date"].tolist() == ["2025-01-24"]
    assert parts["embargo"]["date"].tolist() == ["2025-01-25", "2025-01-31"]
    assert parts["sealed"]["date"].tolist() == ["2025-02-01", "2025-02-02"]


def test_dev_loader_never_returns_a_date_at_or_after_t_minus_7_and_the_sealed_loader_refuses():
    assert config.NFT_FV_SEALED_START == "2026-02-01"
    with pytest.raises(PermissionError, match="10.8"):
        idt.load_sealed("10.6")
    if not (snapshot.snapshot_dir(config.NFT_ITEM_SNAPSHOT_V3) / "sales.parquet").exists():
        pytest.skip("v3 item snapshot files are local only (D64)")
    dev = idt.load_dev()
    assert dev["sales"]["date"].max() < idt.embargo_start(config.NFT_FV_SEALED_START) == "2026-01-25"
    assert dev["sales"]["clean"].all() and dev["sales"]["price_usd"].notna().all()


def test_d72_sales_check_rule_and_withdrawal_threshold():
    from ml.nft import item_report as ir
    floor = pd.DataFrame({"slug": "c", "date": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-03-01"],
                          "floor_eth_asof": [0.1, 0.1, 0.1, 1.0, 0.1], "floor_eth_model": [1.0, 1.0, 1.0, 1.0, 1.0]})
    sales = pd.DataFrame({"slug": "c", "date": ["2025-01-01", "2025-01-01", "2025-01-02", "2025-03-01"],
                          "price_eth": [0.9, 1.2, 0.12, 0.1]})
    r = ir.d66_sales_check(floor, sales, before="2025-02-01")       # 2025-03-01 is after the cut: never looked at
    assert r["per_collection"]["c"] == {"guarded_days": 3, "no_evidence": 1, "supports_raw": 1, "supports_guarded": 1}
    assert [d["verdict"] for d in r["days"]] == ["supports guarded", "supports raw", "no evidence"]
    assert r["days"][0]["p_min"] == 0.9 and r["evidence_days"] == 2 and r["ewma_approval_withdrawn"]   # 1/2 > 1/3
    sales2 = sales.assign(price_eth=[0.9, 1.2, 0.9, 0.1])
    assert not ir.d66_sales_check(floor, sales2, before="2025-02-01")["ewma_approval_withdrawn"]       # 0/2
