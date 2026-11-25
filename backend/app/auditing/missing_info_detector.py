import re
from .types import ProposedFinding
from .severity import for_finding
from ..models import FindingType

TRIGGERS = re.compile(r"\b(?:submit|request|apply|obtain)\b.{0,90}\b(?:approval|approve|form|request)\b", re.I)


def detect(chunks):
    corpus = " ".join(chunk.content.lower() for chunk in chunks)
    findings = []
    for chunk in chunks:
        if not TRIGGERS.search(chunk.content):
            continue
        missing = []
        if not any(word in corpus for word in ["manager", "supervisor", "approver", "human resources", "hr"]):
            missing.append("a named approver")
        if not any(word in corpus for word in ["within", "days", "deadline", "before", "hours"]):
            missing.append("a timeframe")
        if missing:
            findings.append(ProposedFinding(
                FindingType.MISSING_INFORMATION, for_finding(FindingType.MISSING_INFORMATION, .7),
                "Approval workflow may be incomplete",
                f"This passage appears to require a submission or approval, while the audited corpus does not describe {', '.join(missing)}. This is limited to the uploaded documents and may be covered elsewhere.",
                .7, "Add a cross-reference or specify the workflow details if they are intended to be governed here.", [chunk.id]
            ))
    return findings

