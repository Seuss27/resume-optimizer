from abc import ABC, abstractmethod
from typing import Any, Dict, List


class VectorStoreInterface(ABC):
    """Abstract interface defining required vector database operations."""

    @abstractmethod
    def upsert_vectors(self, documents: List[Dict[str, Any]]) -> bool:
        """Embeds and stores documents in the vector database."""
        pass

    @abstractmethod
    def similarity_search(self, query: str, top_k: int = 3) -> List[str]:
        """Retrieves relevant text contexts based on a semantic query."""
        pass


class LLMInterface(ABC):
    """Abstract interface defining required language model operations."""

    @abstractmethod
    def generate_response(self, prompt: str, context: List[str]) -> str:
        """Generates a text completion based on a provided context list."""
        pass


class RAGOrchestrator:
    """The core engine executing the framework-agnostic RAG logic.

    This class relies exclusively on abstract interfaces injected
    at runtime via dependency injection.
    """

    def __init__(self, vector_store: VectorStoreInterface, llm_service: LLMInterface):
        self.vector_store = vector_store
        self.llm_service = llm_service

    def ingest_knowledge_base(self, documents: List[Dict[str, Any]]) -> bool:
        """Triggers document processing within the vector interface."""
        if not documents:
            return False
        return self.vector_store.upsert_vectors(documents)

    def answer_question(self, question: str) -> str:
        """Orchestrates the formal retrieve-and-generate workflow loop."""
        relevant_contexts = self.vector_store.similarity_search(query=question, top_k=3)
        return self.llm_service.generate_response(prompt=question, context=relevant_contexts)
