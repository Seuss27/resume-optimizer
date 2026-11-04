"""Core AI engine handling Gemini API integration, prompt orchestration, and Pandoc generation."""

import argparse
import json
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pypandoc
from dotenv import load_dotenv
from google import genai
from google.genai import types
from jinja2 import Environment, FileSystemLoader, select_autoescape

from resume_optimizer.adapters import BedrockAdapter, GeminiAdapter, MockLLMAdapter
from resume_optimizer.checks import UnsupportedReport, check_unsupported
from resume_optimizer.interfaces import LLMEngineInterface
from resume_optimizer.logging_setup import get_logger
from resume_optimizer.render import (
    DocumentRefusedError,
    PdfConversionError,
    page_count,
    scan_for_active_content,
)

logger = get_logger(__name__)


class _CountingHandler(logging.Handler):
    """Counts records without keeping or writing their text."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.count: int = 0

    def emit(self, record: logging.LogRecord) -> None:
        """Counts one record."""
        self.count += 1


# pypandoc forwards pandoc's warnings, which quote document text and model-written URLs, to the
# root log handlers. Rule 4: logs carry IDs and scores, never resume text. So the pypandoc logger
# stops propagating, and only a count of what pandoc complained about is logged.
PANDOC_WARNINGS: _CountingHandler = _CountingHandler()
_pypandoc_logger: logging.Logger = logging.getLogger("pypandoc")
_pypandoc_logger.setLevel(logging.WARNING)
_pypandoc_logger.propagate = False
_pypandoc_logger.addHandler(PANDOC_WARNINGS)


class RefusedDocumentError(RuntimeError):
    """A generated document contained content the model should not have produced."""


__version__ = "0.1.0"

load_dotenv()

# Model text reaches pandoc as Markdown. Raw attributes would let it pass raw OOXML (field codes,
# external includes) straight into the .docx, and a YAML block in the text would write hidden
# document properties (and can ask for a TOC field), so both are switched off.
PANDOC_INPUT_FORMAT: str = "markdown-raw_attribute-yaml_metadata_block"

# --sandbox stops pandoc reading local files or fetching URLs for model-written Markdown such as
# an image link, which would otherwise embed the file (a `.env`, say) in the deliverable.
PANDOC_SAFETY_ARGS: list[str] = ["--sandbox"]


def get_llm_engine(mock_data: list[dict[str, Any]] | None = None) -> LLMEngineInterface:
    """Factory method to initialize the active LLM adapter via environment config."""
    provider: str = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "mock":
        # Provides safe, offline execution for Pytest and GitHub Actions
        return MockLLMAdapter(mock_responses=mock_data)

    elif provider == "bedrock":
        return BedrockAdapter(region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

    elif provider == "gemini":
        api_key: str | None = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("CRITICAL: GEMINI_API_KEY environment variable is required.")
        return GeminiAdapter(api_key=api_key)

    else:
        raise ValueError(f"CRITICAL: Unsupported LLM_PROVIDER specified: {provider}")


# if not os.environ.get("GEMINI_API_KEY"):
#     raise ValueError(
#         "CRITICAL: GEMINI_API_KEY not found. Please create a .env file and add your key."
#     )


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


def validate_resume(
    job_req_text: str, resume_text: str, llm_engine: LLMEngineInterface
) -> dict[str, Any]:
    """Validates the generated resume against the target job requisition."""
    raw_ats_prompt: str = load_prompt("ats_prompt.txt")
    today: str = date.today().strftime("%B %d, %Y")
    ats_prompt: str = f"SYSTEM DATE: Today is {today}.\n\n{raw_ats_prompt}"

    response_schema: dict[str, Any] = {
        "type": "OBJECT",
        "properties": {
            "ats_score": {"type": "INTEGER"},
            "missing_keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
            "formatting_compliance": {"type": "STRING"},
            "critical_feedback": {"type": "STRING"},
        },
    }

    user_prompt: str = f"Job Requisition:\n{job_req_text}\n\nGenerated Resume Text:\n{resume_text}"

    # Delegate network operations to the injected interface
    result: dict[str, Any] = llm_engine.generate_structured_content(
        prompt=user_prompt,
        response_schema=response_schema,
        system_instruction=ats_prompt,
    )

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

    result: dict[str, Any] = json.loads(response.text or "{}")
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


def collect_output_segments(output: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """Splits the generated fields into slots for the unsupported check.

    Returns:
        (prose, labels, titles). Prose is the summary, bullets and letter body. Labels are the
        other names: skills, certifications, employers, dates, degrees and institutions. Titles
        are the role titles.
    """
    prose: list[str] = [str(output.get("professional_summary") or "")]
    if output.get("headline"):
        prose.append(str(output["headline"]))
    labels: list[str] = []
    titles: list[str] = []
    for key in ("selected_skills", "selected_certifications"):
        labels.extend(str(item) for item in output.get(key) or [])
    for company in output.get("tailored_companies") or []:
        labels.extend([str(company.get("company") or ""), str(company.get("dates") or "")])
        for role in company.get("roles") or []:
            titles.append(str(role.get("title") or ""))
            labels.append(str(role.get("dates") or ""))
            prose.extend(str(bullet) for bullet in role.get("bullets") or [])
    for edu in output.get("selected_education") or []:
        labels.extend(str(edu.get(k) or "") for k in ("degree", "institution", "year"))
    prose.append(str(output.get("cover_letter_body") or ""))
    return prose, labels, titles


def print_unsupported_report(report: UnsupportedReport) -> None:
    """Prints the unsupported-term report and the AI-tell count to the console."""
    print("\n=== Unsupported-Term Report (not in your data) ===")
    sections: list[tuple[str, list[str]]] = [
        ("Vocabulary terms", report.terms),
        ("Numbers", report.numbers),
        ("Level words", report.levels),
        ("Capitalised tokens", report.capitalised),
    ]
    for label, items in sections:
        print(f"{label}: {', '.join(items) if items else 'none'}")
    print(f"From req (verify each is backed by your data): {', '.join(report.from_req) or 'none'}")
    tells: str = ", ".join(f"{p} x{n}" for p, n in report.ai_tells.items()) or "none"
    print(f"AI-tell phrases ({report.ai_tell_total}): {tells}")
    print("==================================================\n")


def _set_aside(label: str, path: Path) -> None:
    """Renames a refused document to `*.REFUSED.docx` and tells the user not to send it."""
    quarantined: Path = path.with_name(f"{path.stem}.REFUSED{path.suffix}")
    try:
        path.replace(quarantined)
        where: str = f"It was renamed to {quarantined.name}."
    except OSError:
        where = "It could not be renamed, so move it aside yourself."
    print(
        f"WARNING: do not open or send the {label.lower()}. It contains content "
        f"the model should not have produced, or it could not be checked. {where}"
    )


def print_page_counts(documents: dict[str, Path]) -> list[str]:
    """Checks every document, then prints each one's real page count, or why it cannot.

    All documents are scanned and any refused one is set aside before a converter opens
    anything, so an interrupted run never leaves an unchecked document under a sendable name.

    Returns:
        The labels of the documents that were refused.
    """
    refused: list[str] = []
    for label, path in documents.items():
        if not path.exists():
            continue
        try:
            active: list[str] = scan_for_active_content(path)
            if active:
                raise DocumentRefusedError(f"refused: document contains {', '.join(active)}")
        except DocumentRefusedError as exc:
            logger.error("Document refused.", extra={"document": label, "reason": str(exc)})
            print(f"{label}: page count unavailable ({exc}).")
            refused.append(label)
            _set_aside(label, path)
    for label, path in documents.items():
        if label in refused:
            continue
        try:
            pages: int = page_count(path)
        except DocumentRefusedError as exc:
            logger.error("Document refused.", extra={"document": label, "reason": str(exc)})
            print(f"{label}: page count unavailable ({exc}).")
            refused.append(label)
            _set_aside(label, path)
        except PdfConversionError as exc:
            logger.error("Page count unavailable.", extra={"document": label, "reason": str(exc)})
            print(f"{label}: page count unavailable ({exc}); no estimate is given.")
        else:
            logger.info("Counted pages.", extra={"document": label, "pages": pages})
            print(f"{label}: {pages} page(s)")
    return refused


# The career keys `build_state.py` writes that the generation call may send. Any other key,
# `contact` included, stays local, so an unknown key fails closed.
PROVIDER_CAREER_KEYS: tuple[str, ...] = ("all_skills", "companies", "certifications", "education")


# A role's dates are read only when the whole field has the shape of a date range such as
# "2018 - Present" or "Jan 2018 - Mar 2021", or is a single year. A stray year in a note, or a
# trailing remark after "Present", makes the field unreadable, and an unreadable field is skipped.
_MONTH: str = (
    r"(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
    r"|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+|\d{1,2}/)?"
)
_YEAR_DIGITS: str = r"((?:19|20)\d{2})"
_DATE_RANGE: re.Pattern[str] = re.compile(
    rf"^\s*{_MONTH}{_YEAR_DIGITS}\s*(?:[-\u2013\u2014]|to)\s*"
    rf"(?:{_MONTH}{_YEAR_DIGITS}|(present|current|now))\s*$",
    re.IGNORECASE,
)
_SINGLE_YEAR: re.Pattern[str] = re.compile(rf"^\s*{_MONTH}{_YEAR_DIGITS}\s*$", re.IGNORECASE)


def career_years(master_data: dict[str, Any], today: date | None = None) -> str | None:
    """Returns the career span as a floor such as "25+", or None if it cannot be read.

    The span runs from the earliest year in any readable role to the latest year found, or to
    today's year when a role ends at Present, Current or Now. A role's dates are readable only
    when the whole field is a date range or a single year (see `_DATE_RANGE`); anything else is
    skipped, which can only shorten the span. The dates are read to the year, so one year is
    taken off: the figure never overstates the span. From ten years up it is floored to a
    multiple of five. A span over 60 years is taken as a typo and returns None. The span is
    calendar time between the first and last role, so a gap between roles is counted.
    Code computes it so the model never does its own arithmetic on dates.
    """
    this_year: int = (today or date.today()).year
    years: list[int] = []
    is_current: bool = False
    for company in master_data.get("companies") or []:
        if not isinstance(company, dict):
            continue
        for role in company.get("roles") or []:
            dates: str = str(role.get("dates") or "") if isinstance(role, dict) else ""
            found: list[int] = []
            ends_now: bool = False
            if range_match := _DATE_RANGE.match(dates):
                start, stop, current = range_match.groups()
                found = [int(start)] + ([int(stop)] if stop else [])
                ends_now = current is not None
            elif single_match := _SINGLE_YEAR.match(dates):
                found = [int(single_match.group(1))]
            if any(year > this_year for year in found):
                continue  # a year in the future is a typo, so the whole field is unreadable
            years.extend(found)
            is_current = is_current or ends_now
    if not years:
        return None
    end: int = this_year if is_current else max(years)
    span: int = end - min(years) - 1
    if span < 1 or span > 60:
        return None
    return f"{span // 5 * 5 if span >= 10 else span}+"


def provider_payload(master_data: dict[str, Any]) -> dict[str, Any]:
    """Returns the career data the generation call sends: an allowlist of career keys.

    The contact block (name, email, phone, location, profile link) is never in it. Code renders
    the header and the letter frame from that block locally (`RO-D13`).
    """
    return {key: master_data[key] for key in PROVIDER_CAREER_KEYS if key in master_data}


# Stand-in contact block for the ATS pass: it keeps the header's shape and sends nothing real.
ATS_PLACEHOLDER_CONTACT: dict[str, str] = {
    "Name": "Candidate Name",
    "Location": "City, ST",
    "Email": "candidate@example.com",
    "Phone": "000-000-0000",
    "LinkedIn": "linkedin.com/in/candidate",
}


def name_stated_in(name: str | None, text: str) -> str:
    """Returns `name` (whitespace collapsed) only if `text` contains it as whole words.

    The match ignores case and runs of whitespace. A name the model supplied but the
    requisition text does not contain is dropped, so a name that is only a fragment of another
    word never counts.
    """
    collapsed: str = " ".join((name or "").split())
    if not collapsed:
        return ""
    pattern: str = rf"(?<!\w){re.escape(collapsed)}(?!\w)"
    return collapsed if re.search(pattern, " ".join(text.split()), re.IGNORECASE) else ""


def format_letter_date(today: date) -> str:
    """Formats a date for the cover-letter frame, for example "March 5, 2026"."""
    return f"{today:%B} {today.day}, {today.year}"


def generate_collateral(
    job_req_text: str,
    validate: bool = False,
    preserve_markdown: bool = False,
    evaluate_job: bool = False,
    grouped_layout: bool = True,
    master_mode: bool = False,
    data_path: str | Path = "master_data.json",
) -> None:
    """Generates tailored resume and cover letter content using Gemini and Pandoc.

    Args:
        job_req_text: The target job requisition text.
        validate: If True, performs a secondary ATS validation pass.
        preserve_markdown: If True, keeps the intermediate Markdown files.
        evaluate_job: If True, evaluates the job against personal preferences.
        grouped_layout: If True (the default), groups roles under each employer.
        master_mode: If True, generates a comprehensive resume and skips cover letter.
    """
    # 1. Initialize our decoupled engine
    llm_engine: LLMEngineInterface = get_llm_engine()

    # 2. Load Local State
    master_data_path: Path = Path(data_path)
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

    prompt_file: str = "master_prompt.txt" if master_mode else "system_prompt.txt"
    sys_prompt_path: Path = Path(prompt_file)
    if not sys_prompt_path.exists():
        raise FileNotFoundError(f"{prompt_file} is missing.")

    with sys_prompt_path.open("r", encoding="utf-8") as f:
        system_prompt: str = f.read()

    if master_mode:
        evaluate_job = False
        validate = False

    # 3. Define the Schema (Now including job_metadata extraction)
    response_schema: dict[str, Any] = {
        "type": "OBJECT",
        "properties": {
            "job_metadata": {
                "type": "OBJECT",
                "properties": {
                    "company_name": {"type": "STRING"},
                    "role_title": {"type": "STRING"},
                    "hiring_manager": {
                        "type": "STRING",
                        "description": "Optional. Only a name the requisition itself states.",
                    },
                },
            },
            "headline": {
                "type": "STRING",
                "description": "Optional. A headline of at most 12 words for the resume header.",
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

    # 4. Call the API. Code computes the career span; it goes in the header, never to the model.
    span: str | None = career_years(master_data)

    sent_data: str = json.dumps(provider_payload(master_data))
    user_prompt: str = f"Job Req:\n{job_req_text}\n\nMaster Data:\n{sent_data}"

    logger.info("Initiating Gemini API call.")

    # 5. Parse the Response & Generate Filename Prefix
    gemini_output: dict[str, Any] = llm_engine.generate_structured_content(
        prompt=user_prompt,
        response_schema=response_schema,
        system_instruction=system_prompt,
    )

    meta: dict[str, str] = gemini_output.get("job_metadata", {})
    company: str = clean_filename(meta.get("company_name", "Master" if master_mode else "Company"))
    role: str = clean_filename(meta.get("role_title", "Resume" if master_mode else "Role"))

    prefix: str = f"{company}_{role}"
    logger.info("AI processing complete.", extra={"output_prefix": prefix})

    # 5. Inject Data into Jinja2 Templates
    env: Environment = Environment(
        loader=FileSystemLoader("."), autoescape=select_autoescape(["html", "xml"])
    )
    resume_template = env.get_template("resume_template.md")

    def render_resume(contact: dict[str, str]) -> str:
        """Renders the resume Markdown for the given contact block."""
        return resume_template.render(
            contact=contact,
            headline=gemini_output.get("headline", ""),
            career_years=span or "",
            professional_summary=gemini_output.get("professional_summary", ""),
            skills_list=gemini_output.get("selected_skills", []),
            experience=gemini_output.get("tailored_companies", []),
            certifications=gemini_output.get("selected_certifications", []),
            education=gemini_output.get("selected_education", []),
            grouped_layout=grouped_layout,
        )

    resume_markdown: str = render_resume(master_data.get("contact", {}))

    cl_markdown: str = ""
    if not master_mode:
        cover_letter_template = env.get_template("cover_letter_template.md")
        cl_markdown = cover_letter_template.render(
            contact=master_data.get("contact", {}),
            letter_date=format_letter_date(date.today()),
            company=meta.get("company_name", ""),
            role=meta.get("role_title", ""),
            hiring_manager=name_stated_in(meta.get("hiring_manager"), job_req_text),
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
        # The ATS pass scores content and layout, so it gets the resume with a placeholder header.
        ats_results: dict[str, Any] = validate_resume(
            job_req_text, render_resume(ATS_PLACEHOLDER_CONTACT), llm_engine
        )

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
    expected_docs: dict[str, str] = {"resume_file": f"{prefix}_Resume_{initials}.docx"}
    if not master_mode:
        expected_docs["cover_letter_file"] = f"{prefix}_CoverLetter_{initials}.docx"
    logger.info("Compiling final documents.", extra=expected_docs)

    # Ensure Pandoc is installed locally; if not, download it automatically
    try:
        pypandoc.get_pandoc_version()
    except OSError:
        logger.info("Pandoc engine not found; downloading it now.")
        pypandoc.download_pandoc()

    temp_resume: Path = Path("temp_resume.md")

    with temp_resume.open("w", encoding="utf-8") as f:
        f.write(resume_markdown)

    temp_cl: Path | None = None
    if not master_mode:
        temp_cl = Path("temp_cl.md")
        with temp_cl.open("w", encoding="utf-8") as f:
            f.write(cl_markdown)

    PANDOC_WARNINGS.count = 0
    # Convert to DOCX
    pypandoc.convert_file(
        str(temp_resume),
        "docx",
        outputfile=f"{prefix}_Resume_{initials}.docx",
        format=PANDOC_INPUT_FORMAT,
        extra_args=["--reference-doc=resume_reference.docx", *PANDOC_SAFETY_ARGS],
    )

    if not master_mode and temp_cl:
        pypandoc.convert_file(
            str(temp_cl),
            "docx",
            outputfile=f"{prefix}_CoverLetter_{initials}.docx",
            format=PANDOC_INPUT_FORMAT,
            extra_args=["--reference-doc=resume_reference.docx", *PANDOC_SAFETY_ARGS],
        )

    if not preserve_markdown:
        temp_resume.unlink()
        if not master_mode and temp_cl:
            temp_cl.unlink()
    else:
        preserved: dict[str, str] = {"resume_md": str(temp_resume)}
        if not master_mode and temp_cl:
            preserved["cover_letter_md"] = str(temp_cl)
        logger.info("Preserving markdown files for template tuning.", extra=preserved)

    logger.info("Pandoc finished.", extra={"pandoc_warnings": PANDOC_WARNINGS.count})
    if PANDOC_WARNINGS.count:
        print(
            f"Pandoc reported {PANDOC_WARNINGS.count} warning(s), for example a blocked image "
            "or link. Check the output."
        )
    logger.info("Successfully deployed generated files.")

    # 7. Deterministic checks on the output (no LLM): unsupported terms and real page counts
    # Only the req itself counts as "from req". The model wrote job_metadata, so it is not a source.
    prose, labels, titles = collect_output_segments(gemini_output)
    report: UnsupportedReport = check_unsupported(
        prose, master_data, job_req_text, labels=labels, titles=titles
    )
    logger.info(
        "Unsupported-term check complete.",
        extra={
            "unsupported": report.unsupported_count,
            "from_req": len(report.from_req),
            "ai_tells": report.ai_tell_total,
        },
    )
    print_unsupported_report(report)
    documents: dict[str, Path] = {"Resume": Path(expected_docs["resume_file"])}
    if "cover_letter_file" in expected_docs:
        documents["Cover letter"] = Path(expected_docs["cover_letter_file"])
    refused: list[str] = print_page_counts(documents)
    if refused:
        raise RefusedDocumentError(
            f"Refused: {', '.join(refused)}. Do not send them; see the warnings above."
        )


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
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Group roles under each employer. Use --no-grouped-layout for the flat "
            "chronological layout."
        ),
    )
    parser.add_argument(
        "--master",
        action="store_true",
        help=(
            "Generates a full 'Master Resume' detailing all experience without filtering. "
            "Bypasses job requisition prompts and skips cover letter generation."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Entry point to handle STDIN reading and initiate the resume pipeline."""
    try:
        _main()
    except RefusedDocumentError as exc:
        logger.error("A generated document was refused.")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def _main() -> None:
    """Runs the pipeline for the parsed command line."""
    args: argparse.Namespace = parse_args()

    if args.master:
        logger.info("Executing Master Resume generation. Bypassing STDIN requisition.")
        generate_collateral(
            job_req_text="MASTER RESUME GENERATION",
            validate=args.validate,
            preserve_markdown=args.preserve_markdown,
            evaluate_job=args.score_job,
            grouped_layout=args.grouped_layout,
            master_mode=True,
        )
        return

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
