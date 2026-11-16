"""Audit G-37: the AAI band is exposed as a rating (Strong / Neutral / Weak) next to the stable `signal` value."""
import pytest

import controllers.market_controller as mc
from models.schemas import DiscoverItem


@pytest.mark.parametrize("score, signal, rating", [(None, None, None), (80, "BUY", "Strong"), (55, "BUY", "Strong"),
                                                   (50, "HOLD", "Neutral"), (44.9, "SELL", "Weak")])
def test_rating_follows_the_signal_band(score, signal, rating):
    assert mc.aai_signal(score) == signal and mc.aai_rating(score) == rating


def test_list_fields_carry_both():
    f = mc._aai_fields({"aai_score": 61.0}, None)
    assert (f["signal"], f["rating"]) == ("BUY", "Strong")
    item = DiscoverItem(category="crypto", id="BTC", name="Bitcoin", **f)
    assert item.rating == "Strong"
