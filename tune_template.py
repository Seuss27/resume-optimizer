import json
import os

import pypandoc
from jinja2 import Environment, FileSystemLoader


def tune_formatting():
    # 1. Load Dummy Contact Data (Mimicking build_state.py output)
    master_data = {
        "contact": {
            "Name": "Jane Doe",
            "Email": "jane.doe@example.com",
            "LinkedIn": "linkedin.com/in/janedoe",
            "Location": "Seattle, WA",
        }
    }

    # 2. Load Dummy LLM Output
    if not os.path.exists("dummy_gemini_output.json"):
        print("Error: dummy_gemini_output.json not found.")
        return

    with open("dummy_gemini_output.json", "r") as f:
        gemini_output = json.load(f)

    # 3. Render Templates
    env = Environment(loader=FileSystemLoader(".")) # noqa: S701
    resume_template = env.get_template("resume_template.md")

    resume_markdown = resume_template.render(
        contact=master_data.get("contact", {}),
        professional_summary=gemini_output.get("professional_summary", ""),
        skills_list=gemini_output.get("selected_skills", []),
        experience=gemini_output.get("tailored_roles", []),
        certifications=gemini_output.get("selected_certifications", []),
        education=gemini_output.get("selected_education", []),
    )

    with open("temp_tune_resume.md", "w", encoding="utf-8") as f:
        f.write(resume_markdown)

    # 4. Compile via Pandoc
    # Note: Ensure 'resume_reference.docx' exists, or omit extra_args for defaults
    if os.path.exists("resume_reference.docx"):
        extra_args = ["--reference-doc=resume_reference.docx"]
    else:
        extra_args = []

    output_file = "Tuning_Output_Resume.docx"

    pypandoc.convert_file(
        "temp_tune_resume.md",
        "docx",
        outputfile=output_file,
        extra_args=extra_args,
    )

    os.remove("temp_tune_resume.md")
    print(f"Successfully generated {output_file} for layout tuning.")


if __name__ == "__main__":
    tune_formatting()
