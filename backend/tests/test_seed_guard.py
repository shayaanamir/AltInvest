"""D69 (Phase 10 step 10.5b): seeds refuse a non-local MongoDB unless --allow-remote; compose defaults to local."""
from pathlib import Path

import pytest

from db import seed_all, seed_guard as g

ATLAS = "mongodb+srv://user:secret@cluster0.abcde.mongodb.net/?retryWrites=true"


@pytest.mark.parametrize("uri", [None, "", "mongodb://localhost:27017", "mongodb://127.0.0.1",
                                 "mongodb://mongodb:27017", "mongodb://u:p@[::1]:27017/aaip_db"])
def test_local_targets_pass(uri):
    g.require_local_target(argv=["seed"], uri=uri)


@pytest.mark.parametrize("uri", [ATLAS, "mongodb://u:p@db.example.com:27017", "mongodb://localhost,10.0.0.5:27017",
                                 "mongodb+srv://localhost"])
def test_remote_targets_are_refused_without_the_flag_and_never_print_credentials(uri):
    with pytest.raises(SystemExit) as e:
        g.require_local_target(argv=["seed"], uri=uri)
    msg = str(e.value)
    assert "refusing to seed a non-local MongoDB" in msg and "--allow-remote" in msg
    assert "secret" not in msg and "u:p" not in msg
    g.require_local_target(argv=["seed", "--allow-remote"], uri=uri)       # explicit flag: allowed


def test_hosts_are_parsed_without_credentials():
    assert g.uri_hosts(ATLAS) == ("mongodb+srv", ["cluster0.abcde.mongodb.net"])
    assert g.uri_hosts("mongodb://a:b@h1:1,h2:2/db?x=1") == ("mongodb", ["h1", "h2"])


def test_seed_all_and_every_seed_entry_point_call_the_guard(monkeypatch):
    monkeypatch.setenv("MONGO_URI", ATLAS)
    monkeypatch.setattr(seed_all, "STEPS", [("must not run", lambda: (_ for _ in ()).throw(AssertionError))])
    monkeypatch.setattr("sys.argv", ["seed_all.py"])
    with pytest.raises(SystemExit, match="refusing to seed"):
        seed_all.run()
    db_dir = Path(g.__file__).resolve().parent
    for p in sorted(db_dir.glob("seed*.py")):
        if p.name in ("seed_guard.py", "seed_all.py"):
            continue
        main = p.read_text(encoding="utf-8").split('if __name__ == "__main__":', 1)[1]
        assert "require_local_target()" in main.split("seed()")[0], p.name


def test_compose_backend_defaults_to_the_local_container():
    compose = (Path(g.__file__).resolve().parents[1] / "docker-compose.yml")
    if not compose.exists():                         # not mounted in the backend container; checked on the host
        pytest.skip("docker-compose.yml not visible here")
    text = compose.read_text(encoding="utf-8")
    assert "MONGO_URI: ${BACKEND_MONGO_URI:-mongodb://mongodb:27017}" in text
    assert "MONGO_URI: ${MONGO_URI" not in text
