"""Unit test suite for the core resume generation and Gemini API integration engine."""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure absolute import alignment to avoid namespace pollution
from resume_optimizer import generate
from resume_optimizer.adapters import MockLLMAdapter

# Ensure the GEMINI_API_KEY check in generate.py passes during import.
os.environ.setdefault("GEMINI_API_KEY", "test-key")

pytestmark = pytest.mark.usefixtures("stand_in_resources")


def test_clean_filename_normalizes_text() -> None:
    """Verifies strings are safely sanitized for file system naming conventions."""
    assert generate.clean_filename("My Role!") == "My_Role"
    assert generate.clean_filename("Acme Inc / Developer") == "Acme_Inc__Developer"
    assert generate.clean_filename("") == "Unknown"
    assert generate.clean_filename(None) == "Unknown"


def test_parse_args_defaults_to_no_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validates the CLI defaults when no flags are provided."""
    monkeypatch.setattr(sys, "argv", ["generate-resume"])
    args: argparse.Namespace = generate.parse_args()

    assert args.validate is False


def test_parse_args_enables_validation_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the --validate CLI flag parses correctly."""
    monkeypatch.setattr(sys, "argv", ["generate-resume", "--validate"])
    args: argparse.Namespace = generate.parse_args()

    assert args.validate is True


def test_parse_args_enables_preserve_markdown_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the --preserve-markdown CLI flag parses correctly."""
    monkeypatch.setattr(sys, "argv", ["generate-resume", "--preserve-markdown"])
    args: argparse.Namespace = generate.parse_args()

    assert args.preserve_markdown is True


def test_parse_args_defaults_preserve_markdown_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validates the markdown preservation defaults to False."""
    monkeypatch.setattr(sys, "argv", ["generate-resume"])
    args: argparse.Namespace = generate.parse_args()

    assert args.preserve_markdown is False


def test_parse_args_defaults_grouped_layout_to_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validates the grouped-by-employer layout is the default."""
    monkeypatch.setattr(sys, "argv", ["generate-resume"])
    args: argparse.Namespace = generate.parse_args()

    assert args.grouped_layout is True


def test_parse_args_disables_grouped_layout_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies --no-grouped-layout restores the flat chronological layout."""
    monkeypatch.setattr(sys, "argv", ["generate-resume", "--no-grouped-layout"])
    args: argparse.Namespace = generate.parse_args()

    assert args.grouped_layout is False


def test_parse_args_enables_grouped_layout_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the --grouped-layout CLI flag parses correctly."""
    monkeypatch.setattr(sys, "argv", ["generate-resume", "--grouped-layout"])
    args: argparse.Namespace = generate.parse_args()

    assert args.grouped_layout is True


def test_parse_args_enables_master_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the --master CLI flag parses correctly."""
    monkeypatch.setattr(sys, "argv", ["generate-resume", "--master"])
    args: argparse.Namespace = generate.parse_args()

    assert args.master is True


def test_generate_collateral_markdown_structure_is_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies Jinja2 markdown templates compile correctly with standard layouts."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text(
        "Resume for {{ contact.name }}\n"
        "## Professional Skills\n"
        "{{ skills_list | join(' • ') }}\n"
        "## Professional Experience\n"
        "{% if grouped_layout %}GROUPED{% else %}"
        "{% for co in experience %}"
        "{% for role in co.roles %}"
        "### {{ co.company }} — {{ role.title }} | {{ role.dates }}\n"
        "{% for bullet in role.bullets %}"
        "* {{ bullet }}\n"
        "{% endfor %}"
        "{% endfor %}"
        "{% endfor %}"
        "{% endif %}",
        encoding="utf-8",
    )
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear Hiring,\n{{ cover_letter_body }}", encoding="utf-8"
    )

    captured_markdown: dict[str, str] = {}

    def mock_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        with open(input_file, "r", encoding="utf-8") as f:
            if "resume" in input_file.lower():
                captured_markdown["resume"] = f.read()
            else:
                captured_markdown["cover_letter"] = f.read()
        Path(outputfile).write_text("fake docx", encoding="utf-8")

    def mock_get_pandoc_version() -> str:
        return "2.0"

    expected_payload = {
        "job_metadata": {
            "company_name": "Acme Inc",
            "role_title": "Developer",
        },
        "professional_summary": "Strategic engineer",
        "selected_skills": ["Python", "SQL"],
        "tailored_companies": [
            {
                "company": "Acme Inc",
                "dates": "2020-2024",
                "roles": [
                    {
                        "title": "Developer",
                        "dates": "2020-2024",
                        "bullets": ["Built features.", "Led team."],
                    }
                ],
            }
        ],
        "cover_letter_body": "I am interested in this role.",
    }

    mock_adapter = MockLLMAdapter(mock_responses=[expected_payload])
    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: mock_adapter)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    generate.generate_collateral("Target job requisition", grouped_layout=False)

    resume_md: str = captured_markdown["resume"]
    cover_letter_md: str = captured_markdown["cover_letter"]

    assert "## Professional Skills" in resume_md
    assert "## Professional Experience" in resume_md
    assert "Python • SQL" in resume_md
    assert "### Acme Inc — Developer | 2020-2024" in resume_md
    assert "* Built features." in resume_md
    assert "* Led team." in resume_md
    assert "Dear Hiring," in cover_letter_md
    assert "I am interested in this role." in cover_letter_md


