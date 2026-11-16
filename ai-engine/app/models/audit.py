"""Request audit metadata. Never persist credentials or raw personal data."""

import uuid

from sqlalchemy import Boolean, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

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
