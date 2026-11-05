"""Tests for the packaged prompts and templates (plan task B2)."""

from pathlib import Path

import pytest

from resume_optimizer import resources

PROMPTS: tuple[str, ...] = (
    "system_prompt.txt",
    "master_prompt.txt",
    "ats_prompt.txt",
    "desirability_prompt.txt",
)
TEMPLATES: tuple[str, ...] = ("resume_template.md", "cover_letter_template.md")


@pytest.mark.parametrize("name", PROMPTS)
def test_the_packaged_prompts_load(name: str) -> None:
    assert resources.read_prompt(name).strip()


@pytest.mark.parametrize("name", TEMPLATES)
def test_the_packaged_templates_load(name: str) -> None:
    assert resources.template_environment().get_template(name) is not None


def test_a_missing_prompt_names_only_the_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("resume_optimizer.resources.PROMPT_DIR", tmp_path / "nowhere")
    with pytest.raises(FileNotFoundError) as raised:
        resources.read_prompt("system_prompt.txt")
    assert str(raised.value) == "system_prompt.txt is missing."


def test_the_seam_is_read_at_call_time(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "system_prompt.txt").write_text("stand-in", encoding="utf-8")
    monkeypatch.setattr("resume_optimizer.resources.PROMPT_DIR", tmp_path)
    assert resources.read_prompt("system_prompt.txt") == "stand-in"
