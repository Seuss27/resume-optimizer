import json
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from google import genai
from google.genai import types

from resume_optimizer.interfaces import LLMEngineInterface
from resume_optimizer.logging_setup import get_logger

logger = get_logger(__name__)


class GeminiAdapter(LLMEngineInterface):
    """Concrete adapter handling Google Gemini API communication and resiliency."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash") -> None:
        self.model_name: str = model_name
        self.http_options: types.HttpOptions = types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=2.0,
                attempts=5,
                http_status_codes=[429, 500, 502, 503, 504],
            )
        )
        self.client: genai.Client = genai.Client(api_key=api_key, http_options=self.http_options)

    def generate_structured_content(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        system_instruction: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:

        logger.info(f"Initiating {self.model_name} API call.")

        config_args: dict[str, Any] = {
            "response_mime_type": "application/json",
            "response_schema": response_schema,
            "temperature": temperature,
        }

        if system_instruction:
            config_args["system_instruction"] = system_instruction

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(**config_args),
        )

        return json.loads(response.text or "{}")


class BedrockAdapter(LLMEngineInterface):
    """Concrete adapter handling AWS Bedrock communication and IAM resolution."""

    def __init__(
        self,
        region_name: str = "us-east-1",
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
    ) -> None:
        """Initializes the Bedrock client using the native AWS credential chain."""
        self.model_id: str = model_id
        # Relies on IAM roles or standard AWS environment variables. Do not pass keys directly.
        try:
            self.client: Any = boto3.client("bedrock-runtime", region_name=region_name)
        except BotoCoreError as e:
            logger.critical("Failed to initialize AWS Bedrock client.", exc_info=True)
            raise RuntimeError("AWS authentication or routing failure.") from e

    def generate_structured_content(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        system_instruction: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Maps standard prompts and schemas to Bedrock's Converse API Tool use."""
        logger.info("Initiating API call via AWS Bedrock.", extra={"model_id": self.model_id})

        messages: list[dict[str, Any]] = [{"role": "user", "content": [{"text": prompt}]}]

        # Force structured output by defining the schema as a required tool
        tool_config: dict[str, Any] = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "generate_resume_structure",
                        "description": "Output the structured resume components.",
                        "inputSchema": {"json": response_schema},
                    }
                }
            ],
            "toolChoice": {"tool": {"name": "generate_resume_structure"}},
        }

        system_prompts: list[dict[str, str]] = []
        if system_instruction:
            system_prompts.append({"text": system_instruction})

        try:
            response: dict[str, Any] = self.client.converse(
                modelId=self.model_id,
                messages=messages,
                system=system_prompts,
                toolConfig=tool_config,
                inferenceConfig={"temperature": temperature},
            )

            # Safely extract the forced tool use input containing the JSON payload
            output_message: dict[str, Any] = response.get("output", {}).get("message", {})
            for block in output_message.get("content", []):
                if "toolUse" in block:
                    return block["toolUse"].get("input", {})

            logger.error("Bedrock model failed to trigger the required output schema tool.")
            return {}

        except ClientError as e:
            logger.error("AWS Bedrock ClientError encountered.", exc_info=True)
            raise RuntimeError(f"Bedrock API failure: {e.response['Error']['Message']}") from e


class MockLLMAdapter(LLMEngineInterface):
    """Deterministic mock adapter with integrated contract validation and fault injection."""

    def __init__(
        self,
        mock_responses: list[dict[str, Any]] | None = None,
        injected_exception: Exception | None = None,
        exception_trigger_count: int = 1,
    ) -> None:
        """Initializes the mock adapter.

        Args:
            mock_responses: Sequenced dictionaries simulating successful LLM returns.
            injected_exception: An active exception class to raise for fault simulation.
            exception_trigger_count: The number of sequential calls that should fail
                before reverting to normal operation. Used to validate retries.
        """
        self.mock_responses: list[dict[str, Any]] = mock_responses or [{}]
        self.injected_exception: Exception | None = injected_exception
        self.exception_trigger_count: int = exception_trigger_count
        self.call_count: int = 0
        self.call_history: list[dict[str, Any]] = []

    def _validate_schema(self, payload: dict[str, Any], schema: dict[str, Any]) -> None:
        """Validates that a provided payload conforms structurally to the target schema."""
        if schema.get("type") == "OBJECT" and "properties" in schema:
            expected_keys = schema["properties"].keys()
            for key in expected_keys:
                # If a property is required or assumed, verify its structural existence
                if key not in payload:
                    raise ValueError(
                        f"Contract Mismatch: Mock fixture is missing required key '{key}' "
                        f"defined in the expected schema definition."
                    )

                # Recursive validation for nested objects (e.g., job_metadata)
                nested_schema = schema["properties"][key]
                if nested_schema.get("type") == "OBJECT" and isinstance(payload[key], dict):
                    self._validate_schema(payload[key], nested_schema)

    def generate_structured_content(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        system_instruction: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Simulates an LLM execution pass, enforcing schema validation and fault injection."""
        self.call_count += 1

        logger.info(
            "Intercepted request via Mock Adapter.", extra={"call_sequence": self.call_count}
        )

        self.call_history.append(
            {
                "prompt": prompt,
                "system_instruction": system_instruction,
                "temperature": temperature,
            }
        )

        # Process Fault Injection Phase
        if self.injected_exception and self.call_count <= self.exception_trigger_count:
            logger.warning(
                f"Simulating injected failure state on call count {self.call_count}.",
                extra={"exception": type(self.injected_exception).__name__},
            )
            raise self.injected_exception

        # Retrieve Current Active Output Payload
        if len(self.mock_responses) > 1:
            current_response = self.mock_responses.pop(0)
        else:
            current_response = self.mock_responses[0]

        # Enforce Structural Interface Gate Validations
        self._validate_schema(current_response, response_schema)

        return current_response

    def get_call_history(self) -> list[dict[str, Any]]:
        """Returns log details of all intercepted pipeline execution payloads."""
        return self.call_history
