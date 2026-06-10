import argparse
import json
import os
import re

import pypandoc
from dotenv import load_dotenv
from google import genai
from google.genai import types
from jinja2 import Environment, FileSystemLoader, select_autoescape

from resume_optimizer.logging_setup import get_logger

logger = get_logger(__name__)

__version__ = "0.1.0"

load_dotenv()

if not os.environ.get("GEMINI_API_KEY"):
    raise ValueError(
        "CRITICAL: GEMINI_API_KEY not found. Please create a .env file and add your key."
    )


def clean_filename(text):
    """Sanitizes strings to be safe for OS file names."""
    if not text:
        return "Unknown"
    # Replace spaces with underscores and strip out non-alphanumeric characters
    clean = re.sub(r"[^a-zA-Z0-9_\-]", "", text.replace(" ", "_"))
    return clean


def load_prompt(prompt_filename):
    if not os.path.exists(prompt_filename):
        raise FileNotFoundError(f"{prompt_filename} is missing.")

    with open(prompt_filename, "r", encoding="utf-8") as f:
        return f.read()


def validate_resume(job_req_text, resume_text):
    ats_prompt = load_prompt("ats_prompt.txt")
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "ats_score": {"type": "INTEGER"},
            "missing_keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
            "formatting_compliance": {"type": "STRING"},
            "critical_feedback": {"type": "STRING"},
        },
    }

    http_options = types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            initial_delay=2.0,
            attempts=5,
            http_status_codes=[429, 500, 502, 503, 504],
        )
    )
    client = genai.Client(http_options=http_options)
    user_prompt = f"Job Requisition:\n{job_req_text}\n\nGenerated Resume Text:\n{resume_text}"

    logger.info("Initiating ATS validation Gemini API call.")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=ats_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.2,
        ),
    )

    return json.loads(response.text)


def print_ats_validation_summary(ats_results):
    print("\n=== ATS Validation Results ===")
    print(f"Score: {ats_results.get('ats_score', 0)}/100")

    missing_keywords = ats_results.get("missing_keywords") or []
    if missing_keywords:
        print("Missing keywords:")
        for keyword in missing_keywords:
            print(f"  - {keyword}")
    else:
        print("Missing keywords: None")

    print(f"Formatting compliance: {ats_results.get('formatting_compliance', 'N/A')}")
    print(f"Critical feedback: {ats_results.get('critical_feedback', 'N/A')}")
    print("\nRaw ATS JSON:")
    print(json.dumps(ats_results, indent=2))


