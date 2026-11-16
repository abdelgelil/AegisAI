"""Shared request and response contracts for the AI security gateway."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.guardrail import SecurityVerdict


class _GatewayModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class LLMExecuteRequest(_GatewayModel):
    prompt: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    mode: str = "cloud"


class KeyValidateRequest(_GatewayModel):
    provider: str = Field(min_length=1)
    api_key: str = Field(min_length=1)


class KeyValidateResponse(_GatewayModel):
    valid: bool
    provider: str
    message: str = ""


class RetrievedChunk(_GatewayModel):
    chunk_id: UUID
    text: str
    score: float = Field(ge=0, le=1)
    source: str | None = None


class RAGQueryRequest(_GatewayModel):
    query: str = Field(min_length=1, max_length=8000)
    project_id: UUID | None = Field(default=None, alias="projectId")
    top_k: int = Field(default=5, alias="topK", ge=1, le=50)
    provider: str | None = None
    model: str | None = None


class AegisResponse(_GatewayModel):
    response: str
    security_verdict: SecurityVerdict
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    latency_ms: float = Field(ge=0)


class AegisRAGResponse(AegisResponse):
    """Gateway result plus legacy RAG fields for existing clients."""

    query: str
    answer: str
    citations: list[dict[str, object]] = Field(default_factory=list)
    evaluation: dict[str, float | None] = Field(default_factory=dict)
    gate_decision: str = Field(serialization_alias="gateDecision")
    block_reason: str | None = Field(default=None, serialization_alias="blockReason")
    correction_attempts: int = Field(default=0, serialization_alias="correctionAttempts")
    model_name: str = Field(serialization_alias="modelName")
    created_at: datetime = Field(serialization_alias="createdAt")
