"""Core AI engine handling Gemini API integration, prompt orchestration, and Pandoc generation."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import pypandoc
from dotenv import load_dotenv
from google import genai
from google.genai import types
from jinja2 import Environment, FileSystemLoader, select_autoescape

from resume_optimizer.logging_setup import get_logger

logger = get_logger(__name__)

__version__: str = "0.1.0"

load_dotenv()

if not os.environ.get("GEMINI_API_KEY"):
    raise ValueError(
        "CRITICAL: GEMINI_API_KEY not found. Please create a .env file and add your key."
    )


def clean_filename(text: str | None) -> str:
    """Sanitizes strings to be safe for OS file names.

    Args:
        text: The raw string to sanitize.

    Returns:
        A clean, file-system-safe string.
    """
    if not text:
        return "Unknown"
    # Replace spaces with underscores and strip out non-alphanumeric characters
    clean: str = re.sub(r"[^a-zA-Z0-9_\-]", "", text.replace(" ", "_"))
    return clean


def load_prompt(prompt_filename: str) -> str:
    """Loads a prompt text file from disk.

    Args:
        prompt_filename: The local filename of the text file to read.

    Returns:
        The string contents of the requested file.
    """
    prompt_path: Path = Path(prompt_filename)
    if not prompt_path.exists():
        raise FileNotFoundError(f"{prompt_filename} is missing.")

    with prompt_path.open("r", encoding="utf-8") as f:
        return f.read()


def validate_resume(job_req_text: str, resume_text: str) -> dict[str, Any]:
    """Validates the generated resume against the target job requisition via Gemini."""
    ats_prompt: str = load_prompt("ats_prompt.txt")
    response_schema: dict[str, Any] = {
        "type": "OBJECT",
        "properties": {
            "ats_score": {"type": "INTEGER"},
            "missing_keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
            "formatting_compliance": {"type": "STRING"},
            "critical_feedback": {"type": "STRING"},
        },
    }

    http_options: types.HttpOptions = types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            initial_delay=2.0,
            attempts=5,
            http_status_codes=[429, 500, 502, 503, 504],
        )
    )
    client: genai.Client = genai.Client(http_options=http_options)
    user_prompt: str = f"Job Requisition:\n{job_req_text}\n\nGenerated Resume Text:\n{resume_text}"

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

    result: dict[str, Any] = json.loads(response.text)
    return result


def evaluate_desirability(job_req_text: str, preferences: dict[str, str]) -> dict[str, Any]:
    """Evaluates a job req against the user's personal job preferences using Gemini.

    Args:
        job_req_text: The source job description.
        preferences: A dictionary mapping preference keys to required values.

    Returns:
        A dictionary containing the desirability score, match analyses, pros, and cons.
    """
    desirability_prompt: str = load_prompt("desirability_prompt.txt")

    response_schema: dict[str, Any] = {
        "type": "OBJECT",
        "properties": {
            "desirability_score": {"type": "INTEGER"},
            "salary_match": {"type": "STRING"},
            "remote_match": {"type": "STRING"},
            "benefits_analysis": {"type": "STRING"},
            "pros": {"type": "ARRAY", "items": {"type": "STRING"}},
            "cons": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": ["desirability_score", "salary_match", "remote_match", "pros", "cons"],
    }

    http_options: types.HttpOptions = types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            initial_delay=2.0,
            attempts=5,
            http_status_codes=[429, 500, 502, 503, 504],
        )
    )
    client: genai.Client = genai.Client(http_options=http_options)

    user_prompt: str = (
        f"User Preferences:\n{json.dumps(preferences, indent=2)}\n\n"
        f"Job Requisition:\n{job_req_text}"
    )

    logger.info("Initiating job desirability evaluation Gemini API call.")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=desirability_prompt,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.2,
        ),
    )

    result: dict[str, Any] = json.loads(response.text)
    return result


def print_desirability_summary(results: dict[str, Any]) -> None:
    """Prints a human-readable snippet to stdout.

    Args:
        results: The parsed dictionary from evaluate_desirability.
    """
    print("\n=== Job Desirability Evaluation ===")
    print(f"Overall Desirability Score: {results.get('desirability_score', 0)}/100")
    print(f"Remote Status: {results.get('remote_match', 'N/A')}")
    print(f"Salary Status: {results.get('salary_match', 'N/A')}")


def print_ats_validation_summary(ats_results: dict[str, Any]) -> None:
    """Prints a human-readable ATS summary to stdout.

    Args:
        ats_results: The parsed dictionary from validate_resume.
    """
    print("\n=== ATS Validation Results ===")
    print(f"Score: {ats_results.get('ats_score', 0)}/100")

    missing_keywords: list[str] = ats_results.get("missing_keywords") or []
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


def generate_collateral(
    job_req_text: str,
    validate: bool = False,
    preserve_markdown: bool = False,
    evaluate_job: bool = False,
    grouped_layout: bool = False,
) -> None:
    """Generates tailored resume and cover letter content using Gemini and Pandoc.

    Args:
        job_req_text: The target job requisition text.
        validate: If True, performs a secondary ATS validation pass.
        preserve_markdown: If True, keeps the intermediate Markdown files.
        evaluate_job: If True, evaluates the job against personal preferences.
        grouped_layout: If True, uses the nested layout template.
    """
    # 1. Load Local State
    master_data_path: Path = Path("master_data.json")
    if not master_data_path.exists():
        raise FileNotFoundError("master_data.json is missing. Run the preprocessor script first.")

    with master_data_path.open("r", encoding="utf-8") as f:
        master_data: dict[str, Any] = json.load(f)

    # DYNAMIC INITIALS DERIVATION
    contact_info: dict[str, str] = master_data.get("contact", {})
    full_name: str = contact_info.get("Name") or contact_info.get("name") or "User"
    initials: str = "".join([part[0].upper() for part in full_name.split() if part])

    # Extract target configuration criteria for desirability evaluation
    preferences: dict[str, str] = {
        "Pref_Remote_Only": contact_info.get("Pref_Remote_Only", "N/A"),
        "Pref_Min_Salary": contact_info.get("Pref_Min_Salary", "N/A"),
        "Pref_Target_Benefits": contact_info.get("Pref_Target_Benefits", "N/A"),
    }

    sys_prompt_path: Path = Path("system_prompt.txt")
    if not sys_prompt_path.exists():
        raise FileNotFoundError("system_prompt.txt is missing.")

    with sys_prompt_path.open("r", encoding="utf-8") as f:
        system_prompt: str = f.read()

    # 2. Define the Schema (Now including job_metadata extraction)
    response_schema: dict[str, Any] = {
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
                "description": "Optional. Omit if no certs are relevant.",
            },
            "tailored_companies": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "company": {"type": "STRING"},
                        "dates": {
                            "type": "STRING",
                            "description": "Full date range worked at company.",
                        },
                        "roles": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "title": {"type": "STRING"},
                                    "dates": {"type": "STRING"},
                                    "bullets": {"type": "ARRAY", "items": {"type": "STRING"}},
                                },
                            },
                        },
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
                "description": "Optional. Educations relevant to requisition.",
            },
            "cover_letter_body": {"type": "STRING"},
        },
    }

    # 3. Call the API
    http_options: types.HttpOptions = types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            initial_delay=2.0,
            attempts=5,
            http_status_codes=[429, 500, 502, 503, 504],
        )
    )
    client: genai.Client = genai.Client(http_options=http_options)
    user_prompt: str = f"Job Req:\n{job_req_text}\n\nMaster Data:\n{json.dumps(master_data)}"

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
    gemini_output: dict[str, Any] = json.loads(response.text)

    meta: dict[str, str] = gemini_output.get("job_metadata", {})
    company: str = clean_filename(meta.get("company_name", "UnknownCompany"))
    role: str = clean_filename(meta.get("role_title", "UnknownRole"))

    prefix: str = f"{company}_{role}"
    logger.info("AI processing complete.", extra={"output_prefix": prefix})

    # 5. Inject Data into Jinja2 Templates
    env: Environment = Environment(
        loader=FileSystemLoader("."), autoescape=select_autoescape(["html", "xml"])
    )
    resume_template = env.get_template("resume_template.md")
    cover_letter_template = env.get_template("cover_letter_template.md")

    resume_markdown: str = resume_template.render(
        contact=master_data.get("contact", {}),
        professional_summary=gemini_output.get("professional_summary", ""),
        skills_list=gemini_output.get("selected_skills", []),
        experience=gemini_output.get("tailored_companies", []),
        certifications=gemini_output.get("selected_certifications", []),
        education=gemini_output.get("selected_education", []),
        grouped_layout=grouped_layout,
    )

    cl_markdown: str = cover_letter_template.render(
        contact=master_data.get("contact", {}),
        cover_letter_body=gemini_output.get("cover_letter_body", ""),
    )

    if evaluate_job:
        eval_results: dict[str, Any] = evaluate_desirability(job_req_text, preferences)
        print_desirability_summary(eval_results)

        desirability_file: Path = Path(f"{prefix}_desirability_{initials}.txt")
        with desirability_file.open("w", encoding="utf-8") as f:
            f.write("=== Job Desirability Report ===\n")
            f.write(f"Score: {eval_results.get('desirability_score', 0)}/100\n\n")
            f.write(f"Remote Alignment: {eval_results.get('remote_match', 'N/A')}\n")
            f.write(f"Salary Alignment: {eval_results.get('salary_match', 'N/A')}\n")
            f.write(f"Benefits Analysis: {eval_results.get('benefits_analysis', 'N/A')}\n\n")

            f.write("Pros:\n")
            for pro in eval_results.get("pros", []):
                f.write(f"  + {pro}\n")

            f.write("\nCons:\n")
            for con in eval_results.get("cons", []):
                f.write(f"  - {con}\n")

            f.write("\nRaw Desirability JSON:\n")
            f.write(json.dumps(eval_results, indent=2))
            f.write("\n")

        logger.info(
            "Saved job desirability metrics to file.",
            extra={"desirability_file": str(desirability_file)},
        )

    if validate:
        ats_results: dict[str, Any] = validate_resume(job_req_text, resume_markdown)
        print_ats_validation_summary(ats_results)

        ats_file: Path = Path(f"{prefix}_ats_{initials}.txt")
        with ats_file.open("w", encoding="utf-8") as f:
            f.write("=== ATS Validation Results ===\n")
            f.write(f"Score: {ats_results.get('ats_score', 0)}/100\n")

            missing_keywords: list[str] = ats_results.get("missing_keywords") or []
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

        logger.info(
            "Saved ATS validation results to file.",
            extra={"ats_file": str(ats_file)},
        )

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

    temp_resume: Path = Path("temp_resume.md")
    temp_cl: Path = Path("temp_cl.md")

    with temp_resume.open("w", encoding="utf-8") as f:
        f.write(resume_markdown)
    with temp_cl.open("w", encoding="utf-8") as f:
        f.write(cl_markdown)

    # Convert to DOCX
    pypandoc.convert_file(
        str(temp_resume),
        "docx",
        outputfile=f"{prefix}_Resume_{initials}.docx",
        extra_args=["--reference-doc=resume_reference.docx"],
    )
    pypandoc.convert_file(
        str(temp_cl),
        "docx",
        outputfile=f"{prefix}_CoverLetter_{initials}.docx",
    )

    if not preserve_markdown:
        temp_resume.unlink()
        temp_cl.unlink()
    else:
        logger.info(
            "Preserving markdown files for template tuning.",
            extra={"resume_md": str(temp_resume), "cover_letter_md": str(temp_cl)},
        )

    logger.info("Successfully deployed generated files.")


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments for the generation script.

    Returns:
        The parsed argument namespace.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
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
    parser.add_argument(
        "--score-job",
        action="store_true",
        help="Run a review pass to score the job req against your personal preferences.",
    )
    parser.add_argument(
        "--grouped-layout",
        action="store_true",
        help=(
            "Use the nested company layout (Company -> Roles). "
            "Defaults to a flat chronological layout."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Entry point to handle STDIN reading and initiate the resume pipeline."""
    args: argparse.Namespace = parse_args()

    print("--- The JIT Resume Engine ---")
    print("Paste the target Job Requisition below.")
    print(
        "When finished, press Enter, then CTRL+D (Mac/Linux) "
        "or CTRL+Z then Enter (Windows) to submit:\n"
    )

    req_input: str = sys.stdin.read()

    if req_input.strip():
        generate_collateral(
            req_input,
            validate=args.validate,
            preserve_markdown=args.preserve_markdown,
            evaluate_job=args.score_job,
            grouped_layout=args.grouped_layout,
        )
    else:
        logger.info("No input detected; exiting without generating collateral.")
        print("No input detected. Exiting.")


if __name__ == "__main__":
    main()
