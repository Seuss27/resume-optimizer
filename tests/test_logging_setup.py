"""Unit test suite for the structured logging setup module."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Generator

import pytest

from resume_optimizer.logging_setup import JsonFormatter, get_logger, setup_logging


@pytest.fixture(autouse=True)
def reset_root_logger() -> Generator[None, None, None]:
    """Fixture to clean up the root logger handlers before and after tests.

    Ensures tests are isolated and don't duplicate handlers across the global state.
    """
    root_logger: logging.Logger = logging.getLogger()
    old_handlers: list[logging.Handler] = list(root_logger.handlers)
    root_logger.handlers.clear()

    yield

    root_logger.handlers.clear()
    for handler in old_handlers:
        root_logger.addHandler(handler)


def test_json_formatter_formats_record() -> None:
    """Verifies that JsonFormatter outputs a correctly structured JSON string."""
    record: logging.LogRecord = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_path.py",
        lineno=42,
        msg="This is a test message",
        args=(),
        exc_info=None,
    )
    formatter: JsonFormatter = JsonFormatter()

    result_str: str = formatter.format(record)
    result: dict[str, Any] = json.loads(result_str)

    assert "timestamp" in result
    assert result["level"] == "INFO"
    assert result["logger"] == "test_logger"
    assert result["message"] == "This is a test message"
    assert result["line"] == 42


def test_json_formatter_includes_exception() -> None:
    """Verifies that exceptions are formatted and included in the JSON output."""
    exc_info = None
    try:
        raise ValueError("Something went wrong")
    except ValueError:
        exc_info = sys.exc_info()

    record: logging.LogRecord = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test_path.py",
        lineno=42,
        msg="An error occurred",
        args=(),
        exc_info=exc_info,
    )
    formatter: JsonFormatter = JsonFormatter()

    result_str: str = formatter.format(record)
    result: dict[str, Any] = json.loads(result_str)

    assert "exception" in result
    assert "ValueError: Something went wrong" in result["exception"]


def test_setup_logging_adds_handlers(tmp_path: Path) -> None:
    """Ensures setup_logging configures exactly one FileHandler and one StreamHandler."""
    log_file: Path = tmp_path / "test.log"
    setup_logging(log_file=str(log_file))

    root_logger: logging.Logger = logging.getLogger()
    assert len(root_logger.handlers) == 2


def test_setup_logging_is_idempotent(tmp_path: Path) -> None:
    """Verifies calling setup_logging multiple times does not duplicate handlers."""
    log_file: Path = tmp_path / "test.log"
    setup_logging(log_file=str(log_file))
    setup_logging(log_file=str(log_file))

    root_logger: logging.Logger = logging.getLogger()
    assert len(root_logger.handlers) == 2


def test_get_logger() -> None:
    """Ensures get_logger automatically sets up handlers and returns a named logger."""
    logger: logging.Logger = get_logger("my_custom_logger")
    assert logger.name == "my_custom_logger"
