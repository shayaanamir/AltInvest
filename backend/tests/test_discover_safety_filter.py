"""Audit G-28: Discover's risk filter is "Min safety score" (risk_score >= x), since risk_score is higher = safer."""
import inspect

from fastapi import Response

import routes.discover as discover

ROWS = [
    {"category": "crypto", "id": "SAFE", "name": "Safe", "symbol": "SAFE", "risk_score": 90.0, "market_cap": 3},
    {"category": "crypto", "id": "MID", "name": "Mid", "symbol": "MID", "risk_score": 60.0, "market_cap": 2},
    {"category": "crypto", "id": "RISKY", "name": "Risky", "symbol": "RISKY", "risk_score": 20.0, "market_cap": 1},
    {"category": "crypto", "id": "NONE", "name": "None", "symbol": "NONE", "risk_score": None, "market_cap": 0},
]


def _call(monkeypatch, **kw):
    monkeypatch.setattr(discover, "_universe", lambda category, user_id: [dict(r) for r in ROWS])
    defaults = {name: p.default.default if hasattr(p.default, "default") else p.default
                for name, p in inspect.signature(discover.discover).parameters.items() if name != "response"}
    defaults.update(user_id=None, **kw)
    return [r["id"] for r in discover.discover(Response(), **defaults)]


def test_min_safety_keeps_the_safer_rows(monkeypatch):
    assert _call(monkeypatch, min_safety=60) == ["SAFE", "MID"]          # >= : 60 itself is kept
    assert _call(monkeypatch, min_safety=95) == []


def test_no_filter_keeps_unscored_rows(monkeypatch):
    assert _call(monkeypatch) == ["SAFE", "MID", "RISKY", "NONE"]


def test_max_risk_is_gone():
    assert "max_risk" not in inspect.signature(discover.discover).parameters
