"""RAG query endpoint backed by pgvector and the correction workflow."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.schemas.rag import Citation, EvaluationScores, RAGQueryRequest, RAGQueryResponse
from app.services.evaluator import EvaluationError
from app.services.rag_workflow import RAGWorkflow
from app.services.vector_store import VectorStoreError


router = APIRouter()
workflow = RAGWorkflow()


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(payload: RAGQueryRequest, db: AsyncSession = Depends(get_db)) -> RAGQueryResponse:
    """Retrieve, generate, evaluate, and correct an answer with source citations."""
    started = time.perf_counter()
    try:
        state = await workflow.run(db, payload.project_id, payload.query, payload.top_k)
    except (EvaluationError, VectorStoreError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        # Keep external service and SQL details out of the client response.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG service is temporarily unavailable",
        ) from exc

    try:
        scores = EvaluationScores(**state.get("scores", {}))
        citations = [Citation(**item) for item in state.get("retrieved", [])]
    except Exception as exc:
        raise HTTPException(status_code=500, detail="RAG workflow returned an invalid response") from exc

    return RAGQueryResponse(
        project_id=payload.project_id,
        query=payload.query,
        answer=state.get("answer", ""),
        citations=citations,
        evaluation=scores,
        gate_decision=state.get("gate_decision", "BLOCK"),
        block_reason=state.get("block_reason"),
        correction_attempts=state.get("retry_count", 0),
        model_name=settings.LLM_MODEL_NAME,
        latency_ms=(time.perf_counter() - started) * 1000,
        created_at=datetime.now(timezone.utc),
    )
