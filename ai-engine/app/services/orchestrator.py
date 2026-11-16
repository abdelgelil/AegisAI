"""Central security, retrieval, inference, and metadata audit pipeline."""

from __future__ import annotations

import re
import time
from typing import Protocol, Sequence
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
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


async def retrieve_chunks(
    db: AsyncSession, project_id: UUID | None, top_k: int
) -> Sequence[ChunkModel]:
    """Load a bounded set of project chunks; callers quarantine poisoned rows."""
    if project_id is None:
        return []
    result = await db.execute(
        select(ChunkModel)
        .where(ChunkModel.project_id == project_id)
        .limit(min(max(top_k * 4, top_k), 200))
    )
    return result.scalars().all()


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

        chunks = await retrieve_chunks(db, request.project_id, request.top_k)
        clean_chunks: list[ChunkModel] = []
        for chunk in chunks:
            if chunk.is_poisoned:
                verdict.quarantined_chunk_ids.append(str(chunk.id))
            else:
                clean_chunks.append(chunk)
        if verdict.quarantined_chunk_ids:
            verdict.detected_entities.append(ThreatCategory.POISONED_CHUNK)
        clean_chunks = clean_chunks[: request.top_k]

        enforced_mode = requested_mode
        if verdict.has_sensitive_credentials and requested_mode == "byok":
            enforced_mode = "local"
            provider_api_key = None
            verdict.auto_rerouted = True
            verdict.message = "Sensitive credentials detected; request was routed locally."
        verdict.enforced_mode = enforced_mode

        context = "\n\n".join(chunk.text for chunk in clean_chunks)
        llm_request = LLMExecuteRequest(
            prompt=request.query,
            provider=request.provider or "ollama",
            model=request.model or settings.LLM_MODEL_NAME,
            mode=requested_mode,
        )
        generated = await llm_router.execute(
            llm_request,
            mode=enforced_mode,
            context=context,
            provider_api_key=provider_api_key,
        )
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
                    score=1.0,
                    source=chunk.document_name,
                )
                for chunk in clean_chunks
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