def generate_collateral(job_req_text, validate=False, preserve_markdown=False):
    # 1. Load Local State
    if not os.path.exists("master_data.json"):
        raise FileNotFoundError("master_data.json is missing. Run the preprocessor script first.")

    with open("master_data.json", "r") as f:
        master_data = json.load(f)

    # DYNAMIC INITIALS DERIVATION
    contact_info = master_data.get("contact", {})
    full_name = contact_info.get("Name") or contact_info.get("name") or "User"
    initials = "".join([part[0].upper() for part in full_name.split() if part])

    if not os.path.exists("system_prompt.txt"):
        raise FileNotFoundError("system_prompt.txt is missing.")

    with open("system_prompt.txt", "r") as f:
        system_prompt = f.read()

    # 2. Define the Schema (Now including job_metadata extraction)
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "job_metadata": {
                "type": "OBJECT",
                "properties": {
                    "company_name": {"type": "STRING"},
                    "role_title": {"type": "STRING"},
                },
            },
            "professional_summary": {"type": "STRING"},
            "selected_skills": {"type": "ARRAY", "items": {"type": "STRING"}},
            "selected_certifications": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Optional. Leave empty if no certifications are relevant.",
            },
            "tailored_roles": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING"},
                        "company": {"type": "STRING"},
                        "dates": {"type": "STRING"},
                        "bullets": {"type": "ARRAY", "items": {"type": "STRING"}},
                    },
                },
            },
            "selected_education": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "degree": {"type": "STRING"},
                        "institution": {"type": "STRING"},
                        "year": {"type": "STRING"},
                    },
                },
                "description": "Optional. Include only educations relevant to the job requisition.",
            },
            "cover_letter_body": {"type": "STRING"},
        },
    }

    # 3. Call the API
    # Configure automatic retries for transient server errors (like 503s)
    http_options = types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            initial_delay=2.0,  # Wait 2 seconds before the first retry
            attempts=5,  # Try up to 5 times before giving up
            http_status_codes=[429, 500, 502, 503, 504],
        )
    )
    client = genai.Client(http_options=http_options)
    user_prompt = f"Job Req:\n{job_req_text}\n\nMaster Data:\n{json.dumps(master_data)}"

    logger.info("Initiating Gemini API call.")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.2,
        ),
    )

    # 4. Parse the Response & Generate Filename Prefix
    gemini_output = json.loads(response.text)

    # Safely extract company and role, defaulting to "Unknown" if the AI couldn't find them
    meta = gemini_output.get("job_metadata", {})
    company = clean_filename(meta.get("company_name", "UnknownCompany"))
    role = clean_filename(meta.get("role_title", "UnknownRole"))

    prefix = f"{company}_{role}"
    logger.info(
        "AI processing complete.",
        extra={"output_prefix": prefix},
    )

    # 5. Inject Data into Jinja2 Templates
    env = Environment(loader=FileSystemLoader("."), autoescape=select_autoescape(["html", "xml"]))
    resume_template = env.get_template("resume_template.md")
    cover_letter_template = env.get_template("cover_letter_template.md")

    resume_markdown = resume_template.render(
        contact=master_data.get("contact", {}),
        professional_summary=gemini_output.get("professional_summary", ""),
        skills_list=gemini_output.get("selected_skills", []),
        experience=gemini_output.get("tailored_roles", []),
        certifications=gemini_output.get("selected_certifications", []),
        education=gemini_output.get("selected_education", []),
    )

    cl_markdown = cover_letter_template.render(
        contact=master_data.get("contact", {}),
        cover_letter_body=gemini_output.get("cover_letter_body", ""),
    )

    if validate:
        ats_results = validate_resume(job_req_text, resume_markdown)
        print_ats_validation_summary(ats_results)

        # Build the filename matching your resume/cover letter naming convention
        ats_filename = f"{prefix}_ats_{initials}.txt"

        # Save the formatted validation results to the text file
        with open(ats_filename, "w", encoding="utf-8") as f:
            f.write("=== ATS Validation Results ===\n")
            f.write(f"Score: {ats_results.get('ats_score', 0)}/100\n")

            missing_keywords = ats_results.get("missing_keywords") or []
            if missing_keywords:
                f.write("Missing keywords:\n")
                for keyword in missing_keywords:
                    f.write(f"  - {keyword}\n")
            else:
                f.write("Missing keywords: None\n")

            f.write(f"Formatting compliance: {ats_results.get('formatting_compliance', 'N/A')}\n")
            f.write(f"Critical feedback: {ats_results.get('critical_feedback', 'N/A')}\n\n")
            f.write("Raw ATS JSON:\n")
            f.write(json.dumps(ats_results, indent=2))
            f.write("\n")

        logger.info("Saved ATS validation results to file.", extra={"ats_file": ats_filename})

    # 6. Compile Final Outputs
    logger.info(
        "Compiling final documents.",
        extra={
            "resume_file": f"{prefix}_Resume_{initials}.docx",
            "cover_letter_file": f"{prefix}_CoverLetter_{initials}.docx",
        },
    )

    # Ensure Pandoc is installed locally; if not, download it automatically
    try:
        pypandoc.get_pandoc_version()
    except OSError:
        logger.info("Pandoc engine not found; downloading it now.")
        pypandoc.download_pandoc()

    # Temporary markdown files
    with open("temp_resume.md", "w", encoding="utf-8") as f:
        f.write(resume_markdown)
    with open("temp_cl.md", "w", encoding="utf-8") as f:
        f.write(cl_markdown)

    # Convert to DOCX
    pypandoc.convert_file(
        "temp_resume.md",
        "docx",
        outputfile=f"{prefix}_Resume_{initials}.docx",
        extra_args=["--reference-doc=resume_reference.docx"],
    )
    pypandoc.convert_file("temp_cl.md", "docx", outputfile=f"{prefix}_CoverLetter_{initials}.docx")

    # Clean up the temporary markdown files so your folder stays clean
    if not preserve_markdown:
        os.remove("temp_resume.md")
        os.remove("temp_cl.md")
    else:
        logger.info(
            "Preserving markdown files for template tuning.",
            extra={"resume_md": "temp_resume.md", "cover_letter_md": "temp_cl.md"},
        )

    logger.info("Successfully deployed generated files.")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate a job-targeted resume and optionally validate it against ATS expectations."
        )
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help=(
            "Run a second Gemini review pass to score the generated resume "
            "against the job requisition."
        ),
    )
    parser.add_argument(
        "--preserve-markdown",
        action="store_true",
        help=(
            "Keep temp_resume.md and temp_cl.md files for template tuning and "
            "review instead of deleting them after DOCX conversion."
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("--- The JIT Resume Engine ---")
    print("Paste the target Job Requisition below.")
    print(
        "When finished, press Enter, then CTRL+D (Mac/Linux) "
        "or CTRL+Z then Enter (Windows) to submit:\n"
    )

    import sys

    req_input = sys.stdin.read()

    if req_input.strip():
        generate_collateral(
            req_input,
            validate=args.validate,
            preserve_markdown=args.preserve_markdown,
        )
    else:
        logger.info("No input detected; exiting without generating collateral.")
        print("No input detected. Exiting.")


if __name__ == "__main__":
    main()
