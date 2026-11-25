from pathlib import Path
from app.ingestion.chunking import intelligent_chunks
from app.ingestion.extractors import ExtractedPage, ExtractionResult, extract_file
from app.rag.citation import citations


def test_extract_text_and_preserve_content(tmp_path: Path):
    path = tmp_path / "policy.txt"; path.write_text("# Rules\n\nEmployees must comply.")
    result = extract_file(path)
    assert "Employees must comply" in result.text


def test_heading_aware_chunking():
    result = ExtractionResult([ExtractedPage(1, "# Remote Work\n\nEmployees may work remotely up to two days per week.\n\n# Leave\n\nEmployees must notify HR.")], 1)
    chunks = intelligent_chunks(result, 100, 20)
    assert chunks[0].section == "Remote Work"
    assert any(chunk.section == "Leave" for chunk in chunks)


def test_citation_metadata_is_explicit():
    document = type("Document", (), {"filename": "policy.txt"})()
    chunk = type("Chunk", (), {"id": "chunk-1", "document_id": "doc-1", "document": document, "page": 3, "section": "Rules"})()
    assert citations([(chunk, .91)])[0]["relevance_score"] == .91
