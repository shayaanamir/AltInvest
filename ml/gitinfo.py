"""Git state recorded in report metadata (AGENTS rule 10). Shared by every report writer.

git_dirty = uncommitted changes (tracked or untracked, git-ignored files excluded) OUTSIDE ml/reports/.
Report files are outputs, so rewriting them must not make the next run look dirty.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_PATHSPEC = "ml/reports"


def _git(cwd: Path, *args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_commit(cwd: Path = REPO_ROOT) -> str | None:
    return _git(cwd, "rev-parse", "HEAD")


def git_dirty(cwd: Path = REPO_ROOT, exclude: str = REPORTS_PATHSPEC) -> bool | None:
    """True if anything outside `exclude` (relative to cwd) is uncommitted. None if git is unavailable."""
    out = _git(cwd, "status", "--porcelain", "--untracked-files=all", "--", ".", f":(exclude){exclude}")
    return None if out is None else bool(out)


def git_metadata(cwd: Path = REPO_ROOT) -> dict:
    """git_commit and git_dirty; prints a one-line warning to stderr when dirty (does not stop the run)."""
    dirty = git_dirty(cwd)
    if dirty:
        print("WARNING: uncommitted changes outside ml/reports/; git_commit does not fully describe this run",
              file=sys.stderr)
    return {"git_commit": git_commit(cwd), "git_dirty": dirty}
