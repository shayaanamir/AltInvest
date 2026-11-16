"""One-command setup (controllers/bootstrap_controller.py). Every step is faked: no network, no Mongo."""
import pytest

from controllers import bootstrap_controller as bc


@pytest.fixture
def steps(monkeypatch):
    """Replaces the real steps with recorders; returns the call log."""
    calls = []

    def make(key, result):
        def fn():
            calls.append(key)
            if isinstance(result, Exception):
                raise result
            return result
        return fn

    fake = [(k, k.title(), make(k, r)) for k, r in [
        ("coins", ("ok", "17 coins")), ("nft", ("ok", "7 collections")), ("market", ("ok", "17 priced")),
        ("sentiment", ("ok", "15 refreshed")), ("themes", ("skipped", "GROQ_API_KEY is not set")),
        ("profiles", ("ok", "17 filled"))]]
    monkeypatch.setattr(bc, "STEPS", fake)
    return calls


def test_real_steps_are_in_dependency_order():
    keys = [k for k, _, _ in bc.STEPS]
    assert keys == ["indexes", "coins", "nft", "market", "sentiment", "nft_sentiment", "insights", "themes", "profiles"]
    assert keys[0] == "indexes"                                   # before any bulk write
    assert keys.index("coins") < keys.index("profiles")           # rows must exist before profiles fill them
    assert keys.index("sentiment") < keys.index("insights") < keys.index("themes")   # headlines before themes
    assert keys[-1] == "profiles"                                 # the slow one last, so the app is usable earlier


def test_runs_every_step_in_order(steps):
    out = []
    results = bc.run(out=out.append)
    assert steps == ["coins", "nft", "market", "sentiment", "themes", "profiles"]
    assert results["themes"] == ("skipped", "GROQ_API_KEY is not set")
    assert any("(1/6)" in line for line in out) and any("SKIPPED" in line for line in out)


def test_a_failing_step_does_not_stop_the_others(steps, monkeypatch):
    def boom():
        steps.append("market")
        raise RuntimeError("CoinGecko down")
    monkeypatch.setattr(bc, "STEPS", [(k, label, boom if k == "market" else fn) for k, label, fn in bc.STEPS])
    results = bc.run(out=lambda s: None)
    assert results["market"][0] == "failed" and "CoinGecko down" in results["market"][1]
    assert steps[-1] == "profiles" and results["profiles"][0] == "ok"      # later steps still ran


def test_only_and_skip_select_steps(steps):
    bc.run(only=["coins", "profiles"], out=lambda s: None)
    assert steps == ["coins", "profiles"]
    steps.clear()
    bc.run(skip=["profiles", "themes"], out=lambda s: None)
    assert steps == ["coins", "nft", "market", "sentiment"]


def test_an_unknown_step_name_is_an_error(steps):
    with pytest.raises(ValueError, match="unknown step"):
        bc.run(only=["coin"], out=lambda s: None)


# ── the slow profile step retries when CoinGecko throttles ──────────────────

def test_profiles_wait_and_retry_after_a_rate_limit(monkeypatch):
    answers = [{"refreshed": ["BTC", "ETH"], "stopped": "rate limited"},
               {"refreshed": ["SOL"], "stopped": "rate limited"},
               {"refreshed": ["BNB"], "stopped": None}]
    slept = []
    import controllers.asset_profile_controller as ap
    monkeypatch.setattr(ap, "refresh_profiles", lambda limit: answers.pop(0))
    monkeypatch.setattr(bc, "_sleep", slept.append)
    status, detail = bc.step_profiles()
    assert status == "ok" and detail == "4 filled this run"
    assert slept == [bc.PROFILE_WAIT_SECONDS] * 2 and not answers


def test_profiles_give_up_after_the_last_round_and_say_so(monkeypatch):
    import controllers.asset_profile_controller as ap
    calls = []
    monkeypatch.setattr(ap, "refresh_profiles", lambda limit: calls.append(1) or {"refreshed": [], "stopped": "rate limited"})
    monkeypatch.setattr(bc, "_sleep", lambda s: None)
    status, detail = bc.step_profiles()
    assert status == "partial" and "run it again" in detail and len(calls) == bc.PROFILE_ROUNDS


def test_profiles_already_filled_is_ok(monkeypatch):
    import controllers.asset_profile_controller as ap
    monkeypatch.setattr(ap, "refresh_profiles", lambda limit: {"refreshed": [], "stopped": None})
    assert bc.step_profiles() == ("ok", "all already filled")


# ── the individual steps summarise honestly ─────────────────────────────────

def test_themes_without_a_key_are_skipped_not_failed(monkeypatch):
    import controllers.insights_controller as ic
    monkeypatch.setattr(ic, "refresh_themes", lambda: {"themes": None, "reason": "GROQ_API_KEY is not set"})
    assert bc.step_themes() == ("skipped", "GROQ_API_KEY is not set")
    monkeypatch.setattr(ic, "refresh_themes", lambda: {"themes": 8, "from_headlines": 36})
    assert bc.step_themes() == ("ok", "8 themes from 36 headlines")


def test_insights_with_no_headlines_say_to_run_sentiment_first(monkeypatch):
    import controllers.insights_controller as ic
    monkeypatch.setattr(ic, "refresh_insights", lambda: {"upserted": 0, "removed": 0})
    status, detail = bc.step_insights()
    assert status == "partial" and "sentiment" in detail


def test_market_reports_coins_it_could_not_get(monkeypatch):
    import controllers.market_data_controller as md
    monkeypatch.setattr(md, "refresh_market_snapshot", lambda: {"updated": 16, "missing": ["DAI"], "removed_fake_rows": 0})
    monkeypatch.setattr(md, "refresh_prices", lambda: {"BTC": 9600, "SOL": "failed: HTTP 451", "removed_fake_rows": 0})
    status, detail = bc.step_market()
    assert status == "partial" and "DAI" in detail and "SOL" in detail and "9600" in detail


def test_sentiment_counts_outcomes(monkeypatch):
    import routes.sentiment as rs
    monkeypatch.setattr(rs, "_refresh_all_assets", lambda: {"btc": "refreshed", "eth": "refreshed", "link": "failed"})
    status, detail = bc.step_sentiment()
    assert status == "partial" and "2 refreshed" in detail and "1 failed" in detail


# ── safety ──────────────────────────────────────────────────────────────────

def test_main_refuses_a_remote_database(monkeypatch, capsys):
    monkeypatch.setenv("MONGO_URI", "mongodb+srv://user:secret@cluster.example.mongodb.net/")
    monkeypatch.setattr(bc, "run", lambda **kw: pytest.fail("must not run against a remote database"))
    with pytest.raises(SystemExit) as exc:
        bc.main([])
    assert "refusing" in str(exc.value) and "secret" not in str(exc.value)


def test_main_runs_against_the_local_container_and_reports_failure(monkeypatch, capsys):
    monkeypatch.setenv("MONGO_URI", "mongodb://mongodb:27017")
    monkeypatch.setattr(bc, "run", lambda **kw: {"coins": ("ok", "17 coins"), "market": ("failed", "boom")})
    assert bc.main([]) == 1
    printed = capsys.readouterr().out
    assert "FAILED" in printed and "Run the command again" in printed
    monkeypatch.setattr(bc, "run", lambda **kw: {"coins": ("ok", "17 coins")})
    assert bc.main([]) == 0
