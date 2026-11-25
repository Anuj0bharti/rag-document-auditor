from dataclasses import dataclass
from ..models import FindingType, Severity


@dataclass
class ProposedFinding:
    type: FindingType
    severity: Severity
    title: str
    description: str
    confidence: float
    recommendation: str
    chunk_ids: list[str]
    ai_interpretation: bool = False

