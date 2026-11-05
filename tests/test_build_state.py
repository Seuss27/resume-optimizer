"""Unit test suite for the CSV-to-JSON state compilation logic."""

import json
from pathlib import Path
from typing import Any

import pytest

from resume_optimizer.build_state import convert_sheets_to_master_data, load_profile, main


def test_load_profile_reads_csv(tmp_path: Path) -> None:
    """Verifies that load_profile correctly parses a two-column CSV into a dictionary."""
    profile_path: Path = tmp_path / "profile.csv"
    profile_path.write_text("Key,Value\nname,Jane Doe\nemail,jane@example.com\n", encoding="utf-8")

    result: dict[str, Any] = load_profile(str(profile_path))

    assert result == {"name": "Jane Doe", "email": "jane@example.com"}


def test_load_profile_missing_file_raises() -> None:
    """Ensures load_profile raises a FileNotFoundError when the target CSV is missing."""
    with pytest.raises(FileNotFoundError, match="Could not find"):
        load_profile("does_not_exist.csv")


def test_convert_sheets_to_master_data_writes_expected_json(tmp_path: Path) -> None:
    """Verifies the core preprocessor merges experience, profile, and certs into valid JSON."""
    profile_path: Path = tmp_path / "profile.csv"
    experience_path: Path = tmp_path / "experience.csv"
    certs_path: Path = tmp_path / "certifications.csv"
    output_path: Path = tmp_path / "master_data.json"

    profile_path.write_text("Key,Value\nfirst_name,Sher\nlast_name,Bones\n", encoding="utf-8")
    experience_path.write_text(
        "Company,Role Title,Years Active,Action Verb,"
        "Core Achievement / Responsibility,Measurable Metric / Impact,"
        "Keywords / Tech Stack\n"
        'Acme,Engineer,2020-2024,Designed,services,improved 20%,"Python, SQL"\n',
        encoding="utf-8",
    )
    # Mock the required certs data
    certs_path.write_text(
        "Name,Issuer,Year\nAWS Certified Solutions Architect,AWS,2023\n",
        encoding="utf-8",
    )

    convert_sheets_to_master_data(
        str(experience_path), str(profile_path), str(certs_path), str(output_path)
    )

    result: dict[str, Any] = json.loads(output_path.read_text(encoding="utf-8"))

    assert result["contact"] == {"first_name": "Sher", "last_name": "Bones"}
    assert result["all_skills"] == ["Python", "SQL"]
    assert "AWS Certified Solutions Architect | AWS (2023)" in result["certifications"]


def test_convert_sheets_to_master_data_handles_missing_metric_and_skills(
    tmp_path: Path,
) -> None:
    """Ensures data without optional metrics or skills still processes gracefully."""
    profile_path: Path = tmp_path / "profile.csv"
    experience_path: Path = tmp_path / "experience.csv"
    output_path: Path = tmp_path / "master_data.json"

    profile_path.write_text("Key,Value\nname,Jordan\n", encoding="utf-8")
    experience_path.write_text(
        "Company,Role Title,Years Active,Action Verb,"
        "Core Achievement / Responsibility,Measurable Metric / Impact\n"
        "Acme,Engineer,2020-2024,Implemented,feature,\n",
        encoding="utf-8",
    )

    convert_sheets_to_master_data(str(experience_path), str(profile_path), str(output_path))

    result: dict[str, Any] = json.loads(output_path.read_text(encoding="utf-8"))

    assert result["all_skills"] == []
    assert result["companies"][0]["roles"][0]["master_bullets"] == ["Implemented feature"]


def test_convert_sheets_to_master_data_missing_experience_file_raises(
    tmp_path: Path,
) -> None:
    """Verifies that an absent experience CSV correctly halts the preprocessor."""
    profile_path: Path = tmp_path / "profile.csv"
    profile_path.write_text("Key,Value\nname,Jordan\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Could not find"):
        convert_sheets_to_master_data(
            "missing_experience.csv", str(profile_path), str(tmp_path / "out.json")
        )


def test_convert_sheets_to_master_data_missing_certs_file_raises(tmp_path: Path) -> None:
    """Ensures missing custom certification files properly raise an error."""
    profile_path: Path = tmp_path / "profile.csv"
    experience_path: Path = tmp_path / "experience.csv"

    profile_path.write_text("Key,Value\nname,Jordan\n", encoding="utf-8")
    experience_path.write_text("Company,Role Title\nAcme,Engineer\n", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="Could not find"):
        convert_sheets_to_master_data(
            str(experience_path),
            str(profile_path),
            "missing_certs.csv",
            str(tmp_path / "out.json"),
        )


def _ledger(tmp_path: Path) -> Path:
    return tmp_path / "ledger"


def _write_inputs(ledger: Path) -> None:
    (ledger / "profile.csv").write_text("Key,Value\nname,Jordan\n", encoding="utf-8")
    (ledger / "experience.csv").write_text("Company,Role Title\nAcme,Engineer\n", encoding="utf-8")


def test_main_reads_and_writes_in_the_ledger_directory(tmp_path: Path) -> None:
    """`main` takes every CSV from `RO_LEDGER_DIR` and writes `master_data.json` there."""
    ledger: Path = _ledger(tmp_path)
    _write_inputs(ledger)
    (ledger / "certifications.csv").write_text(
        "Name,Issuer,Year\nCert One,Issuer,2020\n", encoding="utf-8"
    )

    main()

    data: dict[str, Any] = json.loads((ledger / "master_data.json").read_text(encoding="utf-8"))
    assert data["contact"] == {"name": "Jordan"}
    assert data["certifications"] == ["Cert One | Issuer (2020)"]
    assert not (tmp_path / "master_data.json").exists()


def test_main_builds_with_only_the_profile_and_experience_files(tmp_path: Path) -> None:
    ledger: Path = _ledger(tmp_path)
    _write_inputs(ledger)

    main()

    data: dict[str, Any] = json.loads((ledger / "master_data.json").read_text(encoding="utf-8"))
    assert data["certifications"] == [] and data["education"] == []


def test_main_exits_with_status_3_on_an_in_repo_ledger_directory(
    monkeypatch: pytest.MonkeyPatch, fake_checkout: Path
) -> None:
    monkeypatch.setenv("RO_LEDGER_DIR", str(fake_checkout / "ledger"))
    with pytest.raises(SystemExit) as raised:
        main()
    assert raised.value.code == 3


def test_a_missing_input_error_names_the_file_only(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as raised:
        main()
    message: str = str(raised.value)
    forbidden: list[str] = [str(tmp_path), str(tmp_path.resolve()), tmp_path.as_posix()]
    assert "profile.csv" in message
    assert not any(path in message for path in forbidden)


def test_a_home_relative_output_path_is_written_where_it_was_checked(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    ledger: Path = _ledger(tmp_path)
    _write_inputs(ledger)

    convert_sheets_to_master_data(
        experience_csv_path=ledger / "experience.csv",
        profile_csv_path=ledger / "profile.csv",
        output_json_path="~/out.json",
    )

    assert (tmp_path / "out.json").exists()
    assert not Path("~").exists()
