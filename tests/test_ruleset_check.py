"""Tests for the ruleset drift check (plan task B8)."""

import copy
import importlib.util
import json
import subprocess  # noqa: S404  # fixed argument lists, no shell
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT: Path = Path(__file__).resolve().parent.parent / ".github" / "scripts" / "check_ruleset.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_ruleset", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module: ModuleType = importlib.util.module_from_spec(spec)
    previous: bool = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # keep .pyc files out of the repo tree
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


check_ruleset: ModuleType = _load()

TYPES: list[str] = ["deletion", "non_fast_forward", "pull_request", "required_status_checks"]
CHECKS: list[str] = ["lint", "test"]

PROJECT: dict[str, Any] = {
    "ruleset": {"name": "r", "rule_types": TYPES, "required_checks": CHECKS},
    "rulesets": [{"name": "r", "source": "repo", "rule_types": TYPES, "required_checks": CHECKS}],
}


def _rules(checks: list[str], types: list[str] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"type": t, "ruleset_id": 1} for t in (types or TYPES[:3])]
    out.append(
        {
            "type": "required_status_checks",
            "ruleset_id": 1,
            "parameters": {"required_status_checks": [{"context": c} for c in checks]},
        }
    )
    return out


def test_passes_when_everything_is_present() -> None:
    assert check_ruleset.check(_rules(CHECKS), PROJECT) == []


def test_passes_with_an_extra_check_on_github() -> None:
    assert check_ruleset.check(_rules([*CHECKS, "extra"]), PROJECT) == []


def test_fails_naming_a_missing_check() -> None:
    problems = check_ruleset.check(_rules(["lint"]), PROJECT)
    assert any("missing required check test" in p for p in problems)


def test_fails_naming_a_missing_rule_type() -> None:
    problems = check_ruleset.check(_rules(CHECKS, ["deletion", "pull_request"]), PROJECT)
    assert any("missing rule type non_fast_forward" in p for p in problems)


def test_missing_items_are_found_in_a_rulesets_entry_alone() -> None:
    project = copy.deepcopy(PROJECT)
    project["rulesets"].append(
        {"name": "x", "rule_types": ["creation"], "required_checks": ["other"]}
    )
    problems = check_ruleset.check(_rules(CHECKS), project)
    assert any(p.startswith("rulesets[1]: missing rule type creation") for p in problems)
    assert any(p.startswith("rulesets[1]: missing required check other") for p in problems)
    assert not any(p.startswith("ruleset:") for p in problems)


def test_missing_items_are_found_in_the_ruleset_block_alone() -> None:
    project = copy.deepcopy(PROJECT)
    project["ruleset"]["rule_types"] = [*TYPES, "creation"]
    project["ruleset"]["required_checks"] = [*CHECKS, "other"]
    problems = check_ruleset.check(_rules(CHECKS), project)
    assert any(p.startswith("ruleset: missing rule type creation") for p in problems)
    assert any(p.startswith("ruleset: missing required check other") for p in problems)
    assert not any(p.startswith("rulesets[") for p in problems)


def _pinned_rules(app: int | None) -> list[dict[str, Any]]:
    rules = _rules(CHECKS)
    for rule in rules:
        if rule["type"] == "required_status_checks":
            checks = rule["parameters"]["required_status_checks"]
            checks[0]["integration_id"] = app
    return rules


def _pinned_project(app: Any) -> dict[str, Any]:
    project = copy.deepcopy(PROJECT)
    project["rulesets"][0]["check_integrations"] = {"lint": app}
    return project


def test_a_matching_integration_id_passes() -> None:
    assert check_ruleset.check(_pinned_rules(15368), _pinned_project(15368)) == []


@pytest.mark.parametrize("app", [None, 99])
def test_a_missing_or_different_integration_id_fails(app: int | None) -> None:
    problems = check_ruleset.check(_pinned_rules(app), _pinned_project(15368))
    assert any("rulesets[0]: required check lint is not pinned to app 15368" in p for p in problems)


def test_an_undeclared_pin_is_not_checked() -> None:
    assert check_ruleset.check(_pinned_rules(None), PROJECT) == []


@pytest.mark.parametrize(
    "pins", [["lint"], {"nope": 15368}, {"lint": "15368"}, {"lint": True}, {"lint": 0}]
)
def test_a_bad_check_integrations_fails_closed(pins: Any) -> None:
    project = copy.deepcopy(PROJECT)
    project["rulesets"][0]["check_integrations"] = pins
    with pytest.raises(check_ruleset.ShapeError):
        check_ruleset.check(_pinned_rules(15368), project)


def test_a_non_numeric_integration_id_on_github_fails_closed() -> None:
    rules = _pinned_rules(15368)
    rules[-1]["parameters"]["required_status_checks"][0]["integration_id"] = "15368"
    with pytest.raises(check_ruleset.ShapeError):
        check_ruleset.check(rules, PROJECT)


def _drop(project: dict[str, Any], *path: str | int) -> dict[str, Any]:
    out = copy.deepcopy(project)
    node: Any = out
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    return out


def _empty(project: dict[str, Any], *path: str | int) -> dict[str, Any]:
    out = copy.deepcopy(project)
    node: Any = out
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = []
    return out


@pytest.mark.parametrize(
    "project",
    [
        _drop(PROJECT, "rulesets"),
        _empty(PROJECT, "rulesets"),
        _empty(PROJECT, "ruleset", "required_checks"),
        _empty(PROJECT, "ruleset", "rule_types"),
        _empty(PROJECT, "rulesets", 0, "required_checks"),
        _empty(PROJECT, "rulesets", 0, "rule_types"),
        _drop(PROJECT, "ruleset"),
        ["not", "a", "mapping"],
    ],
)
def test_fails_closed_on_a_bad_project_file(project: Any) -> None:
    with pytest.raises(check_ruleset.ShapeError):
        check_ruleset.check(_rules(CHECKS), project)


@pytest.mark.parametrize(
    "rules",
    [
        {"not": "a list"},
        [{"no_type": True}],
        [{"type": "required_status_checks"}],
        [{"type": "required_status_checks", "parameters": {"required_status_checks": [{}]}}],
    ],
)
def test_fails_closed_on_bad_rules(rules: Any) -> None:
    with pytest.raises(check_ruleset.ShapeError):
        check_ruleset.check(rules, PROJECT)


def _run(tmp_path: Path, rules: str, project: str) -> subprocess.CompletedProcess[str]:
    rules_file = tmp_path / "rules.json"
    project_file = tmp_path / "project.json"
    rules_file.write_text(rules, encoding="utf-8")
    project_file.write_text(project, encoding="utf-8")
    return subprocess.run(  # noqa: S603
        [sys.executable, "-I", str(SCRIPT), str(rules_file), str(project_file)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_script_exit_codes(tmp_path: Path) -> None:
    good = _run(tmp_path, json.dumps(_rules(CHECKS)), json.dumps(PROJECT))
    assert good.returncode == 0
    drift = _run(tmp_path, json.dumps(_rules(["lint"])), json.dumps(PROJECT))
    assert drift.returncode == 1
    assert "test" in drift.stderr
    malformed = _run(tmp_path, "{not json", json.dumps(PROJECT))
    assert malformed.returncode == 1
    assert "failed closed" in malformed.stderr


def test_script_without_arguments_exits_two() -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-I", str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 2
