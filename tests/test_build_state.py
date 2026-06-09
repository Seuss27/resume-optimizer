import json
from pathlib import Path

import pytest

from src.resume_optimizer.build_state import convert_sheets_to_master_data, load_profile


def test_load_profile_reads_csv(tmp_path):
    profile_path = tmp_path / "profile.csv"
    profile_path.write_text("Key,Value\nname,Jane Doe\nemail,jane@example.com\n")

    result = load_profile(str(profile_path))

    assert result == {"name": "Jane Doe", "email": "jane@example.com"}


def test_load_profile_missing_file_raises():
    with pytest.raises(FileNotFoundError, match="Could not find"):
        load_profile("does_not_exist.csv")


def test_convert_sheets_to_master_data_writes_expected_json(tmp_path):
    profile_path = tmp_path / "profile.csv"
    experience_path = tmp_path / "experience.csv"
    output_path = tmp_path / "master_data.json"

    profile_path.write_text("Key,Value\nfirst_name,Sher\nlast_name,Bones\n")
    experience_path.write_text(
        "Company,Role Title,Years Active,Action Verb,Core Achievement / Responsibility,Measurable Metric / Impact,Keywords / Tech Stack\n"
        'Acme,Engineer,2020-2024,Designed,services,improved 20%,"Python, SQL"\n'
    )

    convert_sheets_to_master_data(
        str(experience_path), str(profile_path), str(output_path)
    )

    result = json.loads(output_path.read_text())

    assert result["contact"] == {"first_name": "Sher", "last_name": "Bones"}
    assert result["all_skills"] == ["Python", "SQL"]
    assert result["roles"][0]["company"] == "Acme"
    assert result["roles"][0]["title"] == "Engineer"
    assert result["roles"][0]["dates"] == "2020-2024"
    assert result["roles"][0]["master_bullets"] == [
        "Designed services Impact: improved 20%"
    ]


def test_convert_sheets_to_master_data_handles_missing_metric_and_skills(tmp_path):
    profile_path = tmp_path / "profile.csv"
    experience_path = tmp_path / "experience.csv"
    output_path = tmp_path / "master_data.json"

    profile_path.write_text("Key,Value\nname,Jordan\n")
    experience_path.write_text(
        "Company,Role Title,Years Active,Action Verb,Core Achievement / Responsibility,Measurable Metric / Impact\n"
        "Acme,Engineer,2020-2024,Implemented,feature,\n"
    )

    convert_sheets_to_master_data(
        str(experience_path), str(profile_path), str(output_path)
    )

    result = json.loads(output_path.read_text())

    assert result["all_skills"] == []
    assert result["roles"][0]["master_bullets"] == ["Implemented feature"]


def test_convert_sheets_to_master_data_missing_experience_file_raises(tmp_path):
    profile_path = tmp_path / "profile.csv"
    profile_path.write_text("Key,Value\nname,Jordan\n")

    with pytest.raises(FileNotFoundError, match="Could not find"):
        convert_sheets_to_master_data(
            "missing_experience.csv", str(profile_path), str(tmp_path / "out.json")
        )
