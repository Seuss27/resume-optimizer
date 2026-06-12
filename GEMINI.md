# Gemini Workspace Context and Coding Standards

This file establishes the architectural baseline, coding standards, and constraints for all
code generation, refactoring, and review tasks in this workspace.

---

## 1. Core Development Constraints

When generating, completing, or refactoring code, you must strictly adhere to the following
formatting and structural rules:

* **Target Environment:** All code must target Python 3.10+ idioms. Use modern built-ins for type
    hinting (e.g., `list[]`, `dict[]`, and `|` for unions) rather than importing from `typing`.
* **Line Length Limits:** All **Python source code** (`.py`), docstrings, and comments must
    strictly adhere to a **100-character column limit**. This rule does not apply to Markdown
    (`.md`) files.
* **Type Hinting:** Explicit type hints are mandatory for all function signatures, variable
    assignments, and class properties where the underlying language supports them.
* **Documentation:** Every function, method, module, and class must include clear, descriptive
    documentation (e.g., Docstrings) detailing its purpose, parameters, return types, and exceptions.

---

## 2. Test-Driven AI Requirements

You must operate under a "Tests Mandatory" framework.

* **1:1 Function-to-Test Coverage:** For *every* function or method generated, modified, or
    refactored, you must immediately provide or update a corresponding unit test.
* **Test Isolation:** Ensure tests isolate logic cleanly using appropriate mocking frameworks
    rather than relying on live network, database, or filesystem states.

---

## 3. Static Analysis & Code Quality Guardrails

* **Zero-Tolerance for Linter Bypasses:** You must never generate inline linting bypass
    comments (e.g., `# noqa`, `/* eslint-disable */`, or `<!-- markdownlint-disable -->`)
    to silence warnings. Code must be natively rewritten to fully satisfy the rule.
* **Modern Tooling Compliance:** All generated code must natively conform to strict,
    idiomatic configurations for **Ruff** (Python) and **markdownlint** (Markdown).
    Always prefer modern, standard-library approaches (such as `pathlib.Path`) over legacy or
    deprecated patterns.
* **Defensive and Idiomatic Writing:** Write code assuming strict type-checking and high
    maintainability scores. Avoid legacy wrappers, manual file stream handling, or tightly
    coupled structures.

---

## 4. Git, Issue, and Pull Request (PR) Protocols

When drafting commits, issues, or pull request templates, enforce the following structures:

### Git Commit Messages
Commit titles must use Conventional Commits formatting, limited to **50 characters** for the
subject line, followed by a blank line and a body wrapped at **72 characters**.
* *Format:* `<type>(<scope>): <short description>`
* *Allowed Types:* `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.
* *Tone:* Use imperative present-tense (e.g., "Fix bug", not "Fixed bug").

### Issue Generation
When generating an issue template for a bug or feature, structure it as follows:
1. **Description:** Clear, high-level summary of the requirement or observed behavior.
2. **Acceptance Criteria:** Bulleted checklist of exact conditions required to close the issue.
3. **Technical Notes:** Suggested implementation paths, impacted modules, or dependencies.

### Pull Request (PR) Descriptions
When writing a PR description based on workspace changes, include:
1. **Summary:** Brief explanation of *what* changed and *why* it was changed.
2. **Related Issue:** Link explicitly to the issue using keywords (e.g., `Closes #123`).
3. **Testing Verification:** Detail how the change was tested (e.g., coverage, env details).
4. **Impact Analysis:** Note any breaking changes, database migrations, or config updates.

---

## 5. Standard Code Template Target

Use the following Python snippet as the structural blueprint for styling, type-hinting,
documentation, and column-width constraints:

```python
from pathlib import Path


def process_user_dataset(
    user_ids: list[int],
    scaling_factor: float,
    default_tier: str | None = None
) -> list[dict]:
    """Processes a batch of user identifiers and normalizes system tier structures.

    Args:
        user_ids: A list of unique integer identifiers for target users.
        scaling_factor: A multiplier used to recalibrate internal user metrics.
        default_tier: An optional fallback classification string for new profiles.

    Returns:
        A list of processed dictionary objects representing structured user
        configurations.
    """
    # Keep operational logic clean, readable, and tightly bounded to 100 columns max
    processed_profiles: list[dict] = []

    for user_id in user_ids:
        calculated_metric = float(user_id) * scaling_factor
        profile = {
            "id": user_id,
            "metric": calculated_metric,
            "tier": default_tier or "Standard",
        }
        processed_profiles.append(profile)

    return processed_profiles
