"""Tests for the one version source (plan task B7)."""

import re

import resume_optimizer
from resume_optimizer import generate


def test_the_package_version_is_a_plain_major_minor_patch() -> None:
    version: object = resume_optimizer.__version__
    assert isinstance(version, str)
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is not None


def test_generate_does_not_restate_the_version() -> None:
    assert "__version__" not in vars(generate)
