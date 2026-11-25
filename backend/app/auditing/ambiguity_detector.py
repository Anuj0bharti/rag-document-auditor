import re
from .types import ProposedFinding
from .severity import for_finding
from ..models import FindingType

PATTERN = re.compile(r"\b(as soon as possible|soon|reasonable(?: time)?|appropriate(?: approval)?|as necessary|timely|adequate|where applicable)\b", re.I)


def detect(chunks):
    findings = []
    for chunk in chunks:
        match = PATTERN.search(chunk.content)
        if match:
            phrase = match.group(0)
            findings.append(ProposedFinding(
                FindingType.AMBIGUOUS_STATEMENT, for_finding(FindingType.AMBIGUOUS_STATEMENT, .82),
                f"Ambiguous qualifier: “{phrase}”",
                f"The phrase “{phrase}” does not define a measurable condition, timeframe, or decision-maker. The surrounding statement should be checked against the source document.",
                .82, "Replace the qualifier with a defined timeframe, threshold, or accountable role.", [chunk.id]
            ))
    return findings

