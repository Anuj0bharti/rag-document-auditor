from ..models import FindingType, Severity


def for_finding(kind: FindingType, confidence: float, material: bool = False) -> Severity:
    if kind == FindingType.CONTRADICTION:
        return Severity.CRITICAL if material and confidence >= .88 else Severity.HIGH
    if kind in {FindingType.BROKEN_REFERENCE, FindingType.MISSING_INFORMATION}:
        return Severity.HIGH if confidence >= .8 else Severity.MEDIUM
    if kind in {FindingType.DUPLICATE_CONTENT, FindingType.TERMINOLOGY_INCONSISTENCY, FindingType.AMBIGUOUS_STATEMENT, FindingType.OUTDATED_REFERENCE}:
        return Severity.MEDIUM
    return Severity.INFO


WEIGHTS = {Severity.CRITICAL: 18, Severity.HIGH: 10, Severity.MEDIUM: 5, Severity.LOW: 2, Severity.INFO: 1}


def health_score(findings) -> int:
    """Transparent heuristic: 100 minus severity penalties weighted by confidence, capped at zero."""
    penalty = sum(WEIGHTS[f.severity] * max(.4, f.confidence) for f in findings)
    return max(0, round(100 - penalty))

