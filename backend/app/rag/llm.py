import logging
import time
from abc import ABC, abstractmethod
import httpx
from .retriever import retrieve
from ..config import settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    @abstractmethod
    def answer(self, question: str, context: str) -> str: ...


class OllamaProvider(LLMProvider):
    def answer(self, question, context):
        prompt = """You answer only from the supplied document excerpts. Cite excerpts as [1], [2], etc. If evidence is insufficient, say exactly that. Do not add unsupported facts.\n\n""" + f"Question: {question}\n\nExcerpts:\n{context}"
        start = time.perf_counter()
        try:
            response = httpx.post(f"{settings.ollama_base_url.rstrip('/')}/api/generate", json={"model": settings.ollama_model, "prompt": prompt, "stream": False}, timeout=75)
            response.raise_for_status()
            logger.info("ollama_completed latency_ms=%s", round((time.perf_counter()-start)*1000))
            return response.json().get("response", "").strip()
        except httpx.HTTPError as exc:
            raise RuntimeError("Ollama is unavailable. Start Ollama and pull the configured model, or set LLM_MODE=mock for local testing.") from exc


class GroundedMockProvider(LLMProvider):
    """Test-mode summarizer; every response is composed directly from retrieved source text."""
    def answer(self, question, context):
        excerpts = [line for line in context.splitlines() if line and not line.startswith("[")]
        if not excerpts:
            return "I couldn't find sufficient evidence in the uploaded documents to answer this question."
        return f"Based on the retrieved document evidence: {excerpts[0][:650]} [1]"


def get_llm() -> LLMProvider:
    return GroundedMockProvider() if settings.llm_mode == "mock" else OllamaProvider()

