"""Deterministic unsupported-term report for generated text (plan §3.4, task A3).

No LLM is involved. The report lists what the output says that the candidate's data does not:
general-vocabulary terms, numbers, level words and capitalised tokens. Findings that also appear
in the job requisition are labelled "from req" instead of "unsupported". That label says where
the word came from, not that the claim is true: each one still has to be backed by the data.
It also counts the static AI-tell phrases.

Text comes in two kinds. *Prose* slots (summary, bullets, letter body) get the sentence-initial
exemption, so a capitalised leading verb passes. *Label* slots (titles, employers, skills,
certifications, degrees) are short names, so every word in them is checked.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from resume_optimizer.lexicons import (
    AI_TELL_PHRASES,
    CASE_SENSITIVE_TERMS,
    FUNCTION_NOUNS,
    GENERAL_VOCABULARY,
    LEVEL_WORDS,
    MONTHS,
    VERB_LEXICON,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_ABBREVIATION_END = re.compile(
    r"(?:\be\.g|\bi\.e|\bvs|\betc|\bU\.S|\bInc|\bLtd|\bCorp|\bDr|\bMr|\bMs)\.$"
)
_WORD_PARTS = re.compile(r"[A-Za-z0-9]+")
_CAPITALISED = re.compile(r"(?<!\w)[A-Z][A-Za-z0-9]*(?:[+#]+|(?:[./&][A-Za-z0-9]+)+)?")
_NUMBER = re.compile(
    r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(%|\s?(?:million|billion|thousand)\b|[A-Za-z]{1,4}(?![\w]))?(?!\w)"
)
_LEADING_MARKUP = re.compile(r"^[^A-Za-z0-9]+")
_FRAME_LINE = re.compile(
    r"^\s*(?:(?:dear|hello|hi)\s[^\n.,:;]{0,60}[,:]?|to whom it may concern[,:]?|"
    r"(?:sincerely|best regards|kind regards|regards|respectfully|thank you|thanks),?)\s*$",
    re.IGNORECASE,
)
_MAGNITUDE = {"million": "m", "billion": "b", "thousand": "k"}
_MAGNITUDE_WORDS = {"m": "million", "b": "billion", "k": "thousand"}


@dataclass
class UnsupportedReport:
    """What the output claims that the candidate data does not support."""

    terms: list[str] = field(default_factory=list)
    numbers: list[str] = field(default_factory=list)
    levels: list[str] = field(default_factory=list)
    capitalised: list[str] = field(default_factory=list)
    from_req: list[str] = field(default_factory=list)
    ai_tells: dict[str, int] = field(default_factory=dict)

    @property
    def unsupported_count(self) -> int:
        """Number of findings that are neither supported nor taken from the req."""
        return len(self.terms) + len(self.numbers) + len(self.levels) + len(self.capitalised)

    @property
    def ai_tell_total(self) -> int:
        """Total occurrences of the static AI-tell phrases."""
        return sum(self.ai_tells.values())


def _flatten(value: Any) -> Iterable[str]:
    """Yields every string value in a nested structure, ignoring dictionary keys."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _flatten(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _flatten(item)
    elif isinstance(value, int | float) and not isinstance(value, bool):
        yield str(value)


def _normalise(text: str) -> str:
    """Folds typographic apostrophes so phrase matching sees one form."""
    return text.replace("’", "'").replace("‘", "'")


def _term_pattern(term: str) -> re.Pattern[str]:
    """Whole-word pattern for a vocabulary term.

    Ambiguous terms ("rest", "react") match only their proper form. A hyphen or slash is a
    boundary, so "Kubernetes-native" and "python/django" still contain a term.
    """
    surface: str | None = CASE_SENSITIVE_TERMS.get(term)
    flags: int = 0 if surface else re.IGNORECASE
    body: str = re.escape(surface or term).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![\w+#.&]){body}(?![\w+#&])", flags)


def _contains_term(haystack: str, term: str) -> bool:
    """Whether the vocabulary term appears in the text."""
    return _term_pattern(term).search(haystack) is not None


def _match_terms(segment: str) -> tuple[list[str], str]:
    """Finds the vocabulary terms in a segment, longest first, and blanks each one out.

    Longest-first makes the result independent of set order and counts "pci dss" once, not as
    "pci dss" plus "pci". The blanks are lower-case letters, not spaces, so the word after a
    blanked term never looks sentence-initial, and no number or capitalised word survives
    inside a matched term ("ISO 27001", "GitHub Actions").

    Returns:
        (terms found, the segment with those terms blanked).
    """
    found: list[str] = []
    for term in sorted(GENERAL_VOCABULARY, key=lambda t: (-len(t), t)):
        pattern = _term_pattern(term)
        if pattern.search(segment):
            found.append(term)
            segment = pattern.sub(lambda m: "x" * len(m.group(0)), segment)
    return found, segment


def _role_titles(master_data: Any) -> set[str]:
    """Words from role titles in the data. Level words are judged against these only."""
    title_keys: frozenset[str] = frozenset(
        {"title", "role title", "role", "official_title", "display_title"}
    )
    words: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key).lower() in title_keys and isinstance(item, str):
                    words.update(_words(item))
                else:
                    walk(item)
        elif isinstance(value, list | tuple):
            for item in value:
                walk(item)

    walk(master_data)
    return words


