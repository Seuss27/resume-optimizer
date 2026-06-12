import json
import os
import sys
from pathlib import Path

import pytest

# Ensure the GEMINI_API_KEY check in generate.py passes during import.
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import resume_optimizer.generate as generate


def test_clean_filename_normalizes_text():
    assert generate.clean_filename("My Role!") == "My_Role"
    assert generate.clean_filename("Acme Inc / Developer") == "Acme_Inc__Developer"
    assert generate.clean_filename("") == "Unknown"
    assert generate.clean_filename(None) == "Unknown"


def test_parse_args_defaults_to_no_validation(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["generate-resume"])
    args = generate.parse_args()

    assert args.validate is False


def test_parse_args_enables_validation_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["generate-resume", "--validate"])
    args = generate.parse_args()

    assert args.validate is True


def test_parse_args_enables_preserve_markdown_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["generate-resume", "--preserve-markdown"])
    args = generate.parse_args()

    assert args.preserve_markdown is True


def test_parse_args_defaults_preserve_markdown_to_false(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["generate-resume"])
    args = generate.parse_args()

    assert args.preserve_markdown is False


def test_parse_args_defaults_grouped_layout_to_false(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["generate-resume"])
    args = generate.parse_args()

    assert args.grouped_layout is False


def test_parse_args_enables_grouped_layout_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["generate-resume", "--grouped-layout"])
    args = generate.parse_args()

    assert args.grouped_layout is True


def test_generate_collateral_markdown_structure_is_valid(tmp_path, monkeypatch):
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

    captured_markdown = {}

    def mock_convert_file(input_file, fmt, outputfile, **kwargs):
        with open(input_file, "r", encoding="utf-8") as f:
            if "resume" in input_file.lower():
                captured_markdown["resume"] = f.read()
            else:
                captured_markdown["cover_letter"] = f.read()
        Path(outputfile).write_text("fake docx")

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents, config):
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
        def __init__(self, http_options=None):
            self.models = FakeModels()

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(generate.pypandoc, "convert_file", mock_convert_file)

    generate.generate_collateral("Target job requisition")

    resume_md = captured_markdown["resume"]
    cover_letter_md = captured_markdown["cover_letter"]

    assert "## Professional Skills" in resume_md
    assert "## Professional Experience" in resume_md
    assert "Python • SQL" in resume_md
    assert "### Acme Inc — Developer | 2020-2024" in resume_md
    assert "* Built features." in resume_md
    assert "* Led team." in resume_md
    assert "Dear Hiring," in cover_letter_md
    assert "I am interested in this role." in cover_letter_md


def test_generate_collateral_preserve_markdown_keeps_temp_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "master_data.json").write_text(json.dumps({"contact": {"name": "Alex"}}))
    (tmp_path / "system_prompt.txt").write_text("system prompt")
    (tmp_path / "resume_template.md").write_text("Resume")
    (tmp_path / "cover_letter_template.md").write_text("Cover letter")

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents, config):
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
        def __init__(self, http_options=None):
            self.models = FakeModels()

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(
        generate.pypandoc,
        "convert_file",
        lambda input_file, fmt, outputfile, **kwargs: Path(outputfile).write_text("fake"),
    )

    generate.generate_collateral("Job req", preserve_markdown=True)

    assert (tmp_path / "temp_resume.md").exists()
    assert (tmp_path / "temp_cl.md").exists()
    assert (tmp_path / "Acme_Dev_Resume_A.docx").exists()


def test_validate_resume_requests_ats_prompt_and_returns_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ats_prompt.txt").write_text("ATS parser prompt")

    captured = {}

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents, config):
            captured["model"] = model
            captured["contents"] = contents
            captured["config"] = config
            return FakeResponse(
                json.dumps(
                    {
                        "ats_score": 92,
                        "missing_keywords": ["AWS", "Docker"],
                        "formatting_compliance": "Excellent",
                        "critical_feedback": "Keep using strong action verbs.",
                    }
                )
            )

    class FakeClient:
        def __init__(self, http_options=None):
            self.models = FakeModels()

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))

    result = generate.validate_resume("Target requisition", "Target resume text")

    assert result["ats_score"] == 92
    assert result["missing_keywords"] == ["AWS", "Docker"]
    assert "Target requisition" in captured["contents"]
    assert "Target resume text" in captured["contents"]
    assert captured["config"].system_instruction == "ATS parser prompt"


