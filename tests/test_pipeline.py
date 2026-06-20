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

    # Hydrate all fields expected by the schema rule properties
    expected_payload: dict[str, Any] = {
        "job_metadata": {"company_name": "Acme Corp", "role_title": "Backend Engineer"},
        "professional_summary": "Expert in distributed systems.",
        "selected_skills": ["Python", "AWS"],
        "selected_certifications": [],
        "selected_education": [],
        "tailored_companies": [],
        "cover_letter_body": "Automated pipeline integration text.",
    }

    mock_adapter = MockLLMAdapter(mock_responses=[expected_payload])
    monkeypatch.setattr(
        "resume_optimizer.generate.get_llm_engine", lambda *args, **kwargs: mock_adapter
    )

    # Run execution with mock verification environment active
    generate_collateral(job_req_text="We need a Python expert for AWS microservices.")

    history = mock_adapter.get_call_history()
    assert len(history) == 1
    assert "AWS microservices" in history[0]["prompt"]
