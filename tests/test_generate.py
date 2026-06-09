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
                        "tailored_roles": [
                            {
                                "title": "Developer",
                                "company": "Acme Inc",
                                "dates": "2020-2024",
                                "bullets": ["Built features."],
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

    def fake_convert_file(input_file, fmt, outputfile):
        Path(outputfile).write_text("fake docx content")

    monkeypatch.setattr(generate.pypandoc, "convert_file", fake_convert_file)

    generate.generate_collateral("Target job requisition")

    resume_output = tmp_path / "Acme_Inc_Developer_Resume.docx"
    cover_output = tmp_path / "Acme_Inc_Developer_CoverLetter.docx"

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
                        "tailored_roles": [
                            {
                                "title": "Developer",
                                "company": "Acme Inc",
                                "dates": "2020-2024",
                                "bullets": ["Built features."],
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
        lambda input_file, fmt, outputfile: Path(outputfile).write_text("fake docx content"),
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
                        "tailored_roles": [],
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
        lambda input_file, fmt, outputfile: Path(outputfile).write_text("fake docx"),
    )

    generate.generate_collateral("Target job requisition")

    assert (tmp_path / "Acme_Inc_Developer_Resume.docx").exists()
    assert (tmp_path / "Acme_Inc_Developer_CoverLetter.docx").exists()


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
                        "tailored_roles": [],
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
        lambda input_file, fmt, outputfile: Path(outputfile).write_text("fake docx"),
    )

    generate.generate_collateral("Target job requisition")

    assert (tmp_path / "UnknownCompany_UnknownRole_Resume.docx").exists()
    assert (tmp_path / "UnknownCompany_UnknownRole_CoverLetter.docx").exists()
