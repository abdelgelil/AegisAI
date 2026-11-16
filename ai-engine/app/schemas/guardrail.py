"""Shared contracts for gateway guardrail decisions."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ThreatCategory(str, Enum):
    NONE = "NONE"
    CREDIT_CARD = "CREDIT_CARD"
    API_KEY_OR_SECRET = "API_KEY_OR_SECRET"
    PII = "PII"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    POISONED_CHUNK = "POISONED_CHUNK"


class SecurityVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    has_sensitive_credentials: bool = False
    is_injection_detected: bool = False
    auto_rerouted: bool = False
    requested_mode: str | None = None
    enforced_mode: str | None = None
    detected_entities: list[ThreatCategory] = Field(default_factory=list)
    quarantined_chunk_ids: list[str] = Field(default_factory=list)
    scanner_latency_ms: float = Field(default=0.0, ge=0)
    message: str = ""
