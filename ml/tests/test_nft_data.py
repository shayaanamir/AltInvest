"""Phase 10 step 10.2: NFT collection data (D55-D58, D62). Hand-made fixtures, temporary paths, no network."""

import json

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.nft import build, collect, floor as fl, liquidity as lq, refresh, sales as sl, snapshot, store, traits as tr

DAY = 86400
T0 = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp())          # midnight UTC


def _points(rows):
    return pd.DataFrame(rows, columns=["time", "token_unit", "usd_price"])


def _eth(first="2024-12-25", n=20, open0=2000.0):
    ts = pd.date_range(first, periods=n, freq="D", tz="UTC")
    return pd.DataFrame({"asset": "eth", "timestamp": ts, "open": open0 + np.arange(n), "high": 0.0, "low": 0.0,
                         "close": open0 + np.arange(n) + 0.5, "volume": 1.0})


# ---------- daily floor (D55) ----------

def test_floor_is_the_latest_point_at_or_before_midnight_and_never_a_later_one():
    pts = _points([(T0 - 3600, 5.0, "10000"), (T0 + 60, 9.0, "18000"), (T0 + DAY, 6.0, "12000")])
    f = fl.daily_floor(pts, "2025-01-03")
    assert f["date"].tolist() == ["2025-01-01", "2025-01-02", "2025-01-03"]
    assert f["floor_eth"].tolist() == [5.0, 6.0, 6.0]            # 9.0 was posted 60 s AFTER 1 Jan 00:00
    assert f["floor_point_time"].tolist() == [T0 - 3600, T0 + DAY, T0 + DAY]
    assert not f["date"].duplicated().any() and (f["date"] <= "2025-01-03").all()


def test_floor_older_than_48h_is_a_gap_but_the_asof_series_keeps_the_last_value():
    pts = _points([(T0 - 3600, 5.0, "10000"), (T0 + 3.5 * DAY, 7.0, "0")])
    f = fl.daily_floor(pts, "2025-01-05")
    assert f["floor_eth"].isna().tolist() == [False, False, True, True, False]    # 3 Jan: 49 h old; 4 Jan: 73 h
    assert f["floor_eth_asof"].tolist() == [5.0, 5.0, 5.0, 5.0, 7.0]
    assert fl.gaps(f) == ["2025-01-03", "2025-01-04"]
    assert np.isnan(f["floor_usd_source"].iloc[-1])              # OpenSea usd_price 0 is treated as missing
    assert f["floor_age_hours"].iloc[:3].tolist() == [1.0, 25.0, 49.0]       # from 31 Dec 23:00


def test_floor_rows_do_not_change_when_later_points_change():
    base = [(T0 - 3600, 5.0, "1"), (T0 + DAY - 10, 5.5, "1"), (T0 + 2 * DAY - 10, 6.0, "1")]
    a = fl.daily_floor(_points(base), "2025-01-02")
    b = fl.daily_floor(_points(base[:2] + [(T0 + DAY + 5, 99.0, "1"), (T0 + 3 * DAY, 1.0, "1")]), "2025-01-04")
    pd.testing.assert_frame_equal(a, b.iloc[:2])


def test_usd_uses_the_eth_open_of_the_same_date_and_prev_close_for_the_running_day():
    eth = fl.eth_at_midnight(_eth(n=8))                           # bars 25 Dec .. 1 Jan; 2 Jan is running
    assert eth.iloc[-1].tolist() == ["2025-01-02", 2007.5, "prev_close"]
    assert eth.iloc[-2].tolist() == ["2025-01-01", 2007.0, "open"]
    f = fl.add_usd(fl.daily_floor(_points([(T0 - 5, 2.0, "4000")]), "2025-01-02"), eth)
    assert f["floor_usd"].tolist() == [2.0 * 2007.0, 2.0 * 2007.5]
    with pytest.raises(ValueError, match="no ETH-USD price"):
        fl.add_usd(fl.daily_floor(_points([(T0 - 5, 2.0, "4000")]), "2025-01-03"), eth)


