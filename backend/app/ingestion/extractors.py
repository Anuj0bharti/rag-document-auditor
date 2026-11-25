import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
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


def _extract_docx_fallback(path: Path) -> str:
    paragraphs = []
    try:
        with zipfile.ZipFile(path) as z:
            if "word/document.xml" not in z.namelist():
                return ""
            tree = ET.fromstring(z.read("word/document.xml"))
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            for p in tree.iterfind(".//w:p", ns):
                pStyle = p.find(".//w:pPr/w:pStyle", ns)
                val = pStyle.attrib.get(f"{{{ns['w']}}}val", "") if pStyle is not None else ""
                is_heading = val.lower().startswith("heading")
                texts = [node.text for node in p.iterfind(".//w:t", ns) if node.text]
                p_text = "".join(texts).strip()
                if p_text:
                    paragraphs.append(("# " if is_heading else "") + p_text)
    except Exception:
        pass
    return "\n\n".join(paragraphs)


def extract_file(path: Path) -> ExtractionResult:
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            reader = PdfReader(str(path))
            pages = [ExtractedPage(i + 1, _clean(page.extract_text() or "")) for i, page in enumerate(reader.pages)]
            return ExtractionResult(pages, len(pages))
        if ext == ".docx":
            paragraphs = []
            try:
                from docx import Document as DocxDocument
                document = DocxDocument(str(path))
                for paragraph in document.paragraphs:
                    text = _clean(paragraph.text)
                    if text:
                        style = paragraph.style.name if paragraph.style else ""
                        paragraphs.append(("# " if style.lower().startswith("heading") else "") + text)
                docx_text = "\n\n".join(paragraphs)
            except Exception:
                docx_text = _extract_docx_fallback(path)
            return ExtractionResult([ExtractedPage(None, docx_text)], None)
        if ext in {".txt", ".md", ".markdown"}:
            raw = path.read_text(encoding="utf-8", errors="replace")
            return ExtractionResult([ExtractedPage(None, _clean(raw))], None)
    except Exception as exc:
        raise ExtractionError(f"Could not read this {ext[1:].upper()} file.") from exc
    raise ExtractionError("Unsupported document type. Upload PDF, DOCX, TXT, or Markdown.")


def main():
    parser = argparse.ArgumentParser(description="Extract text from PDF, DOCX, TXT, or Markdown files.")
    parser.add_argument("file_path", help="Path to the file to extract")
    args = parser.parse_args()

    target_path = Path(args.file_path)
    if not target_path.exists():
        print(f"Error: File not found: {target_path}", file=sys.stderr)
        sys.exit(1)

    try:
        result = extract_file(target_path)
        print(f"--- Extraction Successful for {target_path.name} ---")
        print(f"Total Pages: {result.page_count or 1}")
        print(f"Total Characters: {len(result.text)}")
        print("\n--- Extracted Text ---")
        print(result.text)
    except Exception as e:
        print(f"Extraction failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
