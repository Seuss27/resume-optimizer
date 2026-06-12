"""Utility script for tuning Microsoft Word layout templates with dummy data."""

import json
from pathlib import Path
from typing import Any

import pypandoc
from jinja2 import Environment, FileSystemLoader, select_autoescape


def tune_formatting() -> None:
    """Renders a dummy markdown resume and compiles it to docx for layout testing."""
    # 1. Load Dummy Contact Data (Mimicking build_state.py output)
    master_data: dict[str, dict[str, str]] = {
        "contact": {
            "Name": "Jane Doe",
            "Email": "jane.doe@example.com",
            "LinkedIn": "linkedin.com/in/janedoe",
            "Location": "Seattle, WA",
        }
    }

    # 2. Load Dummy LLM Output
    dummy_file: Path = Path("dummy_gemini_output.json")
    if not dummy_file.exists():
        print("Error: dummy_gemini_output.json not found.")
        return

    with dummy_file.open("r", encoding="utf-8") as f:
        gemini_output: dict[str, Any] = json.load(f)

    # 3. Render Templates
    env: Environment = Environment(
        loader=FileSystemLoader("."), autoescape=select_autoescape(["html", "xml"])
    )
    resume_template = env.get_template("resume_template.md")

    resume_markdown: str = resume_template.render(
        contact=master_data.get("contact", {}),
        professional_summary=gemini_output.get("professional_summary", ""),
        skills_list=gemini_output.get("selected_skills", []),
        experience=gemini_output.get("tailored_companies", []),
        certifications=gemini_output.get("selected_certifications", []),
        education=gemini_output.get("selected_education", []),
    )

    temp_markdown: Path = Path("temp_tune_resume.md")
    with temp_markdown.open("w", encoding="utf-8") as f:
        f.write(resume_markdown)

    # 4. Compile via Pandoc
    # Note: Ensure 'resume_reference.docx' exists, or omit extra_args for defaults
    reference_doc: Path = Path("resume_reference.docx")
    if reference_doc.exists():
        extra_args = ["--reference-doc=resume_reference.docx"]
    else:
        extra_args = []

    output_file: str = "Tuning_Output_Resume.docx"

    pypandoc.convert_file(
        str(temp_markdown),
        "docx",
        outputfile=output_file,
        extra_args=extra_args,
    )

    temp_markdown.unlink()
    print(f"Successfully generated {output_file} for layout tuning.")


if __name__ == "__main__":
    tune_formatting()
