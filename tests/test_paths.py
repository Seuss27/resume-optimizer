"""Tests for the data-path resolvers and the in-repo refusal (plan task B2)."""

import os
import stat
import sys
from pathlib import Path

import pytest

from resume_optimizer import paths


def _fake_checkout(root: Path) -> Path:
    """Builds a directory that looks like a working tree of this repository."""
    (root / ".git").mkdir(parents=True)
    package: Path = root / "src" / "resume_optimizer"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    return root


def test_defaults_use_the_per_user_directories(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    for name in ("RO_LEDGER_DIR", "RO_RUNS_DIR", "RO_LOG_DIR"):
        monkeypatch.delenv(name)
    data, log = tmp_path / "data", tmp_path / "log"
    seen: list[tuple[str, object]] = []

    def fake_data(app: str, appauthor: object = None) -> str:
        seen.append((app, appauthor))
        return str(data)

    def fake_log(app: str, appauthor: object = None) -> str:
        seen.append((app, appauthor))
        return str(log)

    monkeypatch.setattr("resume_optimizer.paths.platformdirs.user_data_dir", fake_data)
    monkeypatch.setattr("resume_optimizer.paths.platformdirs.user_log_dir", fake_log)

    assert paths.ledger_dir() == (data / "ledger").resolve()
    assert paths.runs_dir() == (data / "runs").resolve()
    assert paths.log_dir() == log.resolve()
    assert set(seen) == {("resume-optimizer", False)}
    assert not (data / "ledger").exists()  # resolvers never create directories


def test_optional_variables_default_to_none() -> None:
    assert paths.exemplar_dir() is None
    assert paths.send_dir() is None
    assert paths.template_dir() is None


def test_overrides_are_expanded_and_made_absolute(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("RO_SEND_DIR", "~/send")
    monkeypatch.setenv("RO_TEMPLATE_DIR", "tpl")  # relative to the working directory
    assert paths.send_dir() == (tmp_path / "send").resolve()
    assert paths.template_dir() == (tmp_path / "tpl").resolve()


def test_an_empty_variable_counts_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RO_EXEMPLAR_DIR", "")
    monkeypatch.setenv("RO_LEDGER_DIR", "")
    monkeypatch.setattr(
        "resume_optimizer.paths.platformdirs.user_data_dir",
        lambda app, appauthor=None: "/elsewhere/data",
    )
    assert paths.exemplar_dir() is None
    assert paths.ledger_dir() == (Path("/elsewhere/data") / "ledger").resolve()


def test_nothing_is_cached_at_import_time(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RO_LEDGER_DIR", str(tmp_path / "one"))
    first: Path = paths.ledger_dir()
    monkeypatch.setenv("RO_LEDGER_DIR", str(tmp_path / "two"))
    assert paths.ledger_dir() != first


@pytest.mark.parametrize("var", ["RO_LEDGER_DIR", "RO_RUNS_DIR", "RO_LOG_DIR", "RO_SEND_DIR"])
def test_a_variable_inside_a_checkout_is_refused_by_name_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, var: str
) -> None:
    checkout: Path = _fake_checkout(tmp_path / "checkout")
    monkeypatch.setenv(var, str(checkout / "data"))
    with pytest.raises(paths.DataPathRefusedError) as raised:
        paths.validate_all()
    message: str = str(raised.value)
    assert var in message
    assert str(tmp_path) not in message
    assert tmp_path.as_posix() not in message


def test_dot_dot_segments_cannot_hide_a_checkout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkout: Path = _fake_checkout(tmp_path / "checkout")
    (tmp_path / "other").mkdir()
    monkeypatch.setenv("RO_LEDGER_DIR", str(tmp_path / "other" / ".." / "checkout" / "x"))
    assert checkout.exists()
    with pytest.raises(paths.DataPathRefusedError):
        paths.ledger_dir()


def test_a_symlink_into_a_checkout_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    checkout: Path = _fake_checkout(tmp_path / "checkout")
    link: Path = tmp_path / "link"
    try:
        link.symlink_to(checkout, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this OS refused to create a symlink")
    monkeypatch.setenv("RO_RUNS_DIR", str(link / "runs"))
    with pytest.raises(paths.DataPathRefusedError):
        paths.runs_dir()


def test_an_explicit_path_is_refused_with_a_generic_label(tmp_path: Path) -> None:
    checkout: Path = _fake_checkout(tmp_path / "checkout")
    with pytest.raises(paths.DataPathRefusedError, match="data path") as raised:
        paths.refuse_in_repo(checkout / "master_data.json")
    assert str(tmp_path) not in str(raised.value)


def test_an_ancestor_of_a_checkout_is_not_refused(tmp_path: Path) -> None:
    _fake_checkout(tmp_path / "checkout")
    assert paths.refuse_in_repo(tmp_path) == tmp_path.resolve()


def test_a_git_file_marks_a_worktree_checkout(tmp_path: Path) -> None:
    root: Path = tmp_path / "worktree"
    (root / "src" / "resume_optimizer").mkdir(parents=True)
    (root / "src" / "resume_optimizer" / "__init__.py").write_text("", encoding="utf-8")
    (root / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
    with pytest.raises(paths.DataPathRefusedError):
        paths.refuse_in_repo(root / "x")


def test_run_directories_are_unique_and_private() -> None:
    first: Path = paths.new_run_dir()
    second: Path = paths.new_run_dir()
    assert first != second
    assert first.parent == second.parent == paths.runs_dir()
    assert len(first.name) >= 16 and int(first.name, 16) >= 0
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(first).st_mode) == 0o700


def test_surrounding_whitespace_in_a_variable_is_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("RO_SEND_DIR", f"  {tmp_path / 'send'}  ")
    assert paths.send_dir() == (tmp_path / "send").resolve()
