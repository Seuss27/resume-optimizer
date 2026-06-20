from abc import ABC, abstractmethod
from typing import Any


class LLMEngineInterface(ABC):
    """Abstract interface defining the boundary for language model interactions."""

    @abstractmethod
    def generate_structured_content(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        system_instruction: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Generates structured JSON payload based on a prompt and schema.

        Args:
            prompt: The full string prompt/context to send to the engine.
            response_schema: The required JSON schema dictionary for output enforcement.
            system_instruction: Optional system-level instructions/persona.
            temperature: Sampling temperature for output determinism.

        Returns:
            A dictionary containing the parsed model response.
        """
        pass
