"""D83 serving refits and the D84 accuracy lines. The equivalence test needs the host's live NFT folder and the
development artifact (both git-ignored) and is skipped without them."""

import json
import shutil
from datetime import datetime, timezone

import pandas as pd
import pytest

from ml import config
from ml.nft import fv_artifact, fv_refit
from ml.serving import nft_items

BASE = config.NFT_FV_ARTIFACT_DIR


def _need_artifact_and_live():
    if not (BASE / fv_artifact.MODEL).exists() or not fv_refit.fv_serving.store.has_table(config.ML_NFT_DIR,
                                                                                         "sales_raw"):
        pytest.skip("development artifact or live NFT folder not present")


def test_cutoff_is_the_refit_date_minus_the_7_day_embargo():
    assert fv_refit.cutoff_for("2026-12-01") == pd.Timestamp("2026-11-24", tz="UTC")
    assert fv_refit.cutoff_for("2026-11-14") == pd.Timestamp("2026-11-07", tz="UTC")


def _snapshot(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


def test_refit_procedure_reproduces_the_development_artifact(tmp_path):
    """A refit dated 2026-01-01 (cutoff 2025-12-25) on the live folder trains on exactly the development fit's rows
    and gives the same model file: the refit procedure is the D79 / walk-forward procedure (D83). Everything is
    written to the refit folder (the volume, 10.9b); the development folder is only read."""
    _need_artifact_and_live()
    base, vol = tmp_path / "dev", tmp_path / "volume"
    base.mkdir()
    for f in (fv_artifact.META, fv_refit.ACCURACY, fv_artifact.MODEL):
        shutil.copy(BASE / f, base / f)
    before = _snapshot(base)
    dev = json.loads((BASE / fv_artifact.META).read_text(encoding="utf-8"))
    meta = fv_refit.refit("2026-01-01", base=base, out=vol)
    assert _snapshot(base) == before                                    # read only
    assert meta["train_cutoff_exclusive"] == "2025-12-25" and meta["train_rows"] == dev["train_rows"]
    assert meta["train_rows_by_collection"] == dev["train_rows_by_collection"]
    assert meta["model_sha256"] == dev["model_sha256"]
    assert "accuracy_note" not in meta                                  # MINOR 4
    assert (vol / fv_artifact.CURRENT).read_text(encoding="utf-8").strip() == "refits/2026-01-01"
    log = [json.loads(x) for x in (vol / fv_refit.LOG).read_text(encoding="utf-8").splitlines()]
    assert log[-1]["refit_date"] == "2026-01-01" and log[-1]["model_sha256"] == meta["model_sha256"]
    assert log[-1]["train_rows"] == dev["train_rows"] and log[-1]["trigger"] == "manual"
    _, served = fv_artifact.load(base, refit_dir=vol)
    _, reference = fv_artifact.load(base, follow_current=False, refit_dir=vol)
    assert served["model_version"] == "nft-fv-pooled-l1-nl15-refit-2026-01-01"
    assert reference["model_version"] == config.MODEL_VERSION_NFT_FV
    assert served["accuracy"]["source_sha256"] == json.loads(
        (BASE / fv_refit.ACCURACY).read_text(encoding="utf-8"))["source_sha256"]
    assert not list((vol / fv_refit.REFITS).glob(".*.tmp")) and not (vol / fv_refit.LOCK).exists()


def test_guard_refuses_changed_parameters_or_features():
    dev = json.loads((BASE / fv_artifact.META).read_text(encoding="utf-8"))
    fv_refit.guard(dev["columns"], dev)
    with pytest.raises(fv_refit.RefitRefused, match="feature columns"):
        fv_refit.guard(dev["columns"] + ["trait__new__x"], dev)
    with pytest.raises(fv_refit.RefitRefused, match="parameters"):
        fv_refit.guard(dev["columns"], {**dev, "params": {**dev["params"], "num_leaves": 63}})
    with pytest.raises(fv_refit.RefitRefused, match="parameters"):
        fv_refit.guard(dev["columns"], {**dev, "n_rounds": 500})


def test_a_refit_is_due_once_per_calendar_month(tmp_path):
    nov14, nov30, dec1 = (datetime(2026, 11, 14, tzinfo=timezone.utc), datetime(2026, 11, 30, tzinfo=timezone.utc),
                          datetime(2026, 12, 1, tzinfo=timezone.utc))
    assert fv_refit.due(nov14, tmp_path)                                  # no refit yet
    (tmp_path / fv_refit.LOG).write_text(json.dumps({"refit_date": "2026-11-14"}) + "\n", encoding="utf-8")
    assert not fv_refit.due(nov30, tmp_path) and fv_refit.due(dec1, tmp_path)


def test_due_reads_the_log_only_outside_the_source_checkout():
    """10.9b SHOULD FIX 1: a refit log inside the repository (any branch's files) can never decide a refit."""
    now = datetime(2026, 12, 1, tzinfo=timezone.utc)
    for inside in (fv_refit.SOURCE_ROOT, fv_refit.SOURCE_ROOT / "ml" / "artifacts" / "nft_fv", BASE):
        with pytest.raises(fv_refit.RefitRefused, match="source tree"):
            fv_refit.due(now, inside)
    with pytest.raises(fv_refit.RefitRefused, match="source tree"):
        fv_refit.ensure(out=BASE)


def test_refit_outputs_are_not_tracked_and_no_repo_mount_is_writable():
    """10.9b SHOULD FIX 1: CURRENT, the log and the refits are not in the repository, and every bind mount of a
    repository path in docker-compose.yml is read-only."""
    import subprocess
    tracked = subprocess.run(["git", "ls-files", "ml/artifacts/nft_fv", "ml/docs/phase10/live_accuracy"],
                             capture_output=True, text=True, cwd=fv_refit.SOURCE_ROOT).stdout.split()
    assert not [f for f in tracked if f.endswith(("CURRENT", "refit_log.jsonl")) or "/refits/" in f]
    compose = (fv_refit.SOURCE_ROOT / "docker-compose.yml").read_text(encoding="utf-8").splitlines()
    mounts = [x.strip()[2:] for x in compose if x.strip().startswith("- ./")]
    assert mounts and all(m.endswith(":ro") for m in mounts), mounts


def test_artifact_pointer_must_stay_inside_the_refit_folder(tmp_path):
    (tmp_path / fv_artifact.CURRENT).write_text("../elsewhere\n", encoding="utf-8")
    with pytest.raises(OSError, match="outside"):
        fv_artifact.served_dir(tmp_path, refit_dir=tmp_path)
    assert not fv_artifact.has_served_model(tmp_path)


def test_second_refit_on_a_date_gets_a_revision_and_keeps_the_first(tmp_path):
    assert fv_refit._label(tmp_path, "2026-11-14") == "2026-11-14"
    (tmp_path / fv_refit.REFITS / "2026-11-14").mkdir(parents=True)
    assert fv_refit._label(tmp_path, "2026-11-14") == "2026-11-14-r2"
    (tmp_path / fv_refit.REFITS / "2026-11-14-r2").mkdir()
    assert fv_refit._label(tmp_path, "2026-11-14") == "2026-11-14-r3"


def test_a_running_refit_blocks_a_second_one(tmp_path):
    with fv_refit._Lock(tmp_path):
        with pytest.raises(fv_refit.RefitBusy):
            with fv_refit._Lock(tmp_path):
                pass
    with fv_refit._Lock(tmp_path):                                       # released
        pass


def test_startup_refits_only_when_no_refit_is_served(tmp_path, monkeypatch):
    """10.9b MINOR 9: ensure() runs the D79 refit (trigger 'startup') only when the volume serves no refit."""
    data, vol = tmp_path / "data", tmp_path / "volume"
    data.mkdir()
    calls = []
    monkeypatch.setattr(fv_refit, "refit", lambda **kw: calls.append(kw) or {"model_version": "v", "train_rows": 1})
    assert fv_refit.ensure(directory=data, out=vol)["action"] == "skipped" and not calls     # no live data yet
    for t in ("sales_raw", "floor_points"):
        (data / f"{t}.csv").write_text("x\n", encoding="utf-8")
    assert fv_refit.ensure(directory=data, out=vol)["action"] == "refit" and calls[-1]["trigger"] == "startup"
    (vol / fv_refit.REFITS / "2026-11-14").mkdir(parents=True)
    (vol / fv_refit.REFITS / "2026-11-14" / fv_artifact.MODEL).write_text("m", encoding="utf-8")
    (vol / fv_artifact.CURRENT).write_text("refits/2026-11-14\n", encoding="utf-8")
    assert fv_refit.ensure(directory=data, out=vol) == {"action": "none", "served": "refits/2026-11-14"}
    assert len(calls) == 1


ACC = json.loads((BASE / fv_refit.ACCURACY).read_text(encoding="utf-8")) if (BASE / fv_refit.ACCURACY).exists() else None


def test_accuracy_json_is_generated_from_the_sealed_report():
    from ml.data.validate import ML_ROOT
    rep = json.loads((ML_ROOT / "reports" / "nft" / "sealed_fair_value.json").read_text(encoding="utf-8"))
    assert ACC is not None and ACC["window_label"] == "Feb-Nov 2026"
    assert ACC["source_sha256"] == fv_refit._sha(ML_ROOT / "reports" / "nft" / "sealed_fair_value.json")
    for slug, m in config.NFT_FV_SERVE.items():
        assert ACC["by_collection"][slug]["mdape"] == rep["descriptive"]["by_collection"][slug]["served"]
        assert ACC["by_collection"][slug]["method"] == ("model" if m == "model" else "b2")
    assert ACC["by_collection"]["lilpudgys"]["mdape"] == rep["descriptive"]["by_collection"]["lilpudgys"]["B2_decile_90d"]
    assert ACC["rarest_decile"]["mdape"] == rep["descriptive"]["by_rarity_decile"]["1.0"]["served"]
    with pytest.raises(ValueError, match="sealed"):
        fv_refit.write_accuracy(ML_ROOT / "reports" / "nft" / "sealed_fair_value_dry_run.json")


def test_error_lines_per_collection_and_for_the_rarest_decile():
    meta = {"accuracy": ACC}
    assert nft_items.accuracy_lines(meta, "pudgypenguins", 5) == ("Median error in testing (Feb-Nov 2026): 2.0%", None)
    assert nft_items.accuracy_lines(meta, "azuki", 1) == ("Median error in testing (Feb-Nov 2026): 3.8%",
                                                          "Rarest items: about 9%")
    assert nft_items.accuracy_lines(meta, "lilpudgys", 2.0)[0] == "Median error in testing (Feb-Nov 2026): 2.8%"
    assert nft_items.accuracy_lines(meta, "milady", float("nan"))[1] is None
    assert nft_items.accuracy_lines({"accuracy_note": "Accuracy check pending"}, "azuki", 1) == \
        ("Accuracy check pending", None)                                   # an artifact without a sealed result
