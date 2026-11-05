"""Reads the prompts and Jinja templates shipped as package data.

`PROMPT_DIR` and `TEMPLATE_DIR` are module-level seams: tests point them at a temp directory.
Every reader looks them up at call time, so callers must reach them through this module and
never copy them with a from-import.
"""

from importlib import resources
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

# A pip-installed wheel is unpacked on disk, so the directory form is safe.
PROMPT_DIR: Path = Path(str(resources.files("resume_optimizer") / "prompts"))
TEMPLATE_DIR: Path = Path(str(resources.files("resume_optimizer") / "templates"))


def read_prompt(prompt_filename: str) -> str:
    """Reads one packaged prompt file.

    Args:
        prompt_filename: The prompt's file name, such as `system_prompt.txt`.

    Raises:
        FileNotFoundError: If the prompt is missing. The message names the file only.
    """
    prompt_path: Path = PROMPT_DIR / prompt_filename
    if not prompt_path.is_file():
        raise FileNotFoundError(f"{prompt_filename} is missing.")
    return prompt_path.read_text(encoding="utf-8")


def template_environment() -> Environment:
    """Builds the Jinja environment over the packaged templates."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
