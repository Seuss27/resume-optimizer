import pandas as pd
import json
import os


def load_profile(profile_csv_path):
    """Reads a two-column CSV (Key, Value) into a dictionary."""
    if not os.path.exists(profile_csv_path):
        raise FileNotFoundError(
            f"Could not find {profile_csv_path}. Please ensure it exists."
        )

    df_profile = pd.read_csv(profile_csv_path)

    # Convert it into a standard Python dictionary mapping Keys to Values
    profile_dict = pd.Series(
        df_profile["Value"].values, index=df_profile["Key"]
    ).to_dict()

    return profile_dict


def convert_sheets_to_master_data(
    experience_csv_path, profile_csv_path, output_json_path="master_data.json"
):
    # 1. Load the abstracted profile details
    user_profile = load_profile(profile_csv_path)

    # 2. Read the experience CSV
    if not os.path.exists(experience_csv_path):
        raise FileNotFoundError(
            f"Could not find {experience_csv_path}. Please ensure it exists."
        )

    df_experience = pd.read_csv(experience_csv_path)

    # 3. Initialize the base JSON structure
    master_data = {"contact": user_profile, "all_skills": [], "roles": []}

    # 4. Extract all unique skills from the 'Keywords / Tech Stack' column
    if "Keywords / Tech Stack" in df_experience.columns:
        all_skills_nested = (
            df_experience["Keywords / Tech Stack"].dropna().str.split(",").tolist()
        )
        flat_skills = list(
            set([skill.strip() for sublist in all_skills_nested for skill in sublist])
        )
        master_data["all_skills"] = sorted(flat_skills)

    # 5. Group the dataframe by Company, Role, and Years
    grouped = df_experience.groupby(["Company", "Role Title", "Years Active"])

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
            role_entry["master_bullets"].append(bullet)

        master_data["roles"].append(role_entry)

    # 7. Save out the structured JSON
    with open(output_json_path, "w") as f:
        json.dump(master_data, f, indent=4)

    print(f"Successfully built {output_json_path} from spreadsheets!")


if __name__ == "__main__":
    # Ensure you have downloaded your two tabs as 'experience.csv' and 'profile.csv'
    convert_sheets_to_master_data("experience.csv", "profile.csv")
