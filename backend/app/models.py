import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentStatus(str, enum.Enum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"


class AuditStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FindingType(str, enum.Enum):
    CONTRADICTION = "CONTRADICTION"
    MISSING_INFORMATION = "MISSING_INFORMATION"
    DUPLICATE_CONTENT = "DUPLICATE_CONTENT"
    TERMINOLOGY_INCONSISTENCY = "TERMINOLOGY_INCONSISTENCY"
    AMBIGUOUS_STATEMENT = "AMBIGUOUS_STATEMENT"
    OUTDATED_REFERENCE = "OUTDATED_REFERENCE"
    BROKEN_REFERENCE = "BROKEN_REFERENCE"
    IMPORTANT_CLAUSE = "IMPORTANT_CLAUSE"


class Severity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingStatus(str, enum.Enum):
    OPEN = "OPEN"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(140))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    documents: Mapped[list["Document"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(30), default="owner")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    storage_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.UPLOADING)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    workspace: Mapped[Workspace] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(300), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    document: Mapped[Document] = relationship(back_populates="chunks")


class AuditRun(Base):
    __tablename__ = "audit_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    status: Mapped[AuditStatus] = mapped_column(Enum(AuditStatus), default=AuditStatus.PENDING)
    progress_stage: Mapped[str] = mapped_column(String(120), default="Queued")
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    findings: Mapped[list["AuditFinding"]] = relationship(back_populates="audit", cascade="all, delete-orphan")


class AuditFinding(Base):
    __tablename__ = "audit_findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audit_runs.id"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    type: Mapped[FindingType] = mapped_column(Enum(FindingType), index=True)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[FindingStatus] = mapped_column(Enum(FindingStatus), default=FindingStatus.OPEN, index=True)
    recommendation: Mapped[str] = mapped_column(Text)
    is_ai_interpretation: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    audit: Mapped[AuditRun] = relationship(back_populates="findings")
    sources: Mapped[list["FindingSource"]] = relationship(back_populates="finding", cascade="all, delete-orphan")


class FindingSource(Base):
    __tablename__ = "finding_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    finding_id: Mapped[str] = mapped_column(ForeignKey("audit_findings.id"), index=True)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("document_chunks.id"), index=True)
    quoted_text: Mapped[str] = mapped_column(Text)
    finding: Mapped[AuditFinding] = relationship(back_populates="sources")
    chunk: Mapped[DocumentChunk] = relationship()


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(250), default="New conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    sources_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
