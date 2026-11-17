"""The home focus values the Settings API accepts (backend/models/schemas.py) agree with the ones
onboarding writes and with the landing pages the frontend can resolve."""
import pytest
from pydantic import ValidationError

from models.schemas import PreferencesPatch
from routes.profile import FOCUS_LANDING, _VALID_FOCUS

LANDING_PAGES = {"Dashboard", "Portfolio", "Discover", "Sentiment"}


@pytest.mark.parametrize("focus", sorted(_VALID_FOCUS))
def test_every_focus_is_accepted_by_the_settings_patch(focus):
    assert PreferencesPatch(default_dashboard_layout=focus).default_dashboard_layout == focus


@pytest.mark.parametrize("old", ["minimal", "analyst", "trader", "ai-first", "wild"])
def test_the_old_layout_names_are_no_longer_writable(old):
    with pytest.raises(ValidationError):
        PreferencesPatch(default_dashboard_layout=old)


def test_every_focus_lands_on_a_page_the_settings_patch_accepts():
    assert set(FOCUS_LANDING.values()) <= LANDING_PAGES
    for page in LANDING_PAGES:
        assert PreferencesPatch(default_landing_page=page).default_landing_page == page


def test_discover_is_a_valid_landing_page_but_unknown_pages_are_not():
    with pytest.raises(ValidationError):
        PreferencesPatch(default_landing_page="Alerts")
