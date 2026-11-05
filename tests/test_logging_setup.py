"""Unit test suite for the structured logging setup module."""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Generator

import pytest

from resume_optimizer import logging_setup, paths
from resume_optimizer.logging_setup import (
    JsonFormatter,
    ThirdPartyFloor,
    get_logger,
    setup_logging,
    teardown_logging,
)


@pytest.fixture(autouse=True)
def reset_logging() -> Generator[None, None, None]:
    """Removes the handlers this module installed before and after each test.

    pytest's own capture handlers on the root logger are left in place.
    """
    teardown_logging()
    yield
    teardown_logging()


def _ours() -> list[logging.Handler]:
    """The root-logger handlers that `setup_logging` installed."""
    return [h for h in logging.getLogger().handlers if h in logging_setup._installed]


def _record(name: str, level: int, **extra: Any) -> logging.LogRecord:
    """Builds a log record with the given `extra=` attributes."""
    record = logging.LogRecord(name, level, "p.py", 1, "msg", (), None)
    record.__dict__.update(extra)
    return record


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


def test_setup_logging_writes_under_ro_log_dir() -> None:
    """With no argument the file lands in RO_LOG_DIR, which is created, not the working dir."""
    setup_logging()
    logging.getLogger("resume_optimizer.x").info("hello")
    teardown_logging()

    log_file: Path = paths.log_dir() / logging_setup.LOG_FILE_NAME
    assert log_file.is_file()
    assert json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])["message"] == "hello"
    assert not list(Path.cwd().glob("*.log"))


def test_setup_logging_refuses_a_log_dir_in_the_checkout(
    monkeypatch: pytest.MonkeyPatch, fake_checkout: Path
) -> None:
    """A refused RO_LOG_DIR raises and creates nothing."""
    target: Path = fake_checkout / "logs"
    monkeypatch.setenv("RO_LOG_DIR", str(target))

    with pytest.raises(paths.DataPathRefusedError):
        setup_logging()

    assert not target.exists()
    assert not _ours()


def test_setup_logging_is_idempotent(tmp_path: Path) -> None:
    """Calling setup_logging twice installs one file handler and one stream handler."""
    log_file: Path = tmp_path / "test.log"
    setup_logging(log_file=log_file)
    setup_logging(log_file=log_file)

    ours = _ours()
    assert len(ours) == 2
    assert sum(isinstance(h, logging.FileHandler) for h in ours) == 1


def test_teardown_removes_only_our_handlers_and_restores_level(tmp_path: Path) -> None:
    """Teardown closes our handlers, restores the root level and leaves other handlers."""
    root = logging.getLogger()
    other = logging.NullHandler()
    root.addHandler(other)
    before_level: int = root.level
    root.setLevel(logging.ERROR)
    try:
        setup_logging(log_file=tmp_path / "t.log")
        file_handler = next(h for h in _ours() if isinstance(h, logging.FileHandler))
        assert root.level == logging.INFO

        teardown_logging()

        assert not _ours()
        assert other in root.handlers
        assert root.level == logging.ERROR
        assert file_handler.stream is None
    finally:
        root.removeHandler(other)
        root.setLevel(before_level)


def test_a_detached_pair_is_closed_and_replaced_and_the_original_level_kept(
    tmp_path: Path,
) -> None:
    """Handlers other code detached are closed and replaced; teardown restores the first level."""
    root = logging.getLogger()
    before_level: int = root.level
    root.setLevel(logging.ERROR)
    try:
        setup_logging(log_file=tmp_path / "t.log")
        first = _ours()
        for handler in first:
            root.removeHandler(handler)

        setup_logging(log_file=tmp_path / "t.log")

        replacement = _ours()
        assert len(replacement) == 2
        assert not any(h in replacement for h in first)
        assert next(h for h in first if isinstance(h, logging.FileHandler)).stream is None
        teardown_logging()
        assert root.level == logging.ERROR
    finally:
        root.setLevel(before_level)


def test_teardown_without_setup_leaves_the_level_alone() -> None:
    """With nothing saved, teardown does not touch the root level."""
    root = logging.getLogger()
    before: int = root.level
    teardown_logging()
    assert root.level == before


def test_get_logger_configures_nothing() -> None:
    """get_logger returns a named logger and installs no handler."""
    logger: logging.Logger = get_logger("my_custom_logger")
    assert logger.name == "my_custom_logger"
    assert not _ours()


