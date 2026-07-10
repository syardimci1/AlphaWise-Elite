"""HandoffRequest — ajanlar arası iş devri (handoff) mesaj şeması."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HandoffRequest(BaseModel):
    """
    Ajanlar arası handoff payload'ı.

    Not: `from` Python'da rezerve sözcük olduğundan alias ile korunur; model dışa
    her zaman `{"from": ..., "to": ...}` biçiminde serialize edilir.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    from_agent: str = Field(..., alias="from", min_length=1)
    to: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    timestamp: str = Field(default_factory=_utc_now_iso)

    @field_validator("timestamp")
    @classmethod
    def _validate_iso8601(cls, v: str) -> str:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v
