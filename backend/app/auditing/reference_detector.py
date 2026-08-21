import re
from .types import ProposedFinding
from .severity import for_finding
from ..models import FindingType

REFERENCE = re.compile(r"\b(?:see|refer to|under)\s+(?:section|appendix)\s+([A-Za-z]?\d+(?:\.\d+)*(?:\([a-z]\))?)", re.I)
SECTION = re.compile(r"^\s*(\d+(?:\.\d+)*)[.)\s]", re.M)
OLD_YEAR = re.compile(r"\b(?:19|20)(\d{2})\b")


def detect(chunks):
    corpus = "\n".join(chunk.content for chunk in chunks)
    sections = set(SECTION.findall(corpus))
    findings = []
    for chunk in chunks:
        for match in REFERENCE.finditer(chunk.content):
            reference = match.group(1)
            if reference not in sections:
                findings.append(ProposedFinding(
                    FindingType.BROKEN_REFERENCE, for_finding(FindingType.BROKEN_REFERENCE, .9),
                    f"Reference to unavailable Section {reference}",
                    f"This passage refers to Section {reference}, but no matching numbered section was detected in the audited documents. This is evidence of a potentially broken reference, not proof that the section is absent from a non-uploaded document.",
                    .9, "Confirm the cross-reference and update it or include the referenced document.", [chunk.id]
                ))
        for year in OLD_YEAR.findall(chunk.content):
            value = int("20" + year) if int(year) < 70 else int("19" + year)
            if value < 2023 and ("version" in chunk.content.lower() or "policy" in chunk.content.lower()):
                findings.append(ProposedFinding(
                    FindingType.OUTDATED_REFERENCE, for_finding(FindingType.OUTDATED_REFERENCE, .64),
                    f"Potentially outdated reference to {value}",
                    f"This section contains a {value} reference in a policy/version context. Its current validity cannot be determined from the uploaded content alone.",
                    .64, "Verify whether this version or date remains authoritative.", [chunk.id]
                ))
    return findings

