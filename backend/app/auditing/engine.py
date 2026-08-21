import logging
from sqlalchemy.orm import Session
from . import ambiguity_detector, clause_detector, contradiction_detector, duplicate_detector, missing_info_detector, reference_detector, terminology_detector
from .severity import health_score
from .types import ProposedFinding
from ..models import AuditFinding, AuditRun, AuditStatus, FindingSource, Document, DocumentChunk, now

logger = logging.getLogger(__name__)


def run_audit(db: Session, audit: AuditRun) -> AuditRun:
    audit.status = AuditStatus.RUNNING
    audit.progress_stage = "Preparing documents"
    db.commit()
    try:
        from ..models import DocumentStatus
        chunks = db.query(DocumentChunk).join(Document).filter(Document.workspace_id == audit.workspace_id, Document.status == DocumentStatus.READY).all()
        if not chunks:
            raise ValueError("No processed documents are ready to audit.")
        stages = [
            ("Analyzing sections", [clause_detector.detect, ambiguity_detector.detect]),
            ("Checking contradictions", [contradiction_detector.detect]),
            ("Checking references", [reference_detector.detect]),
            ("Checking terminology and duplicates", [terminology_detector.detect, duplicate_detector.detect, missing_info_detector.detect]),
        ]
        proposals: list[ProposedFinding] = []
        for stage, detectors in stages:
            audit.progress_stage = stage
            db.commit()
            for detector in detectors:
                proposals.extend(detector(chunks))
        audit.progress_stage = "Generating findings"
        db.commit()
        for proposed in proposals:
            finding = AuditFinding(
                audit_id=audit.id, workspace_id=audit.workspace_id, type=proposed.type, severity=proposed.severity,
                title=proposed.title, description=proposed.description, confidence=proposed.confidence,
                recommendation=proposed.recommendation, is_ai_interpretation=proposed.ai_interpretation,
            )
            db.add(finding); db.flush()
            for chunk_id in proposed.chunk_ids:
                chunk = db.get(DocumentChunk, chunk_id)
                if chunk:
                    db.add(FindingSource(finding_id=finding.id, chunk_id=chunk.id, quoted_text=chunk.content[:1200]))
        db.flush()
        generated = db.query(AuditFinding).filter_by(audit_id=audit.id).all()
        audit.health_score = health_score(generated)
        audit.status = AuditStatus.COMPLETED
        audit.progress_stage = "Finalizing report"
        audit.completed_at = now()
        db.commit()
        logger.info("audit_completed audit_id=%s findings=%s", audit.id, len(generated))
    except Exception as exc:
        audit.status = AuditStatus.FAILED
        audit.error = str(exc)
        audit.progress_stage = "Failed"
        db.commit()
        logger.exception("audit_failed audit_id=%s", audit.id)
    return audit
