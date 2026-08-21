from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from .models import FindingStatus


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(RegisterIn):
    pass


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class WorkspaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    description: str | None = Field(default=None, max_length=2000)


class WorkspaceOut(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    document_count: int = 0


class DocumentOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    checksum: str
    status: str
    processing_error: str | None
    page_count: int | None
    created_at: datetime


class SourceOut(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page: int | None
    section: str | None
    quoted_text: str


class FindingOut(BaseModel):
    id: str
    audit_id: str
    type: str
    severity: str
    title: str
    description: str
    confidence: float
    status: str
    recommendation: str
    is_ai_interpretation: bool
    created_at: datetime
    sources: list[SourceOut]


class FindingStatusIn(BaseModel):
    status: FindingStatus


class AuditOut(BaseModel):
    id: str
    workspace_id: str
    status: str
    progress_stage: str
    health_score: int | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None
    finding_count: int = 0


class ChatIn(BaseModel):
    workspace_id: str
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class ChatOut(BaseModel):
    answer: str
    sources: list[SourceOut]
    conversation_id: str
    mode: str


class CompareIn(BaseModel):
    document_a_id: str
    document_b_id: str


class CompareItem(BaseModel):
    classification: str
    left: SourceOut | None = None
    right: SourceOut | None = None
    explanation: str

