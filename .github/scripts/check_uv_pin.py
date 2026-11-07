"""Checks that CI's uv binary and the `uv_build` build backend are pinned to one version.

Usage: check_uv_pin.py <pyproject.toml> <expected version> <`uv --version` text>

It parses `[build-system]` with `tomllib` and uses the standard library only. It makes no
network or subprocess calls. Each failure prints one line naming only the check that failed,
never a traceback, and exits 1.
"""

import re
import sys
import tomllib
from pathlib import Path
from typing import Any

NUMBER: str = r"(?:0|[1-9][0-9]*)"
VERSION: re.Pattern[str] = re.compile(rf"{NUMBER}\.{NUMBER}\.{NUMBER}")
PIN: re.Pattern[str] = re.compile(r"uv_build==([0-9]+\.[0-9]+\.[0-9]+)")
SEPARATORS: re.Pattern[str] = re.compile(r"[-_.]+")
NAME: re.Pattern[str] = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class Failure(Exception):
    """A check failed; the message names it."""


def normalised_name(requirement: str) -> str:
    """The leading project name of a requirement string, normalised the PEP 503 way."""
    match: re.Match[str] | None = NAME.match(requirement.strip())
    if match is None:
        return ""
    return SEPARATORS.sub("-", match.group(0)).lower()


def check(pyproject: Path, expected: str, uv_text: str) -> None:
    """Raises Failure unless the pin, the backend and both versions agree."""
    data: dict[str, Any] = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    build: Any = data.get("build-system")
    if not isinstance(build, dict):
        raise Failure("no [build-system] table")
    requires: Any = build.get("requires")
    if not isinstance(requires, list) or not all(isinstance(item, str) for item in requires):
        raise Failure("[build-system].requires must be a list of strings")
    if build.get("build-backend") != "uv_build":
        raise Failure("[build-system].build-backend must be exactly uv_build")
    if "backend-path" in build:
        raise Failure("[build-system] must not set backend-path")
    entries: list[str] = [item for item in requires if normalised_name(item) == "uv-build"]
    if len(entries) != 1:
        raise Failure("[build-system].requires must name uv_build exactly once")
    pinned: re.Match[str] | None = PIN.fullmatch(entries[0])
    if pinned is None or VERSION.fullmatch(pinned.group(1)) is None:
        raise Failure("the uv_build entry must be exactly uv_build==X.Y.Z")
    version: str = pinned.group(1)
    if expected != version:
        raise Failure("the expected version differs from the uv_build pin")
    fields: list[str] = uv_text.split()
    if len(fields) < 2 or fields[1] != version:
        raise Failure("the uv --version output differs from the uv_build pin")


def main(argv: list[str]) -> int:
    """Entry point; prints one line on failure."""
    if len(argv) != 3:
        print("check_uv_pin: usage: check_uv_pin.py <pyproject.toml> <version> <uv --version>")
        return 1
    try:
        check(Path(argv[0]), argv[1], argv[2])
    except (Failure, ValueError, OSError) as error:
        print(f"check_uv_pin: {error}")
        return 1
    print("check_uv_pin: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
