from typing import Any

import pytest

from resume_optimizer.adapters import MockLLMAdapter


@pytest.fixture
def target_sample_schema() -> dict[str, Any]:
    """Provides a baseline structure representing a standardized application schema."""
    return {
        "type": "OBJECT",
        "properties": {
            "job_metadata": {
                "type": "OBJECT",
                "properties": {
                    "company_name": {"type": "STRING"},
                    "role_title": {"type": "STRING"},
                },
            },
            "professional_summary": {"type": "STRING"},
        },
    }


def test_mock_adapter_raises_value_error_on_schema_mismatch(
    target_sample_schema: dict[str, Any],
) -> None:
    """Verifies that the contract gate raises an exception when keys are missing."""
    # Malformed response fixture missing the required inner 'role_title' object
    invalid_payload = {
        "job_metadata": {"company_name": "TestCorp"},
        "professional_summary": "Incomplete fixture test summary.",
    }

    adapter = MockLLMAdapter(mock_responses=[invalid_payload])

    with pytest.raises(ValueError, match="Contract Mismatch: Mock fixture is missing required key"):
        adapter.generate_structured_content(
            prompt="Trigger verification script.", response_schema=target_sample_schema
        )


def test_mock_adapter_fault_injection_and_recovery(target_sample_schema: dict[str, Any]) -> None:
    """Validates that fault injection successfully triggers exceptions up to the threshold."""
    valid_payload = {
        "job_metadata": {
            "company_name": "Resilient LLC",
            "role_title": "Site Reliability Engineer",
        },
        "professional_summary": "Valid payload baseline configuration.",
    }

    # Inject a simulated transient cloud connection termination that occurs once
    simulated_error = ConnectionError("Simulated server timeout or transient API failure.")

    adapter = MockLLMAdapter(
        mock_responses=[valid_payload],
        injected_exception=simulated_error,
        exception_trigger_count=1,
    )

    # First call must throw the configured transient exception
    with pytest.raises(ConnectionError, match="Simulated server timeout"):
        adapter.generate_structured_content(
            prompt="Initial transmission attempt.", response_schema=target_sample_schema
        )

    # Second call must bypass the error loop and succeed natively, validating recovery
    successful_result = adapter.generate_structured_content(
        prompt="Automated pipeline retry pass.", response_schema=target_sample_schema
    )

    assert successful_result["job_metadata"]["company_name"] == "Resilient LLC"
    assert adapter.call_count == 2