def test_intraday_median_uses_only_the_previous_utc_day():
    pts = _points([(T0 - DAY - 1, 100.0, "1"), (T0 - DAY, 1.0, "1"), (T0 - 10, 3.0, "1"), (T0, 50.0, "1")])
    assert fl.intraday_median(pts, "2025-01-01") == (2.0, 2)
    assert fl.intraday_median(pts, "2025-02-01") == (None, 0)


# ---------- sales and the wash filter (D56, D57) ----------

def _event(token="1", ts=T0 + 100, wei=2 * 10 ** 18, symbol="ETH", buyer="0xB", seller="0xA", qty=1, tx="0xT",
           protocol=None):
    e = {"event_type": "sale", "event_timestamp": ts, "transaction": tx, "quantity": qty, "buyer": buyer,
         "seller": seller, "payment": {"quantity": str(wei), "decimals": 18, "symbol": symbol},
         "nft": {"identifier": token}}
    if protocol:
        e["protocol_address"] = protocol
    return e


def test_parse_event_keeps_eth_weth_beth_and_drops_the_rest():
    row, why = sl.parse_event(_event(symbol="WETH", wei=15 * 10 ** 17), "azuki")
    assert why is None and row["price_eth"] == 1.5 and row["date"] == "2025-01-01" and row["token_id"] == "1"
    assert row["buyer"] == "0xb" and row["seller"] == "0xa" and row["marketplace"] == "unknown"
    assert sl.parse_event(_event(symbol="USDC"), "azuki") == (None, "payment_token")
    assert sl.parse_event(_event(qty=2), "azuki") == (None, "quantity_not_1")
    assert sl.parse_event(_event(wei=0), "azuki") == (None, "zero_price")
    seaport = config.NFT_SEAPORT_ADDRESSES[-1].upper().replace("0X", "0x")
    assert sl.parse_event(_event(protocol=seaport), "azuki")[0]["marketplace"] == "opensea"
    assert sl.parse_event(_event(symbol="BETH"), "azuki")[0]["marketplace"] == "blur"


def _sale(token, day, price, seller, buyer, tx):
    ts = T0 + day * DAY + 100
    return {"slug": "c", "token_id": token, "timestamp": ts,
            "date": pd.Timestamp(ts, unit="s", tz="UTC").strftime("%Y-%m-%d"), "price_eth": price,
            "payment_symbol": "ETH", "buyer": buyer, "seller": seller, "tx": tx, "protocol_address": "",
            "marketplace": "unknown"}


def _floor_rows(n=80, value=1.0):
    dates = pd.date_range("2025-01-01", periods=n, freq="D").strftime("%Y-%m-%d")
    return pd.DataFrame({"slug": "c", "date": dates, "floor_eth_asof": value})


def test_wash_rules_mark_the_first_matching_rule():
    s = pd.DataFrame([
        _sale("1", 0, 1.0, "a", "a", "t1"),              # R1 buyer == seller
        _sale("2", 0, 1.0, "a", "b", "t2"),              # R2: b sells it back 30 days later (inside the window)
        _sale("2", 30, 1.0, "b", "a", "t3"),             # R2: the other leg
        _sale("3", 0, 1.0, "a", "b", "t4"),              # kept: the return leg is 31 days later
        _sale("3", 31, 1.0, "b", "a", "t5"),             # kept
        _sale("4", 1, 0.09, "a", "b", "t6"),             # R3 below 0.10 x floor
        _sale("5", 1, 20.5, "a", "b", "t7"),             # R3 above 20 x floor
        _sale("6", 1, 0.10, "a", "b", "t8"),             # kept: exactly 0.10 x
        _sale("7", 1, 20.0, "a", "b", "t9"),             # kept: exactly 20 x
        _sale("8", 2, 0.01, "x", "x", "t10"),            # R1 comes before R3
        _sale("9", 2, 1.0, "a", "b", "t11"),             # kept: b -> a exists only for ANOTHER token
    ])
    marked = sl.wash_filter(s, _floor_rows())
    assert marked["wash_rule"].tolist() == ["R1", "R2", "R2", "", "", "R3", "R3", "", "", "R1", ""]
    assert sl.removal_counts(marked) == {"c": {"before": 11, "R1": 2, "R2": 2, "R3": 2, "kept": 5}}


