"""HTTP endpoints for direct gateway execution and telemetry."""

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.audit import AuditLog
from app.schemas.gateway import (
    KeyValidateRequest,
    KeyValidateResponse,
    LLMExecuteRequest,
    AegisResponse,
)
from app.services.orchestrator import orchestrator


router = APIRouter()


@router.post("/llm/execute", response_model=AegisResponse)
async def execute_llm(
    payload: LLMExecuteRequest,
    db: AsyncSession = Depends(get_db),
    provider_api_key: str | None = Header(default=None, alias="X-Provider-Api-Key"),
) -> AegisResponse:
    return await orchestrator.execute_gateway_request(payload, db, provider_api_key)


@router.post("/llm/validate-key", response_model=KeyValidateResponse)
async def validate_key(payload: KeyValidateRequest) -> KeyValidateResponse:
    return await orchestrator.validate_key(payload)


@router.get("/audit/logs")
async def get_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, object]]:
    result = await db.execute(select(AuditLog).order_by(AuditLog.request_id.desc()).limit(limit))
    return [
        {
            "request_id": str(row.request_id),
            "requested_mode": row.requested_mode,
            "enforced_mode": row.enforced_mode,
            "auto_rerouted": row.auto_rerouted,
            "threat_category": row.threat_category,
            "model_used": row.model_used,
            "provider_used": row.provider_used,
            "faithfulness_score": row.faithfulness_score,
            "latency_ms": row.latency_ms,
        }
        for row in result.scalars().all()
    ]
