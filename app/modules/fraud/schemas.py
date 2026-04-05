"""
AegisClaim AI - Fraud Data Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional


class FraudFlag(BaseModel):
    """A single fraud indicator."""
    flag_type: str  # duplicate, anomaly, pattern, pricing
    severity: str  # low, medium, high, critical
    description: str
    score: float = 0.0
    evidence: str = ""


class FraudAnalysisResult(BaseModel):
    """Complete fraud analysis output."""
    fraud_risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    flags: list[FraudFlag] = Field(default_factory=list)
    anomalies_detected: int = 0
    summary: str = ""
    recommendation: str = ""
