"""Unit test suite for the core resume generation and Gemini API integration engine."""

import argparse
import json
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


def test_parse_args_defaults_grouped_layout_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validates the grouped layout configuration defaults to False."""
    monkeypatch.setattr(sys, "argv", ["generate-resume"])
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
    (tmp_path / "master_data.json").write_text(
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

    class FakeResponse:
        """Mock for Gemini API response."""

        def __init__(self, text: str) -> None:
            self.text: str = text

    class FakeModels:
        """Mock for Gemini models module."""

        def generate_content(self, model: str, contents: str, config: Any) -> FakeResponse:
            return FakeResponse(
                json.dumps(
                    {
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
                )
            )

    class FakeClient:
        """Mock for Gemini API Client."""

        def __init__(self, http_options: Any = None) -> None:
            self.models: FakeModels = FakeModels()

    def mock_get_pandoc_version() -> str:
        return "2.0"

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    generate.generate_collateral("Target job requisition")

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
    (tmp_path / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Resume", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text("Cover letter", encoding="utf-8")

    class FakeResponse:
        """Mock for Gemini API response."""

        def __init__(self, text: str) -> None:
            self.text: str = text

    class FakeModels:
        """Mock for Gemini models module."""

        def generate_content(self, model: str, contents: str, config: Any) -> FakeResponse:
            return FakeResponse(
                json.dumps(
                    {
                        "job_metadata": {"company_name": "Acme", "role_title": "Dev"},
                        "selected_skills": [],
                        "tailored_companies": [],
                        "cover_letter_body": "Hello",
                    }
                )
            )

    class FakeClient:
        """Mock for Gemini API Client."""

        def __init__(self, http_options: Any = None) -> None:
            self.models: FakeModels = FakeModels()

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def mock_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake", encoding="utf-8")

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    generate.generate_collateral("Job req", preserve_markdown=True)

    assert (tmp_path / "temp_resume.md").exists()
    assert (tmp_path / "temp_cl.md").exists()
    assert (tmp_path / "Acme_Dev_Resume_A.docx").exists()


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

    # Instantiate the adapter decoupled alternative
    mock_engine = MockLLMAdapter(mock_responses=[expected_ats_output])

    # Pass the required decoupled parameter directly down to the method signature
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
    (tmp_path / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )

    with pytest.raises(FileNotFoundError, match="system_prompt.txt is missing"):
        generate.generate_collateral("Sample job requisition")


def test_generate_collateral_builds_docx_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies full system compilation successfully produces final docx files."""
    monkeypatch.chdir(tmp_path)

    (tmp_path / "master_data.json").write_text(
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

    class FakeResponse:
        """Mock for Gemini API response."""

        def __init__(self, text: str) -> None:
            self.text: str = text

    class FakeModels:
        """Mock for Gemini models module."""

        def generate_content(self, model: str, contents: str, config: Any) -> FakeResponse:
            return FakeResponse(
                json.dumps(
                    {
                        "job_metadata": {
                            "company_name": "Acme Inc",
                            "role_title": "Developer",
                        },
                        "professional_summary": (
                            "Strategic software engineer specializing in "
                            "scalable system integrations."
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
                )
            )

    class FakeClient:
        """Mock for Gemini API Client."""

        def __init__(self, http_options: Any = None) -> None:
            self.models: FakeModels = FakeModels()

    def mock_get_pandoc_version() -> str:
        return "2.0"

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)

    def fake_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake docx content", encoding="utf-8")

    monkeypatch.setattr(generate.pypandoc, "convert_file", fake_convert_file)

    generate.generate_collateral("Target job requisition")

    resume_output: Path = tmp_path / "Acme_Inc_Developer_Resume_A.docx"
    cover_output: Path = tmp_path / "Acme_Inc_Developer_CoverLetter_A.docx"

    assert resume_output.exists()
    assert cover_output.exists()
    assert not (tmp_path / "temp_resume.md").exists()
    assert not (tmp_path / "temp_cl.md").exists()


def test_generate_collateral_performs_optional_ats_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Ensures ATS validation execution integrates into the compilation lifecycle."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "master_data.json").write_text(
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

    class FakeResponse:
        """Mock for Gemini API response."""

        def __init__(self, text: str) -> None:
            self.text: str = text

    class FakeModels:
        """Mock for Gemini models module."""

        def generate_content(self, model: str, contents: str, config: Any) -> FakeResponse:
            if "ATS parser" in config.system_instruction:
                return FakeResponse(
                    json.dumps(
                        {
                            "ats_score": 86,
                            "missing_keywords": ["Python", "CI/CD"],
                            "formatting_compliance": "Good",
                            "critical_feedback": (
                                "Add more role-specific metrics and reduce dense language."
                            ),
                        }
                    )
                )

            return FakeResponse(
                json.dumps(
                    {
                        "job_metadata": {
                            "company_name": "Acme Inc",
                            "role_title": "Developer",
                        },
                        "professional_summary": (
                            "Strategic software engineer specializing in "
                            "scalable system integrations."
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
                )
            )

    class FakeClient:
        """Mock for Gemini API Client."""

        def __init__(self, http_options: Any = None) -> None:
            self.models: FakeModels = FakeModels()

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def mock_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake docx content", encoding="utf-8")

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
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
    (tmp_path / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Resume for {{ contact.name }}", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear {{ contact.name }}, {{ cover_letter_body }}", encoding="utf-8"
    )

    def fail_if_called(job_req_text: str, resume_text: str) -> None:
        raise AssertionError("validate_resume should not be called when validate=False")

    class FakeResponse:
        """Mock for Gemini API response."""

        def __init__(self, text: str) -> None:
            self.text: str = text

    class FakeModels:
        """Mock for Gemini models module."""

        def generate_content(self, model: str, contents: str, config: Any) -> FakeResponse:
            return FakeResponse(
                json.dumps(
                    {
                        "job_metadata": {
                            "company_name": "Acme Inc",
                            "role_title": "Developer",
                        },
                        "selected_skills": [],
                        "tailored_companies": [],
                        "cover_letter_body": "Hello",
                    }
                )
            )

    class FakeClient:
        """Mock for Gemini API Client."""

        def __init__(self, http_options: Any = None) -> None:
            self.models: FakeModels = FakeModels()

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def mock_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake docx", encoding="utf-8")

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate, "validate_resume", fail_if_called)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    generate.generate_collateral("Target job requisition")

    assert (tmp_path / "Acme_Inc_Developer_Resume_A.docx").exists()
    assert (tmp_path / "Acme_Inc_Developer_CoverLetter_A.docx").exists()


def test_generate_collateral_uses_unknown_prefix_when_metadata_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensures fallback dynamic prefix is used if metadata is absent from AI response."""
    monkeypatch.chdir(tmp_path)

    (tmp_path / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Resume for {{ contact.name }}", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear {{ contact.name }}, {{ cover_letter_body }}", encoding="utf-8"
    )

    class FakeResponse:
        """Mock for Gemini API response."""

        def __init__(self, text: str) -> None:
            self.text: str = text

    class FakeModels:
        """Mock for Gemini models module."""

        def generate_content(self, model: str, contents: str, config: Any) -> FakeResponse:
            return FakeResponse(
                json.dumps(
                    {
                        "selected_skills": [],
                        "tailored_companies": [],
                        "cover_letter_body": "Hello",
                    }
                )
            )

    class FakeClient:
        """Mock for Gemini API Client."""

        def __init__(self, http_options: Any = None) -> None:
            self.models: FakeModels = FakeModels()

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def mock_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake docx", encoding="utf-8")

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    generate.generate_collateral("Target job requisition")

    assert (tmp_path / "Company_Role_Resume_A.docx").exists()
    assert (tmp_path / "Company_Role_CoverLetter_A.docx").exists()


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

    # Mock minimal master data with profile preferences
    (tmp_path / "master_data.json").write_text(
        json.dumps({"contact": {"Name": "Alex Tester", "Pref_Min_Salary": "150k"}}),
        encoding="utf-8",
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Resume Layout", encoding="utf-8")
    (tmp_path / "cover_letter_template.md").write_text("Cover Letter Layout", encoding="utf-8")

    class FakeResponse:
        """Mock for Gemini API response."""

        def __init__(self, text: str) -> None:
            self.text: str = text

    class FakeModels:
        """Mock for Gemini models module."""

        def generate_content(self, model: str, contents: str, config: Any) -> FakeResponse:
            # Dynamic response depending on which system prompt is being hit
            if (
                hasattr(config, "system_instruction")
                and "Desirability" in config.system_instruction
            ):
                return FakeResponse(
                    json.dumps(
                        {
                            "desirability_score": 95,
                            "salary_match": "Match",
                            "remote_match": "Match",
                            "benefits_analysis": "Great",
                            "pros": ["Remote"],
                            "cons": [],
                        }
                    )
                )
            return FakeResponse(
                json.dumps(
                    {
                        "job_metadata": {
                            "company_name": "Stark Industries",
                            "role_title": "Security Lead",
                        },
                        "cover_letter_body": "Hello",
                    }
                )
            )

    class FakeClient:
        """Mock for Gemini API Client."""

        def __init__(self, http_options: Any = None) -> None:
            self.models: FakeModels = FakeModels()

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def mock_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake", encoding="utf-8")

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    # Mock the prompt loading
    (tmp_path / "desirability_prompt.txt").write_text("Desirability core rule", encoding="utf-8")

    generate.generate_collateral("We are looking for a remote security expert.", evaluate_job=True)

    # Initials should be AT for "Alex Tester"
    expected_report: Path = tmp_path / "Stark_Industries_Security_Lead_desirability_AT.txt"
    assert expected_report.exists()
    assert "Score: 95/100" in expected_report.read_text(encoding="utf-8")


def test_generate_collateral_master_mode_skips_cover_letter_and_validations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies that master mode overrides validations and avoids cover letter rendering."""
    monkeypatch.chdir(tmp_path)

    (tmp_path / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}}), encoding="utf-8"
    )
    (tmp_path / "master_prompt.txt").write_text("master prompt rules", encoding="utf-8")
    (tmp_path / "resume_template.md").write_text("Master Resume", encoding="utf-8")

    class FakeResponse:
        """Mock for Gemini API response."""

        def __init__(self, text: str) -> None:
            self.text: str = text

    class FakeModels:
        """Mock for Gemini models module."""

        def generate_content(self, model: str, contents: str, config: Any) -> FakeResponse:
            return FakeResponse(
                json.dumps(
                    {
                        "job_metadata": {
                            "company_name": "Master",
                            "role_title": "Resume",
                        },
                        "selected_skills": ["Everything"],
                        "tailored_companies": [],
                        "cover_letter_body": "",
                    }
                )
            )

    class FakeClient:
        """Mock for Gemini API Client."""

        def __init__(self, http_options: Any = None) -> None:
            self.models: FakeModels = FakeModels()

    def mock_get_pandoc_version() -> str:
        return "2.0"

    def fake_convert_file(input_file: str, fmt: str, outputfile: str, **kwargs: Any) -> None:
        Path(outputfile).write_text("fake docx content", encoding="utf-8")

    def fail_if_called(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Validation/Desirability logic should not be invoked in master mode.")

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", mock_get_pandoc_version)
    monkeypatch.setattr(generate.pypandoc, "convert_file", fake_convert_file)
    monkeypatch.setattr(generate, "validate_resume", fail_if_called)
    monkeypatch.setattr(generate, "evaluate_desirability", fail_if_called)

    # Intentionally trigger the flags, which should be ignored by the master_mode override
    generate.generate_collateral("Bypass text", validate=True, evaluate_job=True, master_mode=True)

    resume_output: Path = tmp_path / "Master_Resume_Resume_A.docx"
    cover_output: Path = tmp_path / "Master_Resume_CoverLetter_A.docx"

    assert resume_output.exists()
    assert not cover_output.exists()
    assert not (tmp_path / "temp_cl.md").exists()
