"""Checks that the rulesets on `main` still hold what `.ai/project.yml` mirrors (plan task B8).

Usage: check_ruleset.py RULES_JSON PROJECT_JSON

RULES_JSON is the response of `GET /repos/{repo}/rules/branches/main`: the rules of every ruleset
that applies to the branch, tagged by ruleset id. PROJECT_JSON is `.ai/project.yml` as JSON. For
the `ruleset` block and every entry under `rulesets`, each declared rule type must be among the
applying rules and each declared required check among the `required_status_checks` contexts.
Extra checks on GitHub are not drift. A block may also declare `check_integrations`, a mapping
from a declared check to the id of the app it must be pinned to (for example 15368, GitHub
Actions). GitHub must then require that check with that `integration_id`, so a status from
another app or a personal token cannot satisfy it. A job in this repo that can write statuses
still posts as that app, so the pin does not stop one. A `check_integrations` that is null or not
a mapping fails closed. So does unreadable or wrongly shaped input, an empty `rulesets` list, and
an empty declared `required_checks` or `rule_types`. Bypass actors are not in the branch-rules
response, so they are not checked. The `pull_request` rule's parameters (approval count, merge
methods) are in it, but this check leaves them alone.
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


def applying(rules: Any) -> tuple[set[str], dict[str, set[int | None]]]:
    """Returns the rule types, and the required check contexts with the app ids they carry."""
    if not isinstance(rules, list):
        raise ShapeError("the branch rules are not a list")
    types: set[str] = set()
    contexts: dict[str, set[int | None]] = {}
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
                app: Any = check.get("integration_id")
                if app is not None and (isinstance(app, bool) or not isinstance(app, int)):
                    raise ShapeError("a required check has an integration_id that is not a number")
                contexts.setdefault(check["context"], set()).add(app)
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


def _integrations(block: Any, label: str, declared: list[str]) -> dict[str, int]:
    """Returns the app ids a block pins its checks to, which may be none."""
    pins: Any = block.get("check_integrations", {})
    if not isinstance(pins, dict):
        raise ShapeError(f"{label} has a check_integrations that is not a mapping")
    for context, app in pins.items():
        if context not in declared:
            raise ShapeError(f"{label} pins a check that is not in its required_checks")
        if isinstance(app, bool) or not isinstance(app, int) or app <= 0:
            raise ShapeError(f"{label} pins a check to an id that is not a positive number")
    return pins


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
        declared: list[str] = _declared(block, label, "required_checks")
        for context in declared:
            if context not in contexts:
                problems.append(f"{label}: missing required check {context}")
        for context, app in _integrations(block, label, declared).items():
            if context in contexts and app not in contexts[context]:
                problems.append(f"{label}: required check {context} is not pinned to app {app}")
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