def test_generate_collateral_preserve_markdown_keeps_temp_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensures temp markdown files are successfully retained when the preserve flag is passed."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Resume", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text("Cover letter", encoding="utf-8")

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def mock_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake", encoding="utf-8")

    expected_payload = {
        "job_metadata": {"company_name": "Acme", "role_title": "Dev"},
        "professional_summary": "Experienced engineer specializing in automated test pipelines.",
        "selected_skills": [],
        "tailored_companies": [],
        "cover_letter_body": "Hello",
    }

    mock_adapter = MockLLMAdapter(mock_responses=[expected_payload])
    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: mock_adapter)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    run_dir = generate.generate_collateral("Job req", preserve_markdown=True)

    assert (run_dir / "temp_resume.md").exists()
    assert (run_dir / "temp_cl.md").exists()
    assert (run_dir / "Acme_Dev_Resume_A.docx").exists()


def test_validate_resume_requests_ats_prompt_and_returns_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensures ATS validation correctly sends the target prompt and parses output."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ats_prompt.txt").write_text("ATS parser prompt", encoding="utf-8")

    expected_ats_output = {
        "ats_score": 92,
        "missing_keywords": ["AWS", "Docker"],
        "formatting_compliance": "Excellent",
        "critical_feedback": "Keep using strong action verbs.",
    }

    mock_engine = MockLLMAdapter(mock_responses=[expected_ats_output])

    result: dict[str, Any] = generate.validate_resume(
        job_req_text="Target requisition", resume_text="Target resume", llm_engine=mock_engine
    )

    assert result["ats_score"] == 92
    assert result["missing_keywords"] == ["AWS", "Docker"]


def test_print_ats_validation_summary_outputs_expected_fields(
    capsys: pytest.CaptureFixture,
) -> None:
    """Verifies ATS JSON results are correctly flattened to STDOUT."""
    ats_results: dict[str, Any] = {
        "ats_score": 90,
        "missing_keywords": ["SQL"],
        "formatting_compliance": "Good",
        "critical_feedback": "Use metrics.",
    }

    generate.print_ats_validation_summary(ats_results)
    captured: Any = capsys.readouterr()

    assert "=== ATS Validation Results ===" in captured.out
    assert "Score: 90/100" in captured.out
    assert "Missing keywords:" in captured.out
    assert "  - SQL" in captured.out
    assert "Formatting compliance: Good" in captured.out
    assert "Critical feedback: Use metrics." in captured.out
    assert '"ats_score": 90' in captured.out


def test_generate_collateral_requires_master_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensures generate_collateral raises a FileNotFoundError if the master JSON is missing."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="master_data.json is missing"):
        generate.generate_collateral("Sample job requisition")


def test_generate_collateral_requires_system_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensures generate_collateral raises a FileNotFoundError if the prompt is missing."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )

    with pytest.raises(FileNotFoundError, match="system_prompt.txt is missing"):
        generate.generate_collateral("Sample job requisition")


