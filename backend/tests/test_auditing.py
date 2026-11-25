from types import SimpleNamespace
from app.auditing.ambiguity_detector import detect as ambiguous
from app.auditing.contradiction_detector import detect as contradictory
from app.auditing.reference_detector import detect as references


def chunk(identifier, content): return SimpleNamespace(id=identifier, content=content, document_id=identifier, chunk_index=0)


def test_detects_evidence_backed_contradiction():
    findings = contradictory([chunk("a", "Employees may work remotely up to 3 days per week."), chunk("b", "Employees may work remotely up to 2 days per week.")])
    assert findings and findings[0].chunk_ids == ["a", "b"]


def test_detects_ambiguous_statement():
    findings = ambiguous([chunk("a", "Submit the request as soon as possible.")])
    assert findings[0].type.value == "AMBIGUOUS_STATEMENT"


def test_detects_broken_section_reference():
    findings = references([chunk("a", "See Section 9.4 for the exception.")])
    assert findings[0].type.value == "BROKEN_REFERENCE"