def test_price_rule_uses_the_floor_of_the_sale_date_and_every_sale_needs_a_floor():
    floor = _floor_rows()
    floor.loc[floor["date"] == "2025-01-03", "floor_eth_asof"] = 100.0
    s = pd.DataFrame([_sale("1", 1, 5.0, "a", "b", "t1"), _sale("2", 2, 5.0, "a", "b", "t2")])
    assert sl.wash_filter(s, floor)["wash_rule"].tolist() == ["", "R3"]       # 5 < 0.10 x 100 on 3 Jan only
    with pytest.raises(ValueError, match="no floor for their date"):
        sl.wash_filter(pd.DataFrame([_sale("1", 500, 1.0, "a", "b", "t1")]), floor)


def test_dedupe_keeps_one_row_per_transaction_token_and_pair():
    a = _sale("1", 0, 1.0, "a", "b", "t1")
    out = sl.dedupe(pd.DataFrame([a, dict(a), _sale("1", 0, 1.0, "b", "c", "t1")]))
    assert len(out) == 2


# ---------- liquidity (D58) ----------

def _activity(counts, usd=10.0):
    dates = pd.date_range("2025-01-01", periods=len(counts), freq="D").strftime("%Y-%m-%d")
    c = np.asarray(counts, dtype=float)
    return pd.DataFrame({"date": dates, "sales_count": c, "volume_eth": c * 2.0, "volume_usd": c * usd})


def test_windows_end_at_midnight_of_the_date_and_incomplete_windows_are_nan():
    act = _activity(np.arange(1, 41))
    w = lq.windows(act, lq.first_complete_dates("2025-01-01"))
    row = w.set_index("date").loc["2025-01-31"]                  # sales on 1..30 Jan = 1 + ... + 30
    assert row["sales_30d"] == 465 and row["sales_7d"] == sum(range(24, 31)) and row["volume_30d_eth"] == 930
    assert w.set_index("date").loc["2025-01-30", ["sales_30d", "volume_30d_usd"]].isna().all()
    assert w.set_index("date").loc["2025-01-07", "sales_7d"] != w.set_index("date").loc["2025-01-07", "sales_7d"]
    assert w.set_index("date").loc["2025-01-08", "sales_7d"] == 28
    changed = act.copy()
    changed.loc[changed["date"] >= "2025-01-31", "sales_count"] = 1000        # the date itself and later
    w2 = lq.windows(changed, lq.first_complete_dates("2025-01-01"))
    pd.testing.assert_frame_equal(w[w["date"] <= "2025-01-31"], w2[w2["date"] <= "2025-01-31"])


def test_pooled_percentile_counts_ties_half_and_ignores_later_dates():
    t = pd.DataFrame({"date": ["d1", "d1", "d2", "d2", "d3"], "x": [1.0, 3.0, 3.0, 2.0, np.nan]})
    p = lq.pooled_percentiles(t, "x")
    assert p[:4].tolist() == [0.25, 0.75, 0.75, 0.375] and np.isnan(p[4])
    t2 = t.copy()
    t2.loc[2:, "x"] = [100.0, 200.0, 300.0]
    assert lq.pooled_percentiles(t2, "x")[:2].tolist() == [0.25, 0.75]


def test_scores_labels_and_the_illiquid_rule():
    t = pd.DataFrame({"slug": ["a", "b", "c"], "date": "d1", "sales_7d": [5.0, 10.0, 50.0],
                      "sales_30d": [20.0, 40.0, 200.0], "volume_7d_usd": [1.0, 2.0, 3.0],
                      "volume_30d_usd": [1.0, 2.0, 3.0]})
    out = lq.add_scores(t)
    assert out["liquidity_score"].round(4).tolist() == [16.6667, 50.0, 83.3333]
    assert out["is_illiquid"].tolist() == [True, False, False]              # N = 10: 9 is illiquid, 10 is not
    assert out["liquidity_label"].tolist() == ["Illiquid", "Medium", "High"]
    assert lq.label(32.9, False) == "Low" and lq.label(33.0, False) == "Medium" and lq.label(67.0, False) == "High"
    assert lq.label(float("nan"), False) is None and config.NFT_ILLIQUID_MIN_SALES_7D == 10