def test_print_ats_validation_summary_outputs_expected_fields(capsys):
    ats_results = {
        "ats_score": 90,
        "missing_keywords": ["SQL"],
        "formatting_compliance": "Good",
        "critical_feedback": "Use metrics.",
    }

    generate.print_ats_validation_summary(ats_results)
    captured = capsys.readouterr()

    assert "=== ATS Validation Results ===" in captured.out
    assert "Score: 90/100" in captured.out
    assert "Missing keywords:" in captured.out
    assert "  - SQL" in captured.out
    assert "Formatting compliance: Good" in captured.out
    assert "Critical feedback: Use metrics." in captured.out
    assert '"ats_score": 90' in captured.out


def test_generate_collateral_requires_master_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "system_prompt.txt").write_text("system prompt")

    with pytest.raises(FileNotFoundError, match="master_data.json is missing"):
        generate.generate_collateral("Sample job requisition")


def test_generate_collateral_requires_system_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "master_data.json").write_text(json.dumps({"contact": {"name": "Alex"}}))

    with pytest.raises(FileNotFoundError, match="system_prompt.txt is missing"):
        generate.generate_collateral("Sample job requisition")


def test_generate_collateral_builds_docx_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    (tmp_path / "master_data.json").write_text(json.dumps({"contact": {"name": "Alex"}}))
    (tmp_path / "system_prompt.txt").write_text("system prompt")
    (tmp_path / "resume_template.md").write_text(
        "Resume for {{ contact.name }}\n"
        "Skills:\n"
        "{% for skill in skills_list %}- {{ skill }}\n{% endfor %}"
    )
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear {{ contact.name }},\n{{ cover_letter_body }}"
    )

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents, config):
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
        def __init__(self, http_options=None):
            self.models = FakeModels()

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")

    def fake_convert_file(input_file, fmt, outputfile, **kwargs):
        Path(outputfile).write_text("fake docx content")

    monkeypatch.setattr(generate.pypandoc, "convert_file", fake_convert_file)

    generate.generate_collateral("Target job requisition")

    resume_output = tmp_path / "Acme_Inc_Developer_Resume_A.docx"
    cover_output = tmp_path / "Acme_Inc_Developer_CoverLetter_A.docx"

    assert resume_output.exists()
    assert cover_output.exists()
    assert not (tmp_path / "temp_resume.md").exists()
    assert not (tmp_path / "temp_cl.md").exists()


def test_generate_collateral_performs_optional_ats_validation(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "master_data.json").write_text(json.dumps({"contact": {"name": "Alex"}}))
    (tmp_path / "system_prompt.txt").write_text("system prompt")
    (tmp_path / "ats_prompt.txt").write_text("ATS parser prompt")
    (tmp_path / "resume_template.md").write_text(
        "Resume for {{ contact.name }}\n"
        "Skills:\n"
        "{% for skill in skills_list %}- {{ skill }}\n{% endfor %}"
    )
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear {{ contact.name }},\n{{ cover_letter_body }}"
    )

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents, config):
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
        def __init__(self, http_options=None):
            self.models = FakeModels()

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(
        generate.pypandoc,
        "convert_file",
        lambda input_file, fmt, outputfile, **kwargs: Path(outputfile).write_text(
            "fake docx content"
        ),
    )

    generate.generate_collateral("Target job requisition", validate=True)

    captured = capsys.readouterr()
    assert "=== ATS Validation Results ===" in captured.out
    assert "Score: 86/100" in captured.out
    assert "Python" in captured.out
    assert "critical_feedback" in captured.out


