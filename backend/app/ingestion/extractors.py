from dataclasses import dataclass
from pathlib import Path
import re
from docx import Document as DocxDocument
from pypdf import PdfReader


class ExtractionError(ValueError):
    pass


@dataclass
class ExtractedPage:
    number: int | None
    text: str


@dataclass
class ExtractionResult:
    pages: list[ExtractedPage]
    page_count: int | None

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}


def _clean(text: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\r\n?", "\n", text)).strip()


def extract_file(path: Path) -> ExtractionResult:
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            reader = PdfReader(str(path))
            pages = [ExtractedPage(i + 1, _clean(page.extract_text() or "")) for i, page in enumerate(reader.pages)]
            return ExtractionResult(pages, len(pages))
        if ext == ".docx":
            document = DocxDocument(str(path))
            paragraphs = []
            for paragraph in document.paragraphs:
                text = _clean(paragraph.text)
                if text:
                    style = paragraph.style.name if paragraph.style else ""
                    paragraphs.append(("# " if style.lower().startswith("heading") else "") + text)
            return ExtractionResult([ExtractedPage(None, "\n\n".join(paragraphs))], None)
        if ext in {".txt", ".md", ".markdown"}:
            raw = path.read_text(encoding="utf-8", errors="replace")
            return ExtractionResult([ExtractedPage(None, _clean(raw))], None)
    except Exception as exc:
        raise ExtractionError(f"Could not read this {ext[1:].upper()} file.") from exc
    raise ExtractionError("Unsupported document type. Upload PDF, DOCX, TXT, or Markdown.")

