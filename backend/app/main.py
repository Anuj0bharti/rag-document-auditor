import hashlib
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Annotated
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from .auth import create_access_token, get_current_user, hash_password, require_workspace, verify_password
from .auditing.engine import run_audit
from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .ingestion.extractors import SUPPORTED_EXTENSIONS
from .ingestion.service import process_document
from .logging_config import configure_logging
from .models import AuditFinding, AuditRun, AuditStatus, Conversation, Document, DocumentChunk, DocumentStatus, FindingSource, FindingStatus, Message, User, Workspace, WorkspaceMember
from .rag.pipeline import answer_question
from .rag.vector_store import get_vector_store
from .reports import build_pdf
from .schemas import AuditOut, ChatIn, ChatOut, CompareIn, CompareItem, DocumentOut, FindingOut, FindingStatusIn, LoginIn, RegisterIn, SourceOut, TokenOut, WorkspaceIn, WorkspaceOut

configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI(title="RAG Document Auditor API", version="1.0.0", description="Evidence-first document auditing and local RAG.")
app.add_middleware(CORSMiddleware, allow_origins=[item.strip() for item in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    if settings.database_url.startswith("sqlite"):
        Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    settings.upload_path


def workspace_out(workspace: Workspace, document_count: int = 0) -> WorkspaceOut:
    return WorkspaceOut(id=workspace.id, name=workspace.name, description=workspace.description, created_at=workspace.created_at, document_count=document_count)


def document_out(document: Document) -> DocumentOut:
    return DocumentOut(id=document.id, filename=document.filename, content_type=document.content_type, size_bytes=document.size_bytes, checksum=document.checksum, status=document.status.value, processing_error=document.processing_error, page_count=document.page_count, created_at=document.created_at)


def source_out(source: FindingSource | DocumentChunk, quote: str | None = None) -> SourceOut:
    chunk = source.chunk if isinstance(source, FindingSource) else source
    return SourceOut(chunk_id=chunk.id, document_id=chunk.document_id, filename=chunk.document.filename, page=chunk.page, section=chunk.section, quoted_text=quote or (source.quoted_text if isinstance(source, FindingSource) else chunk.content))


def finding_out(finding: AuditFinding) -> FindingOut:
    return FindingOut(id=finding.id, audit_id=finding.audit_id, type=finding.type.value, severity=finding.severity.value, title=finding.title, description=finding.description, confidence=finding.confidence, status=finding.status.value, recommendation=finding.recommendation, is_ai_interpretation=finding.is_ai_interpretation, created_at=finding.created_at, sources=[source_out(source) for source in finding.sources])


def audit_out(audit: AuditRun) -> AuditOut:
    return AuditOut(id=audit.id, workspace_id=audit.workspace_id, status=audit.status.value, progress_stage=audit.progress_stage, health_score=audit.health_score, error=audit.error, created_at=audit.created_at, completed_at=audit.completed_at, finding_count=len(audit.findings))


def background_process(document_id: str):
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc:
            process_document(db, doc)
    finally:
        db.close()


def background_audit(audit_id: str):
    db = SessionLocal()
    try:
        audit = db.get(AuditRun, audit_id)
        if audit:
            run_audit(db, audit)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "llm_mode": settings.llm_mode, "qdrant_configured": bool(settings.qdrant_url)}


@app.post("/api/auth/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn, db: Annotated[Session, Depends(get_db)]):
    if db.query(User).filter(func.lower(User.email) == payload.email.lower()).first():
        raise HTTPException(409, "An account with this email already exists.")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id))