# ---------- traits (D60) ----------

def test_parse_token_reads_attributes_or_traits_and_hex_token_ids():
    a = {"tokenId": "0x0a", "name": "X #10", "image": {"cachedUrl": "u"},
         "raw": {"metadata": {"attributes": [{"trait_type": "Fur", "value": "Gold"}, {"trait_type": "Fur", "value": "dup"},
                                             {"trait_type": "Hat", "value": None}]}}}
    token, rows = tr.parse_token(a, "c")
    assert token == {"slug": "c", "token_id": "10", "name": "X #10", "image_url": "u", "n_traits": 1}
    assert rows == [{"slug": "c", "token_id": "10", "trait_type": "Fur", "value": "Gold"}]
    b = {"tokenId": "7", "raw": {"metadata": {"traits": [{"trait_type": "Eyes", "value": 3}], "image_url": "v"}}}
    token, rows = tr.parse_token(b, "c")
    assert token["image_url"] == "v" and rows[0]["value"] == "3"
    assert tr.parse_token({"tokenId": "8", "raw": {}}, "c")[0]["n_traits"] == 0


def test_rarity_counts_missing_categories_as_none_and_rank_1_is_rarest():
    tokens = pd.DataFrame({"slug": "c", "token_id": ["1", "2", "3", "4"]})
    traits = pd.DataFrame([("c", "1", "Fur", "Gold"), ("c", "2", "Fur", "Brown"), ("c", "3", "Fur", "Brown"),
                           ("c", "4", "Fur", "Brown"), ("c", "1", "Hat", "Cap")], columns=tr.TRAIT_COLUMNS)
    r = tr.rarity(tokens, traits).set_index("token_id")
    assert r.loc["1", "rarity_score"] == pytest.approx(-np.log(0.25) - np.log(0.25))     # Gold 1/4, Cap 1/4
    assert r.loc["2", "rarity_score"] == pytest.approx(-np.log(0.75) - np.log(0.75))     # Brown 3/4, none 3/4
    assert r["rarity_rank"].tolist() == [1, 2, 2, 2] and r.loc["1", "rarity_pct"] == 25.0


# ---------- store, snapshot, refresh (D62) ----------

def _live_dir(tmp_path):
    """A small live directory: 2 collections, 70 floor days, a few sales and tokens."""
    live = tmp_path / "live"
    start = int(pd.Timestamp("2024-11-09", tz="UTC").timestamp())
    pts = [(slug, start + d * DAY - 600, 1.0 + 0.01 * d + i, "2000") for i, slug in enumerate(("aa", "bb"))
           for d in range(71)]
    store.write_csv(pd.DataFrame(pts, columns=["slug", "time", "token_unit", "usd_price"]), live / "floor_points.csv")
    _eth("2024-11-01", 90).to_csv(live / "eth_1d.csv", index=False)
    s0 = int(pd.Timestamp("2024-11-10", tz="UTC").timestamp())
    rows = [{**_sale(str(k % 5).zfill(3), 0, 1.5 + i, f"s{k}", f"b{k}", f"tx{i}{k}"), "slug": slug,
             "timestamp": s0 + k * DAY + 5,
             "date": pd.Timestamp(s0 + k * DAY + 5, unit="s", tz="UTC").strftime("%Y-%m-%d")}
            for i, slug in enumerate(("aa", "bb")) for k in range(60)]
    store.write_csv(pd.DataFrame(rows)[sl.SALE_COLUMNS], live / "sales_raw.csv")
    for slug in ("aa", "bb"):
        ids = [str(k).zfill(3) for k in range(5)]
        store.write_csv(pd.DataFrame({"slug": slug, "token_id": ids, "name": "n", "image_url": "", "n_traits": 1}),
                        live / "tokens" / f"{slug}.csv")
        store.write_csv(pd.DataFrame({"slug": slug, "token_id": ids, "trait_type": "Fur",
                                      "value": ["a", "a", "b", "c", "c"]}), live / "traits" / f"{slug}.csv")
    (live / "collections.json").write_text(json.dumps({"aa": {"total_supply": 5}, "bb": {"total_supply": 5}}))
    return live


