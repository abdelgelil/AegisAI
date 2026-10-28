"""Interactive prompt endpoint for testing local LLMs from Swagger UI."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.rag import Citation, EvaluationScores, RAGQueryResponse
from app.schemas.playground import PromptRequest, PromptResponse
from app.services.evaluator import EvaluationError
from app.services.local_llm import LocalLLMService
from app.services.rag_workflow import RAGWorkflow
from app.services.vector_store import VectorStoreError


router = APIRouter()
rag_workflow = RAGWorkflow()


@router.post(
    "/prompt",
    response_model=PromptResponse | RAGQueryResponse,
    summary="Run a prompt against a local LLM",
    description="Send an ad hoc prompt to an Ollama model and return its response.",
    responses={503: {"description": "The LLM backend is unavailable, timed out, or rejected the request."}},
)
async def run_prompt(
    payload: PromptRequest,
    db: AsyncSession = Depends(get_db),
) -> PromptResponse | RAGQueryResponse:
    """Generate directly, or run project-scoped RAG when project_id is supplied."""
    started = time.perf_counter()
    try:
        if payload.project_id is not None:
            state = await rag_workflow.run(db, payload.project_id, payload.prompt, payload.top_k)
            scores = EvaluationScores(**state.get("scores", {}))
            citations = [Citation(**item) for item in state.get("retrieved", [])]
            return RAGQueryResponse(
                project_id=payload.project_id,
                query=payload.prompt,
                answer=state.get("answer", ""),
                citations=citations,
                evaluation=scores,
                gate_decision=state.get("gate_decision", "BLOCK"),
                block_reason=state.get("block_reason"),
                correction_attempts=state.get("retry_count", 0),
                model_name=payload.model,
                latency_ms=(time.perf_counter() - started) * 1000,
                created_at=datetime.now(timezone.utc),
            )
        llm_service = LocalLLMService(model_name=payload.model)
        generated = await llm_service.generate_response(context="", question=payload.prompt)
    except (EvaluationError, VectorStoreError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        # Ollama client errors include connection failures, timeouts, and missing models.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM backend unavailable or unable to generate a response: {exc}",
        ) from exc

    elapsed_ms = (time.perf_counter() - started) * 1000
    return PromptResponse(response=generated, latency_ms=elapsed_ms)
