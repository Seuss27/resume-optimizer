"""Unified structured logging configuration for the resume optimizer."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_FILE_NAME: str = "resume_optimizer.log"


class JsonFormatter(logging.Formatter):
    """Custom logging formatter to output log records as structured JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        """Formats a standard LogRecord into a JSON-serialized string.

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

        return json.dumps(log_record, ensure_ascii=False)


def setup_logging(log_file: str = LOG_FILE_NAME) -> None:
    """Initializes the root logger with JSON file output and standard console output.

    Args:
        log_file: The path to the targeted log file. Defaults to LOG_FILE_NAME.
    """
    root_logger: logging.Logger = logging.getLogger()
    if root_logger.handlers:
        return

    root_logger.setLevel(logging.INFO)

    log_path: Path = Path(log_file)
    file_handler: logging.FileHandler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())

    console_handler: logging.StreamHandler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")
    )

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Retrieves a configured logger instance for a given module name.

    Args:
        name: The module name (usually `__name__`).

    Returns:
        A configured logging.Logger instance.
    """
    setup_logging()
    return logging.getLogger(name)
