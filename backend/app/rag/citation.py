def citations(hits) -> list[dict]:
    return [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "document": chunk.document.filename,
            "page": chunk.page,
            "section": chunk.section,
            "relevance_score": round(score, 4),
        }
        for chunk, score in hits
    ]

