"""A3 regressions found in review: determinism, blanked terms, ordinary prose, label slots."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_checks import MASTER

from resume_optimizer.checks import check_unsupported
from resume_optimizer.generate import print_page_counts
from resume_optimizer.render import DocumentRefusedError

pytestmark = pytest.mark.usefixtures("stand_in_resources")


def test_overlapping_terms_are_counted_once_and_in_a_stable_order() -> None:
    """ "PCI DSS" and "GitLab CI" are one hit each, whatever the set order."""
    text = "Achieved PCI DSS compliance and ran GitLab CI pipelines."
    report = check_unsupported([text], {"x": ["Worked on things"]})
    assert report.terms == ["gitlab ci", "pci dss"]
    assert report.capitalised == []
    assert report.unsupported_count == 2


def test_report_is_identical_under_different_hash_seeds() -> None:
    """The same input yields the same report in separate interpreters."""
    code = (
        "from resume_optimizer.checks import check_unsupported as c;"
        "r=c(['Achieved PCI DSS compliance and ran GitLab CI pipelines.'],{'x':['y']});"
        "print(r.terms, r.capitalised, r.unsupported_count)"
    )
    outputs = {
        subprocess.run(  # noqa: S603 - fixed argv, test only
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
            env={
                "PYTHONHASHSEED": str(seed),
                "PYTHONPATH": os.pathsep.join(sys.path),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            },
        ).stdout
        for seed in (0, 1, 2, 3)
    }
    assert len(outputs) == 1


def test_word_after_a_leading_tool_name_is_still_checked() -> None:
    """A blanked leading term does not make the next word look sentence-initial."""
    for text, token in [
        ("AWS Redshift migration.", "Redshift"),
        ("Kubernetes Zorblax operator.", "Zorblax"),
        ("Terraform Enterprise rollout.", "Enterprise"),
    ]:
        assert token in check_unsupported([text], MASTER).capitalised


def test_ordinary_of_phrases_are_not_title_inflation() -> None:
    """ "a staff of 12" and "took the lead of" are prose, not titles."""
    report = check_unsupported(["Managed a staff of 12 and took the lead of the rollout."], MASTER)
    assert report.levels == []


def test_names_in_label_slots_cannot_come_from_the_req() -> None:
    """An employer or skill copied from the req is still unsupported."""
    report = check_unsupported(
        [], MASTER, "Join TargetCo. Kafka experience required.", labels=["TargetCo", "Kafka"]
    )
    assert "TargetCo" in report.capitalised
    assert "kafka" not in report.from_req


def test_level_words_are_judged_against_role_titles() -> None:
    """ "senior leadership" in a bullet does not make the title "Principal" supported."""
    data = {
        "companies": [{"roles": [{"title": "Cloud Architect", "master_bullets": ["senior lead"]}]}]
    }
    assert "senior" in check_unsupported([], data, titles=["Senior Cloud Architect"]).levels


def test_spelling_variant_of_an_ambiguous_term_is_not_skipped() -> None:
    """ "SWIFT" is not "Swift", but it is still not in the data."""
    assert "SWIFT" in check_unsupported(["Integrated SWIFT messaging."], MASTER).capitalised


def test_non_breaking_space_inside_a_term() -> None:
    """A non-breaking space does not split "GitHub Actions"."""
    report = check_unsupported(["Used GitHub Actions."], MASTER)
    assert report.terms == ["github actions"]
    assert report.capitalised == []


def test_etc_does_not_end_a_sentence() -> None:
    """ "etc." followed by a name keeps the name mid-sentence."""
    assert "Zorblax" in check_unsupported(["Used tools, etc. Zorblax next."], MASTER).capitalised


def test_refused_document_is_set_aside_and_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refused document is renamed so it cannot be sent, and the warning says so."""
    from resume_optimizer import generate
    from resume_optimizer.render import DocumentRefusedError

    def refuse(path: Path) -> int:
        raise DocumentRefusedError("refused: document contains external target")

    monkeypatch.setattr(generate, "page_count", refuse)
    doc = tmp_path / "Co_Role_Resume_XX.docx"
    doc.write_bytes(b"x")
    assert print_page_counts({"Resume": doc}) == ["Resume"]
    assert not doc.exists()
    assert (tmp_path / "Co_Role_Resume_XX.REFUSED.docx").exists()
    assert "do not open or send the resume" in capsys.readouterr().out


