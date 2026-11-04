"""Proves the repo-root guard in conftest.py fails the run when a test touches the root."""

from pathlib import Path

import pytest

pytest_plugins = ["pytester"]

_CONFTEST: str = (Path(__file__).parent / "conftest.py").read_text(encoding="utf-8")


def _stage(pytester: pytest.Pytester, test_body: str) -> None:
    """Builds a miniature repo whose `tests/conftest.py` is a copy of the real guard.

    The repo sits in a `repo/` subdirectory so the capture files that pytester itself writes
    next to it are not part of the guarded root.
    """
    repo: Path = pytester.path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "tests" / "conftest.py").write_text(_CONFTEST, encoding="utf-8")
    (repo / "tests" / "test_inner.py").write_text(test_body, encoding="utf-8")
    (repo / "tracked.txt").write_text("original", encoding="utf-8")


def _run(pytester: pytest.Pytester, outside: Path) -> pytest.RunResult:
    """Runs the staged suite with its temp directories outside the staged root."""
    return pytester.runpytest_subprocess("repo/tests", f"--basetemp={outside / 'inner'}")


def test_guard_passes_when_root_is_untouched(pytester: pytest.Pytester, tmp_path: Path) -> None:
    _stage(pytester, "def test_ok(tmp_path):\n    (tmp_path / 'x.txt').write_text('x')\n")
    result = _run(pytester, tmp_path)
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    "body",
    [
        "(ROOT / 'stray.txt').write_text('x')",
        "(ROOT / 'tracked.txt').unlink()",
        "(ROOT / 'tracked.txt').write_text('changed content')",
        "import os; st = (ROOT / 'tracked.txt').stat(); "
        "os.utime(ROOT / 'tracked.txt', ns=(st.st_atime_ns, st.st_mtime_ns + 10_000_000))",
    ],
    ids=["added", "removed", "modified-size", "modified-mtime"],
)
def test_guard_fails_when_root_changes(
    pytester: pytest.Pytester, tmp_path: Path, body: str
) -> None:
    _stage(
        pytester,
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parent.parent\n"
        f"def test_touches_root():\n    {body}\n",
    )
    result = _run(pytester, tmp_path)
    assert result.ret != 0
    result.stdout.fnmatch_lines(["*The test suite changed the repo root*"])
