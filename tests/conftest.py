"""Shared pytest fixtures that keep the suite from touching the repo root (plan task A1)."""

import os
import subprocess
import sys
import types
from collections.abc import Iterator
from pathlib import Path

import keyring.backend
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


@pytest.fixture(autouse=True)
def ro_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Points the data-path variables into `tmp_path`, so no test touches the per-user folders.

    The ledger directory is created, since resolvers never create one. The three optional
    variables are unset.
    """
    ledger: Path = tmp_path / "ledger"
    ledger.mkdir()
    monkeypatch.setenv("RO_LEDGER_DIR", str(ledger))
    monkeypatch.setenv("RO_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("RO_LOG_DIR", str(tmp_path / "logs"))
    for name in ("RO_EXEMPLAR_DIR", "RO_SEND_DIR", "RO_TEMPLATE_DIR"):
        monkeypatch.delenv(name, raising=False)


class MemoryKeyring(keyring.backend.KeyringBackend):
    """An in-memory keyring backend, so no test reaches the real OS keyring."""

    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self.store.pop((service, username), None)


@pytest.fixture(autouse=True)
def memory_keyring(monkeypatch: pytest.MonkeyPatch) -> MemoryKeyring:
    """Installs an empty in-memory keyring and unsets the credential-adjacent variables.

    Patches the private `keyring.core._keyring_backend` attribute (pytest restores it on
    teardown) and never calls `keyring.get_keyring()`, which would probe the real OS keyring.
    If a later keyring release removes the attribute, this fails loudly, by design.
    """
    backend = MemoryKeyring()
    monkeypatch.setattr("keyring.core._keyring_backend", backend)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    return backend


@pytest.fixture(autouse=True)
def teardown_logging_after_test() -> Iterator[None]:
    """Removes the handlers a test's `setup_logging()` call left on the root logger.

    Looks the module up in `sys.modules` rather than importing it, so the copy of this file that
    the root-guard test stages keeps working.
    """
    yield
    module = sys.modules.get("resume_optimizer.logging_setup")
    if module is not None:
        module.teardown_logging()


@pytest.fixture
def stand_in_resources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Points the packaged prompt and template folders at `tmp_path`, for stand-in files.

    Patched by string target: the copy of this file that the root-guard test stages must keep
    working without importing `resume_optimizer` itself.
    """
    monkeypatch.setattr("resume_optimizer.resources.PROMPT_DIR", tmp_path)
    monkeypatch.setattr("resume_optimizer.resources.TEMPLATE_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def fake_checkout(tmp_path: Path) -> Path:
    """A directory that looks like a working tree of this repo, for the in-repo refusal tests."""
    root: Path = tmp_path / "fake_checkout"
    (root / ".git").mkdir(parents=True)
    (root / "src" / "resume_optimizer").mkdir(parents=True)
    (root / "src" / "resume_optimizer" / "__init__.py").write_text("", encoding="utf-8")
    return root


@pytest.fixture(autouse=True)
def no_real_converters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stops any test from launching Word or LibreOffice. Render tests install their own stub."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise OSError("tests never run a real converter")

    shim = types.SimpleNamespace(
        run=refuse,
        Popen=refuse,
        DEVNULL=subprocess.DEVNULL,
        SubprocessError=subprocess.SubprocessError,
        TimeoutExpired=subprocess.TimeoutExpired,
        CalledProcessError=subprocess.CalledProcessError,
    )
    monkeypatch.setattr("resume_optimizer.render.subprocess", shim)
    # Pipeline tests write placeholder files named .docx. The real scan is tested in
    # test_render_safety.py and in the tests that opt back in.
    monkeypatch.setattr("resume_optimizer.generate.scan_for_active_content", lambda path: [])
    monkeypatch.setattr("resume_optimizer.generate.page_count", lambda path: 1)


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