def test_importing_the_modules_sets_up_no_logging(tmp_path: Path) -> None:
    """A fresh interpreter importing the four modules has no root handlers and writes no log."""
    code: str = (
        "import logging;"
        "import resume_optimizer.generate, resume_optimizer.build_state;"
        "import resume_optimizer.adapters, resume_optimizer.render;"
        "import resume_optimizer.credentials, keyring.core;"
        "assert keyring.core._keyring_backend is None;"
        "assert not logging.getLogger().handlers, logging.getLogger().handlers"
    )
    env: dict[str, str] = {
        "PYTHONPATH": os.pathsep.join(sys.path),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
    }
    for name in ("RO_LEDGER_DIR", "RO_RUNS_DIR", "RO_LOG_DIR"):
        env[name] = os.environ[name]

    subprocess.run(  # noqa: S603 - fixed argv, test only
        [sys.executable, "-c", code], cwd=tmp_path, env=env, check=True, capture_output=True
    )

    assert not list(tmp_path.rglob("*.log"))
    assert not Path(os.environ["RO_LOG_DIR"]).exists()


def test_extras_on_the_allowlist_pass_and_others_are_dropped() -> None:
    """An allowlisted count is written; an off-list key and a file-name label are not."""
    record = _record("t", logging.INFO, pages=2, output_prefix="x", document="Acme_Dev_Resume.docx")
    result: dict[str, Any] = json.loads(JsonFormatter().format(record))

    assert result["pages"] == 2
    assert "output_prefix" not in result
    assert "document" not in result


@pytest.mark.parametrize(
    ("key", "good", "bad"),
    [
        ("pages", 3, True),
        ("pages", 0, "3"),
        ("unsupported", 1, 1.5),
        ("document", "Resume", "Acme_Dev_Resume.docx"),
        ("document", "Cover letter", "resume"),
        ("exception", "PdfConversionError", "Failed to convert Acme's resume"),
        ("exception", "ValueError", "Value"),
        ("exception", "_PrivateException", "1BadError"),
        ("exception", "ValueError", "ÉrrorError"),
        ("exception", "A" * 59 + "Error", "A" * 60 + "Error"),
        ("model_id", "gemini-2.5-pro", "Acme Corp"),
        ("model_id", "us.anthropic.claude:1/x_y", "x" * 129),
    ],
)
def test_each_typed_check_accepts_good_and_drops_bad(key: str, good: Any, bad: Any) -> None:
    """Every allowlisted key has a check that accepts a good value and drops a bad one."""
    formatter = JsonFormatter()
    assert json.loads(formatter.format(_record("t", logging.INFO, **{key: good})))[key] == good
    assert key not in json.loads(formatter.format(_record("t", logging.INFO, **{key: bad})))


def test_an_extra_never_replaces_a_base_field() -> None:
    """The base field wins over an allowlisted extra of the same name."""
    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()
    record = _record("t", logging.ERROR, exception="OtherError")
    record.exc_info = exc_info

    result: dict[str, Any] = json.loads(JsonFormatter().format(record))

    assert "ValueError: boom" in result["exception"]


def test_third_party_info_is_filtered_and_warnings_pass() -> None:
    """Below WARNING only this package's loggers and __main__ reach the handlers."""
    floor = ThirdPartyFloor()
    assert not floor.filter(_record("httpx", logging.INFO))
    assert not floor.filter(_record("resume_optimizerish", logging.INFO))
    assert floor.filter(_record("httpx", logging.WARNING))
    assert floor.filter(_record("resume_optimizer", logging.INFO))
    assert floor.filter(_record("resume_optimizer.generate", logging.INFO))
    assert floor.filter(_record("__main__", logging.INFO))


def test_installed_handlers_apply_the_floor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Both installed handlers drop third-party INFO and keep third-party WARNING."""
    log_file: Path = tmp_path / "t.log"
    setup_logging(log_file=log_file)

    logging.getLogger("httpx").info("third party info")
    logging.getLogger("httpx").warning("third party warning")
    logging.getLogger("resume_optimizer.generate").info("own info")
    teardown_logging()

    written: str = log_file.read_text(encoding="utf-8")
    assert "third party info" not in written
    assert "third party warning" in written
    assert "own info" in written
    err: str = capsys.readouterr().err
    assert "third party info" not in err
    assert "third party warning" in err
