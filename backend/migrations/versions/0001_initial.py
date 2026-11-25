"""initial RAG Document Auditor schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def uid_column():
    return sa.Column("id", sa.String(length=36), primary_key=True, nullable=False)


def upgrade() -> None:
    op.create_table("users", uid_column(), sa.Column("email", sa.String(255), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("workspaces", uid_column(), sa.Column("name", sa.String(140), nullable=False), sa.Column("description", sa.Text()), sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])
    op.create_table("workspace_members", uid_column(), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("role", sa.String(30), nullable=False), sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"))
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"]); op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])
    op.create_table("documents", uid_column(), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False), sa.Column("filename", sa.String(255), nullable=False), sa.Column("content_type", sa.String(100), nullable=False), sa.Column("size_bytes", sa.Integer(), nullable=False), sa.Column("checksum", sa.String(64), nullable=False), sa.Column("storage_path", sa.String(500), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("processing_error", sa.Text()), sa.Column("extracted_text", sa.Text()), sa.Column("page_count", sa.Integer()), sa.Column("document_metadata", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"]); op.create_index("ix_documents_checksum", "documents", ["checksum"])
    op.create_table("document_chunks", uid_column(), sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False), sa.Column("chunk_index", sa.Integer(), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("page", sa.Integer()), sa.Column("section", sa.String(300)), sa.Column("metadata_json", sa.JSON(), nullable=False))
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"]); op.create_index("ix_document_chunks_workspace_id", "document_chunks", ["workspace_id"])
    op.create_table("audit_runs", uid_column(), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("progress_stage", sa.String(120), nullable=False), sa.Column("health_score", sa.Integer()), sa.Column("error", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_audit_runs_workspace_id", "audit_runs", ["workspace_id"])
    op.create_table("audit_findings", uid_column(), sa.Column("audit_id", sa.String(36), sa.ForeignKey("audit_runs.id"), nullable=False), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False), sa.Column("type", sa.String(50), nullable=False), sa.Column("severity", sa.String(20), nullable=False), sa.Column("title", sa.String(300), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("recommendation", sa.Text(), nullable=False), sa.Column("is_ai_interpretation", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for name, column in (("ix_audit_findings_audit_id", "audit_id"), ("ix_audit_findings_workspace_id", "workspace_id"), ("ix_audit_findings_type", "type"), ("ix_audit_findings_severity", "severity"), ("ix_audit_findings_status", "status")):
        op.create_index(name, "audit_findings", [column])
    op.create_table("finding_sources", uid_column(), sa.Column("finding_id", sa.String(36), sa.ForeignKey("audit_findings.id"), nullable=False), sa.Column("chunk_id", sa.String(36), sa.ForeignKey("document_chunks.id"), nullable=False), sa.Column("quoted_text", sa.Text(), nullable=False))
    op.create_index("ix_finding_sources_finding_id", "finding_sources", ["finding_id"]); op.create_index("ix_finding_sources_chunk_id", "finding_sources", ["chunk_id"])
    op.create_table("conversations", uid_column(), sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False), sa.Column("title", sa.String(250), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"]); op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_table("messages", uid_column(), sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id"), nullable=False), sa.Column("role", sa.String(20), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("sources_json", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])


def downgrade() -> None:
    for table in ["messages", "conversations", "finding_sources", "audit_findings", "audit_runs", "document_chunks", "documents", "workspace_members", "workspaces", "users"]:
        op.drop_table(table)
