"""
AegisClaim AI - Decision Data Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

from app.modules.ocr.schemas import ClaimDecision as SettlementClaimDecision, RejectionCitation


class ClaimDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"


class ItemDecision(str, Enum):
    COVERED = "COVERED"
    NOT_COVERED = "NOT_COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class RuleViolation(BaseModel):
    """A specific policy rule that was checked."""
    rule_name: str
    rule_description: str
    passed: bool
    details: str = ""
    severity: str = "medium"  # low, medium, high, critical


class ItemEvaluation(BaseModel):
    """Evaluation result for a single bill item."""
    bill_item: str
    amount: float
    approved_amount: float = 0.0
    decision: ItemDecision = ItemDecision.NEEDS_REVIEW
    reason: str = ""
    clause_reference: str = ""
    page_number: Optional[int] = None
    rejection_citation: Optional[RejectionCitation] = None


class RuleEngineResult(BaseModel):
    """Output from the deterministic rule engine."""
    decision: ClaimDecision = ClaimDecision.NEEDS_REVIEW
    violations: list[RuleViolation] = Field(default_factory=list)
    item_evaluations: list[ItemEvaluation] = Field(default_factory=list)
    total_approved_amount: float = 0.0
    total_bill_amount: float = 0.0
    confidence: float = 0.0
    reasoning_summary: str = ""
    rejection_citations: list[RejectionCitation] = Field(default_factory=list)
    claim_decision: Optional[SettlementClaimDecision] = None


class LLMReasoningResult(BaseModel):
    """Output from LLM-based reasoning."""
    decision: ClaimDecision = ClaimDecision.NEEDS_REVIEW
    confidence: float = 0.0
    reasoning: str = ""
    item_analyses: list[dict] = Field(default_factory=list)
    cited_clauses: list[dict] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    model_used: str = ""


class HybridDecisionResult(BaseModel):
    """Combined decision from rule engine + LLM."""
    final_decision: ClaimDecision = ClaimDecision.NEEDS_REVIEW
    confidence: float = 0.0
    rule_engine_result: Optional[RuleEngineResult] = None
    llm_result: Optional[LLMReasoningResult] = None
    item_evaluations: list[ItemEvaluation] = Field(default_factory=list)
    total_approved_amount: float = 0.0
    total_bill_amount: float = 0.0
    reasoning_summary: str = ""
    decision_factors: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    rejection_citations: list[RejectionCitation] = Field(default_factory=list)
    claim_decision: Optional[SettlementClaimDecision] = None
