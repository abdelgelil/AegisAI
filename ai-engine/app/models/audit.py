"""Request audit metadata. Never persist credentials or raw personal data.

Table is gateway_audit_logs, NOT audit_logs. The ERD's audit_logs is an
org/user action trail (org_id and action are required); this model records
per-request gateway metadata and has a different shape.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "gateway_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    requested_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    enforced_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    auto_rerouted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    threat_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    faithfulness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)