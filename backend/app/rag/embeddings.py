import hashlib
import logging
from abc import ABC, abstractmethod
import numpy as np
from ..config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbeddingProvider(EmbeddingProvider):
    """Deterministic, local fallback. It trades semantic quality for zero model downloads."""
    dimensions = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = np.zeros(self.dimensions, dtype=np.float32)
            for token in text.lower().split():
                digest = hashlib.sha256(token.encode()).digest()
                vector[int.from_bytes(digest[:4], "big") % self.dimensions] += 1
            norm = np.linalg.norm(vector)
            vectors.append((vector / norm if norm else vector).tolist())
        return vectors


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self._model = None
        self._fallback = HashingEmbeddingProvider()

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            if self._model is None:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(settings.embedding_model)
            return self._model.encode(texts, normalize_embeddings=True).tolist()
        except Exception as exc:
            logger.warning("embedding_model_unavailable; using hashing fallback error=%s", type(exc).__name__)
            return self._fallback.embed(texts)


_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        _provider = HashingEmbeddingProvider() if settings.embedding_provider == "hashing" else LocalEmbeddingProvider()
    return _provider

