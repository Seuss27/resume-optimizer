"""The release workflow's deterministic planning step (plan task B7, RO-D18).

It reads `[project].version` from pyproject.toml with `tomllib`, checks it against the
wheel's file name, the changelog and three lists of tag names, writes the release notes and
prints exactly three lines on stdout: `version=`, `tag=` and `previous=` (empty when there is no
earlier release). It makes no network or git calls. Each refusal goes to stderr and exits 1.
"""

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

NUMBER: str = r"(?:0|[1-9][0-9]*)"
VERSION: re.Pattern[str] = re.compile(rf"({NUMBER})\.({NUMBER})\.({NUMBER})")
TAG: re.Pattern[str] = re.compile(rf"v({NUMBER})\.({NUMBER})\.({NUMBER})")
HEADING: re.Pattern[str] = re.compile(
    rf"## \[({NUMBER}\.{NUMBER}\.{NUMBER})\] - [0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}"
)


class Refusal(Exception):
    """A check failed; the message names it."""


def read_version(pyproject_path: Path) -> str:
    """Returns `[project].version` from a pyproject.toml, which `tomllib` parses and never runs."""
    data: dict[str, Any] = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project: Any = data.get("project")
    if not isinstance(project, dict):
        raise Refusal("version: pyproject.toml has no [project] table")
    dynamic: Any = project.get("dynamic", [])
    if not isinstance(dynamic, list) or not all(isinstance(item, str) for item in dynamic):
        raise Refusal("version: [project].dynamic must be a list of strings")
    if "version" in dynamic:
        raise Refusal("version: [project].version must be static, not listed under dynamic")
    if "version" not in project:
        raise Refusal("version: [project].version is missing")
    value: Any = project["version"]
    if not isinstance(value, str):
        raise Refusal("version: [project].version must be a string")
    if VERSION.fullmatch(value) is None:
        raise Refusal("version: [project].version must be a bare major.minor.patch")
    return value


def check_wheel(wheel_name: str, version: str) -> None:
    """The wheel file name's version field (the second dash-separated field) must equal it."""
    fields: list[str] = Path(wheel_name).name.split("-")
    if len(fields) < 2 or fields[1] != version:
        raise Refusal("wheel: the file name's version does not equal [project].version")


def read_tags(path: Path, label: str) -> list[str]:
    """Returns the `v` tags in a list, refusing any that is not a bare v plus major.minor.patch."""
    tags: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        name: str = line.strip("\r")
        if not name.strip().startswith("v"):
            continue
        if TAG.fullmatch(name) is None:
            raise Refusal(f"tags: a tag in the {label} list is not a bare v major.minor.patch")
        tags.append(name)
    return tags


def as_tuple(tag: str) -> tuple[int, int, int]:
    """The integers of a bare tag, for a numeric comparison."""
    match: re.Match[str] | None = TAG.fullmatch(tag)
    if match is None:
        raise Refusal("tags: not a bare v major.minor.patch")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def changelog_section(changelog: Path, version: str) -> str:
    """Returns the body of the version's changelog section, refusing a missing or empty one."""
    lines: list[str] = changelog.read_text(encoding="utf-8").splitlines()
    body: list[str] = []
    inside: bool = False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            heading: re.Match[str] | None = HEADING.fullmatch(line)
            inside = heading is not None and heading.group(1) == version
            continue
        if inside:
            body.append(line)
    text: str = "\n".join(body).strip()
    if not inside:
        raise Refusal("changelog: no section for this version")
    if not text:
        raise Refusal("changelog: the section for this version is empty")
    return text


def plan(args: argparse.Namespace) -> tuple[str, str, str]:
    """Runs every check, writes the notes file and returns (version, tag, previous)."""
    version: str = read_version(args.pyproject)
    check_wheel(args.wheel, version)
    tag: str = f"v{version}"
    existing: list[str] = read_tags(args.all_tags, "existing")
    merged: list[str] = read_tags(args.merged_tags, "merged")
    drafts: list[str] = read_tags(args.draft_tags, "draft")
    if tag in existing:
        raise Refusal("tags: this tag already exists")
    if tag in drafts:
        raise Refusal("tags: a draft release for this tag exists; delete it first")
    previous: str = ""
    if merged:
        previous = max(merged, key=as_tuple)
        if as_tuple(tag) <= as_tuple(previous):
            raise Refusal("version: not greater than the greatest merged tag")
    notes: str = changelog_section(args.changelog, version)
    if previous:
        notes += "\n\n## Commits since " + previous + "\n"
    else:
        notes += "\n"
    args.notes.write_text(notes, encoding="utf-8", newline="\n")
    return version, tag, previous


def main(argv: list[str]) -> int:
    """Entry point; prints the three output lines or the refusal."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", type=Path, required=True)
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--changelog", type=Path, required=True)
    parser.add_argument("--all-tags", type=Path, required=True)
    parser.add_argument("--merged-tags", type=Path, required=True)
    parser.add_argument("--draft-tags", type=Path, required=True)
    parser.add_argument("--notes", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        version, tag, previous = plan(args)
    except (Refusal, SyntaxError, ValueError, OSError) as error:
        print(f"release_plan: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(f"version={version}\ntag={tag}\nprevious={previous}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
