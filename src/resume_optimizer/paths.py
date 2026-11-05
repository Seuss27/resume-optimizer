"""Resolves every data path from the environment, and refuses any that lands in this repo.

The defaults and the refusal are plan section 3.1. Nothing here is cached or read at import
time, and a resolver never creates a directory. The refusal message names the variable, never
the path, which can carry the user name (CLAUDE.md rule 4).
"""

import os
import secrets
from pathlib import Path

import platformdirs

APP_NAME: str = "resume-optimizer"

LEDGER_VAR: str = "RO_LEDGER_DIR"
RUNS_VAR: str = "RO_RUNS_DIR"
LOG_VAR: str = "RO_LOG_DIR"
EXEMPLAR_VAR: str = "RO_EXEMPLAR_DIR"
SEND_VAR: str = "RO_SEND_DIR"
TEMPLATE_VAR: str = "RO_TEMPLATE_DIR"

# The exit status of an entry point that refused a data path (argparse's usage error is 2).
EXIT_REFUSED: int = 3


class DataPathRefusedError(RuntimeError):
    """A data path resolves inside a working tree of this repository."""


def _is_checkout(directory: Path) -> bool:
    """Tells whether a directory is the top of a working tree of this repository."""
    return (
        os.path.lexists(directory / ".git")
        and (directory / "src" / "resume_optimizer" / "__init__.py").is_file()
    )


def refuse_in_repo(path: str | Path, label: str = "data path") -> Path:
    """Resolves a path to an absolute one and refuses it when it lies inside a checkout.

    A path is refused when it, or any ancestor, holds both a `.git` entry and
    `src/resume_optimizer/__init__.py`. An ancestor of a checkout is not refused, since nothing
    lands inside the tree.

    Args:
        path: The path to check; `~` is expanded and symlinks and `..` are resolved.
        label: What to call the path in the message: an environment variable's name, or
            "data path" for one a caller passed in.

    Returns:
        The resolved absolute path.

    Raises:
        DataPathRefusedError: If the path is inside a checkout. The message omits the path.
    """
    try:
        resolved: Path = Path(path).expanduser().resolve()
    except (OSError, RuntimeError):
        # The system's own message names the path, which can carry the user name.
        raise DataPathRefusedError(f"{label} cannot be resolved to a real path.") from None
    for candidate in (resolved, *resolved.parents):
        if _is_checkout(candidate):
            raise DataPathRefusedError(
                f"{label} resolves inside a checkout of this repository. "
                "Point it at a directory outside the working tree."
            )
    return resolved


def _required(var: str, default: Path) -> Path:
    """Reads one variable (empty counts as unset), else the default; refuses an in-repo path."""
    raw: str = os.environ.get(var, "").strip()
    return refuse_in_repo(raw if raw else default, var)


def _optional(var: str) -> Path | None:
    """Reads one variable (empty counts as unset); None when unset."""
    raw: str = os.environ.get(var, "").strip()
    return refuse_in_repo(raw, var) if raw else None


def ledger_dir() -> Path:
    """Returns `RO_LEDGER_DIR`, by default the `ledger` folder of the per-user data directory."""
    return _required(
        LEDGER_VAR, Path(platformdirs.user_data_dir(APP_NAME, appauthor=False)) / "ledger"
    )


def runs_dir() -> Path:
    """Returns `RO_RUNS_DIR`, by default the `runs` folder of the per-user data directory."""
    return _required(RUNS_VAR, Path(platformdirs.user_data_dir(APP_NAME, appauthor=False)) / "runs")


def log_dir() -> Path:
    """Returns `RO_LOG_DIR`, by default the per-user log directory."""
    return _required(LOG_VAR, Path(platformdirs.user_log_dir(APP_NAME, appauthor=False)))


def exemplar_dir() -> Path | None:
    """Returns `RO_EXEMPLAR_DIR`, or None when unset."""
    return _optional(EXEMPLAR_VAR)


def send_dir() -> Path | None:
    """Returns `RO_SEND_DIR`, or None when unset."""
    return _optional(SEND_VAR)


def template_dir() -> Path | None:
    """Returns `RO_TEMPLATE_DIR`, or None when unset."""
    return _optional(TEMPLATE_VAR)


def validate_all() -> None:
    """Runs every resolver, so an entry point refuses a bad path before it does any work.

    Raises:
        DataPathRefusedError: If any variable, or its default, resolves inside a checkout.
    """
    for resolver in (ledger_dir, runs_dir, log_dir, exemplar_dir, send_dir, template_dir):
        resolver()


def new_run_dir() -> Path:
    """Creates and returns a fresh, randomly named run directory under `RO_RUNS_DIR`.

    The runs root is created if missing. The run directory is created with mode 0o700 (the mode
    has no effect on Windows) and must not already exist.
    """
    root: Path = runs_dir()
    root.mkdir(parents=True, exist_ok=True)
    run_dir: Path = root / secrets.token_hex(8)
    run_dir.mkdir(mode=0o700, exist_ok=False)
    return run_dir
