import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
import numpy as np
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class SearchHit:
    chunk_id: str
    score: float


class VectorStore(ABC):
    @abstractmethod
    def replace_document(self, document_id: str, workspace_id: str, chunks, vectors: list[list[float]]) -> None: ...

    @abstractmethod
    def search(self, workspace_id: str, vector: list[float], top_k: int, document_id: str | None = None) -> list[SearchHit]: ...

    @abstractmethod
    def delete_document(self, document_id: str) -> None: ...


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self.entries: dict[str, tuple[str, str, np.ndarray]] = {}

    def replace_document(self, document_id, workspace_id, chunks, vectors):
        self.delete_document(document_id)
        for chunk, vector in zip(chunks, vectors):
            self.entries[chunk.id] = (workspace_id, document_id, np.array(vector, dtype=np.float32))

    def search(self, workspace_id, vector, top_k, document_id=None):
        needle = np.array(vector, dtype=np.float32)
        hits = []
        for chunk_id, (entry_workspace, entry_document, candidate) in self.entries.items():
            if entry_workspace != workspace_id or (document_id and entry_document != document_id):
                continue
            score = float(np.dot(needle, candidate) / ((np.linalg.norm(needle) * np.linalg.norm(candidate)) or 1))
            hits.append(SearchHit(chunk_id, score))
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:top_k]

    def delete_document(self, document_id):
        for chunk_id in [key for key, value in self.entries.items() if value[1] == document_id]:
            del self.entries[chunk_id]


class QdrantVectorStore(VectorStore):
    COLLECTION = "rag_document_chunks"

    def __init__(self) -> None:
        from qdrant_client import QdrantClient
        self.client = QdrantClient(url=settings.qdrant_url)
        self.initialized = False

    def _init(self, dimensions: int):
        if self.initialized:
            return
        from qdrant_client.models import Distance, VectorParams
        if not self.client.collection_exists(self.COLLECTION):
            self.client.create_collection(self.COLLECTION, vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE))
        self.initialized = True

    def replace_document(self, document_id, workspace_id, chunks, vectors):
        from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct
        self._init(len(vectors[0]))
        self.client.delete(self.COLLECTION, points_selector=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]))
        self.client.upsert(self.COLLECTION, points=[PointStruct(id=chunk.id, vector=vector, payload={"workspace_id": workspace_id, "document_id": document_id}) for chunk, vector in zip(chunks, vectors)])

    def search(self, workspace_id, vector, top_k, document_id=None):
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        conditions = [FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))]
        if document_id:
            conditions.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
        points = self.client.query_points(self.COLLECTION, query=vector, query_filter=Filter(must=conditions), limit=top_k).points
        return [SearchHit(str(point.id), float(point.score)) for point in points]

    def delete_document(self, document_id):
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        self.client.delete(self.COLLECTION, points_selector=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]))


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        if settings.qdrant_url:
            try:
                _store = QdrantVectorStore()
            except Exception:
                logger.warning("qdrant_unavailable_at_startup; using process-local store")
                _store = InMemoryVectorStore()
        else:
            _store = InMemoryVectorStore()
    return _store

