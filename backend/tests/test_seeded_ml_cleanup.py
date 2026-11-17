"""D94 Stage 1: no seed writes predictions, risk scores, risk breakdowns or AAI scores, and
db/cleanup_seeded_ml_rows.py removes exactly the rows older seeds typed in (dry run by default)."""
import json

import pytest
from bson import ObjectId

from db import cleanup_seeded_ml_rows as cleanup
from db import seed_all


def _match(doc: dict, flt: dict) -> bool:
    for key, cond in flt.items():
        val = doc.get(key)
        if "$ne" in cond and val == cond["$ne"]:
            return False
        if "$nin" in cond and val in cond["$nin"]:
            return False
        if "$exists" in cond and (key in doc) != cond["$exists"]:
            return False
    return True


class FakeColl:
    def __init__(self, docs):
        self.docs = [{"_id": ObjectId(), **d} for d in docs]

    def find(self, flt, projection=None):
        return [dict(d) for d in self.docs if _match(d, flt)]

    def find_one(self, flt):
        return next((d for d in self.docs if d["_id"] == flt["_id"]), None)

    def insert_many(self, rows):
        self.docs.extend(dict(r) for r in rows)

    def count_documents(self, flt):
        return len(self.find(flt))

    def delete_many(self, flt):
        gone = self.find(flt)
        self.docs = [d for d in self.docs if d not in gone]
        return type("R", (), {"deleted_count": len(gone)})()


class FakeDb(dict):
    name = "test_db"


def _db():
    return FakeDb(
        predictions=FakeColl([
            {"asset": "BTC", "source": "ml-service", "model_version": "baseline-last-value"},
            {"asset": "LINK", "model_version": "seed-v1", "predicted_price": 17.22},
            {"asset": "DAI", "model_version": "seed-v1"},
        ]),
        risk_scores=FakeColl([
            {"asset": "BTC", "source": "ml-service", "risk_score": 85.98},
            {"asset": "LINK", "risk_score": 58.0},
        ]),
        risk_breakdown=FakeColl([
            {"asset": "BTC", "regulatory_risk": 30},
            {"asset": "LINK", "regulatory_risk": 28},
            {"asset": "LINK", "source": "measured", "liquidity_score": 60},
        ]),
        aai_scores=FakeColl([
            {"target_type": "crypto", "target_id": "BTC", "model_version": "baseline-last-value"},
            {"target_type": "crypto", "target_id": "LINK", "model_version": "seed-v1"},
            {"target_type": "crypto", "target_id": "ETH", "model_version": "mock-v1"},
            {"target_type": "nft", "target_id": "azuki", "model_version": "nft-x"},
        ]),
    )


def test_dry_run_counts_and_deletes_nothing():
    db = _db()
    r = cleanup.run(db, confirm=False)
    assert {k: v["remove"] for k, v in r.items()} == {"predictions": 2, "risk_scores": 1, "risk_breakdown": 2,
                                                      "aai_scores": 2}
    assert r["predictions"]["assets"] == {"DAI": 1, "LINK": 1}
    assert len(db["predictions"].docs) == 3 and "deleted" not in r["predictions"]


def _strip(docs):
    return [{k: v for k, v in d.items() if k != "_id"} for d in docs]


def test_confirm_backs_up_first_then_keeps_only_real_rows(tmp_path):
    db = _db()
    original = {name: _strip(db[name].docs) for name in cleanup.FILTERS}
    r = cleanup.run(db, confirm=True, backup_dir=tmp_path)
    assert [d["asset"] for d in db["predictions"].docs] == ["BTC"]
    assert [d["asset"] for d in db["risk_scores"].docs] == ["BTC"]
    assert _strip(db["risk_breakdown"].docs) == [{"asset": "LINK", "source": "measured", "liquidity_score": 60}]
    assert [d["target_id"] for d in db["aai_scores"].docs] == ["BTC", "azuki"]     # NFT rows untouched
    backup = json.loads(open(r["_backup"], encoding="utf-8").read())
    assert {k: len(v) for k, v in backup["rows"].items()} == {"predictions": 2, "risk_scores": 1,
                                                              "risk_breakdown": 2, "aai_scores": 2}
    assert cleanup.restore(db, r["_backup"]) == {"predictions": 2, "risk_scores": 1, "risk_breakdown": 2,
                                                 "aai_scores": 2}
    for name in cleanup.FILTERS:                                                  # everything is back
        assert sorted(map(repr, _strip(db[name].docs))) == sorted(map(repr, original[name]))
    assert cleanup.restore(db, r["_backup"])["predictions"] == 0                  # restore is idempotent


def test_confirm_without_backup_is_refused_and_deletes_nothing():
    db = _db()
    with pytest.raises(SystemExit, match="--backup"):
        cleanup.run(db, confirm=True)
    assert len(db["predictions"].docs) == 3


def test_backup_inside_the_repository_is_refused():
    with pytest.raises(SystemExit, match="inside the repository"):
        cleanup.backup_rows(_db(), cleanup.REPO_ROOT / "backups")


def test_refuses_atlas_without_allow_remote(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb+srv://u:p@cluster.example.mongodb.net/")
    with pytest.raises(SystemExit, match="non-local"):
        cleanup.main([])


def test_no_seed_step_writes_ml_or_aai_rows():
    labels = " ".join(label for label, _ in seed_all.STEPS).lower()
    for word in ("prediction", "risk", "aai"):
        assert word not in labels
    import importlib.util
    for gone in ("db.seed_predictions_risk", "db.seed_aai_scores"):
        assert importlib.util.find_spec(gone) is None
