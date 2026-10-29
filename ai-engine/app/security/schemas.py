"""Security verdict schema.

One SecurityVerdict is produced per detector run at one of the three
checkpoints. A SecurityReport bundles them and carries the final decision.

Naming follows Ahmed's schemas: snake_case in Python, camelCase in the API.
Decisions here are ALLOW / FLAG / BLOCK and always carry source="security",
so they never get confused with the faithfulness gate (PASS / BLOCK).

Policy: a BLOCK on a single retrieved chunk drops that chunk and the request
continues. A BLOCK at pre_retrieval or pre_response stops the request.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Stage(str, Enum):
    PRE_RETRIEVAL = "pre_retrieval"      # the user's question
    POST_RETRIEVAL = "post_retrieval"    # each retrieved chunk
    PRE_RESPONSE = "pre_response"        # the model's answer


class Decision(str, Enum):
    ALLOW = "ALLOW"
    FLAG = "FLAG"      # let it through, but record and show a warning
    BLOCK = "BLOCK"    # stop here


class Category(str, Enum):
    NONE = "none"
    PROMPT_INJECTION = "prompt_injection"
    INDIRECT_INJECTION = "indirect_injection"   # hidden instructions in a chunk
    JAILBREAK = "jailbreak"
    UNSAFE_CONTENT = "unsafe_content"           # Llama Guard categories
    SENSITIVE_INFO = "sensitive_info"           # PII, secrets
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"
    MALICIOUS_LINK = "malicious_link"
    DETECTOR_ERROR = "detector_error"           # a detector crashed or timed out


_SEVERITY = {Decision.ALLOW: 0, Decision.FLAG: 1, Decision.BLOCK: 2}


class _ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )


class SecurityVerdict(_ApiModel):
    source: Literal["security"] = "security"
    stage: Stage
    decision: Decision
    category: Category = Category.NONE
    score: float = Field(ge=0.0, le=1.0, description="Detector confidence the input is an attack.")
    detector: str = Field(min_length=1, description="e.g. 'rules', 'injection_model', 'llama_guard', 'links'")
    reason: str = ""
    latency_ms: float = Field(default=0.0, ge=0.0)
    chunk_id: str | None = None   # set only at post_retrieval, so we know which chunk

    @property
    def dropped_chunk(self) -> bool:
        """A BLOCK on one retrieved chunk removes that chunk. The request continues."""
        return (
            self.decision is Decision.BLOCK
            and self.stage is Stage.POST_RETRIEVAL
            and self.chunk_id is not None
        )

    @property
    def blocks_request(self) -> bool:
        return self.decision is Decision.BLOCK and not self.dropped_chunk


class SecurityReport(_ApiModel):
    verdicts: list[SecurityVerdict] = Field(default_factory=list)
    final_decision: Decision = Decision.ALLOW

    @property
    def blocked(self) -> bool:
        return self.final_decision is Decision.BLOCK


def combine(verdicts: list[SecurityVerdict]) -> SecurityReport:
    """Final decision is the most severe request-level verdict. No verdicts means ALLOW.

    A dropped chunk does not block the request. It counts as FLAG, so the
    response still shows that something was removed.
    """
    final = Decision.ALLOW
    for v in verdicts:
        effective = Decision.FLAG if v.dropped_chunk else v.decision
        if _SEVERITY[effective] > _SEVERITY[final]:
            final = effective
    return SecurityReport(verdicts=verdicts, final_decision=final)
