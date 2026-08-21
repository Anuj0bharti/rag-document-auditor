import time
import logging
from sqlalchemy.orm import Session
from .embeddings import get_embedding_provider
from .vector_store import get_vector_store
from ..models import DocumentChunk

logger = logging.getLogger(__name__)


def retrieve(db: Session, workspace_id: str, question: str, top_k: int = 5) -> list[tuple[DocumentChunk, float]]:
    start = time.perf_counter()
    vector = get_embedding_provider().embed([question])[0]
    hits = get_vector_store().search(workspace_id, vector, top_k)
    ids = [hit.chunk_id for hit in hits]
    chunks = {chunk.id: chunk for chunk in db.query(DocumentChunk).filter(DocumentChunk.id.in_(ids)).all()} if ids else {}
    results = [(chunks[hit.chunk_id], hit.score) for hit in hits if hit.chunk_id in chunks]
    logger.info("retrieval workspace_id=%s chunks=%s latency_ms=%s", workspace_id, len(results), round((time.perf_counter()-start)*1000))
    return results

