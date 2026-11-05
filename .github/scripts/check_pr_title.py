"""Fails unless the PR title in `PR_TITLE` follows the CLAUDE.md commit grammar (plan task B8).

The grammar is `type(scope): subject`, where `type` is one of the allowed commit types, the
optional scope is lower-case ASCII letters, digits and hyphens, the subject does not start with
an upper-case ASCII letter or end with a period, and the whole title is at most 72 characters.
There is no `!` breaking-change marker. A failure message names the rule broken and never echoes
the title.
"""

import os
import re
import sys

MAX_LENGTH: int = 72
TYPES: str = "feat|fix|docs|test|refactor|perf|chore|ci|revert"
PREFIX: re.Pattern[str] = re.compile(rf"(?:{TYPES})(?:\([a-z0-9-]+\))?: ")
SUBJECT: re.Pattern[str] = re.compile(r"[^A-Z\s.](?:[^\r\n]*[^.\s])?")


def check(title: str) -> str | None:
    """Returns the rule the title breaks, or None when it is valid."""
    if len(title) > MAX_LENGTH:
        return f"the title is longer than {MAX_LENGTH} characters"
    prefix: re.Match[str] | None = PREFIX.match(title)
    if prefix is None:
        return "the title does not start with 'type(scope): ' using an allowed type"
    subject: str = title[prefix.end() :]
    if "A" <= subject[:1] <= "Z":
        return "the subject starts with an upper-case letter"
    if subject.endswith("."):
        return "the subject ends with a period"
    if SUBJECT.fullmatch(subject) is None:
        return "the subject is empty, spans several lines or has stray whitespace"
    return None


def main() -> int:
    """Reads the title from the environment and reports the first rule it breaks."""
    title: str | None = os.environ.get("PR_TITLE")
    if title is None:
        print("PR_TITLE is not set.", file=sys.stderr)
        return 2
    broken: str | None = check(title)
    if broken is not None:
        print(f"PR title rejected: {broken}.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
