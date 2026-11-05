"""Tests for the PR-title grammar check (plan task B8)."""

import importlib.util
import os
import subprocess  # noqa: S404  # fixed argument lists, no shell
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT: Path = Path(__file__).resolve().parent.parent / ".github" / "scripts" / "check_pr_title.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_pr_title", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module: ModuleType = importlib.util.module_from_spec(spec)
    previous: bool = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # keep .pyc files out of the repo tree
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


check_pr_title: ModuleType = _load()

GOOD: list[str] = [
    "feat: add a thing",
    "fix(checks): reject a bad citation",
    "chore(deps): bump pip-audit from 2.10.0 to 2.10.1",
    "chore(deps-dev): bump cyclonedx-bom from 8.0.0 to 8.0.1",
    "ci(deps): bump actions/upload-artifact from 7.0.1 to 7.0.2",
    "chore(deps): bump google-genai from 2.33.10 to 2.34.0",
    "revert: undo the thing",
    "feat: x",
    "chore(deps): bump " + "a" * 54,  # exactly 72 characters
]

BAD: list[tuple[str, str]] = [
    ("style: tidy up", "allowed type"),
    ("Feat: add a thing", "allowed type"),
    ("feat add a thing", "allowed type"),
    ("feat:add a thing", "allowed type"),
    ("feat(Checks): add a thing", "allowed type"),
    ("feat!: add a thing", "allowed type"),
    ("feat(checks)!: add a thing", "allowed type"),
    ('Revert "feat: add a thing"', "allowed type"),
    ("feat: Add a thing", "upper-case"),
    ("feat: add a thing.", "period"),
    ("feat: ", "empty"),
    ("feat:  add a thing", "upper-case|empty|whitespace"),
    ("feat: add a thing\nand more", "lines"),
    ("feat: " + "a" * 67, "longer than 72"),
]


def test_good_titles_pass() -> None:
    for title in GOOD:
        assert len(title) <= 72
        assert check_pr_title.check(title) is None, title


def test_longest_good_title_is_72_characters() -> None:
    assert len(GOOD[-1]) == 72


@pytest.mark.parametrize(("title", "reason"), BAD)
def test_bad_titles_fail(title: str, reason: str) -> None:
    broken = check_pr_title.check(title)
    assert broken is not None
    import re

    assert re.search(reason, broken)


def test_73_character_title_fails() -> None:
    title = "chore(deps): bump " + "a" * 55
    assert len(title) == 73
    assert check_pr_title.check(title) is not None


def _run(title: str | None) -> subprocess.CompletedProcess[str]:
    env: dict[str, str] = {k: v for k, v in os.environ.items() if k != "PR_TITLE"}
    if title is not None:
        env["PR_TITLE"] = title
    return subprocess.run(  # noqa: S603
        [sys.executable, "-I", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_script_exits_zero_on_a_good_title() -> None:
    assert _run("fix(core): handle a missing file").returncode == 0


def test_script_failure_message_never_echoes_the_title() -> None:
    secret = "Zebra-marker-title-text"
    result = _run(secret)
    assert result.returncode == 1
    assert secret not in result.stdout + result.stderr


def test_script_without_a_title_exits_two() -> None:
    assert _run(None).returncode == 2
