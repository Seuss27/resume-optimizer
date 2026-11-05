"""Tests for the CI guard against tracked files that must stay local (plan task B2)."""

import os
import shutil
import subprocess  # noqa: S404  # fixed argument lists, no shell
import sys
from pathlib import Path

import pytest

SCRIPT: Path = (
    Path(__file__).resolve().parent.parent / ".github" / "scripts" / ("check_tracked_paths.py")
)

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def _env(tmp_path: Path) -> dict[str, str]:
    """A git environment that no developer configuration can reach."""
    empty: Path = tmp_path / "empty.gitconfig"
    empty.write_text("", encoding="utf-8")
    env: dict[str, str] = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = str(empty)
    return env


def _repo(tmp_path: Path, files: list[str]) -> Path:
    """Initialises a repo and stages the files with `git add -f`, without a commit."""
    repo: Path = tmp_path / "repo"
    repo.mkdir()
    env: dict[str, str] = _env(tmp_path)
    git: list[str] = ["git", "-c", "init.defaultBranch=main"]
    subprocess.run([*git, "init", "-q"], cwd=repo, env=env, check=True)  # noqa: S603,S607
    for name in files:
        target: Path = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "-f", name], cwd=repo, env=env, check=True)  # noqa: S603,S607
    return repo


def _run(tmp_path: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-I", str(SCRIPT)],
        cwd=cwd,
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "name",
    ["runs/x", "RUNS/x", "temp_a.md", "a.xlsx", "a.XLSX", "tests/fixtures_x/a.xlsx", "eval"],
)
def test_the_guard_fails_on_a_forbidden_tracked_file(tmp_path: Path, name: str) -> None:
    result = _run(tmp_path, _repo(tmp_path, [name]))
    assert result.returncode == 1
    assert name not in result.stdout  # rule 4: no file names in the message


@pytest.mark.parametrize("name", ["README.md", "tests/fixtures/a.xlsx", "docs/runs/x"])
def test_the_guard_passes_on_allowed_files(tmp_path: Path, name: str) -> None:
    assert _run(tmp_path, _repo(tmp_path, [name])).returncode == 0


def test_the_guard_checks_the_whole_repo_from_a_subdirectory(tmp_path: Path) -> None:
    repo: Path = _repo(tmp_path, ["runs/x", "docs/a.md"])
    assert _run(tmp_path, repo / "docs").returncode == 1


def test_the_guard_passes_on_a_clean_repo(tmp_path: Path) -> None:
    assert _run(tmp_path, _repo(tmp_path, [])).returncode == 0


def test_the_guard_fails_closed_outside_a_repository(tmp_path: Path) -> None:
    outside: Path = tmp_path / "not_a_repo"
    outside.mkdir()
    env: dict[str, str] = _env(tmp_path)
    probe = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "--show-toplevel"],  # noqa: S607
        cwd=outside,
        env=env,
        capture_output=True,
        check=False,
    )
    if probe.returncode == 0:
        pytest.skip("the temp directory sits inside a git repository")
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-I", str(SCRIPT)],
        cwd=outside,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
