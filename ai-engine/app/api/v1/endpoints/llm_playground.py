"""Interactive prompt endpoint for testing local LLMs from Swagger UI."""

import time

from fastapi import APIRouter, HTTPException, status

from app.schemas.playground import PromptRequest, PromptResponse
from app.services.local_llm import LocalLLMService


router = APIRouter()


@router.post(
    "/prompt",
    response_model=PromptResponse,
    summary="Run a prompt against a local LLM",
    description="Send an ad hoc prompt to an Ollama model and return its response.",
    responses={503: {"description": "The LLM backend is unavailable, timed out, or rejected the request."}},
)
async def run_prompt(payload: PromptRequest) -> PromptResponse:
    """Generate a response using the requested Ollama model."""
    started = time.perf_counter()
    try:
        llm_service = LocalLLMService(model_name=payload.model)
        generated = await llm_service.generate_response(context="", question=payload.prompt)
    except Exception as exc:
        # Ollama client errors include connection failures, timeouts, and missing models.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM backend unavailable or unable to generate a response: {exc}",
        ) from exc

    elapsed_ms = (time.perf_counter() - started) * 1000
    return PromptResponse(response=generated, latency_ms=elapsed_ms)
