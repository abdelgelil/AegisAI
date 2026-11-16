"""Persistent pgvector-backed document chunks used by ingestion and RAG."""

from datetime import datetime
from typing import Any
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, false, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, synonym

from app.core.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("project_id", "source_key", name="uq_chunk_project_source_key"),
        UniqueConstraint("project_id", "content_hash", name="uq_chunk_project_content_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    document_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    content = synonym("text")
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=False)
    is_poisoned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# Preserve the name used by ingestion and retrieval services.
ChunkModel = DocumentChunk
