import re
from .types import ProposedFinding
from .severity import for_finding
from ..models import FindingType


def _tokens(text):
    return {token for token in re.findall(r"[a-z]{3,}", text.lower()) if token not in {"the", "and", "that", "with", "from", "this", "must"}}


def detect(chunks):
    findings, emitted = [], set()
    tokens = [_tokens(chunk.content) for chunk in chunks]
    for i, first in enumerate(chunks):
        if len(first.content) < 80:
            continue
        for j in range(i + 1, len(chunks)):
            second = chunks[j]
            intersection = len(tokens[i] & tokens[j])
            union = len(tokens[i] | tokens[j]) or 1
            similarity = intersection / union
            if similarity >= .62 and (first.document_id != second.document_id or abs(first.chunk_index - second.chunk_index) > 1):
                key = tuple(sorted((first.id, second.id)))
                if key not in emitted:
                    emitted.add(key)
                    findings.append(ProposedFinding(
                        FindingType.DUPLICATE_CONTENT, for_finding(FindingType.DUPLICATE_CONTENT, min(.93, .55 + similarity / 2)),
                        "Potentially duplicate content", "Two separate sections share unusually similar substantive wording. This is a review prompt; repeated clauses may be intentional.",
                        min(.93, .55 + similarity / 2), "Confirm whether both clauses are needed and consolidate or cross-reference if appropriate.", [first.id, second.id]
                    ))
    return findings

