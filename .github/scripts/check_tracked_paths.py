"""Fails when a tracked file matches a path pattern that must never be committed.

Run in CI. The patterns are the B2 ignores in .gitignore (plan task B2). The guard compares
case-insensitively, and its tests/fixtures/ exemption covers only the .xlsx rule. The failure
message gives counts and the pattern hit, never a file name, because a name can identify a
person (CLAUDE.md rule 4).
"""

import os
import subprocess  # noqa: S404  # a fixed argument list, no shell
import sys
from collections import Counter

GUARDED_DIRS: frozenset[str] = frozenset({"runs", "imports", "corpus", "voice", "eval"})
EXEMPT_PREFIX: str = "tests/fixtures/"  # exempts the .xlsx rule only, and is case-sensitive
GIT_TIMEOUT_SECONDS: int = 60


def tracked_paths() -> list[str]:
    """Lists the index of the repository in the working directory, failing closed.

    Raises:
        RuntimeError: If git fails, times out or is missing, or this is not a repository.
    """
    env: dict[str, str] = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    base: list[str] = ["git", "-c", "core.fsmonitor=false"]
    try:
        # `ls-files` lists only the current directory, so anchor it at the top level first.
        top: subprocess.CompletedProcess[bytes] = subprocess.run(  # noqa: S603
            [*base, "rev-parse", "--show-toplevel"],
            capture_output=True,
            check=False,
            env=env,
            timeout=GIT_TIMEOUT_SECONDS,
        )
        if top.returncode != 0 or not top.stdout.strip():
            raise RuntimeError("git could not list the tracked files")
        toplevel: str = top.stdout.decode("utf-8", "surrogateescape").strip()
        done: subprocess.CompletedProcess[bytes] = subprocess.run(  # noqa: S603
            [*base, "-C", toplevel, "ls-files", "-z"],
            capture_output=True,
            check=False,
            env=env,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("git could not list the tracked files") from exc
    if done.returncode != 0:
        raise RuntimeError("git could not list the tracked files")
    return [p.decode("utf-8", "surrogateescape") for p in done.stdout.split(b"\0") if p]


def pattern_hit(path: str) -> str | None:
    """Returns the name of the pattern a tracked path violates, or None."""
    folded: str = path.casefold()
    parts: list[str] = folded.split("/")
    if parts[0] in GUARDED_DIRS:
        return "first component is a guarded directory"
    if len(parts) == 1 and parts[0].startswith("temp_") and parts[0].endswith(".md"):
        return "root-level temp_*.md"
    if folded.endswith(".xlsx") and not path.startswith(EXEMPT_PREFIX):
        return "*.xlsx outside tests/fixtures/"
    return None


def main() -> int:
    """Checks the index and returns the process exit status."""
    try:
        paths: list[str] = tracked_paths()
    except RuntimeError as exc:
        print(f"check_tracked_paths: {exc}.", file=sys.stderr)
        return 1
    hits: Counter[str] = Counter(h for h in map(pattern_hit, paths) if h)
    if hits:
        print(f"check_tracked_paths: {sum(hits.values())} tracked file(s) match a guarded pattern:")
        for pattern, count in sorted(hits.items()):
            print(f"  {count} file(s): {pattern}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
