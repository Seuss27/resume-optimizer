"""Structured logging configuration for the resume optimizer.

Logging is configured by the entry points, never by import. The module keeps a list of the
handlers it installed and keys idempotence and teardown on those alone, so another handler on
the root logger (pytest's capture handlers, say) neither blocks set-up nor is touched by
teardown.

Logs carry IDs, counts and scores, never resume text or contact details (CLAUDE.md rule 4).
Two paths stay open on purpose: exception tracebacks, and the message text of third-party
WARNING records.
"""

import json
import logging
import re
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from resume_optimizer import paths

LOG_FILE_NAME: str = "resume_optimizer.log"

_DOCUMENT_LABELS: frozenset[str] = frozenset({"Resume", "Cover letter"})
_EXCEPTION_NAME: re.Pattern[str] = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
_MODEL_ID: re.Pattern[str] = re.compile(r"[A-Za-z0-9._:/-]{1,128}")


def _is_count(value: object) -> bool:
    """Accepts an int that is not a bool."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_document_label(value: object) -> bool:
    """Accepts only the two document labels the generator uses."""
    return isinstance(value, str) and value in _DOCUMENT_LABELS


def _is_exception_name(value: object) -> bool:
    """Accepts an ASCII exception type name ending in `Error` or `Exception`."""
    return (
        isinstance(value, str)
        and _EXCEPTION_NAME.fullmatch(value) is not None
        and value.endswith(("Error", "Exception"))
    )


def _is_model_id(value: object) -> bool:
    """Accepts a short string drawn from the characters a model identifier uses."""
    return isinstance(value, str) and _MODEL_ID.fullmatch(value) is not None


# Each `extra=` key the JSON file may carry, with the check its value must pass. The checks
# constrain the shape of a value, not its meaning: what keeps personal text out is that no call
# site puts it under one of these keys, and a reviewer of any new `extra=` call.
EXTRA_ALLOWLIST: dict[str, Callable[[object], bool]] = {
    "pages": _is_count,
    "call_sequence": _is_count,
    "pandoc_warnings": _is_count,
    "unsupported": _is_count,
    "from_req": _is_count,
    "ai_tells": _is_count,
    "document": _is_document_label,
    "exception": _is_exception_name,
    "model_id": _is_model_id,
}


class JsonFormatter(logging.Formatter):
    """Custom logging formatter to output log records as structured JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        """Formats a standard LogRecord into a JSON-serialized string.

        Only `extra=` keys on `EXTRA_ALLOWLIST` whose value passes the key's check are written,
        and one never replaces a base field.

        Args:
            record: The logging event record to format.

        Returns:
            A JSON-formatted string containing the structured log details.
        """
        now: datetime = datetime.now(timezone.utc)
        timestamp: str = now.isoformat(timespec="seconds").replace("+00:00", "Z")

        log_record: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        for key, accepts in EXTRA_ALLOWLIST.items():
            if key in log_record or key not in record.__dict__:
                continue
            value: object = record.__dict__[key]
            if accepts(value):
                log_record[key] = value

        return json.dumps(log_record, ensure_ascii=False)


class ThirdPartyFloor(logging.Filter):
    """Lets a record below WARNING through only when this package's own code logged it."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Tells whether a record may reach the handler this filter is attached to."""
        if record.levelno >= logging.WARNING:
            return True
        name: str = record.name
        return (
            name == "resume_optimizer"
            or name.startswith("resume_optimizer.")
            or (name == "__main__")
        )


# The handlers this module installed, and the root level it replaced (None: none saved).
_installed: list[logging.Handler] = []
_saved_level: int | None = None


def setup_logging(log_file: str | Path | None = None) -> None:
    """Installs a JSON file handler and a console handler on the root logger.

    Idempotent: it returns early only while one of the handlers this module installed is still
    attached to the root logger. Handlers it installed that other code has since detached are
    closed and replaced. With no argument the file is `RO_LOG_DIR`'s `LOG_FILE_NAME`, and the
    directory is created private to the user when this call creates it.

    Args:
        log_file: An explicit log file path, for tests. Defaults to the file under `RO_LOG_DIR`.

    Raises:
        paths.DataPathRefusedError: If `RO_LOG_DIR` resolves inside a checkout. Nothing is
            created then.
    """
    global _saved_level

    root_logger: logging.Logger = logging.getLogger()
    if any(handler in root_logger.handlers for handler in _installed):
        return

    log_path: Path
    if log_file is None:
        log_directory: Path = paths.log_dir()
        log_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        log_path = log_directory / LOG_FILE_NAME
    else:
        log_path = Path(log_file)

    for stale in _installed:
        stale.close()
    _installed.clear()

    file_handler: logging.FileHandler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())

    console_handler: logging.StreamHandler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")
    )

    for handler in (file_handler, console_handler):
        handler.addFilter(ThirdPartyFloor())
        root_logger.addHandler(handler)
        _installed.append(handler)

    if _saved_level is None:
        _saved_level = root_logger.level
    root_logger.setLevel(logging.INFO)


def teardown_logging() -> None:
    """Removes and closes the handlers `setup_logging` installed and restores the root level.

    Any other handler on the root logger is left alone, and so is the level when none is saved.
    """
    global _saved_level

    root_logger: logging.Logger = logging.getLogger()
    for handler in _installed:
        root_logger.removeHandler(handler)
        handler.close()
    _installed.clear()

    if _saved_level is not None:
        root_logger.setLevel(_saved_level)
        _saved_level = None


def get_logger(name: str) -> logging.Logger:
    """Retrieves a logger for a given module name. It configures nothing.

    Args:
        name: The module name (usually `__name__`).

    Returns:
        A logging.Logger instance.
    """
    return logging.getLogger(name)
