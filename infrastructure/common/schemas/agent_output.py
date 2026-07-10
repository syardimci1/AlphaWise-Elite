"""AgentOutput — CONSTITUTION.md Madde 3.4 Output Schema.

Her ajanın (TAA/FAA/RAA/SAA/MAA) üretmesi ZORUNLU olan çıktı formatı.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Signal(str, Enum):
    EKLE = "EKLE"
    TUT = "TUT"
    BEKLE = "BEKLE"
    DIKKAT_ET = "DİKKAT ET"


class AgentRole(str, Enum):
    TAA = "TAA"  # Technical
    FAA = "FAA"  # Fundamental
    RAA = "RAA"  # Risk
    SAA = "SAA"  # Sentiment
    MAA = "MAA"  # Macro / Master


class DataLayer(str, Enum):
    FRED = "FRED"
    DCF = "DCF"
    DIX_GEX = "DIX/GEX"
    L2 = "L2"
    FINBERT = "FinBERT"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentOutput(BaseModel):
    """Ajan çıktı şeması — Madde 3.4 birebir."""

    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    signal: Signal
    confidence: float = Field(..., ge=0.0, le=1.0)
    confluence_score: int = Field(..., ge=0, le=100)
    reasoning: str = Field(
        ...,
        description="[VERİ] → [ANALİZ] → [ÇIKARIM] → [KARAR KODU] formatında",
        min_length=1,
    )
    agent: AgentRole
    model_used: str = Field(..., min_length=1)
    fallback_triggered: bool = False
    data_layers: List[DataLayer] = Field(default_factory=list)
    missing_data: List[str] = Field(default_factory=list)
    parse_error: bool = False
    parse_retry_count: int = Field(default=0, ge=0, le=2)
    timestamp: str = Field(default_factory=_utc_now_iso)
    self_critique: Optional[str] = None
    counter_argument: Optional[str] = None
    short_term: Optional[str] = Field(default=None, description="1-3 ay görünüm")
    mid_term: Optional[str] = Field(default=None, description="3-12 ay görünüm")
    long_term: Optional[str] = Field(default=None, description="1-3 yıl görünüm")
    data_freshness: Dict[str, str] = Field(
        default_factory=dict,
        description='{"katman": "ISO8601 tarih"} biçiminde',
    )
    failover_chain: List[str] = Field(default_factory=list)
    cascade_tier: int = Field(..., ge=1, le=4)

    @field_validator("timestamp")
    @classmethod
    def _validate_iso8601(cls, v: str) -> str:
        # datetime.fromisoformat, Python 3.11+ için Z suffix'ini de destekler
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v

    @field_validator("data_freshness")
    @classmethod
    def _validate_freshness_values(cls, v: Dict[str, str]) -> Dict[str, str]:
        for layer, iso_ts in v.items():
            datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return v
