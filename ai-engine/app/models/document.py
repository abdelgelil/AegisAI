from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base

class DocumentModel(Base):
    __tablename__ = "document"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    status = Column(String, default="UPLOADED")
    quality_score = Column(Float, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("DocumentChunkModel", back_populates="document", cascade="all, delete-orphan")


class DocumentChunkModel(Base):
    __tablename__ = "document_chunk"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("document.id"), nullable=False)
    text = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    section = Column(String, nullable=True)
    embedding_id = Column(String, nullable=True)  # Reference for vector store

    document = relationship("DocumentModel", back_populates="chunks")


class InferenceTraceModel(Base):
    __tablename__ = "inference_trace"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    model_name = Column(String, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    gate_decision = Column(String, default="PASS")
    block_reason = Column(String, nullable=True)
    context_relevance = Column(Float, nullable=False)
    groundedness = Column(Float, nullable=False)
    answer_relevance = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)