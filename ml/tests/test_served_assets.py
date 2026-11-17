"""D94: 13 more assets are SERVED (data, no-change baseline, 30-day volatility, D36 risk score); every evaluation
stays on the 3 EVALUATED assets. No network: the serving tables here are hand-made, NOT market data."""

import inspect

import numpy as np
import pandas as pd
import pytest

from ml import config
from ml.data.serving_gate import NotServable
from ml.evaluation import live_score, run_sealed_test, run_walkforward_price_v2, run_walkforward_risk_v2
from ml.serving import prediction_log
from ml.serving import responses as rs

NEW = ("bnb", "xrp", "ada", "avax", "doge", "dot", "link", "matic", "uni", "ltc", "atom", "near", "arb")


def test_evaluated_assets_are_still_the_original_three():
    assert config.ASSETS == ("btc", "eth", "sol")
    assert config.ASSET_SYMBOLS == {"btc": "BTCUSDT", "eth": "ETHUSDT", "sol": "SOLUSDT"}


def test_served_assets_are_the_evaluated_three_plus_thirteen():
    assert config.SERVED_ASSETS == config.ASSETS + NEW
    assert {a: config.SERVED_ASSET_SYMBOLS[a] for a in config.ASSETS} == config.ASSET_SYMBOLS
    assert config.SERVED_ASSET_SYMBOLS["matic"] == "POLUSDT"           # MATIC -> POL migration
    assert all(s.endswith("USDT") for s in config.SERVED_ASSET_SYMBOLS.values())
    assert "dai" not in config.SERVED_ASSETS                           # a stablecoin: not served


def test_no_direction_model_is_served_for_any_asset():
    assert set(config.DIRECTION_SERVED) == set(config.SERVED_ASSETS)
    assert not any(config.DIRECTION_SERVED.values())


@pytest.mark.parametrize("module", [run_sealed_test, run_walkforward_price_v2, run_walkforward_risk_v2,
                                    live_score, prediction_log])
def test_evaluation_and_live_tracking_never_read_the_served_list(module):
    """The sealed test, the walk-forwards and live tracking loop over config.ASSETS only (D40 snapshot guard)."""
    src = inspect.getsource(module)
    assert "SERVED_ASSETS" not in src and "SERVED_ASSET_SYMBOLS" not in src


def _table(n: int, level: float) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC")
    vol = level + 0.001 * np.sin(np.arange(n))
    return pd.DataFrame({"vol_30d": vol, "ewma_vol": vol, "ret_1d": 0.001 * np.cos(np.arange(n))}, index=idx)


def test_risk_score_is_pooled_over_every_served_asset():
    """D36 over the D94 pool: the calmest asset scores highest, and widening the pool moves BTC's score."""
    now = pd.Timestamp("2025-03-01", tz="UTC").to_pydatetime()
    small = {"btc": _table(60, 0.03), "eth": _table(60, 0.04), "sol": _table(60, 0.05)}
    wide = {**small, "link": _table(60, 0.02), "doge": _table(60, 0.06)}
    btc_small = rs.risk_inputs("btc", now, small)
    btc_wide = rs.risk_inputs("btc", now, wide)
    assert btc_small["pool_assets"] == ["btc", "eth", "sol"]
    assert btc_wide["pool_assets"] == ["btc", "eth", "sol", "link", "doge"]
    assert btc_wide["risk_score"] != btc_small["risk_score"]
    scores = {a: rs.risk_inputs(a, now, wide)["risk_score"] for a in wide}
    assert max(scores, key=scores.get) == "link" and min(scores, key=scores.get) == "doge"
    assert "BTC, ETH, SOL, LINK, DOGE" in rs.risk("btc", now, wide)["note"]


def test_a_failing_served_asset_is_left_out_but_an_evaluated_one_refuses_all(monkeypatch):
    def fake(asset):
        if asset in ("link", "sol"):
            raise NotServable(f"{asset}: raw CSV is missing")
        return _table(60, 0.03)
    monkeypatch.setattr(rs, "_table", fake)
    feats = rs.feature_tables(assets=("btc", "eth", "link"))
    assert list(feats) == ["btc", "eth"]
    with pytest.raises(NotServable, match="link"):
        rs.risk_inputs("link", pd.Timestamp("2025-03-01", tz="UTC").to_pydatetime(), feats)
    with pytest.raises(NotServable, match="sol"):
        rs.feature_tables(assets=("btc", "sol", "link"))


@pytest.mark.parametrize("asset", config.SERVED_ASSETS)
def test_fetch_cli_accepts_every_served_asset(monkeypatch, asset):
    """D94: python -m ml.data.fetch --asset X works for all 16 served assets (any case); DAI is refused."""
    from ml.data import fetch
    seen = []
    monkeypatch.setattr(fetch, "fetch", lambda a: seen.append(a) or {"asset": a})
    monkeypatch.setattr("sys.argv", ["fetch", "--asset", asset.upper()])
    fetch.main()
    assert seen == [asset]


def test_fetch_cli_refuses_dai(monkeypatch):
    from ml.data import fetch
    monkeypatch.setattr("sys.argv", ["fetch", "--asset", "dai"])
    with pytest.raises(SystemExit):
        fetch.main()
