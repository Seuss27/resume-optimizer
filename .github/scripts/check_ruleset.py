"""Checks that the rulesets on `main` still hold what `.ai/project.yml` mirrors (plan task B8).

Usage: check_ruleset.py RULES_JSON PROJECT_JSON

RULES_JSON is the response of `GET /repos/{repo}/rules/branches/main`: the rules of every ruleset
that applies to the branch, tagged by ruleset id. PROJECT_JSON is `.ai/project.yml` as JSON. For
the `ruleset` block and every entry under `rulesets`, each declared rule type must be among the
applying rules and each declared required check among the `required_status_checks` contexts.
Extra checks on GitHub are not drift. The script fails closed on unreadable or wrongly shaped
input, an empty `rulesets` list, and an empty declared `required_checks` or `rule_types`. Bypass
actors are not in the branch-rules response, so they are not checked. The `pull_request` rule's
parameters (approval count, merge methods) are in it, but this check leaves them alone.
"""

import json
import sys
from pathlib import Path
from typing import Any


class ShapeError(Exception):
    """The input is unreadable or does not have the expected shape."""


def _load(path: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ShapeError(f"cannot read {Path(path).name} as JSON") from exc


def applying(rules: Any) -> tuple[set[str], set[str]]:
    """Returns the rule types and the required check contexts of the applying rules."""
    if not isinstance(rules, list):
        raise ShapeError("the branch rules are not a list")
    types: set[str] = set()
    contexts: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("type"), str):
            raise ShapeError("a branch rule has no type")
        types.add(rule["type"])
        if rule["type"] == "required_status_checks":
            params: Any = rule.get("parameters")
            checks: Any = params.get("required_status_checks") if isinstance(params, dict) else None
            if not isinstance(checks, list):
                raise ShapeError("a required_status_checks rule has no check list")
            for check in checks:
                if not isinstance(check, dict) or not isinstance(check.get("context"), str):
                    raise ShapeError("a required check has no context")
                contexts.add(check["context"])
    return types, contexts


def _declared(block: Any, label: str, key: str) -> list[str]:
    if not isinstance(block, dict):
        raise ShapeError(f"{label} is not a mapping")
    values: Any = block.get(key)
    if not isinstance(values, list) or not values:
        raise ShapeError(f"{label} declares no {key}")
    if not all(isinstance(v, str) and v for v in values):
        raise ShapeError(f"{label} has a {key} entry that is not a string")
    return values


def check(rules: Any, project: Any) -> list[str]:
    """Returns what the declared rulesets require and GitHub does not apply."""
    types, contexts = applying(rules)
    if not isinstance(project, dict):
        raise ShapeError("the project file is not a mapping")
    blocks: list[tuple[str, Any]] = [("ruleset", project.get("ruleset"))]
    entries: Any = project.get("rulesets")
    if not isinstance(entries, list) or not entries:
        raise ShapeError("rulesets is missing or empty")
    blocks += [(f"rulesets[{i}]", entry) for i, entry in enumerate(entries)]
    problems: list[str] = []
    for label, block in blocks:
        for rule_type in _declared(block, label, "rule_types"):
            if rule_type not in types:
                problems.append(f"{label}: missing rule type {rule_type}")
        for context in _declared(block, label, "required_checks"):
            if context not in contexts:
                problems.append(f"{label}: missing required check {context}")
    return problems


def main(argv: list[str]) -> int:
    """Runs the check on the two files named in `argv`."""
    if len(argv) != 3:
        print("usage: check_ruleset.py RULES_JSON PROJECT_JSON", file=sys.stderr)
        return 2
    try:
        problems: list[str] = check(_load(argv[1]), _load(argv[2]))
    except ShapeError as exc:
        print(f"ruleset check failed closed: {exc}.", file=sys.stderr)
        return 1
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
