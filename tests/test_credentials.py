"""Tests for the credentials module (plan task B5): keyring only, no environment fallback."""

import ast
import logging
from pathlib import Path
from typing import Any

import keyring.backend
import keyring.errors
import pytest

import resume_optimizer
from resume_optimizer import credentials, generate
from resume_optimizer.credentials import MissingCredentialError, get_credential

PACKAGE_DIR: Path = Path(resume_optimizer.__file__).resolve().parent
SECRET: str = "s3cret-value-123"  # noqa: S105 - a test stand-in


class RaisingKeyring(keyring.backend.KeyringBackend):
    """A backend whose every call fails, to prove a branch never reads the keyring."""

    priority = 1  # type: ignore[assignment]

    def get_password(self, service: str, username: str) -> str | None:
        raise keyring.errors.KeyringError("locked")

    def set_password(self, service: str, username: str, password: str) -> None:
        raise keyring.errors.KeyringError("locked")

    def delete_password(self, service: str, username: str) -> None:
        raise keyring.errors.KeyringError("locked")


def test_a_stored_value_is_returned_unchanged(memory_keyring: Any) -> None:
    memory_keyring.set_password("resume-optimizer", "gemini-api-key", SECRET)
    assert get_credential("gemini") == SECRET


@pytest.mark.parametrize(
    "bad",
    [
        f" {SECRET}",
        f"{SECRET}\n",
        f"{SECRET} ",
        f"{SECRET}\x00x",
        f"{SECRET}\x7fx",
        f"{SECRET}\tx",
        f" {SECRET}",
        f"﻿{SECRET}",
    ],
)
def test_a_malformed_value_is_rejected_without_quoting_it(memory_keyring: Any, bad: str) -> None:
    memory_keyring.set_password("resume-optimizer", "gemini-api-key", bad)
    with pytest.raises(MissingCredentialError) as info:
        get_credential("gemini")
    assert SECRET not in str(info.value)
    assert "malformed" in str(info.value)


@pytest.mark.parametrize("stored", [None, ""])
def test_a_missing_or_empty_entry_raises(memory_keyring: Any, stored: str | None) -> None:
    if stored is not None:
        memory_keyring.set_password("resume-optimizer", "anthropic-api-key", stored)
    with pytest.raises(MissingCredentialError) as info:
        get_credential("anthropic")
    message: str = str(info.value)
    assert "resume-optimizer" in message
    assert "anthropic-api-key" in message
    assert "python -m keyring set resume-optimizer anthropic-api-key" in message


def test_an_unknown_name_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown credential"):
        get_credential("ledger")


def test_a_keyring_error_becomes_missing_credential_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("keyring.core._keyring_backend", RaisingKeyring())
    with pytest.raises(MissingCredentialError) as info:
        get_credential("gemini")
    assert "RaisingKeyring" in str(info.value)
    assert isinstance(info.value.__cause__, keyring.errors.KeyringError)


def test_no_log_record_or_message_carries_the_value(
    memory_keyring: Any, caplog: pytest.LogCaptureFixture
) -> None:
    memory_keyring.set_password("resume-optimizer", "gemini-api-key", SECRET)
    with caplog.at_level(logging.DEBUG):
        get_credential("gemini")
        with pytest.raises(MissingCredentialError) as info:
            get_credential("perplexity")
    assert SECRET not in caplog.text
    assert SECRET not in str(info.value)


def test_there_is_no_environment_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    with pytest.raises(MissingCredentialError):
        get_credential("gemini")


def test_gemini_engine_gets_the_stored_key(
    memory_keyring: Any, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    memory_keyring.set_password("resume-optimizer", "gemini-api-key", SECRET)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    seen: dict[str, Any] = {}

    class Recorder:
        def __init__(self, **kwargs: Any) -> None:
            seen.update(kwargs)

    monkeypatch.setattr("resume_optimizer.adapters.genai.Client", Recorder)
    with caplog.at_level(logging.DEBUG):
        generate.get_llm_engine()
    assert seen["api_key"] == SECRET
    assert SECRET not in caplog.text


def test_mock_and_bedrock_never_read_the_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("keyring.core._keyring_backend", RaisingKeyring())
    built: list[object] = []

    class Recorder:
        def __init__(self, **kwargs: Any) -> None:
            built.append(kwargs)

    monkeypatch.setattr("resume_optimizer.generate.BedrockAdapter", Recorder)
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    generate.get_llm_engine()
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")
    generate.get_llm_engine()
    assert len(built) == 1


def test_main_exits_one_when_the_gemini_key_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setattr("sys.argv", ["generate-resume", "--master"])
    built: list[object] = []

    class Recorder:
        def __init__(self, **kwargs: Any) -> None:
            built.append(kwargs)

    monkeypatch.setattr("resume_optimizer.generate.GeminiAdapter", Recorder)
    with pytest.raises(SystemExit) as info:
        generate.main()
    assert info.value.code == 1
    err: str = capsys.readouterr().err
    assert "python -m keyring set resume-optimizer gemini-api-key" in err
    assert "Traceback" not in err
    assert not built


def _violations(source: str) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import) and any(
            a.name == "keyring" or a.name.startswith("keyring.") for a in node.names
        ):
            lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            module: str = node.module or ""
            if module == "keyring" or module.startswith("keyring."):
                lines.append(node.lineno)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.endswith("_API_KEY")
        ):
            lines.append(node.lineno)
    return lines


def test_only_credentials_reads_secrets() -> None:
    offenders: list[str] = []
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        if path.name == "credentials.py" and path.parent == PACKAGE_DIR:
            continue
        offenders += [f"{path.name}:{n}" for n in _violations(path.read_text(encoding="utf-8"))]
    assert not offenders, f"secret access outside credentials.py: {offenders}"


def test_the_exempt_module_exists_and_is_the_reader() -> None:
    """Pins the exemption: credentials.py is where the keyring import lives."""
    assert _violations((PACKAGE_DIR / "credentials.py").read_text(encoding="utf-8"))


def test_the_boundary_check_catches_a_violation() -> None:
    assert _violations("import keyring\n") == [1]
    assert _violations("from keyring.core import x\n") == [1]
    assert _violations("K = 'FOO_API_KEY'\n") == [1]
    assert _violations("import os\n") == []


def test_service_name_is_fixed() -> None:
    assert credentials.SERVICE_NAME == "resume-optimizer"
