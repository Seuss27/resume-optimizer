"""More A3 checks: label slots, units, ordinary words, letter frame. Synthetic persona only."""

from test_checks import MASTER, REQ

from resume_optimizer.checks import check_unsupported


def test_title_and_employer_slots_are_checked_without_initial_exemption() -> None:
    """Fabricated titles, employers and skills are caught in label slots, first word included."""
    report = check_unsupported(
        [],
        MASTER,
        REQ,
        labels=["Globex", "Zorblax", "Okta", "Terraform"],
        titles=["Director of Engineering"],
    )
    assert "director" in report.levels
    assert "Globex" in report.capitalised
    assert "Zorblax" in report.capitalised
    assert "Okta" in report.capitalised  # a req cannot be the source of a skill claim
    assert "Terraform" not in report.capitalised


def test_unit_suffixed_numbers_are_checked() -> None:
    """Numbers with units are reported unless the data has them."""
    report = check_unsupported(["Cut latency to 200ms and moved 50TB of data."], MASTER)
    assert report.numbers == ["200ms", "50tb"]
    data = {"x": ["Latency was 200 ms and spend was $1.2 million."]}
    assert check_unsupported(["Held latency at 200ms and spend at $1.2M."], data).numbers == []


def test_ordinary_words_are_not_read_as_tools() -> None:
    """The words react, rest, lean and the phrase R&D are not vocabulary hits."""
    report = check_unsupported(
        ["Helped the rest of the team react to feedback in R&D, keeping rollouts lean and safe."],
        MASTER,
    )
    assert report.terms == []
    proper = check_unsupported(["Built services with React and REST."], MASTER)
    assert proper.terms == ["react", "rest"]


def test_letter_greeting_and_sign_off_are_frame_not_claims() -> None:
    """The salutation and sign-off are not reported."""
    report = check_unsupported(["Dear Hiring Manager,\nI built things.\nSincerely,"], MASTER)
    assert report.levels == []
    assert report.capitalised == []


def test_vocabulary_term_is_reported_once() -> None:
    """A capitalised vocabulary term is not also reported as a capitalised token."""
    report = check_unsupported(["Built pipelines with Snowflake."], MASTER)
    assert report.terms == ["snowflake"]
    assert report.capitalised == []
    assert report.unsupported_count == 1


def test_abbreviations_do_not_end_a_sentence() -> None:
    """An abbreviation such as "e.g." does not make the next word sentence-initial."""
    report = check_unsupported(["Used tools, e.g. Zorblax and Okta."], MASTER)
    assert "Zorblax" in report.capitalised


def test_hyphenated_compound_checks_the_proper_noun_only() -> None:
    """A compound such as "AWS-based" is judged on AWS, which the data has."""
    assert check_unsupported(["Ran AWS-based Terraform-managed stacks."], MASTER).capitalised == []


def test_curly_apostrophe_ai_tell_is_counted() -> None:
    """Typographic apostrophes do not hide a phrase."""
    assert check_unsupported(["In today’s market."], MASTER).ai_tells == {"in today's": 1}


def test_unsupported_term_inside_a_compound_is_reported() -> None:
    """A tool hidden in a hyphenated or slashed compound is still a vocabulary hit."""
    report = check_unsupported(
        ["Built Kubernetes-native services and Docker-based builds."], MASTER
    )
    assert report.terms == ["docker", "kubernetes"]
    assert check_unsupported([], MASTER, labels=["Kubernetes-certified"]).terms == ["kubernetes"]
    assert check_unsupported(["Wrote python/django and AWS/GCP code."], MASTER).terms == [
        "django",
        "gcp",
    ]


def test_leading_level_of_phrase_is_flagged() -> None:
    """A sentence that opens with "Director of ..." is title inflation."""
    assert "director" in check_unsupported(["Director of Engineering at Acme."], MASTER).levels
    assert "head" in check_unsupported(["Head of Platform at Acme."], MASTER).levels


def test_salutation_only_exempts_a_bare_greeting_line() -> None:
    """A claim written on the same line as the greeting is still checked."""
    same_line = check_unsupported(["Dear Hiring Manager, I built Zorblax at Globex."], MASTER)
    assert "Zorblax" in same_line.capitalised
    assert "Globex" in same_line.capitalised
    hyphen = check_unsupported(["Hi-touch onboarding at Globex."], MASTER)
    assert "Globex" in hyphen.capitalised


def test_multi_word_terms_are_counted_once() -> None:
    """Words and numbers inside a vocabulary term are not reported again."""
    report = check_unsupported(["Used GitHub Actions and held ISO 27001."], MASTER)
    assert report.terms == ["github actions", "iso 27001"]
    assert report.capitalised == []
    assert report.numbers == []
    assert report.unsupported_count == 2


def test_contact_numbers_do_not_support_claims() -> None:
    """A number in the contact block does not make a claimed number supported."""
    data = {"contact": {"Phone": "555 0123"}, "x": ["Led a team"]}
    assert check_unsupported(["Cut costs by 555."], data).numbers == ["555"]
