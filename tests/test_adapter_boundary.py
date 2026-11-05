"""Boundary test: only adapters.py may touch the Gemini SDK (``google.genai``)."""

import ast
from pathlib import Path

import resume_optimizer

PACKAGE_DIR: Path = Path(resume_optimizer.__file__).resolve().parent
ALLOWED: Path = Path("adapters.py")
SDK_NAMES: frozenset[str] = frozenset({"genai", "types"})


def _is_genai_module(name: str) -> bool:
    return name == "google.genai" or name.startswith("google.genai.")


def genai_reference_lines(source: str) -> list[int]:
    """Returns the line numbers where the source imports or reaches the Gemini SDK.

    Flags direct imports, any ``.genai`` attribute access (``google.genai.Client``,
    ``adapters.genai.Client``), re-export imports of the SDK names from the adapters module
    (absolute or relative), and string constants naming the SDK module.
    """
    lines: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            if any(_is_genai_module(a.name) for a in node.names):
                lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            module: str = node.module or ""
            names: set[str] = {a.name for a in node.names}
            if node.level == 0 and _is_genai_module(module):
                lines.append(node.lineno)
            elif node.level == 0 and module == "google" and "genai" in names:
                lines.append(node.lineno)
            elif (module.endswith("adapters") or (node.level > 0 and "adapters" in names)) and (
                names & SDK_NAMES
            ):
                lines.append(node.lineno)
        elif isinstance(node, ast.Attribute) and node.attr == "genai":
            lines.append(node.lineno)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if _is_genai_module(node.value):
                lines.append(node.lineno)
    return lines


def test_only_adapters_touch_google_genai() -> None:
    """No module in the package other than adapters.py references google.genai."""
    seen: set[Path] = set()
    offenders: list[str] = []
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        relative: Path = path.relative_to(PACKAGE_DIR)
        seen.add(relative)
        if relative == ALLOWED:
            continue
        for line in genai_reference_lines(path.read_text(encoding="utf-8")):
            offenders.append(f"{relative}:{line}")
    assert not offenders, f"google.genai referenced outside adapters.py: {offenders}"

    # Positive control on the real tree: the scan sees adapters.py and flags its SDK import.
    assert ALLOWED in seen
    assert genai_reference_lines((PACKAGE_DIR / ALLOWED).read_text(encoding="utf-8"))


def test_scanner_flags_each_form() -> None:
    """The scanner is not blind: each reference form is flagged."""
    flagged: list[str] = [
        "import google.genai",
        "from google import genai",
        "from google.genai import Client",
        "from google.genai.types import X",
        "from resume_optimizer.adapters import genai",
        "from .adapters import genai, types",
        "from . import adapters\nx = adapters.genai.Client()",
        "import google\nx = google.genai.Client()",
        'import importlib\nimportlib.import_module("google.genai")',
    ]
    for source in flagged:
        assert genai_reference_lines(source), source
    assert genai_reference_lines("import os\nfrom pathlib import Path") == []
