"""Strict API contracts for document-backed RAG queries."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RAGQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    project_id: UUID = Field(alias="projectId", description="Project UUID used to scope retrieval")
    query: str = Field(min_length=1, max_length=8000)
    top_k: int = Field(default=5, alias="topK", ge=1, le=50)


class EvaluationScores(BaseModel):
    context_relevance: float = Field(ge=0, le=1)
    faithfulness: float = Field(ge=0, le=1)
    answer_relevance: float = Field(ge=0, le=1)


class Citation(BaseModel):
    chunk_id: UUID
    source_filename: str
    page_number: Optional[int] = None
    section_header: Optional[str] = None
    text: str
    score: float = Field(ge=0, le=1)


class RAGQueryResponse(BaseModel):
    project_id: UUID = Field(serialization_alias="projectId")
    query: str
    answer: str
    citations: list[Citation]
    evaluation: EvaluationScores
    gate_decision: str = Field(serialization_alias="gateDecision")
    block_reason: str | None = Field(default=None, serialization_alias="blockReason")
    correction_attempts: int = Field(serialization_alias="correctionAttempts")
    model_name: str = Field(serialization_alias="modelName")
    latency_ms: float = Field(serialization_alias="latencyMs")
    created_at: datetime = Field(serialization_alias="createdAt")
