"""The release workflow's deterministic planning step (plan task B7, RO-D18).

It reads the package version with `ast` (the file is never imported), checks it against the
wheel's file name, the changelog and three lists of tag names, writes the release notes and
prints exactly three lines on stdout: `version=`, `tag=` and `previous=` (empty when there is no
earlier release). It makes no network or git calls. Each refusal goes to stderr and exits 1.
"""

import argparse
import ast
import re
import sys
from pathlib import Path

NUMBER: str = r"(?:0|[1-9][0-9]*)"
VERSION: re.Pattern[str] = re.compile(rf"({NUMBER})\.({NUMBER})\.({NUMBER})")
TAG: re.Pattern[str] = re.compile(rf"v({NUMBER})\.({NUMBER})\.({NUMBER})")
HEADING: re.Pattern[str] = re.compile(
    rf"## \[({NUMBER}\.{NUMBER}\.{NUMBER})\] - [0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}"
)


class Refusal(Exception):
    """A check failed; the message names it."""


def read_version(init_path: Path) -> str:
    """Returns the one top-level `__version__` string, parsed without importing the file."""
    tree: ast.Module = ast.parse(init_path.read_text(encoding="utf-8"))
    assigns: list[ast.Assign] = []
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and _names_version(node.target):
            raise Refusal("version: __version__ must not be annotated")
        if isinstance(node, ast.Assign) and any(_names_version(t) for t in node.targets):
            assigns.append(node)
    if len(assigns) != 1:
        raise Refusal("version: expected exactly one top-level __version__ assignment")
    value: ast.expr = assigns[0].value
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        raise Refusal("version: __version__ must be a string constant")
    if VERSION.fullmatch(value.value) is None:
        raise Refusal("version: __version__ must be a bare major.minor.patch")
    return value.value


def _names_version(target: ast.expr) -> bool:
    return isinstance(target, ast.Name) and target.id == "__version__"


def check_wheel(wheel_name: str, version: str) -> None:
    """The wheel file name's version field (the second dash-separated field) must equal it."""
    fields: list[str] = Path(wheel_name).name.split("-")
    if len(fields) < 2 or fields[1] != version:
        raise Refusal("wheel: the file name's version does not equal __version__")


def read_tags(path: Path, label: str) -> list[str]:
    """Returns the `v` tags in a list, refusing any that is not a bare v plus major.minor.patch."""
    tags: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        name: str = line.strip("\r")
        if not name.startswith("v"):
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
    version: str = read_version(args.init)
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
    parser.add_argument("--init", type=Path, required=True)
    parser.add_argument("--wheel", required=True)
    parser.add_argument("--changelog", type=Path, required=True)
    parser.add_argument("--all-tags", type=Path, required=True)
    parser.add_argument("--merged-tags", type=Path, required=True)
    parser.add_argument("--draft-tags", type=Path, required=True)
    parser.add_argument("--notes", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        version, tag, previous = plan(args)
    except (Refusal, SyntaxError, OSError, UnicodeDecodeError) as error:
        print(f"release_plan: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(f"version={version}\ntag={tag}\nprevious={previous}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
