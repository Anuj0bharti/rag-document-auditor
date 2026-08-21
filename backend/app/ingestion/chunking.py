from dataclasses import dataclass
import re
from .extractors import ExtractionResult


@dataclass
class ChunkDraft:
    content: str
    page: int | None
    section: str | None
    chunk_index: int


HEADING = re.compile(r"^(?:#{1,6}\s+|(?:\d+(?:\.\d+)*[.)]?\s+))(.{2,180})$")
SENTENCES = re.compile(r"(?<=[.!?])\s+")


def _is_heading(paragraph: str) -> str | None:
    match = HEADING.match(paragraph.strip())
    if match:
        return match.group(1).strip()
    if len(paragraph) < 90 and paragraph.isupper() and any(char.isalpha() for char in paragraph):
        return paragraph.title()
    return None


def _split_to_size(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    sentences = SENTENCES.split(text)
    chunks, current = [], ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if current and len(candidate) > size:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail} {sentence}".strip()
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def intelligent_chunks(result: ExtractionResult, size: int = 900, overlap: int = 150) -> list[ChunkDraft]:
    if size < 100 or overlap >= size:
        raise ValueError("Chunk size must be at least 100 and larger than overlap.")
    output: list[ChunkDraft] = []
    section: str | None = None
    index = 0
    for page in result.pages:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", page.text) if p.strip()]
        buffer: list[str] = []
        for paragraph in paragraphs:
            heading = _is_heading(paragraph)
            if heading:
                if buffer:
                    for text in _split_to_size("\n\n".join(buffer), size, overlap):
                        output.append(ChunkDraft(text, page.number, section, index)); index += 1
                    buffer = []
                section = heading
                continue
            candidate = "\n\n".join(buffer + [paragraph])
            if buffer and len(candidate) > size:
                for text in _split_to_size("\n\n".join(buffer), size, overlap):
                    output.append(ChunkDraft(text, page.number, section, index)); index += 1
                buffer = [paragraph]
            else:
                buffer.append(paragraph)
        if buffer:
            for text in _split_to_size("\n\n".join(buffer), size, overlap):
                output.append(ChunkDraft(text, page.number, section, index)); index += 1
    return output

