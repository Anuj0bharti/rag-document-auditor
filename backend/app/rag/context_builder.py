def build_context(hits) -> str:
    """Build labeled evidence only; no document text beyond retrieved chunks is included."""
    return "\n\n".join(
        f"[{index}] {chunk.document.filename} | page {chunk.page or 'n/a'} | {chunk.section or 'unsectioned'}\n{chunk.content}"
        for index, (chunk, _) in enumerate(hits, 1)
    )

