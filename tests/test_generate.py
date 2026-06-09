import importlib
import json
import os
from pathlib import Path

import pytest

# Ensure the GEMINI_API_KEY check in generate.py passes during import.
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import generate


def test_clean_filename_normalizes_text():
    assert generate.clean_filename("My Role!") == "My_Role"
    assert generate.clean_filename("Acme Inc / Developer") == "Acme_Inc__Developer"
    assert generate.clean_filename("") == "Unknown"
    assert generate.clean_filename(None) == "Unknown"


def test_generate_collateral_requires_master_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "system_prompt.txt").write_text("system prompt")

    with pytest.raises(FileNotFoundError, match="master_data.json is missing"):
        generate.generate_collateral("Sample job requisition")


def test_generate_collateral_requires_system_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}})
    )

    with pytest.raises(FileNotFoundError, match="system_prompt.txt is missing"):
        generate.generate_collateral("Sample job requisition")


def test_generate_collateral_builds_docx_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    (tmp_path / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}})
    )
    (tmp_path / "system_prompt.txt").write_text("system prompt")
    (tmp_path / "resume_template.md").write_text(
        "Resume for {{ contact.name }}\nSkills:\n{% for skill in skills_list %}- {{ skill }}\n{% endfor %}"
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

    monkeypatch.setattr(
        generate, "genai", type("DummyGenai", (), {"Client": FakeClient})
    )
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


def test_generate_collateral_uses_unknown_prefix_when_metadata_is_missing(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    (tmp_path / "master_data.json").write_text(
        json.dumps({"contact": {"name": "Alex"}})
    )
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

    monkeypatch.setattr(
        generate, "genai", type("DummyGenai", (), {"Client": FakeClient})
    )
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "2.0")
    monkeypatch.setattr(
        generate.pypandoc,
        "convert_file",
        lambda input_file, fmt, outputfile: Path(outputfile).write_text("fake docx"),
    )

    generate.generate_collateral("Target job requisition")

    assert (tmp_path / "UnknownCompany_UnknownRole_Resume.docx").exists()
    assert (tmp_path / "UnknownCompany_UnknownRole_CoverLetter.docx").exists()