def test_generate_collateral_skips_ats_validation_when_flag_not_set(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "master_data.json").write_text(json.dumps({"contact": {"name": "Alex"}}))
    (tmp_path / "system_prompt.txt").write_text("system prompt")
    (tmp_path / "resume_template.md").write_text("Resume for {{ contact.name }}")
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear {{ contact.name }}, {{ cover_letter_body }}"
    )

    def fail_if_called(job_req_text, resume_text):
        raise AssertionError("validate_resume should not be called when validate=False")

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents, config):
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
        def __init__(self, http_options=None):
            self.models = FakeModels()

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate, "validate_resume", fail_if_called)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(
        generate.pypandoc,
        "convert_file",
        lambda input_file, fmt, outputfile, **kwargs: Path(outputfile).write_text("fake docx"),
    )

    generate.generate_collateral("Target job requisition")

    assert (tmp_path / "Acme_Inc_Developer_Resume_A.docx").exists()
    assert (tmp_path / "Acme_Inc_Developer_CoverLetter_A.docx").exists()


def test_generate_collateral_uses_unknown_prefix_when_metadata_is_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    (tmp_path / "master_data.json").write_text(json.dumps({"contact": {"name": "Alex"}}))
    (tmp_path / "system_prompt.txt").write_text("system prompt")
    (tmp_path / "resume_template.md").write_text("Resume for {{ contact.name }}")
    (tmp_path / "cover_letter_template.md").write_text(
        "Dear {{ contact.name }}, {{ cover_letter_body }}"
    )

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents, config):
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
        def __init__(self, http_options=None):
            self.models = FakeModels()

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(
        generate.pypandoc,
        "convert_file",
        lambda input_file, fmt, outputfile, **kwargs: Path(outputfile).write_text("fake docx"),
    )

    generate.generate_collateral("Target job requisition")

    assert (tmp_path / "UnknownCompany_UnknownRole_Resume_A.docx").exists()
    assert (tmp_path / "UnknownCompany_UnknownRole_CoverLetter_A.docx").exists()


def test_evaluate_desirability_requests_prompt_and_returns_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "desirability_prompt.txt").write_text("Desirability prompt rules")

    captured = {}

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents, config):
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
        def __init__(self, http_options=None):
            self.models = FakeModels()

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))

    prefs = {"Pref_Min_Salary": "160000"}
    result = generate.evaluate_desirability("Looking for architect role paying 180k", prefs)

    assert result["desirability_score"] == 85
    assert result["salary_match"] == "Exceeds minimum"
    assert captured["config"].system_instruction == "Desirability prompt rules"


def test_generate_collateral_saves_desirability_report_when_flag_set(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Mock minimal master data with profile preferences
    (tmp_path / "master_data.json").write_text(
        json.dumps({"contact": {"Name": "Alex Tester", "Pref_Min_Salary": "150k"}})
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt")
    (tmp_path / "resume_template.md").write_text("Resume Layout")
    (tmp_path / "cover_letter_template.md").write_text("Cover Letter Layout")

    class FakeResponse:
        def __init__(self, text):
            self.text = text

    class FakeModels:
        def generate_content(self, model, contents, config):
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
        def __init__(self, http_options=None):
            self.models = FakeModels()

    monkeypatch.setattr(generate, "genai", type("DummyGenai", (), {"Client": FakeClient}))
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(
        generate.pypandoc,
        "convert_file",
        lambda input_file, fmt, outputfile, **kwargs: Path(outputfile).write_text("fake"),
    )

    # Mock the prompt loading
    (tmp_path / "desirability_prompt.txt").write_text("Desirability core rule")

    generate.generate_collateral("We are looking for a remote security expert.", evaluate_job=True)

    # Initials should be AT for "Alex Tester"
    expected_report = tmp_path / "Stark_Industries_Security_Lead_desirability_AT.txt"
    assert expected_report.exists()
    assert "Score: 95/100" in expected_report.read_text()
