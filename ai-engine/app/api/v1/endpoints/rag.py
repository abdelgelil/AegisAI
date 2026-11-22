"""Gateway RAG endpoint, retaining the legacy response fields."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.schemas.gateway import AegisRAGResponse, RAGQueryRequest
from app.services.orchestrator import orchestrator


router = APIRouter()


@router.post("/query", response_model=AegisRAGResponse)
async def query_rag(
    payload: RAGQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    provider_api_key: str | None = Header(default=None, alias="X-Provider-Api-Key"),
) -> AegisRAGResponse:
    """Run guarded retrieval while preserving fields consumed by legacy clients."""
    result = await orchestrator.execute_rag_request(
        payload,
        db,
        provider_api_key,
        redis=getattr(request.app.state, "redis", None),
    )
    citations = [
        {
            "chunk_id": str(chunk.chunk_id),
            "source_filename": chunk.source or "unknown",
            "page_number": None,
            "section_header": None,
            "text": chunk.text,
            "score": chunk.score,
        }
        for chunk in result.retrieved_chunks
    ]
    return AegisRAGResponse(
        response=result.response,
        security_verdict=result.security_verdict,
        retrieved_chunks=result.retrieved_chunks,
        latency_ms=result.latency_ms,
        query=payload.query,
        answer=result.response,
        citations=citations,
        evaluation={"context_relevance": None, "faithfulness": None, "answer_relevance": None},
        gate_decision="NOT_EVALUATED",
        block_reason=None,
        correction_attempts=0,
        model_name=payload.model or settings.LLM_MODEL_NAME,
        created_at=datetime.now(timezone.utc),
    )