def test_clean_document_is_left_alone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A document that is counted keeps its name."""
    from resume_optimizer import generate

    monkeypatch.setattr(generate, "page_count", lambda path: 1)
    doc = tmp_path / "a.docx"
    doc.write_bytes(b"x")
    assert print_page_counts({"Resume": doc}) == []
    assert doc.exists()


def test_main_exits_non_zero_when_a_document_is_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The command line fails, not just warns."""
    from resume_optimizer import generate

    def boom() -> None:
        raise generate.RefusedDocumentError("Refused and set aside: Resume.")

    monkeypatch.setattr(generate, "_main", boom)
    with pytest.raises(SystemExit) as info:
        generate.main()
    assert info.value.code == 1
    assert "Refused and set aside" in capsys.readouterr().err


def test_pandoc_warnings_are_counted_not_logged() -> None:
    """A pandoc warning that quotes text never reaches a root handler (the log file's route)."""
    import logging

    from resume_optimizer import generate

    class Collect(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.messages: list[str] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.messages.append(record.getMessage())

    root = logging.getLogger()
    collector = Collect()
    root.addHandler(collector)
    try:
        generate.PANDOC_WARNINGS.count = 0
        logging.getLogger("pypandoc").warning("Could not fetch resource secret-name.png")
    finally:
        root.removeHandler(collector)
    assert generate.PANDOC_WARNINGS.count == 1
    assert collector.messages == []


def test_skills_and_employers_are_not_read_as_claimed_levels() -> None:
    """Names copied from the data pass, whatever level words they contain."""
    data = {
        "all_skills": ["Executive Communication"],
        "companies": [{"company": "Principal Widgets Ltd"}],
    }
    report = check_unsupported(
        [], data, labels=["Executive Communication", "Principal Widgets Ltd", "Principal Component"]
    )
    assert report.levels == []


def test_such_as_and_as_well_as_are_not_title_position() -> None:
    """ "such as senior leadership" is prose."""
    data = {"companies": [{"roles": [{"title": "Cloud Engineer"}]}]}
    report = check_unsupported(
        [
            "Briefed stakeholders such as senior leadership, "
            "and engineers as well as executive sponsors."
        ],
        data,
    )
    assert report.levels == []
    assert "senior" in check_unsupported(["Worked as senior lead."], data).levels


def test_contact_free_text_does_not_support_a_tool_claim() -> None:
    """A preference note in the contact block is not evidence of a tool."""
    data = {"contact": {"Pref_Target_Benefits": "Kubernetes shop"}, "x": ["Ran things"]}
    assert check_unsupported(["Built Kubernetes clusters."], data).terms == ["kubernetes"]


def test_collect_output_segments_routes_slots() -> None:
    """Bullets are prose. Titles, employers, skills and degrees are name slots."""
    from resume_optimizer.generate import collect_output_segments

    output = {
        "professional_summary": "Summary.",
        "selected_skills": ["Python"],
        "tailored_companies": [
            {
                "company": "Acme",
                "dates": "2020",
                "roles": [{"title": "Engineer", "dates": "2020", "bullets": ["Built it."]}],
            }
        ],
        "selected_education": [{"degree": "BS", "institution": "Uni", "year": "2010"}],
        "cover_letter_body": "Body.",
    }
    prose, labels, titles = collect_output_segments(output)
    assert prose == ["Summary.", "Built it.", "Body."]
    assert titles == ["Engineer"]
    assert {"Python", "Acme", "BS", "Uni"} <= set(labels)


def test_collect_output_segments_checks_the_headline_as_prose() -> None:
    """The model-written headline goes through the unsupported-term check."""
    from resume_optimizer.generate import collect_output_segments

    prose, _, _ = collect_output_segments({"professional_summary": "S.", "headline": "Head line"})
    assert prose == ["S.", "Head line", ""]


def test_unscannable_document_is_set_aside_before_any_conversion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every document is scanned first, so a bad one is quarantined before a converter runs."""
    import zipfile

    from resume_optimizer import generate
    from resume_optimizer.render import scan_for_active_content

    monkeypatch.setattr(generate, "scan_for_active_content", scan_for_active_content)
    converted: list[Path] = []
    monkeypatch.setattr(generate, "page_count", lambda path: converted.append(path) or 1)
    good = tmp_path / "Co_Resume_XX.docx"
    with zipfile.ZipFile(good, "w") as package:
        package.writestr("word/document.xml", "<w:document/>")
    bad = tmp_path / "Co_CoverLetter_XX.docx"
    bad.write_bytes(b"not a zip")
    refused = print_page_counts({"Resume": good, "Cover letter": bad})
    assert refused == ["Cover letter"]
    assert (tmp_path / "Co_CoverLetter_XX.REFUSED.docx").exists()
    assert converted == [good]


def test_generate_collateral_raises_when_a_document_is_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The pipeline itself fails, not only the printout."""
    import json

    from resume_optimizer import generate
    from resume_optimizer.adapters import MockLLMAdapter

    def refuse(path: Path) -> int:
        raise DocumentRefusedError("refused: document contains field")

    monkeypatch.setattr(generate, "page_count", refuse)
    monkeypatch.setattr(generate.pypandoc, "get_pandoc_version", lambda: "3.0")
    monkeypatch.setattr(
        generate.pypandoc,
        "convert_file",
        lambda input_file, fmt, outputfile, **kw: Path(outputfile).write_bytes(b"x"),
    )
    adapter = MockLLMAdapter(
        mock_responses=[
            {
                "job_metadata": {"company_name": "Acme", "role_title": "Role"},
                "professional_summary": "Summary.",
                "selected_skills": [],
                "selected_certifications": [],
                "selected_education": [],
                "tailored_companies": [],
                "cover_letter_body": "Body.",
            }
        ]
    )
    monkeypatch.setattr(generate, "get_llm_engine", lambda *a, **k: adapter)
    Path("ledger/master_data.json").write_text(json.dumps({"contact": {"name": "Test Person"}}))
    Path("system_prompt.txt").write_text("p")
    Path("resume_template.md").write_text("R")
    Path("cover_letter_template.md").write_text("C")
    with pytest.raises(generate.RefusedDocumentError):
        generate.generate_collateral("req text")


def test_sentence_initial_title_run_is_flagged_but_ordinary_prose_is_not() -> None:
    """A sentence that opens with a title run claims a level; ordinary prose does not."""
    inflated = check_unsupported(["Principal Cloud Architect with 12 years of AWS."], MASTER)
    assert "principal" in inflated.levels
    assert "director" in check_unsupported(["Director-level Cloud Architect."], MASTER).levels
    ordinary = check_unsupported(["Senior leadership adopted the plan."], MASTER)
    assert ordinary.levels == []


def test_slash_compounds_do_not_show_placeholder_text() -> None:
    """A name next to a blanked tool is reported as itself, and a supported pair is clean."""
    data = {"all_skills": ["Okta", "AWS"]}
    assert check_unsupported(["Integrated Okta/AWS sign-on."], data).capitalised == []
    report = check_unsupported(["Integrated Zorblax/AWS sign-on."], data)
    assert report.capitalised == ["Zorblax"]


def test_certification_names_copied_from_the_data_are_not_level_findings() -> None:
    """A label that is in the data passes whatever level word it contains."""
    data = {"certs": ["Certified Information Security Manager", "The Principal Group"]}
    report = check_unsupported(
        [], data, labels=["Certified Information Security Manager", "The Principal Group"]
    )
    assert report.levels == []


def test_yaml_block_in_model_text_is_not_parsed_as_metadata() -> None:
    """The pandoc input format turns off YAML metadata and raw attributes."""
    from resume_optimizer.generate import PANDOC_INPUT_FORMAT

    assert PANDOC_INPUT_FORMAT.startswith("markdown")
    assert "-yaml_metadata_block" in PANDOC_INPUT_FORMAT
    assert "-raw_attribute" in PANDOC_INPUT_FORMAT