@app.post("/api/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    return TokenOut(access_token=create_access_token(user.id))


@app.get("/api/workspaces", response_model=list[WorkspaceOut])
def list_workspaces(user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    rows = db.query(Workspace, func.count(Document.id)).join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id).outerjoin(Document, Document.workspace_id == Workspace.id).filter(WorkspaceMember.user_id == user.id).group_by(Workspace.id).order_by(Workspace.created_at.desc()).all()
    return [workspace_out(workspace, count) for workspace, count in rows]


@app.post("/api/workspaces", response_model=WorkspaceOut, status_code=201)
def create_workspace(payload: WorkspaceIn, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    workspace = Workspace(name=payload.name.strip(), description=payload.description, owner_id=user.id)
    db.add(workspace); db.flush(); db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner")); db.commit(); db.refresh(workspace)
    return workspace_out(workspace)


@app.get("/api/workspaces/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(workspace_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    workspace = require_workspace(db, workspace_id, user)
    return workspace_out(workspace, db.query(Document).filter_by(workspace_id=workspace.id).count())


@app.get("/api/workspaces/{workspace_id}/documents", response_model=list[DocumentOut])
def list_documents(workspace_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    require_workspace(db, workspace_id, user)
    return [document_out(item) for item in db.query(Document).filter_by(workspace_id=workspace_id).order_by(Document.created_at.desc()).all()]


@app.post("/api/workspaces/{workspace_id}/documents", response_model=DocumentOut, status_code=201)
def upload_document(workspace_id: str, background: BackgroundTasks, file: Annotated[UploadFile, File(...)], user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    require_workspace(db, workspace_id, user)
    raw_name = Path(file.filename or "document").name
    if not raw_name or raw_name != file.filename or ".." in raw_name:
        raise HTTPException(400, "Invalid filename.")
    extension = Path(raw_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(415, "Unsupported file. Upload PDF, DOCX, TXT, or Markdown.")
    content = file.file.read()
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"File exceeds the {settings.max_file_size_mb} MB limit.")
    checksum = hashlib.sha256(content).hexdigest()
    duplicate = db.query(Document).filter_by(workspace_id=workspace_id, checksum=checksum).first()
    if duplicate:
        raise HTTPException(409, f"This document is already uploaded as {duplicate.filename}.")
    storage_name = f"{checksum}{extension}"
    stored_path = settings.upload_path / storage_name
    stored_path.write_bytes(content)
    document = Document(workspace_id=workspace_id, filename=raw_name, content_type=file.content_type or "application/octet-stream", size_bytes=len(content), checksum=checksum, storage_path=str(stored_path), status=DocumentStatus.UPLOADING)
    db.add(document); db.commit(); db.refresh(document)
    background.add_task(background_process, document.id)
    return document_out(document)


@app.post("/api/workspaces/{workspace_id}/documents/{document_id}/process", response_model=DocumentOut)
def process_document_endpoint(workspace_id: str, document_id: str, background: BackgroundTasks, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    require_workspace(db, workspace_id, user)
    document = db.query(Document).filter_by(id=document_id, workspace_id=workspace_id).first()
    if not document:
        raise HTTPException(404, "Document not found.")
    if document.status in {DocumentStatus.PROCESSING, DocumentStatus.INDEXING}:
        raise HTTPException(409, "Document is already being processed.")
    background.add_task(background_process, document.id)
    return document_out(document)


@app.delete("/api/documents/{document_id}", status_code=204)
def delete_document(document_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found.")
    require_workspace(db, document.workspace_id, user)
    get_vector_store().delete_document(document.id)
    try:
        Path(document.storage_path).unlink(missing_ok=True)
    except OSError:
        logger.warning("could_not_delete_file document_id=%s", document.id)
    db.delete(document); db.commit()


@app.post("/api/workspaces/{workspace_id}/audit", response_model=AuditOut, status_code=202)
def create_audit(workspace_id: str, background: BackgroundTasks, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    require_workspace(db, workspace_id, user)
    if not db.query(Document).filter_by(workspace_id=workspace_id, status=DocumentStatus.READY).first():
        raise HTTPException(409, "Process at least one document before running an audit.")
    audit = AuditRun(workspace_id=workspace_id, status=AuditStatus.PENDING, progress_stage="Queued")
    db.add(audit); db.commit(); db.refresh(audit)
    background.add_task(background_audit, audit.id)
    return audit_out(audit)


@app.get("/api/workspaces/{workspace_id}/audits", response_model=list[AuditOut])
def list_audits(workspace_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    require_workspace(db, workspace_id, user)
    return [audit_out(item) for item in db.query(AuditRun).options(joinedload(AuditRun.findings)).filter_by(workspace_id=workspace_id).order_by(AuditRun.created_at.desc()).all()]


@app.get("/api/audits/{audit_id}", response_model=AuditOut)
def get_audit(audit_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    audit = db.query(AuditRun).options(joinedload(AuditRun.findings)).filter_by(id=audit_id).first()
    if not audit: raise HTTPException(404, "Audit not found.")
    require_workspace(db, audit.workspace_id, user)
    return audit_out(audit)


@app.get("/api/audits/{audit_id}/findings", response_model=list[FindingOut])
def audit_findings(audit_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    audit = db.get(AuditRun, audit_id)
    if not audit: raise HTTPException(404, "Audit not found.")
    require_workspace(db, audit.workspace_id, user)
    findings = db.query(AuditFinding).options(joinedload(AuditFinding.sources).joinedload(FindingSource.chunk).joinedload(DocumentChunk.document)).filter_by(audit_id=audit_id).order_by(AuditFinding.created_at.desc()).all()
    return [finding_out(item) for item in findings]


@app.get("/api/workspaces/{workspace_id}/findings", response_model=list[FindingOut])
def list_findings(workspace_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)], severity: str | None = None, type: str | None = None, finding_status: str | None = Query(None, alias="status"), search: str | None = None, min_confidence: float | None = Query(None, ge=0, le=1)):
    require_workspace(db, workspace_id, user)
    query = db.query(AuditFinding).options(joinedload(AuditFinding.sources).joinedload(FindingSource.chunk).joinedload(DocumentChunk.document)).filter_by(workspace_id=workspace_id)
    if severity: query = query.filter(AuditFinding.severity == severity)
    if type: query = query.filter(AuditFinding.type == type)
    if finding_status: query = query.filter(AuditFinding.status == finding_status)
    if min_confidence is not None: query = query.filter(AuditFinding.confidence >= min_confidence)
    if search: query = query.filter(AuditFinding.title.ilike(f"%{search}%") | AuditFinding.description.ilike(f"%{search}%"))
    return [finding_out(item) for item in query.order_by(AuditFinding.created_at.desc()).all()]


@app.patch("/api/findings/{finding_id}", response_model=FindingOut)
def update_finding(finding_id: str, payload: FindingStatusIn, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    finding = db.query(AuditFinding).options(joinedload(AuditFinding.sources).joinedload(FindingSource.chunk).joinedload(DocumentChunk.document)).filter_by(id=finding_id).first()
    if not finding: raise HTTPException(404, "Finding not found.")
    require_workspace(db, finding.workspace_id, user)
    finding.status = payload.status; db.commit(); db.refresh(finding)
    return finding_out(finding)


@app.get("/api/chunks/{chunk_id}", response_model=SourceOut)
def get_chunk(chunk_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    chunk = db.query(DocumentChunk).options(joinedload(DocumentChunk.document)).filter_by(id=chunk_id).first()
    if not chunk: raise HTTPException(404, "Source passage not found.")
    require_workspace(db, chunk.workspace_id, user)
    return source_out(chunk)


@app.post("/api/chat", response_model=ChatOut)
def chat(payload: ChatIn, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    require_workspace(db, payload.workspace_id, user)
    conversation = db.get(Conversation, payload.conversation_id) if payload.conversation_id else None
    if conversation and (conversation.workspace_id != payload.workspace_id or conversation.user_id != user.id):
        raise HTTPException(404, "Conversation not found.")
    if not conversation:
        conversation = Conversation(workspace_id=payload.workspace_id, user_id=user.id, title=payload.question[:80])
        db.add(conversation); db.flush()
    answer, hits = answer_question(db, payload.workspace_id, payload.question)
    sources = [source_out(chunk, chunk.content[:1200]) for chunk, _ in hits]
    db.add_all([Message(conversation_id=conversation.id, role="user", content=payload.question), Message(conversation_id=conversation.id, role="assistant", content=answer, sources_json=[item.model_dump() for item in sources])])
    db.commit()
    return ChatOut(answer=answer, sources=sources, conversation_id=conversation.id, mode=settings.llm_mode)


@app.get("/api/workspaces/{workspace_id}/conversations")
def conversations(workspace_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    require_workspace(db, workspace_id, user)
    return [{"id": item.id, "title": item.title, "created_at": item.created_at} for item in db.query(Conversation).filter_by(workspace_id=workspace_id, user_id=user.id).all()]


def _overlap(left: str, right: str) -> float:
    tokens = lambda value: set(re.findall(r"[a-z]{3,}", value.lower()))
    a, b = tokens(left), tokens(right)
    return len(a & b) / (len(a | b) or 1)


@app.post("/api/compare", response_model=list[CompareItem])
def compare(payload: CompareIn, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    first, second = db.get(Document, payload.document_a_id), db.get(Document, payload.document_b_id)
    if not first or not second or first.workspace_id != second.workspace_id:
        raise HTTPException(400, "Choose two documents in the same workspace.")
    require_workspace(db, first.workspace_id, user)
    if first.status != DocumentStatus.READY or second.status != DocumentStatus.READY:
        raise HTTPException(409, "Both documents must be processed before comparison.")
    left_chunks = db.query(DocumentChunk).options(joinedload(DocumentChunk.document)).filter_by(document_id=first.id).all()
    right_chunks = db.query(DocumentChunk).options(joinedload(DocumentChunk.document)).filter_by(document_id=second.id).all()
    output, paired = [], set()
    for left in left_chunks:
        candidates = [(right, _overlap(left.content, right.content)) for right in right_chunks]
        if not candidates: output.append(CompareItem(classification="REMOVED", left=source_out(left), explanation="No corresponding section was detected in the second document.")); continue
        right, score = max(candidates, key=lambda pair: pair[1])
        if score < .18:
            output.append(CompareItem(classification="REMOVED", left=source_out(left), explanation="No semantically similar section was detected in the second document."))
        else:
            paired.add(right.id)
            category = "UNCHANGED" if score > .88 else "MODIFIED"
            explanation = "Sections are substantially similar." if category == "UNCHANGED" else "Sections address similar content but have material wording changes. Review both passages."
            output.append(CompareItem(classification=category, left=source_out(left), right=source_out(right), explanation=explanation))
    for right in right_chunks:
        if right.id not in paired:
            output.append(CompareItem(classification="ADDED", right=source_out(right), explanation="No corresponding section was detected in the first document."))
    return output


@app.get("/api/audits/{audit_id}/report.pdf")
def report_pdf(audit_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    audit = db.query(AuditRun).options(joinedload(AuditRun.findings).joinedload(AuditFinding.sources)).filter_by(id=audit_id).first()
    if not audit: raise HTTPException(404, "Audit not found.")
    workspace = require_workspace(db, audit.workspace_id, user)
    documents = db.query(Document).filter_by(workspace_id=workspace.id).all()
    pdf = build_pdf(workspace, audit, audit.findings, documents)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="audit-{audit.id}.pdf"'})


@app.get("/api/audits/{audit_id}/report.json")
def report_json(audit_id: str, user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    audit = db.query(AuditRun).options(joinedload(AuditRun.findings).joinedload(AuditFinding.sources).joinedload(FindingSource.chunk).joinedload(DocumentChunk.document)).filter_by(id=audit_id).first()
    if not audit: raise HTTPException(404, "Audit not found.")
    require_workspace(db, audit.workspace_id, user)
    return {"audit": audit_out(audit).model_dump(mode="json"), "findings": [finding_out(item).model_dump(mode="json") for item in audit.findings], "disclaimer": "AI-assisted analysis; verify findings against original documents."}
