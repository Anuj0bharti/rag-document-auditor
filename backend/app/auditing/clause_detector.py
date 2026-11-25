import re
from .types import ProposedFinding
from ..models import FindingType, Severity

PATTERN = re.compile(r"\b(must|shall|required|prohibited|deadline|penalty|exception|responsible for|may not)\b", re.I)


def detect(chunks):
    findings = []
    for chunk in chunks:
        match = PATTERN.search(chunk.content)
        if match:
            findings.append(ProposedFinding(
                FindingType.IMPORTANT_CLAUSE, Severity.INFO, f"Important clause: {match.group(0).lower()}",
                "This passage contains obligation, restriction, deadline, exception, or responsibility language. It is highlighted for review, not as legal or compliance advice.",
                .88, "Review the clause for ownership, scope, and any referenced exceptions.", [chunk.id]
            ))
    return findings