def test_generate_collateral_builds_docx_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies full system compilation successfully produces final docx files."""
    monkeypatch.chdir(tmp_path)

    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text(
        "Resume for {{ contact.name }}\n"
        "Skills:\n"
        "{% for skill in skills_list %}- {{ skill }}\n{% endfor %}",
        encoding="utf-8",
    )
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear {{ contact.name }},\n{{ cover_letter_body }}",
        encoding="utf-8",
    )

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def fake_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake docx content", encoding="utf-8")

    expected_payload = {
        "job_metadata": {
            "company_name": "Acme Inc",
            "role_title": "Developer",
        },
        "professional_summary": (
            "Strategic software engineer specializing in scalable system integrations."
        ),
        "selected_skills": ["Python", "SQL"],
        "tailored_companies": [
            {
                "company": "Acme Inc",
                "dates": "2020-2024",
                "roles": [
                    {
                        "title": "Developer",
                        "dates": "2020-2024",
                        "bullets": ["Built features."],
                    }
                ],
            }
        ],
        "cover_letter_body": "Hello from Acme",
    }

    mock_adapter = MockLLMAdapter(mock_responses=[expected_payload])
    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: mock_adapter)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", fake_convert_file)

    run_dir = generate.generate_collateral("Target job requisition")

    resume_output: Path = run_dir / "Acme_Inc_Developer_Resume_A.docx"
    cover_output: Path = run_dir / "Acme_Inc_Developer_CoverLetter_A.docx"

    assert resume_output.exists()
    assert cover_output.exists()
    assert not (run_dir / "temp_resume.md").exists()
    assert not (run_dir / "temp_cl.md").exists()


def test_generate_collateral_performs_optional_ats_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Ensures ATS validation execution integrates into the compilation lifecycle."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "ats_prompt.txt").write_text("ATS parser prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text(
        "Resume for {{ contact.name }}\n"
        "Skills:\n"
        "{% for skill in skills_list %}- {{ skill }}\n{% endfor %}",
        encoding="utf-8",
    )
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear {{ contact.name }},\n{{ cover_letter_body }}", encoding="utf-8"
    )

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def mock_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake docx content", encoding="utf-8")

    expected_resume_payload = {
        "job_metadata": {
            "company_name": "Acme Inc",
            "role_title": "Developer",
        },
        "professional_summary": (
            "Strategic software engineer specializing in scalable system integrations."
        ),
        "selected_skills": ["Python", "SQL"],
        "tailored_companies": [
            {
                "company": "Acme Inc",
                "dates": "2020-2024",
                "roles": [
                    {
                        "title": "Developer",
                        "dates": "2020-2024",
                        "bullets": ["Built features."],
                    }
                ],
            }
        ],
        "cover_letter_body": "Hello from Acme",
    }

    expected_ats_payload = {
        "ats_score": 86,
        "missing_keywords": ["Python", "CI/CD"],
        "formatting_compliance": "Good",
        "critical_feedback": "Add more role-specific metrics and reduce dense language.",
    }

    # Pass sequential fixtures to satisfy both generate_collateral and validate_resume engine hits
    mock_adapter = MockLLMAdapter(mock_responses=[expected_resume_payload, expected_ats_payload])
    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: mock_adapter)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    generate.generate_collateral("Target job requisition", validate=True)

    captured: Any = capsys.readouterr()
    assert "=== ATS Validation Results ===" in captured.out
    assert "Score: 86/100" in captured.out
    assert "Python" in captured.out
    assert "critical_feedback" in captured.out


def test_generate_collateral_skips_ats_validation_when_flag_not_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensures the ATS parser is skipped when the validation flag defaults to false."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Resume for {{ contact.name }}", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear {{ contact.name }}, {{ cover_letter_body }}", encoding="utf-8"
    )

    def fail_if_called(job_req_text: str, resume_text: str, llm_engine: Any) -> None:
        raise AssertionError("validate_resume should not be called when validate=False")

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def mock_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake docx", encoding="utf-8")

    expected_payload = {
        "job_metadata": {
            "company_name": "Acme Inc",
            "role_title": "Developer",
        },
        "professional_summary": "Strategic software engineer specializing in automated tooling.",
        "selected_skills": [],
        "tailored_companies": [],
        "cover_letter_body": "Hello",
    }

    mock_adapter = MockLLMAdapter(mock_responses=[expected_payload])
    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: mock_adapter)
    monkeypatch.setattr(generate, "validate_resume", fail_if_called)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    run_dir = generate.generate_collateral("Target job requisition")

    assert (run_dir / "Acme_Inc_Developer_Resume_A.docx").exists()
    assert (run_dir / "Acme_Inc_Developer_CoverLetter_A.docx").exists()


def test_generate_collateral_uses_unknown_prefix_when_metadata_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensures fallback dynamic prefix is used if metadata is absent or empty from AI response."""
    monkeypatch.chdir(tmp_path)

    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Resume for {{ contact.name }}", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear {{ contact.name }}, {{ cover_letter_body }}", encoding="utf-8"
    )

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def mock_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake docx", encoding="utf-8")

    # Fixed: Satisfy contract schema layer while passing empty strings to trigger clean_filename
    expected_payload = {
        "job_metadata": {
            "company_name": "",
            "role_title": "",
        },
        "professional_summary": "",
        "selected_skills": [],
        "tailored_companies": [],
        "cover_letter_body": "Hello",
    }

    mock_adapter = MockLLMAdapter(mock_responses=[expected_payload])
    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: mock_adapter)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    run_dir = generate.generate_collateral("Target job requisition")

    # Fixed: clean_filename("") safely normalizes to "Unknown" when keys are empty
    assert (run_dir / "Unknown_Unknown_Resume_A.docx").exists()
    assert (run_dir / "Unknown_Unknown_CoverLetter_A.docx").exists()


