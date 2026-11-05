"""Runs the mock pipeline from an installed wheel, outside the checkout (plan task B2).

CI runs it as `python -I wheel_smoke.py <wheel>`, with the interpreter of a plain venv the wheel
was installed into, from a directory outside the checkout. Every check raises SystemExit with a
message. All data is synthetic and the provider, pandoc and the page counter are stood in for.
"""

import importlib.metadata
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

PACKAGED: tuple[str, ...] = (
    "resume_optimizer/prompts/system_prompt.txt",
    "resume_optimizer/prompts/master_prompt.txt",
    "resume_optimizer/prompts/ats_prompt.txt",
    "resume_optimizer/prompts/desirability_prompt.txt",
    "resume_optimizer/templates/resume_template.md",
    "resume_optimizer/templates/cover_letter_template.md",
)


def fail(message: str) -> None:
    """Stops the smoke test with a message."""
    raise SystemExit(f"wheel_smoke: {message}")


def check_wheel(argv: list[str]) -> Path:
    """Validates the argument and that the wheel holds every packaged file."""
    if len(argv) != 2:
        fail("usage: wheel_smoke.py <path to one .whl file>")
    wheel: Path = Path(argv[1])
    if wheel.suffix != ".whl" or not wheel.is_file():
        fail("the argument must name exactly one existing .whl file")
    with zipfile.ZipFile(wheel) as archive:
        names: set[str] = set(archive.namelist())
    missing: list[str] = [name for name in PACKAGED if name not in names]
    if missing:
        fail(f"the wheel is missing {len(missing)} packaged file(s)")
    return wheel


def check_versions(wheel: Path, package_version: str) -> None:
    """The installed metadata and the wheel file name must both carry the package version."""
    if importlib.metadata.version("resume-optimizer") != package_version:
        fail("the installed metadata version differs from the package __version__")
    if wheel.name.split("-")[1] != package_version:
        fail("the wheel file name's version differs from the package __version__")


def main(argv: list[str]) -> None:
    """Runs every check."""
    wheel: Path = check_wheel(argv)

    work: Path = Path(tempfile.mkdtemp(prefix="ro-smoke-"))
    ledger, runs, logs = work / "ledger", work / "runs", work / "logs"
    ledger.mkdir()
    os.environ["RO_LEDGER_DIR"] = str(ledger)
    os.environ["RO_RUNS_DIR"] = str(runs)
    os.environ["RO_LOG_DIR"] = str(logs)
    os.chdir(work)

    import resume_optimizer

    if "site-packages" not in Path(resume_optimizer.__file__).resolve().parts:
        fail("resume_optimizer was not imported from the installed wheel")
    check_versions(wheel, resume_optimizer.__version__)

    from resume_optimizer import generate
    from resume_optimizer.adapters import MockLLMAdapter

    (ledger / "master_data.json").write_text(
        json.dumps({"contact": {"Name": "Jane Doe"}, "all_skills": ["Python"], "companies": []}),
        encoding="utf-8",
    )
    payload: dict[str, Any] = {
        "job_metadata": {"company_name": "Example Co", "role_title": "Engineer"},
        "professional_summary": "Builds reliable software.",
        "selected_skills": ["Python"],
        "selected_certifications": [],
        "selected_education": [],
        "tailored_companies": [],
        "cover_letter_body": "A synthetic letter.",
    }
    adapter = MockLLMAdapter(mock_responses=[payload])

    def write_placeholder(_input: str, _fmt: str, outputfile: str, **_kwargs: object) -> None:
        Path(outputfile).write_text("placeholder", encoding="utf-8")

    generate.get_llm_engine = lambda *args, **kwargs: adapter
    generate.pypandoc.get_pandoc_version = lambda: "0"
    generate.pypandoc.convert_file = write_placeholder
    generate.scan_for_active_content = lambda path: []
    generate.page_count = lambda path: 1

    run_dir: Path = generate.generate_collateral("A synthetic requisition.", preserve_markdown=True)

    system_prompt: str = (generate.resources.PROMPT_DIR / "system_prompt.txt").read_text(
        encoding="utf-8"
    )
    if adapter.call_history[0]["system_instruction"] != system_prompt:
        fail("the first call did not carry the packaged system prompt")
    if "## Professional Skills" not in (run_dir / "temp_resume.md").read_text(encoding="utf-8"):
        fail("the preserved resume does not show the packaged template")
    children: list[Path] = list(runs.iterdir())
    if children != [run_dir]:
        fail("RO_RUNS_DIR must hold exactly the returned run directory")
    docs: list[str] = sorted(p.name for p in run_dir.glob("*.docx"))
    if len(docs) != 2:
        fail("the run directory must hold both documents")
    strays: list[str] = [p.name for p in work.iterdir() if p.suffix in {".docx", ".md"}]
    if strays:
        fail("a document or Markdown file was written to the working directory")
    print("wheel_smoke: ok")


if __name__ == "__main__":
    main(sys.argv)
