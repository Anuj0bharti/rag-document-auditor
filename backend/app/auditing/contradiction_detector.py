import re
from collections import defaultdict
from .types import ProposedFinding
from .severity import for_finding
from ..models import FindingType

NUMBER_RULE = re.compile(r"\b(?:up to |maximum of |no more than )?(\d+)\s+(day|days|hour|hours|week|weeks|percent|%)\b", re.I)
SIGNALS = ("remote", "leave", "approval", "retention", "notice", "expense", "work from home", "telework")


def _topic(text):
    lowered = text.lower()
    return next((signal for signal in SIGNALS if signal in lowered), None)


def detect(chunks):
    candidates = defaultdict(list)
    for chunk in chunks:
        topic = _topic(chunk.content)
        if not topic:
            continue
        for amount, unit in NUMBER_RULE.findall(chunk.content):
            candidates[(topic, unit.lower())].append((int(amount), chunk))
    findings, emitted = [], set()
    for (topic, unit), values in candidates.items():
        for i, (left_value, left) in enumerate(values):
            for right_value, right in values[i + 1:]:
                if left_value == right_value or left.id == right.id:
                    continue
                key = tuple(sorted((left.id, right.id)))
                if key in emitted:
                    continue
                emitted.add(key)
                material = topic in {"remote", "leave", "retention"}
                findings.append(ProposedFinding(
                    FindingType.CONTRADICTION, for_finding(FindingType.CONTRADICTION, .84, material),
                    f"Potentially conflicting {topic} limits",
                    f"One passage states {left_value} {unit} while another related passage states {right_value} {unit}. The wording refers to the same topic, but scope and exceptions must be checked before concluding that the policy conflicts.",
                    .84, "Verify the authoritative rule, audience, date, and exception conditions; clarify the governing limit.", [left.id, right.id], True
                ))
    return findings