def _words(text: str) -> set[str]:
    """Lower-case alphanumeric parts of a text."""
    return {m.group(0).lower() for m in _WORD_PARTS.finditer(text)}


def _numbers(text: str) -> list[tuple[str, str]]:
    """Finds (value, suffix) pairs, with separators removed and the suffix lower-cased."""
    found: list[tuple[str, str]] = []
    for m in _NUMBER.finditer(text):
        suffix: str = (m.group(2) or "").strip().lower()
        found.append((m.group(1).replace(",", ""), _MAGNITUDE.get(suffix, suffix)))
    return found


def _number_supported(
    value: str, suffix: str, known: set[tuple[str, str]], source_text: str
) -> bool:
    """A number is supported when the data has it with a matching unit.

    A bare number or a percentage may match the data's bare value ("40%" against "40 percent").
    A unit may be written apart in the data ("200 ms") or spelled out ("1.2 million").
    """
    if (value, suffix) in known:
        return True
    if suffix in ("", "%"):
        return any(v == value and s in ("", "%") for v, s in known)
    spelled: str = _MAGNITUDE_WORDS.get(suffix, suffix)
    pattern = rf"(?<![\w.]){re.escape(value)}\s?(?:{re.escape(suffix)}|{re.escape(spelled)})\b"
    return re.search(pattern, source_text.replace(",", ""), re.IGNORECASE) is not None


def _sentences(segment: str) -> list[str]:
    """Splits a segment into sentences and bullets, without breaking after abbreviations."""
    merged: list[str] = []
    for piece in _SENTENCE_SPLIT.split(segment):
        if not piece.strip():
            continue
        if merged and _ABBREVIATION_END.search(merged[-1]):
            merged[-1] = f"{merged[-1]} {piece}"
        else:
            merged.append(piece)
    return merged


def _drop_frame_lines(segment: str) -> str:
    """Removes salutation and sign-off lines, which are letter frame, not claims."""
    return "\n".join(line for line in segment.split("\n") if not _FRAME_LINE.match(line))


def _capitalised_tokens(segment: str, skip_initial: bool) -> list[str]:
    """Capitalised tokens, leaving out sentence- and bullet-initial ones in prose."""
    found: list[str] = []
    for sentence in _sentences(segment):
        stripped: str = _LEADING_MARKUP.sub("", sentence)
        initial = _CAPITALISED.match(stripped)
        for match in _CAPITALISED.finditer(stripped):
            if skip_initial and initial and match.start() == initial.start():
                continue
            token: str = re.sub(r"[./&]x+(?![A-Za-z0-9])", "", match.group(0)).rstrip(".&/")
            if token:
                found.append(token)
    return found


def _token_known(token: str, known_words: set[str]) -> bool:
    """A token is known when every alphanumeric part of it appears in the data."""
    parts: set[str] = _words(token)
    return bool(parts) and parts <= known_words


def _opens_a_title(rest: str) -> bool:
    """Whether the text after a sentence-initial level word reads as a title run."""
    if re.match(r"-level\b", rest, re.IGNORECASE):
        return True
    following = re.match(r"[\s,]+([A-Za-z]+)", rest)
    if following and following.group(1)[0].isupper():
        return True
    return any(w.lower() in FUNCTION_NOUNS for w in re.findall(r"[A-Za-z]+", rest)[:3])


def _level_words(segment: str, any_level: bool) -> list[str]:
    """Level words used as title or scope inflation, per plan §3.4's matching rules.

    In a role-title slot any level word counts, wherever it sits. Elsewhere only title-position
    phrases do, so a skill such as "Executive Communication" is not read as a claimed level.
    """
    levels: str = "|".join(sorted(LEVEL_WORDS, key=len, reverse=True))
    nouns: str = "|".join(sorted(FUNCTION_NOUNS))
    found: list[str] = []
    patterns: list[str] = [
        (
            rf"\b(?:(?<!such\s)(?<!well\s)as|become|became|promoted to)"
            rf"\s+(?:an?\s+|the\s+)?({levels})\b"
        ),
        rf"\b({levels})\s+(?:{nouns})\b",
    ]
    capitalised_levels: str = "|".join(
        "VP" if w == "vp" else w.title() for w in sorted(LEVEL_WORDS, key=len, reverse=True)
    )
    if any_level:
        patterns.append(rf"\b({levels})\b")
    for pattern in patterns:
        found.extend(m.group(1).lower() for m in re.finditer(pattern, segment, re.IGNORECASE))
    found.extend(
        m.group(1).lower() for m in re.finditer(rf"\b({capitalised_levels})\s+of\b", segment)
    )
    if not any_level:
        for sentence in _sentences(segment):
            stripped: str = _LEADING_MARKUP.sub("", sentence)
            initial = _CAPITALISED.match(stripped)
            for match in re.finditer(rf"\b({capitalised_levels})\b", stripped):
                if initial and match.start() == initial.start():
                    # Sentence-initial is exempt as ordinary capitalisation, unless it opens a
                    # title: "Principal Cloud Architect", "VP, Engineering", "Director-level".
                    if not _opens_a_title(stripped[match.end() :]):
                        continue
                found.append(match.group(1).lower())
    return found


