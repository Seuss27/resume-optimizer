"""Shared pytest fixtures that keep the suite from touching the repo root (plan task A1)."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT: Path = Path(__file__).resolve().parent.parent

# Directories that are never part of the guarded file set: caches the tools themselves rewrite,
# and VCS or environment directories that are not repo content.
_IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".tox",
        ".nox",
        ".hatch",
        ".venv",
        "venv",
        "env",
        "__pycache__",
    }
)

Snapshot = dict[str, tuple[int, int]]


def snapshot_root(root: Path = REPO_ROOT) -> Snapshot:
    """Maps every file under `root`, tracked, untracked or git-ignored, to its size and mtime.

    Recording size and mtime, not just the name, catches a file that is overwritten in place.

    Args:
        root: The directory to scan. Defaults to the repository root.

    Returns:
        POSIX-style relative path -> (size in bytes, mtime in nanoseconds), minus the ignored
        cache and environment directories.
    """
    files: Snapshot = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORED_DIRS]
        for name in filenames:
            path: Path = Path(dirpath) / name
            try:
                stat: os.stat_result = path.lstat()
            except FileNotFoundError:
                continue  # vanished between listing and stat, e.g. an editor's lock file
            files[path.relative_to(root).as_posix()] = (stat.st_size, stat.st_mtime_ns)
    return files


def _describe(paths: list[str]) -> str:
    """Summarizes paths by top-level directory and extension only, never by file name.

    Generated outputs are named after companies and roles, and this message can end up in a PR
    or an issue on a public repo (CLAUDE.md rule 4).
    """
    labels: list[str] = sorted(
        f"{p.split('/')[0] if '/' in p else '.'}/*{Path(p).suffix or '(no extension)'}"
        for p in paths
    )
    return f"{len(paths)} ({', '.join(labels)})" if paths else "0"


# Taken at import, before test modules are collected, so a write made while collecting or
# importing the suite is seen too (provided at least one test then runs). Known limits: a file
# created and deleted within the run is invisible, and a `--basetemp` inside the repo is a
# false red.
_BEFORE: Snapshot = snapshot_root()


@pytest.fixture(autouse=True)
def run_in_tmp_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Runs every test with its own temporary directory as the working directory.

    Code that writes to relative paths then lands in `tmp_path`, never in the repo root.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True, scope="session")
def repo_root_unchanged() -> Iterator[None]:
    """Fails the run if any file under the repo root was added, removed or modified."""
    yield
    after: Snapshot = snapshot_root()
    added: list[str] = sorted(after.keys() - _BEFORE.keys())
    removed: list[str] = sorted(_BEFORE.keys() - after.keys())
    modified: list[str] = sorted(p for p in _BEFORE.keys() & after.keys() if _BEFORE[p] != after[p])
    if added or removed or modified:
        pytest.fail(
            "The test suite changed the repo root "
            f"(added {_describe(added)}; removed {_describe(removed)}; "
            f"modified {_describe(modified)}). "
            "The error is reported on the last test to run, not necessarily the one at fault, "
            "and a concurrent editor or tool can cause it too: re-run to confirm.",
            pytrace=False,
        )
