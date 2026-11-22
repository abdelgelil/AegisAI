"""Central security, retrieval, inference, and metadata audit pipeline."""

from __future__ import annotations

import asyncio
import re
import time
from typing import Protocol
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.chunk import ChunkModel
from app.schemas.gateway import (
    AegisResponse,
    KeyValidateRequest,
    KeyValidateResponse,
    LLMExecuteRequest,
    RAGQueryRequest,
    RetrievedChunk,
)
from app.schemas.guardrail import SecurityVerdict, ThreatCategory
from app.services.embedding import embedding_service
from app.services.vector_store import similarity_search


class SecurityScanner(Protocol):
    """Interface for Ganna's inbound scanner implementation."""

    async def scan(self, text: str, requested_mode: str) -> SecurityVerdict: ...


class LLMRouter(Protocol):
    """Interface for Ziad's provider router implementation."""

    async def execute(
        self,
        request: LLMExecuteRequest,
        *,
        mode: str,
        context: str,
        provider_api_key: str | None,
    ) -> str: ...

    async def validate_key(self, request: KeyValidateRequest) -> KeyValidateResponse: ...


def _luhn_valid(number: str) -> bool:
    digits = [int(char) for char in number]
    if not 13 <= len(digits) <= 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


class DefaultSecurityScanner:
    """Standalone rules scanner; replace through the SecurityScanner protocol."""

    _injection = re.compile(
        r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|"
        r"disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions|"
        r"reveal\s+(?:the\s+)?system\s+prompt",
        re.IGNORECASE,
    )
    _card_candidate = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
    _secret = re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{30,}|"
        r"(?:api[_-]?key|secret|token)\s*[:=]\s*\S+)\b",
        re.IGNORECASE,
    )

    async def scan(self, text: str, requested_mode: str) -> SecurityVerdict:
        started = time.perf_counter()
        categories: list[ThreatCategory] = []
        if self._injection.search(text):
            categories.append(ThreatCategory.PROMPT_INJECTION)
        if self._secret.search(text):
            categories.append(ThreatCategory.API_KEY_OR_SECRET)
        for candidate in self._card_candidate.finditer(text):
            digits = re.sub(r"\D", "", candidate.group())
            if _luhn_valid(digits):
                categories.append(ThreatCategory.CREDIT_CARD)
                break

        return SecurityVerdict(
            has_sensitive_credentials=any(
                item in categories
                for item in (ThreatCategory.CREDIT_CARD, ThreatCategory.API_KEY_OR_SECRET)
            ),
            is_injection_detected=ThreatCategory.PROMPT_INJECTION in categories,
            requested_mode=requested_mode,
            enforced_mode=requested_mode,
            detected_entities=categories or [ThreatCategory.NONE],
            scanner_latency_ms=(time.perf_counter() - started) * 1000,
            message="Inbound content scanned.",
        )


class LocalLLMFallback:
    """Fallback for environments where the provider router has not been merged."""

    async def execute(
        self,
        request: LLMExecuteRequest,
        *,
        mode: str,
        context: str,
        provider_api_key: str | None,
    ) -> str:
        if mode != "local":
            raise HTTPException(status_code=503, detail="Cloud LLM router is not configured")
        from app.services.local_llm import LocalLLMService

        return await LocalLLMService(model_name=request.model).generate_response(
            context=context,
            question=request.prompt,
        )

    async def validate_key(self, request: KeyValidateRequest) -> KeyValidateResponse:
        return KeyValidateResponse(
            valid=False,
            provider=request.provider,
            message="Provider key validation is unavailable until the LLM router is configured.",
        )


security_scanner: SecurityScanner = DefaultSecurityScanner()
llm_router: LLMRouter = LocalLLMFallback()

NO_CONTEXT_ANSWER = "I could not find relevant source material to answer this question."


async def retrieve_chunks(
    db: AsyncSession,
    project_id: UUID | None,
    query: str,
    top_k: int,
    redis=None,
) -> list[tuple[ChunkModel, float]]:
    """Semantic retrieval: embed the query (Redis-cached), then cosine search.

    Returns (chunk, score) pairs, best first, scores in [0, 1]. Over-fetches so that
    poisoned chunks can be quarantined and still leave top_k clean ones.
    """
    if project_id is None:
        return []
    if redis is not None:
        vector = await embedding_service.embed_query_cached(query, redis)
    else:
        vector = await asyncio.to_thread(embedding_service.embed_text, query)
    return await similarity_search(db, project_id, vector, min(max(top_k * 4, top_k), 50))


