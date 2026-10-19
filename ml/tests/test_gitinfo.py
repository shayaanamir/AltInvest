"""Tests for ml.gitinfo.git_dirty.

The repo used here is a FIXTURE: a throwaway git repo created in a pytest temp directory.
The real project repo is never touched.
"""

import shutil
import subprocess

import pytest

from ml.gitinfo import git_dirty

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _run(cwd, *args):
    subprocess.run(["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", *args],
                   cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "ml" / "reports").mkdir(parents=True)
    (tmp_path / "ml" / "code.py").write_text("x = 1\n")
    (tmp_path / "ml" / "reports" / "r.json").write_text("{}\n")
    (tmp_path / ".gitignore").write_text("*.csv\n")
    _run(tmp_path, "init", "-q")
    _run(tmp_path, "add", ".")
    _run(tmp_path, "commit", "-q", "-m", "fixture")
    return tmp_path


def test_clean_repo_is_not_dirty(repo):
    assert git_dirty(repo) is False


def test_report_changes_do_not_count(repo):
    (repo / "ml" / "reports" / "r.json").write_text('{"new": 1}\n')         # tracked, modified
    (repo / "ml" / "reports" / "new").mkdir()
    (repo / "ml" / "reports" / "new" / "b.json").write_text("{}\n")          # untracked
    assert git_dirty(repo) is False


def test_ignored_files_do_not_count(repo):
    (repo / "ml" / "data.csv").write_text("a,b\n")
    assert git_dirty(repo) is False


def test_modified_code_is_dirty(repo):
    (repo / "ml" / "code.py").write_text("x = 2\n")
    assert git_dirty(repo) is True


def test_untracked_code_is_dirty(repo):
    (repo / "ml" / "new.py").write_text("y = 1\n")
    assert git_dirty(repo) is True


def test_not_a_repo_gives_none(tmp_path):
    assert git_dirty(tmp_path) is None
