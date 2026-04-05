"""
AegisClaim AI - Explainability Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional


class ItemExplanation(BaseModel):
    """Detailed explanation for a single bill item."""
    bill_item: str
    amount: float
    approved_amount: float = 0.0
    status: str  # COVERED, NOT_COVERED, PARTIALLY_COVERED
    clause_text: str = ""
    clause_section: str = ""
    page_number: Optional[int] = None
    reasoning: str = ""
    policy_reference: str = ""


class ClaimExplanation(BaseModel):
    """Full explainability output for a claim decision."""
    claim_id: str = ""
    decision: str
    confidence: float
    overall_reasoning: str
    item_explanations: list[ItemExplanation] = Field(default_factory=list)
    cited_clauses: list[dict] = Field(default_factory=list)
    decision_factors: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    total_bill_amount: float = 0.0
    total_approved_amount: float = 0.0
    summary_html: str = ""