def check_unsupported(
    prose: Iterable[str],
    master_data: dict[str, Any],
    req_text: str = "",
    labels: Iterable[str] = (),
    titles: Iterable[str] = (),
) -> UnsupportedReport:
    """Reports what the generated text claims that `master_data` does not contain.

    Args:
        prose: Generated prose slots (summary, each bullet, the letter body), one string each.
            Sentence- and bullet-initial words are exempt from the capitalised-token check.
        master_data: The candidate data the generator was given.
        req_text: The job requisition text, plus any letter-frame fields such as the company
            name. Findings that appear here are labelled "from req".
        labels: Generated name slots (titles, employers, skills, certifications, degrees,
            institutions). Every word in them is checked, with no initial-word exemption.
        titles: Generated role titles. Like labels, plus any level word counts, wherever it
            sits, and is judged against the data's role titles.

    Returns:
        The report. Entries are de-duplicated and sorted.
    """
    source_text: str = _normalise("\n".join(_flatten(master_data)))
    req_text = _normalise(req_text)
    known_words: set[str] = _words(source_text)
    source_lower: str = source_text.lower()
    number_source: str = _normalise(
        "\n".join(_flatten({k: v for k, v in master_data.items() if k != "contact"}))
    )
    known_numbers: set[tuple[str, str]] = set(_numbers(number_source))
    req_words: set[str] = _words(req_text)

    terms: set[str] = set()
    numbers: set[str] = set()
    levels: set[str] = set()
    capitalised: set[str] = set()
    from_req: dict[str, str] = {}
    ai_tells: dict[str, int] = {}

    # (text, is_label, is_title). Labels and titles are names: no initial-word exemption, and
    # nothing in them can come from the req.
    slots: list[tuple[str, bool, bool]] = [
        (_drop_frame_lines(_normalise(s)), False, False) for s in prose if s and s.strip()
    ]
    slots += [(_normalise(s), True, False) for s in labels if s and s.strip()]
    slots += [(_normalise(s), True, True) for s in titles if s and s.strip()]

    term_source: str = number_source  # everything but the contact block's free text
    supported_terms: set[str] = {t for t in GENERAL_VOCABULARY if _contains_term(term_source, t)}
    title_words: set[str] = _role_titles(master_data) or known_words

    for segment, is_label, is_title in slots:
        matched, remainder = _match_terms(segment)
        for term in matched:
            if term in supported_terms:
                continue
            # A name in a label slot (employer, title, skill) cannot come from the req.
            if not is_label and _contains_term(req_text, term):
                from_req.setdefault(term.lower(), term)
            else:
                terms.add(term)

        copied_from_data: bool = (
            is_label and not is_title and segment.strip().lower() in source_lower
        )
        for level in () if copied_from_data else _level_words(segment, is_title):
            if level not in title_words:
                levels.add(level)

        for value, suffix in _numbers(remainder):
            if not _number_supported(value, suffix, known_numbers, number_source):
                numbers.add(f"{value}{suffix}")

        for token in _capitalised_tokens(remainder, skip_initial=not is_label):
            lowered: str = token.lower()
            if lowered in VERB_LEXICON or lowered in MONTHS or lowered in LEVEL_WORDS:
                continue
            if (
                lowered in GENERAL_VOCABULARY and lowered not in CASE_SENSITIVE_TERMS
            ) or _token_known(token, known_words):
                continue
            if not is_label and _token_known(token, req_words):
                from_req.setdefault(lowered, token)
            else:
                capitalised.add(token)

        if not is_label:
            for phrase in AI_TELL_PHRASES:
                hits: int = len(re.findall(rf"(?<!\w){re.escape(phrase)}(?!\w)", segment, re.I))
                if hits:
                    ai_tells[phrase] = ai_tells.get(phrase, 0) + hits

    return UnsupportedReport(
        terms=sorted(terms),
        numbers=sorted(numbers),
        levels=sorted(levels),
        capitalised=sorted(capitalised),
        from_req=sorted(from_req.values(), key=str.lower),
        ai_tells=dict(sorted(ai_tells.items())),
    )
