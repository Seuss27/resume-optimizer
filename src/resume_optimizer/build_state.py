"""Data preprocessor compiling user experience and profile CSVs into unified JSON state."""

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from resume_optimizer import paths
from resume_optimizer.logging_setup import get_logger

logger = get_logger(__name__)


def load_profile(profile_csv_path: str | Path) -> dict[str, Any]:
    """Reads a two-column CSV (Key, Value) into a dictionary."""
    csv_path: Path = Path(profile_csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not find {csv_path.name}. Please ensure it exists.")

    df_profile: pd.DataFrame = pd.read_csv(csv_path)

    # Convert it into a standard Python dictionary mapping Keys to Values
    profile_dict: dict[str, Any] = dict(zip(df_profile["Key"], df_profile["Value"]))

    return profile_dict


def convert_sheets_to_master_data(
    experience_csv_path: str | Path,
    profile_csv_path: str | Path,
    certs_csv_path: str | Path = "certifications.csv",
    output_json_path: str | Path = "master_data.json",
    education_csv_path: str | Path = "education.csv",
) -> None:
    """Parses experience, profile, certs, and education CSVs into a centralized JSON master file.

    Raises:
        DataPathRefusedError: If any path resolves inside a checkout of this repository.
    """
    # Support a common 3-argument call pattern where the third positional
    # argument is intended to be the output path.
    if (
        isinstance(certs_csv_path, str)
        and certs_csv_path.lower().endswith(".json")
        and output_json_path == "master_data.json"
    ):
        output_json_path, certs_csv_path = certs_csv_path, "certifications.csv"

    # Use the resolved paths from here on, so the path that is checked is the path that is used.
    experience_csv_path = paths.refuse_in_repo(experience_csv_path)
    profile_csv_path = paths.refuse_in_repo(profile_csv_path)
    certs_csv_path = paths.refuse_in_repo(certs_csv_path)
    output_json_path = paths.refuse_in_repo(output_json_path)
    education_csv_path = paths.refuse_in_repo(education_csv_path)

    # 1. Load the abstracted profile details
    user_profile: dict[str, Any] = load_profile(profile_csv_path)

    # 2. Read the experience CSV
    experience_path: Path = Path(experience_csv_path)
    if not experience_path.exists():
        raise FileNotFoundError(f"Could not find {experience_path.name}. Please ensure it exists.")

    df_experience: pd.DataFrame = pd.read_csv(experience_path)

    # 3. Initialize the base JSON structure
    master_data: dict[str, Any] = {
        "contact": user_profile,
        "all_skills": [],
        "companies": [],
        "certifications": [],
        "education": [],
    }

    # 4. Extract all unique skills from the 'Keywords / Tech Stack' column
    if "Keywords / Tech Stack" in df_experience.columns:
        all_skills_nested: list[list[str]] = (
            df_experience["Keywords / Tech Stack"].dropna().str.split(",").tolist()
        )
        flat_skills: list[str] = list(
            set([skill.strip() for sublist in all_skills_nested for skill in sublist])
        )
        master_data["all_skills"] = sorted(flat_skills)

    # 5. Fill optional columns with defaults to make grouping robust.
    if "Role Start" not in df_experience.columns:
        df_experience["Role Start"] = ""
    if "Role End" not in df_experience.columns:
        df_experience["Role End"] = ""

    def format_dates(row):
        start = str(row.get("Role Start", "")).strip()
        end = str(row.get("Role End", "")).strip()

        if start.lower() == "nan":
            start = ""
        if end.lower() == "nan":
            end = ""

        if start and end:
            return f"{start} - {end}"
        elif start:
            return f"{start} - Present"
        elif end:
            return end
        return ""

    df_experience["Role Dates"] = df_experience.apply(format_dates, axis=1)

    companies_dict: dict[str, dict[str, Any]] = {}
    grouped = df_experience.groupby(["Company", "Role Title", "Role Dates"], sort=False)

    for (raw_company, raw_title, raw_dates), group in grouped:
        company: str = str(raw_company)
        role_entry = {
            "title": str(raw_title),
            "dates": str(raw_dates),
            "master_bullets": [],
        }

        # 6. Combine the components into complete bullet points
        for _, row in group.iterrows():
            action = row.get("Action Verb", "")
            responsibility = row.get("Core Achievement / Responsibility", "")
            metric = row.get("Measurable Metric / Impact", "")

            # Format the bullet point, handling missing metrics gracefully
            if pd.notna(metric) and str(metric).strip() != "":
                bullet = f"{action} {responsibility} Impact: {metric}"
            else:
                bullet = f"{action} {responsibility}"

            # Clean up any accidental double spaces
            bullet = " ".join(bullet.split())
            if bullet:
                role_entry["master_bullets"].append(bullet)

        if company not in companies_dict:
            companies_dict[company] = {"company": company, "roles": []}
        companies_dict[company]["roles"].append(role_entry)

    master_data["companies"] = list(companies_dict.values())

    # 7. Extract Certifications (Graceful Warning Fallback)
    certs_path: Path = Path(certs_csv_path)
    if certs_path.exists():
        df_certs: pd.DataFrame = pd.read_csv(certs_path)
        for _, row in df_certs.iterrows():
            name = str(row.get("Name", "")).strip()
            issuer = str(row.get("Issuer", "")).strip()
            year = str(row.get("Year", "")).strip()

            if name and name != "nan":
                cert_string = name
                if issuer and issuer != "nan":
                    cert_string += f" | {issuer}"
                if year and year != "nan":
                    cert_string += f" ({year})"
                master_data["certifications"].append(cert_string)
    elif certs_path.name == "certifications.csv":
        logger.warning(
            "Default certifications file not found; building state without certifications.",
            extra={"certs_csv_path": certs_path.name},
        )
    else:
        raise FileNotFoundError(f"Could not find {certs_path.name}. Please ensure it exists.")

    # 8. Extract Education (Graceful Warning Fallback)
    edu_path: Path = Path(education_csv_path)
    if edu_path.exists():
        df_education: pd.DataFrame = pd.read_csv(edu_path)
        for _, row in df_education.iterrows():
            degree = str(row.get("Degree", "")).strip()
            institution = str(row.get("Institution", "")).strip()
            year = str(row.get("Graduation Year", "")).strip()

            if degree and degree != "nan":
                edu_entry = {
                    "degree": degree,
                    "institution": institution if institution and institution != "nan" else "",
                    "year": year if year and year != "nan" else "",
                }
                master_data["education"].append(edu_entry)
    elif edu_path.name == "education.csv":
        logger.warning(
            "Default education file not found; building state without education.",
            extra={"education_csv_path": edu_path.name},
        )
    else:
        raise FileNotFoundError(f"Could not find {edu_path.name}. Please ensure it exists.")

    # 9. Save out the structured JSON
    out_path: Path = Path(output_json_path)
    with out_path.open("w") as f:
        json.dump(master_data, f, indent=4)

    logger.info(
        "Successfully built master data from spreadsheets.",
        extra={"output_json_path": out_path.name},
    )


def main() -> None:
    """Entry point for local execution: builds `master_data.json` in `RO_LEDGER_DIR`."""
    try:
        paths.validate_all()
        ledger: Path = paths.ledger_dir()
        convert_sheets_to_master_data(
            experience_csv_path=ledger / "experience.csv",
            profile_csv_path=ledger / "profile.csv",
            certs_csv_path=ledger / "certifications.csv",
            output_json_path=ledger / "master_data.json",
            education_csv_path=ledger / "education.csv",
        )
    except paths.DataPathRefusedError as exc:
        logger.error("A data path was refused.")
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(paths.EXIT_REFUSED)


if __name__ == "__main__":
    main()