def test_evaluate_desirability_requests_prompt_and_returns_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensures evaluate desirability triggers the correct prompt and returns parsed results."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "desirability_prompt.txt").write_text("Desirability prompt rules", encoding="utf-8")

    captured: dict[str, Any] = {}

    class FakeResponse:
        """Mock for Gemini API response."""

        def __init__(self, text: str) -> None:
            self.text: str = text

    class FakeModels:
        """Mock for Gemini models module."""

        def generate_content(self, model: str, contents: str, config: Any) -> FakeResponse:
            captured["config"] = config
            return FakeResponse(
                json.dumps(
                    {
                        "desirability_score": 85,
                        "salary_match": "Exceeds minimum",
                        "remote_match": "Fully remote match",
                        "benefits_analysis": "Includes target matching 401k",
                        "pros": ["Good pay"],
                        "cons": ["Unknown PTO limitations"],
                    }
                )
            )

    class FakeClient:
        """Mock for Gemini API Client."""

        def __init__(self, http_options: Any = None) -> None:
            self.models: FakeModels = FakeModels()

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))

    prefs: dict[str, str] = {"Pref_Min_Salary": "160000"}
    result: dict[str, Any] = generate.evaluate_desirability("Looking for architect role", prefs)

    assert result["desirability_score"] == 85
    assert result["salary_match"] == "Exceeds minimum"
    assert captured["config"].system_instruction == "Desirability prompt rules"