class GatewayOrchestrator:
    async def execute_gateway_request(
        self,
        request: LLMExecuteRequest,
        db: AsyncSession,
        provider_api_key: str | None = None,
    ) -> AegisResponse:
        started = time.perf_counter()
        verdict = await security_scanner.scan(request.prompt, request.mode)
        if verdict.is_injection_detected:
            verdict.enforced_mode = request.mode
            await self._write_audit(
                db,
                request_id=uuid4(),
                verdict=verdict,
                model=request.model,
                provider=request.provider,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Request blocked by inbound security policy.",
                    "security_verdict": verdict.model_dump(mode="json"),
                },
            )

        enforced_mode = request.mode
        if verdict.has_sensitive_credentials and request.mode == "byok":
            enforced_mode = "local"
            provider_api_key = None
            verdict.auto_rerouted = True
            verdict.message = "Sensitive credentials detected; request was routed locally."
        verdict.enforced_mode = enforced_mode

        generated = await llm_router.execute(
            request,
            mode=enforced_mode,
            context="",
            provider_api_key=provider_api_key,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        await self._write_audit(
            db,
            request_id=uuid4(),
            verdict=verdict,
            model=request.model,
            provider=request.provider,
            latency_ms=latency_ms,
        )
        return AegisResponse(
            response=generated,
            security_verdict=verdict,
            latency_ms=latency_ms,
        )

    async def execute_rag_request(
        self,
        request: RAGQueryRequest,
        db: AsyncSession,
        provider_api_key: str | None = None,
        redis=None,
    ) -> AegisResponse:
        started = time.perf_counter()
        requested_mode = "byok" if provider_api_key else "local"
        verdict = await security_scanner.scan(request.query, requested_mode)
        if verdict.is_injection_detected:
            verdict.enforced_mode = requested_mode
            await self._write_audit(
                db,
                request_id=uuid4(),
                verdict=verdict,
                model=request.model or settings.LLM_MODEL_NAME,
                provider=request.provider,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Request blocked by inbound security policy.",
                    "security_verdict": verdict.model_dump(mode="json"),
                },
            )

        matches = await retrieve_chunks(db, request.project_id, request.query, request.top_k, redis)
        # Drop weak matches: irrelevant context makes a small model refuse to answer.
        matches = [(chunk, score) for chunk, score in matches if score >= settings.RAG_MIN_SCORE]
        clean_matches: list[tuple[ChunkModel, float]] = []
        for chunk, score in matches:
            if chunk.is_poisoned:
                verdict.quarantined_chunk_ids.append(str(chunk.id))
            else:
                clean_matches.append((chunk, score))
        if verdict.quarantined_chunk_ids:
            verdict.detected_entities.append(ThreatCategory.POISONED_CHUNK)
        clean_matches = clean_matches[: request.top_k]

        enforced_mode = requested_mode
        if verdict.has_sensitive_credentials and requested_mode == "byok":
            enforced_mode = "local"
            provider_api_key = None
            verdict.auto_rerouted = True
            verdict.message = "Sensitive credentials detected; request was routed locally."
        verdict.enforced_mode = enforced_mode

        context = "\n\n".join(chunk.text for chunk, _ in clean_matches)
        llm_request = LLMExecuteRequest(
            prompt=request.query,
            provider=request.provider or "ollama",
            model=request.model or settings.LLM_MODEL_NAME,
            mode=requested_mode,
        )
        if clean_matches:
            generated = await llm_router.execute(
                llm_request,
                mode=enforced_mode,
                context=context,
                provider_api_key=provider_api_key,
            )
        else:
            # Nothing relevant retrieved: do not ask the model (it would guess or refuse).
            generated = NO_CONTEXT_ANSWER
        latency_ms = (time.perf_counter() - started) * 1000
        await self._write_audit(
            db,
            request_id=uuid4(),
            verdict=verdict,
            model=llm_request.model,
            provider=llm_request.provider,
            latency_ms=latency_ms,
        )
        return AegisResponse(
            response=generated,
            security_verdict=verdict,
            retrieved_chunks=[
                RetrievedChunk(
                    chunk_id=chunk.id,
                    text=chunk.text,
                    score=score,
                    source=chunk.document_name or (chunk.metadata_json or {}).get("source_filename"),
                )
                for chunk, score in clean_matches
            ],
            latency_ms=latency_ms,
        )

    async def validate_key(self, request: KeyValidateRequest) -> KeyValidateResponse:
        return await llm_router.validate_key(request)

    @staticmethod
    async def _write_audit(
        db: AsyncSession,
        *,
        request_id: UUID,
        verdict: SecurityVerdict,
        model: str,
        provider: str | None,
        latency_ms: float,
    ) -> None:
        db.add(
            AuditLog(
                request_id=request_id,
                requested_mode=verdict.requested_mode,
                enforced_mode=verdict.enforced_mode,
                auto_rerouted=verdict.auto_rerouted,
                threat_category=next(
                    (category.value for category in verdict.detected_entities if category != ThreatCategory.NONE),
                    ThreatCategory.NONE.value,
                ),
                model_used=model,
                provider_used=provider,
                latency_ms=latency_ms,
            )
        )
        await db.commit()


orchestrator = GatewayOrchestrator()