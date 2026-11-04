"""Tests for the deterministic unsupported-term report (plan task A3). Synthetic persona only."""

from typing import Any

import pytest

from resume_optimizer.checks import check_unsupported

MASTER: dict[str, Any] = {
    "contact": {"Name": "Example Person", "Email": "person@example.com"},
    "all_skills": ["AWS", "Python", "Terraform", "CI/CD"],
    "companies": [
        {
            "company": "Acme Corp",
            "roles": [
                {
                    "title": "Senior Cloud Architect",
                    "dates": "2020 - Present",
                    "master_bullets": [
                        "Architected cloud infrastructure using Terraform, reducing deployment "
                        "time by 40%",
                    ],
                }
            ],
        }
    ],
}
REQ = "We need a Cloud Architect with Kubernetes and Okta experience."


def test_injected_unsupported_term_is_flagged() -> None:
    """A vocabulary term and a capitalised token absent from the data and the req are reported."""
    report = check_unsupported(
        ["Built pipelines with Snowflake and Jenkins for Zorblax Industries."], MASTER, REQ
    )
    assert "jenkins" in report.terms
    assert "snowflake" in report.terms
    assert "Zorblax" in report.capitalised


def test_reworded_supported_bullet_with_capitalised_verb_is_clean() -> None:
    """A capitalised leading verb and supported content produce no findings."""
    report = check_unsupported(
        ["Designed cloud infrastructure with Terraform on AWS, cutting deployment time by 40%."],
        MASTER,
        REQ,
    )
    assert report.unsupported_count == 0


def test_req_terms_are_labelled_not_unsupported() -> None:
    """A term that comes from the req is labelled "from req"."""
    report = check_unsupported(["Operated Kubernetes clusters with Okta sign-on."], MASTER, REQ)
    assert "kubernetes" in report.from_req
    assert "Okta" in report.from_req
    assert report.terms == []
    assert report.capitalised == []


def test_unsupported_number_is_flagged_and_supported_ones_pass() -> None:
    """Numbers absent from the data are reported; "40%" and the role's year are not."""
    report = check_unsupported(["Cut costs by 65% since 2020, and deployment time by 40%."], MASTER)
    assert report.numbers == ["65%"]


def test_level_words() -> None:
    """Unsupported level words in title position are flagged; ordinary prose is not."""
    inflated = check_unsupported(["Promoted to Director of Engineering."], MASTER)
    assert "director" in inflated.levels
    ordinary = check_unsupported(["Led a team and briefed senior stakeholders."], MASTER)
    assert ordinary.levels == []
    supported = check_unsupported(["Worked as a senior cloud architect."], MASTER)
    assert supported.levels == []


def test_sentence_initial_months_and_verb_lexicon_are_exempt() -> None:
    """Initial words, months and lexicon verbs are not reported as capitalised tokens."""
    report = check_unsupported(["Zorblaxed things. Since March we Delivered results."], MASTER)
    assert report.capitalised == []


def test_ai_tell_phrases_are_counted() -> None:
    """The static phrase list is counted per phrase."""
    report = check_unsupported(
        ["Spearheaded a robust rollout.", "Leveraging a proven track record."], MASTER
    )
    assert report.ai_tells["spearheaded"] == 1
    assert report.ai_tells["robust"] == 1
    assert report.ai_tells["proven track record"] == 1
    assert report.ai_tell_total == 4


def test_short_vocabulary_terms_do_not_match_inside_words() -> None:
    """The single-letter term "r" never matches inside other words."""
    report = check_unsupported(["Architect and runner of reliable systems."], MASTER)
    assert report.terms == []


@pytest.mark.parametrize("segments", [[], [""], ["   "]])
def test_empty_input(segments: list[str]) -> None:
    """Empty segments yield an empty report."""
    assert check_unsupported(segments, MASTER).unsupported_count == 0