def test_csv_round_trip_keeps_token_ids_as_text(tmp_path):
    live = _live_dir(tmp_path)
    assert store.read_table(live, "sales_raw")["token_id"].iloc[0] == "000"
    assert store.read_table(live, "tokens")["token_id"].tolist()[:2] == ["000", "001"]
    assert not store.has_table(live, "nothing")


def test_build_gives_every_day_and_every_sale_a_floor_and_never_a_future_date(tmp_path):
    out = build.build(_live_dir(tmp_path), last_day="2025-01-15")
    f = out["floor"]
    assert not f.duplicated(["slug", "date"]).any() and f["date"].max() == "2025-01-15"
    assert (f["floor_usd"] == f["floor_eth"] * f["eth_usd"]).all()
    assert out["sales_marked"]["floor_eth_asof"].notna().all()
    assert f.loc[f["date"] < "2024-12-10", "liquidity_score"].isna().all()       # 30-day window not complete
    assert f.loc[f["date"] >= "2024-12-10", "liquidity_score"].notna().all()
    assert set(out["tokens"].columns) >= {"rarity_rank", "rarity_score", "rarity_pct"}
    assert f["floor_intraday_median_eth"].isna().all()                          # never backfilled (D55)


def test_snapshot_is_written_once_hashed_and_a_changed_file_is_refused(tmp_path, monkeypatch):
    live = _live_dir(tmp_path)
    monkeypatch.setattr(config, "NFT_SNAPSHOT_ROOT", tmp_path / "snapshots")
    monkeypatch.setattr(config, "NFT_SNAPSHOT_DATE", "2025-01-15")
    out = snapshot.freeze("2025-01-15", live)
    man = snapshot.manifest()
    assert set(man["files"]) == {f"{t}.parquet" for t in snapshot.TABLES}
    assert man["files"]["floor.parquet"]["range"] == ["2024-11-09", "2025-01-15"]
    assert man["wash_filter"]["aa"]["before"] == 60 and man["last_floor_date"] == "2025-01-15"
    assert snapshot.mismatches() == [] and len(snapshot.require_snapshot()) == 64
    assert snapshot.load("sales_filtered")["token_id"].iloc[0] == "000"
    assert "eth_usd.parquet" in man["files"]                                     # ETH prices frozen (D55 amended)
    with pytest.raises(SystemExit, match="never rewritten"):
        snapshot.freeze("2025-01-15", live)
    snapshot.load("floor").iloc[:-1].to_parquet(out / "floor.parquet", index=False)
    assert snapshot.mismatches() == ["floor.parquet"] and snapshot.mismatches(tables=("tokens",)) == []
    assert len(snapshot.require_snapshot("tokens", "traits")) == 64      # only the named tables are checked
    with pytest.raises(SystemExit, match=r"does not match its manifest \(D62\)"):
        snapshot.require_snapshot()


def test_refresh_refuses_the_snapshot_directory_and_older_floor_data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "NFT_SNAPSHOT_ROOT", tmp_path / "snapshots")
    monkeypatch.setattr(config, "ML_NFT_DIR", tmp_path / "snapshots" / "2025-01-15")
    with pytest.raises(refresh.SnapshotProtected, match="D62"):
        refresh.run_once()
    live = _live_dir(tmp_path)
    monkeypatch.setattr(config, "ML_NFT_DIR", live)
    before = (live / "floor_points.csv").read_bytes()
    old = store.read_csv(live / "floor_points.csv")

    def shorter(client):
        store.write_csv(old.iloc[:-5], live / "floor_points.csv")
        return old.iloc[:-5]

    monkeypatch.setattr(collect, "collect_floor", shorter)
    with pytest.raises(refresh.OlderData, match="kept the stored file"):
        refresh.refresh_floor(client=None)
    assert (live / "floor_points.csv").read_bytes() == before
