import os
from typing import Any

import pytest

from resume_optimizer.adapters import MockLLMAdapter
from resume_optimizer.generate import generate_collateral


@pytest.fixture
def configure_mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forces the application into the mock provider state."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")


def test_resume_generation_pipeline_success(
    configure_mock_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validates the core application flow using deterministic LLM outputs."""

    # 1. Define the exact state the AI *should* return
    expected_payload: dict[str, Any] = {
        "job_metadata": {"company_name": "Acme Corp", "role_title": "Backend Engineer"},
        "professional_summary": "Expert in distributed systems.",
        "selected_skills": ["Python", "AWS"],
    }

    # 2. Inject the mock data into the factory routing
    mock_adapter = MockLLMAdapter(mock_responses=[expected_payload])
    monkeypatch.setattr("resume_optimizer.generate.get_llm_engine", lambda: mock_adapter)

    # 3. Execute the core pipeline
    generate_collateral(job_req_text="We need a Python expert for AWS microservices.")

    # 4. Assert architectural intent
    history: list[dict[str, Any]] = mock_adapter.get_call_history()

    assert len(history) == 1
    assert "AWS microservices" in history[0]["prompt"]
    # Verify Pandoc/Jinja successfully created the target files using the mock data
    assert os.path.exists("Acme_Corp_Backend_Engineer_Resume.docx")
