import json
import os

import pandas as pd


def load_profile(profile_csv_path):
    """Reads a two-column CSV (Key, Value) into a dictionary."""
    if not os.path.exists(profile_csv_path):
        raise FileNotFoundError(f"Could not find {profile_csv_path}. Please ensure it exists.")

    df_profile = pd.read_csv(profile_csv_path)

    # Convert it into a standard Python dictionary mapping Keys to Values
    profile_dict = pd.Series(df_profile["Value"].values, index=df_profile["Key"]).to_dict()

    return profile_dict


def convert_sheets_to_master_data(
    experience_csv_path,
    profile_csv_path,
    certs_csv_path="certifications.csv",
    output_json_path="master_data.json",
    education_csv_path="education.csv",
):
    # Support a common 3-argument call pattern where the third positional
    # argument is intended to be the output path.
    if (
        isinstance(certs_csv_path, str)
        and certs_csv_path.lower().endswith(".json")
        and output_json_path == "master_data.json"
    ):
        output_json_path, certs_csv_path = certs_csv_path, "certifications.csv"

    # 1. Load the abstracted profile details
    user_profile = load_profile(profile_csv_path)

    # 2. Read the experience CSV
    if not os.path.exists(experience_csv_path):
        raise FileNotFoundError(f"Could not find {experience_csv_path}. Please ensure it exists.")

    df_experience = pd.read_csv(experience_csv_path)

    # 3. Initialize the base JSON structure
    master_data = {
        "contact": user_profile,
        "all_skills": [],
        "roles": [],
        "certifications": [],
        "education": [],
    }

    # 4. Extract all unique skills from the 'Keywords / Tech Stack' column
    if "Keywords / Tech Stack" in df_experience.columns:
        all_skills_nested = df_experience["Keywords / Tech Stack"].dropna().str.split(",").tolist()
        flat_skills = list(
            set([skill.strip() for sublist in all_skills_nested for skill in sublist])
        )
        master_data["all_skills"] = sorted(flat_skills)

    # 5. Fill optional columns with defaults to make grouping robust.
    if "Years Active" not in df_experience.columns:
        df_experience["Years Active"] = ""

    grouped = df_experience.groupby(["Company", "Role Title", "Years Active"], sort=False)

    for (company, title, dates), group in grouped:
        role_entry = {
            "title": title,
            "company": company,
            "dates": dates,
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

        master_data["roles"].append(role_entry)

    # 7. Extract Certifications (Graceful Warning Fallback)
    if os.path.exists(certs_csv_path):
        df_certs = pd.read_csv(certs_csv_path)
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
    elif certs_csv_path == "certifications.csv":
        # Warn the user in the console, but allow the pipeline to proceed safely
        print(f"WARNING: '{certs_csv_path}' not found. Building state without certifications.")
    else:
        raise FileNotFoundError(f"Could not find {certs_csv_path}. Please ensure it exists.")

    # 8. Extract Education (Graceful Warning Fallback)
    if os.path.exists(education_csv_path):
        df_education = pd.read_csv(education_csv_path)
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
    elif education_csv_path == "education.csv":
        # Warn the user in the console, but allow the pipeline to proceed safely
        print(f"WARNING: '{education_csv_path}' not found. Building state without education.")
    else:
        raise FileNotFoundError(f"Could not find {education_csv_path}. Please ensure it exists.")

    # 9. Save out the structured JSON
    with open(output_json_path, "w") as f:
        json.dump(master_data, f, indent=4)

    print(f"Successfully built {output_json_path} from spreadsheets!")


def main():
    # Ensure you have downloaded your two tabs as 'experience.csv' and 'profile.csv'
    convert_sheets_to_master_data("experience.csv", "profile.csv")


if __name__ == "__main__":
    main()
