import re
from .types import ProposedFinding
from .severity import for_finding
from ..models import FindingType

TERM_FAMILIES = {
    "employee identifier": ["employee id", "employee number", "staff id", "personnel number"],
    "people team": ["human resources", "hr department", "people operations"],
    "remote work": ["remote work", "telework", "work from home"],
}


def detect(chunks):
    text = "\n".join(chunk.content.lower() for chunk in chunks)
    findings = []
    for concept, terms in TERM_FAMILIES.items():
        seen = [term for term in terms if re.search(r"\b" + re.escape(term) + r"\b", text)]
        if len(seen) > 1:
            evidence = [chunk for chunk in chunks if any(term in chunk.content.lower() for term in seen)][:3]
            findings.append(ProposedFinding(
                FindingType.TERMINOLOGY_INCONSISTENCY, for_finding(FindingType.TERMINOLOGY_INCONSISTENCY, .76),
                f"Potentially inconsistent terminology for {concept}",
                f"The terms {', '.join('“' + term + '”' for term in seen)} occur in the audited content and may refer to the same concept. Context should be reviewed before treating this as an inconsistency.",
                .76, f"Choose and define a preferred term for {concept}, or clarify where the terms differ.", [chunk.id for chunk in evidence]
            ))
    return findings

