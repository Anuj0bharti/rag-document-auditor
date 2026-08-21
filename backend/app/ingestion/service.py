import hashlib
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from .extractors import extract_file, ExtractionError
from .chunking import intelligent_chunks
from ..config import settings
from ..models import Document, DocumentChunk, DocumentStatus
from ..rag.vector_store import get_vector_store
from ..rag.embeddings import get_embedding_provider

logger = logging.getLogger(__name__)


def process_document(db: Session, document: Document) -> Document:
    document.status = DocumentStatus.PROCESSING
    document.processing_error = None
    db.commit()
    try:
        result = extract_file(Path(document.storage_path))
        if not result.text.strip():
            raise ExtractionError("This document does not contain extractable text.")
        document.extracted_text = result.text
        document.page_count = result.page_count
        db.query(DocumentChunk).filter_by(document_id=document.id).delete()
        drafts = intelligent_chunks(result, settings.chunk_size, settings.chunk_overlap)
        if not drafts:
            raise ExtractionError("No usable text sections were found in this document.")
        chunks = [DocumentChunk(
            document_id=document.id, workspace_id=document.workspace_id,
            chunk_index=draft.chunk_index, content=draft.content, page=draft.page, section=draft.section,
            metadata_json={"filename": document.filename, "document_version": document.document_metadata.get("version")},
        ) for draft in drafts]
        db.add_all(chunks)
        document.status = DocumentStatus.INDEXING
        db.commit()
        db.refresh(document)
        for chunk in chunks:
            db.refresh(chunk)
        provider = get_embedding_provider()
        vectors = provider.embed([chunk.content for chunk in chunks])
        try:
            get_vector_store().replace_document(document.id, document.workspace_id, chunks, vectors)
        except Exception as exc:
            if settings.qdrant_url:
                raise ExtractionError("Vector database is unavailable. Confirm that Qdrant is running, then process the document again.") from exc
            raise
        document.status = DocumentStatus.READY
        db.commit()
        logger.info("document_processed document_id=%s chunks=%s", document.id, len(chunks))
    except Exception as exc:
        document.status = DocumentStatus.FAILED
        document.processing_error = str(exc) if isinstance(exc, ExtractionError) else "Processing failed. Please try a valid document."
        db.commit()
        logger.exception("document_processing_failed document_id=%s", document.id)
    return document


def sha256_stream(upload) -> tuple[bytes, str]:
    content = upload.file.read()
    return content, hashlib.sha256(content).hexdigest()
