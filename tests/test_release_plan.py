"""Tests for the release workflow's planning step (plan task B7)."""

import importlib.util
import subprocess  # noqa: S404  # fixed argument lists, no shell
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT: Path = Path(__file__).resolve().parent.parent / ".github" / "scripts" / "release_plan.py"
WHEEL: str = "resume_optimizer-0.1.0-py3-none-any.whl"
CHANGELOG: str = "# Changelog\n\n## Unreleased\n\n## [0.1.0] - 2026-11-05\n\nFirst release.\n"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_plan", SCRIPT)
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


release_plan: ModuleType = _load()


def _pyproject(version: str = "0.1.0") -> str:
    return f'[project]\nname = "resume-optimizer"\nversion = "{version}"\n'


def _run(
    tmp_path: Path,
    *,
    pyproject: str | None = None,
    wheel: str = WHEEL,
    changelog: str = CHANGELOG,
    existing: str = "",
    merged: str = "",
    drafts: str = "",
) -> subprocess.CompletedProcess[str]:
    files: dict[str, str] = {
        "pyproject.toml": _pyproject() if pyproject is None else pyproject,
        "CHANGELOG.md": changelog,
        "all.txt": existing,
        "merged.txt": merged,
        "drafts.txt": drafts,
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8", newline="\n")
    return subprocess.run(  # noqa: S603  # fixed argument list
        [
            sys.executable,
            "-B",
            str(SCRIPT),
            "--pyproject",
            str(tmp_path / "pyproject.toml"),
            "--wheel",
            wheel,
            "--changelog",
            str(tmp_path / "CHANGELOG.md"),
            "--all-tags",
            str(tmp_path / "all.txt"),
            "--merged-tags",
            str(tmp_path / "merged.txt"),
            "--draft-tags",
            str(tmp_path / "drafts.txt"),
            "--notes",
            str(tmp_path / "notes.md"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _refused(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr.startswith("release_plan:")


def test_first_release_prints_exactly_three_lines(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.returncode == 0
    assert result.stdout == "version=0.1.0\ntag=v0.1.0\nprevious=\n"
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "First release.\n"


def test_later_release_names_the_previous_tag_and_adds_the_commit_heading(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        pyproject=_pyproject("0.10.0"),
        wheel=WHEEL.replace("0.1.0", "0.10.0"),
        changelog=CHANGELOG.replace("0.1.0", "0.10.0"),
        existing="v0.9.0\nv0.1.0\n",
        merged="v0.9.0\nv0.1.0\n",
    )
    assert result.returncode == 0
    assert result.stdout == "version=0.10.0\ntag=v0.10.0\nprevious=v0.9.0\n"
    notes: str = (tmp_path / "notes.md").read_text(encoding="utf-8")
    assert notes.startswith("First release.\n")
    assert "## Commits since v0.9.0" in notes


@pytest.mark.parametrize(
    "bad",
    [
        "x = 1\n",
        "project = 1\n",
        '[project]\nname = "x"\ndynamic = "version"\n',
        '[project]\nname = "x"\nversion = "0.1.0"\ndynamic = ["version", 1]\n',
        '[project]\nname = "x"\n',
        '[project]\nname = "x"\nversion = "0.1.0"\ndynamic = ["version"]\n',
        '[project]\nname = "x"\nversion = 1\n',
        '[project]\nname = "x"\nversion = "0.1.0\n"\n',
        '[project]\nname = "x"\nversion = "0.1.0rc1"\n',
        '[project]\nname = "x"\nversion = "0.1.0-dev"\n',
        '[project]\nname = "x"\nversion = "\u0660.1.0"\n',
        "[project\n",
    ],
)
def test_refuses_a_bad_version_source(tmp_path: Path, bad: str) -> None:
    _refused(_run(tmp_path, pyproject=bad))


@pytest.mark.parametrize(
    "wheel",
    ["resume_optimizer-10.1.0-py3-none-any.whl", "resume_optimizer-0.1.1-py3-none-any.whl", "x"],
)
def test_refuses_a_wheel_whose_version_differs(tmp_path: Path, wheel: str) -> None:
    _refused(_run(tmp_path, wheel=wheel))


@pytest.mark.parametrize("field", ["existing", "merged", "drafts"])
@pytest.mark.parametrize("tag", ["v1.0", "v1.0.0-rc1", "v01.0.0", "v1.0.0\u0663", "vx"])
def test_refuses_a_non_bare_v_tag_in_any_list(tmp_path: Path, field: str, tag: str) -> None:
    _refused(_run(tmp_path, **{field: f"{tag}\n"}))


def test_refuses_an_existing_tag(tmp_path: Path) -> None:
    _refused(_run(tmp_path, existing="v0.1.0\n"))


def test_refuses_an_existing_draft_for_the_tag(tmp_path: Path) -> None:
    _refused(_run(tmp_path, drafts="v0.1.0\n"))


@pytest.mark.parametrize("merged", ["v0.1.0", "v0.2.0", "v0.2.0\nv0.0.1"])
def test_refuses_a_version_not_above_the_greatest_merged_tag(tmp_path: Path, merged: str) -> None:
    _refused(_run(tmp_path, merged=merged + "\n"))


def test_the_comparison_is_numeric_not_textual(tmp_path: Path) -> None:
    _refused(
        _run(
            tmp_path,
            pyproject=_pyproject("0.9.0"),
            wheel=WHEEL.replace("0.1.0", "0.9.0"),
            changelog=CHANGELOG.replace("0.1.0", "0.9.0"),
            merged="v0.10.0\n",
        )
    )


@pytest.mark.parametrize(
    "changelog",
    [
        "# Changelog\n\n## Unreleased\n",
        "# Changelog\n\n## [0.1.0] - 2026-11-05\n\n## [0.0.1] - 2026-01-01\n\nOld.\n",
        "# Changelog\n\n## [0.1.0] - 2026-11-05\n   \n",
        "# Changelog\n\n## [0.1.0]\n\nNo date.\n",
    ],
)
def test_refuses_a_missing_or_empty_changelog_section(tmp_path: Path, changelog: str) -> None:
    _refused(_run(tmp_path, changelog=changelog))


def test_the_section_stops_at_the_next_heading(tmp_path: Path) -> None:
    changelog: str = CHANGELOG + "\n## [0.0.1] - 2026-01-01\n\nOld.\n"
    assert _run(tmp_path, changelog=changelog).returncode == 0
    assert "Old." not in (tmp_path / "notes.md").read_text(encoding="utf-8")