def test_generate_collateral_saves_desirability_report_when_flag_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies job desirability logic generates and saves the metric report."""
    monkeypatch.chdir(tmp_path)

    # 1. Mock minimal master data with profile preferences
    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": {"Name": "Alex Tester", "Pref_Min_Salary": "150k"}}),
        encoding="utf-8",
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Resume Layout", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text("Cover Letter Layout", encoding="utf-8")
    (tmp_path / "desirability_prompt.txt").write_text("Desirability core rule", encoding="utf-8")

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def mock_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake", encoding="utf-8")

    # 2. Define payload 1: Core Resume Generation Response
    expected_resume_payload = {
        "job_metadata": {
            "company_name": "Stark Industries",
            "role_title": "Security Lead",
        },
        "professional_summary": "Expert IT architecture specialist.",
        "selected_skills": [],
        "tailored_companies": [],
        "cover_letter_body": "Hello",
    }

    # 3. Define payload 2: Desirability Review Pass Response
    expected_desirability_payload = {
        "desirability_score": 95,
        "salary_match": "Match",
        "remote_match": "Match",
        "benefits_analysis": "Great",
        "pros": ["Remote"],
        "cons": [],
    }

    # 4. Inject MockLLMAdapter for the resume generation step
    mock_adapter = MockLLMAdapter(mock_responses=[expected_resume_payload])
    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: mock_adapter)

    # 5. Patch evaluate_desirability directly to return our controlled mock payload
    monkeypatch.setattr(
        generate, "evaluate_desirability", lambda job_req, prefs: expected_desirability_payload
    )

    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    # 6. Execute the pipeline
    run_dir = generate.generate_collateral(
        "We are looking for a remote security expert.", evaluate_job=True
    )

    # Assert filename existence and correct content formatting matches the mock payload
    expected_report: Path = run_dir / "Stark_Industries_Security_Lead_desirability_AT.txt"
    assert expected_report.exists()
    assert "Score: 95/100" in expected_report.read_text(encoding="utf-8")


def test_generate_collateral_master_mode_skips_cover_letter_and_validations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies that master mode overrides validations and avoids cover letter rendering."""
    monkeypatch.chdir(tmp_path)

    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    (tmp_path / "master_prompt.txt").write_text("master prompt rules", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Master Resume", encoding="utf-8")

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def fake_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake docx content", encoding="utf-8")

    def fail_if_called(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Validation/Desirability logic should not be invoked in master mode.")

    # Fixed: Added professional_summary to satisfy MockLLMAdapter's contract guard
    expected_payload = {
        "job_metadata": {
            "company_name": "Master",
            "role_title": "Resume",
        },
        "professional_summary": "Comprehensive engineering portfolio master document.",
        "selected_skills": ["Everything"],
        "tailored_companies": [],
        "cover_letter_body": "",
    }

    mock_adapter = MockLLMAdapter(mock_responses=[expected_payload])
    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: mock_adapter)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", fake_convert_file)
    monkeypatch.setattr(generate, "validate_resume", fail_if_called)
    monkeypatch.setattr(generate, "evaluate_desirability", fail_if_called)

    run_dir = generate.generate_collateral(
        "Bypass text", validate=True, evaluate_job=True, master_mode=True
    )

    resume_output: Path = run_dir / "Master_Resume_Resume_A.docx"
    cover_output: Path = run_dir / "Master_Resume_CoverLetter_A.docx"

    assert resume_output.exists()
    assert not cover_output.exists()
    assert not (run_dir / "temp_cl.md").exists()


SYNTHETIC_CONTACT: dict[str, str] = {
    "Name": "Jane Doe",
    "Email": "jane.doe@example.com",
    "Phone": "555-0100",
    "LinkedIn": "linkedin.com/in/janedoe",
    "Location": "Seattle, WA",
    "Pref_Min_Salary": "150k",
}


def test_provider_payload_is_an_allowlist_of_career_keys() -> None:
    """Only the career keys go out. `contact` and any unknown key stay local."""
    data: dict[str, Any] = {
        "contact": SYNTHETIC_CONTACT,
        "Contact": SYNTHETIC_CONTACT,
        "profile": {"phone": "555-0100"},
        "all_skills": ["Python"],
        "companies": [],
    }

    assert generate.provider_payload(data) == {"all_skills": ["Python"], "companies": []}


def test_name_stated_in_keeps_only_names_the_text_states() -> None:
    """A hiring manager is kept only if the requisition states the name."""
    req: str = "Questions go to  sam   LEE in talent."

    assert generate.name_stated_in("Sam Lee", req) == "Sam Lee"
    assert generate.name_stated_in("Pat Roe", req) == ""
    assert generate.name_stated_in("", req) == ""
    assert generate.name_stated_in(None, req) == ""
    assert generate.name_stated_in("Ann", "strong annual planning skills") == ""


def test_format_letter_date_has_no_zero_padded_day() -> None:
    """The letter date reads like a business letter."""
    from datetime import date

    assert generate.format_letter_date(date(2026, 3, 5)) == "March 5, 2026"


def test_no_contact_field_reaches_the_provider_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No contact value appears in the prompt or the system instruction sent to the provider."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps(
            {
                "contact": SYNTHETIC_CONTACT,
                "all_skills": ["Python"],
                "companies": [{"company": "Acme Inc", "roles": []}],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    # Templates that print the whole contact block, as the real ones do, so a leak would show.
    (tmp_path / "resume_template.md").write_text(
        "{{ contact['Name'] }} {{ contact['Email'] }} {{ contact['Phone'] }} "
        "{{ contact['Location'] }} {{ contact['LinkedIn'] }}",
        encoding="utf-8",
    )
    (tmp_path / "cover_letter_template.md").write_text("Letter", encoding="utf-8")
    (tmp_path / "ats_prompt.txt").write_text("ats prompt", encoding="utf-8")

    payload: dict[str, Any] = {
        "job_metadata": {"company_name": "Acme Inc", "role_title": "Developer"},
        "professional_summary": "Engineer.",
        "selected_skills": ["Python"],
        "tailored_companies": [],
        "cover_letter_body": "Hello.",
    }
    ats_payload: dict[str, Any] = {
        "ats_score": 90,
        "missing_keywords": [],
        "formatting_compliance": "ok",
        "critical_feedback": "none",
    }
    mock_adapter = MockLLMAdapter(mock_responses=[payload, ats_payload])
    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: mock_adapter)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(
        generate.pypandoc,
        "convert_file",
        lambda input_file, fmt, outputfile, **kw: Path(outputfile).write_text("x"),
    )
    monkeypatch.setattr(generate, "page_count", lambda path: 1)

    generate.generate_collateral("Target job requisition", validate=True)

    assert len(mock_adapter.call_history) == 2  # generation and the ATS pass
    sent: str = json.dumps(mock_adapter.call_history)
    for value in SYNTHETIC_CONTACT.values():
        assert value not in sent
    assert "contact" not in mock_adapter.call_history[0]["prompt"]
    assert "Acme Inc" in mock_adapter.call_history[0]["prompt"]


def test_generate_collateral_renders_headline_and_letter_frame(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Code supplies the headline, location and the letter's date, addressee and Re: line."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": SYNTHETIC_CONTACT}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text(
        "{{ contact['Name'] }}|{{ headline }}|{{ contact['Location'] }}", encoding="utf-8"
    )
    (tmp_path / "cover_letter_template.md").write_text(
        "{{ letter_date }}|{{ hiring_manager }}|{{ company }}|Re: {{ role }}|{{ contact['Name'] }}",
        encoding="utf-8",
    )

    captured: dict[str, str] = {}

    def fake_convert(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        captured[Path(input_file).name] = Path(input_file).read_text(encoding="utf-8")
        Path(outputfile).write_text("x", encoding="utf-8")

    payload: dict[str, Any] = {
        "job_metadata": {
            "company_name": "Acme Inc",
            "role_title": "Developer",
            "hiring_manager": "Sam Lee",
        },
        "headline": "Platform engineer for regulated systems",
        "professional_summary": "Engineer.",
        "selected_skills": [],
        "tailored_companies": [],
        "cover_letter_body": "Hello.",
    }
    monkeypatch.setattr(
        "resume_optimizer.generate.get_llm_engine",
        lambda: MockLLMAdapter(mock_responses=[payload]),
    )
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(generate.pypandoc, "convert_file", fake_convert)
    monkeypatch.setattr(generate, "page_count", lambda path: 1)
    monkeypatch.setattr(generate, "format_letter_date", lambda today: "January 2, 2030")

    generate.generate_collateral("Reach Sam Lee in talent.", preserve_markdown=True)

    assert (
        captured["temp_resume.md"] == "Jane Doe|Platform engineer for regulated systems|Seattle, WA"
    )
    assert captured["temp_cl.md"] == "January 2, 2030|Sam Lee|Acme Inc|Re: Developer|Jane Doe"


def test_unstated_hiring_manager_is_dropped_from_the_letter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hiring manager the requisition does not name never reaches the letter."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": SYNTHETIC_CONTACT}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Resume", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear {{ hiring_manager or 'Hiring Manager' }},", encoding="utf-8"
    )

    captured: dict[str, str] = {}

    def fake_convert(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        captured[Path(input_file).name] = Path(input_file).read_text(encoding="utf-8")
        Path(outputfile).write_text("x", encoding="utf-8")

    payload: dict[str, Any] = {
        "job_metadata": {
            "company_name": "Acme Inc",
            "role_title": "Developer",
            "hiring_manager": "Invented Person",
        },
        "professional_summary": "Engineer.",
        "selected_skills": [],
        "tailored_companies": [],
        "cover_letter_body": "Hello.",
    }
    monkeypatch.setattr(
        "resume_optimizer.generate.get_llm_engine",
        lambda: MockLLMAdapter(mock_responses=[payload]),
    )
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(generate.pypandoc, "convert_file", fake_convert)
    monkeypatch.setattr(generate, "page_count", lambda path: 1)

    generate.generate_collateral("A requisition that names nobody.", preserve_markdown=True)

    assert captured["temp_cl.md"] == "Dear Hiring Manager,"


def _roles(*dates: str) -> dict[str, Any]:
    """Master data with one role per dates string."""
    roles = [{"title": "T", "dates": d} for d in dates]
    return {"companies": [{"company": "Acme Inc", "roles": roles}]}


def test_career_years_is_a_floor_from_the_earliest_year() -> None:
    """The span is floored: a year is taken off, then it rounds down to a multiple of five."""
    from datetime import date

    today = date(2026, 1, 15)

    assert generate.career_years(_roles("2000 - Present"), today) == "25+"
    assert generate.career_years(_roles("2015 - 2019", "2010 - Present"), today) == "15+"
    assert generate.career_years(_roles("2016 - Present"), today) == "9+"
    assert generate.career_years(_roles("2020 - Present"), today) == "5+"


def test_career_years_ends_at_the_last_year_unless_a_role_is_current() -> None:
    """A career that ended years ago is not counted up to today."""
    from datetime import date

    today = date(2026, 11, 4)

    assert generate.career_years(_roles("2000 - 2015"), today) == "10+"
    assert generate.career_years(_roles("2000 - Now"), today) == "25+"
    assert generate.career_years(_roles("Jan 2000 - Present"), today) == "25+"
    assert generate.career_years(_roles("Sept. 2000 - Present"), today) == "25+"
    assert generate.career_years(_roles("January 2000 - September 2010"), today) == "9+"
    assert generate.career_years(_roles("2000 to Present"), today) == "25+"
    assert generate.career_years(_roles("2008"), today) is None
    assert generate.career_years(_roles("2000", "2008"), today) == "7+"
    assert generate.career_years(_roles("2000 - 2015", "2020 - current"), today) == "25+"


def test_career_years_skips_fields_that_are_not_plain_date_ranges() -> None:
    """A stray year or a remark in a dates field makes it unreadable, so it is skipped."""
    from datetime import date

    today = date(2026, 11, 4)

    assert generate.career_years(_roles("2015 - Present (founded 1990)"), today) is None
    assert generate.career_years(_roles("2005 - 2010 (firm now defunct)"), today) is None
    assert generate.career_years(_roles("2010 - 2015 (rehired 2024)"), today) is None
    # a leading word that is not a month is not a date
    assert generate.career_years(_roles("Founded 1990 - Present"), today) is None
    assert generate.career_years(_roles("Est. 1990"), today) is None
    # a year in the future is a typo, so the whole field is skipped, not clamped
    assert generate.career_years(_roles("2000 - 2052"), today) is None
    assert generate.career_years(_roles("2000 - 2010", "2020 - 2052"), today) == "9+"
    # a skipped current role can only shorten the span
    assert generate.career_years(_roles("2000 - 2010", "2019 - Present (remote)"), today) == "9+"


def test_career_years_is_none_when_it_cannot_be_trusted() -> None:
    """No year, no companies, a span under a year or an absurd span gives nothing."""
    from datetime import date

    today = date(2026, 11, 4)

    assert generate.career_years({}, today) is None
    assert generate.career_years({"companies": ["not a dict"]}, today) is None
    assert generate.career_years(_roles("Present", ""), today) is None
    assert generate.career_years(_roles("2026 - Present"), today) is None
    assert generate.career_years(_roles("1906 - Present"), today) is None


def test_career_years_is_written_by_code_and_a_model_years_claim_is_flagged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Code puts the span in the header. The model never sees it, and a years claim it writes
    anyway is reported like any other unsupported number."""
    from datetime import date

    monkeypatch.chdir(tmp_path)
    started: int = date.today().year - 30  # a span under the 60-year sanity limit, in any year
    data: dict[str, Any] = {
        "contact": SYNTHETIC_CONTACT,
        "all_skills": ["Python"],
        **_roles(f"{started} - Present"),
    }
    (tmp_path / "ledger" / "master_data.json").write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text(
        "{{ headline }}|{{ career_years }} years of experience", encoding="utf-8"
    )
    (tmp_path / "cover_letter_template.md").write_text("Letter", encoding="utf-8")
    span: str | None = generate.career_years(data)
    assert span is not None
    digits: str = span.rstrip("+")
    captured: dict[str, str] = {}

    def fake_convert(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        captured[Path(input_file).name] = Path(input_file).read_text(encoding="utf-8")
        Path(outputfile).write_text("x", encoding="utf-8")

    def run(summary: str) -> tuple[str, MockLLMAdapter]:
        payload: dict[str, Any] = {
            "job_metadata": {"company_name": "Acme Inc", "role_title": "Developer"},
            "headline": "Platform engineer",
            "professional_summary": summary,
            "selected_skills": [],
            "tailored_companies": [],
            "cover_letter_body": "Hello.",
        }
        adapter = MockLLMAdapter(mock_responses=[payload])
        monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: adapter)
        monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
        monkeypatch.setattr(generate.pypandoc, "convert_file", fake_convert)
        monkeypatch.setattr(generate, "page_count", lambda path: 1)
        generate.generate_collateral("Target job requisition", preserve_markdown=True)
        return capsys.readouterr().out, adapter

    out, adapter = run("Engineer who cut costs.")
    assert captured["temp_resume.md"] == f"Platform engineer|{span} years of experience"
    assert "career_years" not in adapter.call_history[0]["prompt"]
    assert span not in adapter.call_history[0]["prompt"]
    assert "Numbers: none" in out
    for claim in (
        f"Leader with {span} years of experience.",
        f"Leader with {span} years of experience in Python.",
        f"{span} years of cloud work.",
    ):
        assert f"Numbers: {digits}" in run(claim)[0]


def test_resume_and_letter_share_the_reference_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The letter gets the resume's margins and styles, and both stay sandboxed."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": SYNTHETIC_CONTACT}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Resume", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text("Letter", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_convert(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        calls.append(kwargs["extra_args"])
        Path(outputfile).write_text("x", encoding="utf-8")

    payload: dict[str, Any] = {
        "job_metadata": {"company_name": "Acme Inc", "role_title": "Developer"},
        "professional_summary": "Engineer.",
        "selected_skills": [],
        "tailored_companies": [],
        "cover_letter_body": "Hello.",
    }
    monkeypatch.setattr(
        "resume_optimizer.generate.get_llm_engine",
        lambda: MockLLMAdapter(mock_responses=[payload]),
    )
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(generate.pypandoc, "convert_file", fake_convert)
    monkeypatch.setattr(generate, "page_count", lambda path: 1)

    generate.generate_collateral("Target job requisition")

    assert len(calls) == 2
    for extra_args in calls:
        assert "--reference-doc=resume_reference.docx" in extra_args
        assert "--sandbox" in extra_args


def test_main_exits_with_status_3_before_reading_stdin_when_a_path_is_in_the_repo(
    monkeypatch: pytest.MonkeyPatch,
    fake_checkout: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A data path inside a checkout is refused at start-up, naming the variable only."""
    monkeypatch.setenv("RO_RUNS_DIR", str(fake_checkout / "runs"))
    monkeypatch.setattr(sys, "argv", ["generate-resume"])

    def refuse_to_read() -> str:
        raise AssertionError("stdin was read")

    monkeypatch.setattr(sys.stdin, "read", refuse_to_read)

    with pytest.raises(SystemExit) as raised:
        generate.main()

    assert raised.value.code == 3
    stderr: str = capsys.readouterr().err
    assert "RO_RUNS_DIR" in stderr
    assert str(tmp_path) not in stderr
    assert tmp_path.as_posix() not in stderr


def test_an_explicit_data_path_in_the_repo_is_refused(fake_checkout: Path) -> None:
    from resume_optimizer import paths

    with pytest.raises(paths.DataPathRefusedError):
        generate.generate_collateral("Job req", data_path=fake_checkout / "master_data.json")


def test_no_log_record_carries_a_resolved_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The ATS, desirability and preserved-Markdown log extras carry bare names, never paths."""
    (tmp_path / "ledger" / "master_data.json").write_text(
        json.dumps({"contact": {"Name": "Alex Tester"}}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "ats_prompt.txt").write_text("ats prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Resume", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text("Letter", encoding="utf-8")

    resume_payload = {
        "job_metadata": {"company_name": "Acme", "role_title": "Dev"},
        "professional_summary": "Builds software.",
        "selected_skills": [],
        "tailored_companies": [],
        "cover_letter_body": "Hello",
    }
    ats_payload = {
        "ats_score": 90,
        "missing_keywords": [],
        "formatting_compliance": "ok",
        "critical_feedback": "none",
    }
    adapter = MockLLMAdapter(mock_responses=[resume_payload, ats_payload])
    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: adapter)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(
        generate.pypandoc,
        "convert_file",
        lambda input_file, fmt, outputfile, **kw: Path(outputfile).write_text("x"),
    )
    desirability = {
        "desirability_score": 80,
        "salary_match": "ok",
        "remote_match": "ok",
        "benefits_analysis": "ok",
        "pros": [],
        "cons": [],
    }
    monkeypatch.setattr(generate, "evaluate_desirability", lambda job_req, prefs: desirability)

    with caplog.at_level(logging.INFO):
        generate.generate_collateral(
            "A job requisition.", validate=True, evaluate_job=True, preserve_markdown=True
        )

    forbidden: list[str] = [str(tmp_path), str(tmp_path.resolve()), tmp_path.as_posix()]
    assert caplog.records
    for record in caplog.records:
        values: list[str] = [record.getMessage()]
        values += [v for v in record.__dict__.values() if isinstance(v, str)]
        for value in values:
            assert not any(path in value for path in forbidden)


def test_an_in_repo_runs_directory_is_refused_before_any_provider_call(
    monkeypatch: pytest.MonkeyPatch, fake_checkout: Path
) -> None:
    from resume_optimizer import paths

    (Path("ledger") / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    monkeypatch.setenv("RO_RUNS_DIR", str(fake_checkout / "runs"))

    def no_provider() -> None:
        raise AssertionError("the provider was called")

    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", no_provider)
    with pytest.raises(paths.DataPathRefusedError):
        generate.generate_collateral("Job req")
