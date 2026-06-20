# tests/test_pipeline.py
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from resume_optimizer.adapters import MockLLMAdapter


# Add the patch decorator targeting the pypandoc module INSIDE your generate.py file
@patch("resume_optimizer.generate.pypandoc.convert_file")
def test_resume_generation_pipeline_success(
    mock_pandoc_convert,  # <-- Add the mock object to arguments
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Validates the core application flow using deterministic LLM outputs and isolated I/O."""

    # 1. Create an isolated, temporary master_data.json
    mock_data_path = tmp_path / "master_data.json"
    mock_master_data = {
        "contact": {"name": "Test Architect"},
        "skills": ["Python", "AWS", "Clean Architecture"],
        "experience": [],
    }
    mock_data_path.write_text(json.dumps(mock_master_data))

    # 2. Setup the LLM Mock
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

    # 3. Run execution injecting the isolated test path
    from resume_optimizer.generate import generate_collateral

    generate_collateral(
        job_req_text="We need a Python expert for AWS microservices.", data_path=mock_data_path
    )

    # 4. (Optional but recommended) Assert the boundary was crossed correctly
    mock_pandoc_convert.assert_called()
