"""Phase 11 (ml/docs/DECISIONS.md D87): pulling /past-ranges and trimming it for the asset chart.
Mocked HTTP client and mocked database writes (no network, no Mongo)."""
import httpx
import pytest

import db.queries as queries
from controllers import ml_pull_controller as pull
from controllers.asset_detail_controller import PAST_RANGE_MAX_PRICE_GAP, past_ranges_for_chart, price_gap


def _point(date, made_on, close=100.0):
    return {"date": date, "made_on": made_on, "centre": 95.0, "volatility": 0.5, "inner_lower": 88.0,
            "inner_upper": 102.0, "outer_lower": 82.0, "outer_upper": 110.0, "close": close}


BODY = {
    "asset": "BTC", "timestamp": "2026-11-16T00:10:00Z", "lag_days": 30, "volatility_measure": "vol_30d",
    "note": "Each day's range is ... Not a price prediction (D87).",
    "points": [_point("2026-11-14", "2026-10-15"), _point("2026-11-15", "2026-10-16", 120.0)],
}


@pytest.fixture
def stored(monkeypatch):
    rows = []
    monkeypatch.setattr(queries, "replace_ml_past_ranges", rows.append)
    return rows


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _no_sleep(_):
    pass


def test_200_replaces_the_document_with_every_point(stored):
    seen = []

    def handler(req):
        seen.append(str(req.url))
        return httpx.Response(200, json=BODY)

    assert pull.pull_past_ranges(_client(handler), "BTC", sleep=_no_sleep) == "stored: 2 points"
    assert seen[0].endswith(f"/past-ranges/btc?days={pull.PAST_RANGES_DAYS}")
    row = stored[0]
    assert row["points"] == BODY["points"] and row["lag_days"] == 30 and row["source"] == "ml-service"
    assert row["timestamp"].year == 2026


@pytest.mark.parametrize("status", [404, 503])
def test_404_and_503_write_nothing(stored, status):
    out = pull.pull_past_ranges(_client(lambda r: httpx.Response(status)), "BTC", sleep=_no_sleep)
    assert out.startswith("skipped" if status == 404 else "failed") and stored == []


@pytest.mark.parametrize("bad", [
    {**BODY, "asset": "ETH"},
    {k: v for k, v in BODY.items() if k != "points"},
    {**BODY, "points": [{"date": "2026-11-15"}]},
    {**BODY, "points": "none"},
])
def test_bad_body_writes_nothing(stored, bad):
    out = pull.pull_past_ranges(_client(lambda r: httpx.Response(200, json=bad)), "BTC", sleep=_no_sleep)
    assert out.startswith("failed: bad body") and stored == []
    assert pull.has_failures({"past ranges": {"BTC": out}})


def test_pull_all_includes_past_ranges(monkeypatch, stored):
    monkeypatch.setattr(queries, "ML_COVERED_ASSETS", ("BTC",))
    monkeypatch.setattr(pull, "pull_asset", lambda c, a, sleep: {"predict": "stored", "risk": "stored"})
    monkeypatch.setattr("controllers.nft_pull.pull_nft", lambda c, f, s: {})
    monkeypatch.setattr("controllers.nft_items.pull_item_values", lambda c, f, s: {})
    out = pull.pull_all(client=_client(lambda r: httpx.Response(200, json=BODY)), sleep=_no_sleep)
    assert out["past ranges"] == {"BTC": "stored: 2 points"}


def test_chart_gets_only_the_points_inside_the_history_window():
    doc = {**BODY, "points": [_point("2026-11-13", "2026-10-14"), *BODY["points"],
                              _point("2026-11-16", "2026-10-17")]}
    history = [{"date": "2026-11-14", "price": 100.5}, {"date": "2026-11-15", "price": 119.0}]
    out = past_ranges_for_chart(doc, history)
    assert [p["date"] for p in out["points"]] == ["2026-11-14", "2026-11-15"]
    assert out["lag_days"] == 30 and "Not a price prediction" in out["note"]
    assert set(out["points"][0]) == {"date", "made_on", "inner_lower", "inner_upper", "outer_lower", "outer_upper",
                                     "close"}


def test_chart_gets_null_without_a_document_or_overlap():
    history = [{"date": "2026-01-01", "price": 1.0}, {"date": "2026-01-02", "price": 2.0}]
    assert past_ranges_for_chart(None, history) is None
    assert past_ranges_for_chart(BODY, history) is None
    assert past_ranges_for_chart(BODY, []) is None


def test_price_gap_is_the_median_relative_gap():
    pts = BODY["points"]                                            # closes 100 and 120
    gap = price_gap(pts, [{"date": "2026-11-14", "price": 101.0}, {"date": "2026-11-15", "price": 120.0}])
    assert gap == pytest.approx(0.005)
    assert price_gap(pts, [{"date": "2026-01-01", "price": 1.0}]) is None


def test_chart_gets_null_when_its_prices_are_not_the_ml_closes():
    """D89: demo seed prices (here 40% of the ML close, as seen in the shared database) hide the past ranges."""
    seed = [{"date": "2026-11-14", "price": 40.0}, {"date": "2026-11-15", "price": 48.0}]
    assert past_ranges_for_chart(BODY, seed) is None
    near = [{"date": "2026-11-14", "price": 100 * (1 + 0.99 * PAST_RANGE_MAX_PRICE_GAP)},
            {"date": "2026-11-15", "price": 120 * (1 + 0.99 * PAST_RANGE_MAX_PRICE_GAP)}]
    assert past_ranges_for_chart(BODY, near) is not None
