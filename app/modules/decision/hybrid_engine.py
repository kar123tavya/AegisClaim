"""
AegisClaim AI - Hybrid Decision Engine
Combines deterministic rules + LLM reasoning for robust claim decisions.
"""
import logging
from typing import Optional

logger = logging.getLogger("aegisclaim.decision.hybrid_engine")

from app.core.config import settings
from app.modules.ocr.schemas import ExtractedBillData
from app.modules.policy.schemas import PolicyChunk, PolicyMetadata
from .rule_engine import RuleEngine
from .llm_reasoner import LLMReasoner
from .schemas import (
    ClaimDecision, HybridDecisionResult, ItemEvaluation, ItemDecision
)


class HybridDecisionEngine:
    """
    Combines deterministic rule engine with LLM reasoning.
    
    Decision Logic:
    - Rules clearly reject → REJECTED (high confidence)
    - Rules clearly approve + LLM agrees → APPROVED (high confidence)
    - Rules ambiguous → LLM decides with confidence threshold
    - Low confidence from both → NEEDS_REVIEW
    """

    def __init__(self):
        self.rule_engine = RuleEngine()
        self.llm_reasoner = LLMReasoner()
        self.confidence_threshold = settings.confidence_threshold

    def evaluate(
        self,
        bill_data: ExtractedBillData,
        policy_chunks: list[PolicyChunk],
        policy_metadata: Optional[PolicyMetadata] = None,
    ) -> HybridDecisionResult:
        """
        Evaluate a claim using both rule engine and LLM reasoning.
        
        Args:
            bill_data: Structured bill data from OCR
            policy_chunks: Relevant policy clauses from RAG
            policy_metadata: Extracted policy metadata
            
        Returns:
            HybridDecisionResult with combined decision
        """
        # Step 1: Rule engine evaluation
        rule_result = self.rule_engine.evaluate(bill_data, policy_metadata, policy_chunks)
        logger.info(f"Rule engine: {rule_result.decision.value} (confidence: {rule_result.confidence}%)")

        # Step 2: LLM reasoning (if enabled and needed)
        llm_result = None
        if settings.enable_llm_reasoning and self.llm_reasoner.client:
            llm_result = self.llm_reasoner.reason(bill_data, policy_chunks, policy_metadata)
            logger.info(f"LLM reasoning: {llm_result.decision.value} (confidence: {llm_result.confidence}%)")

        # Step 3: Combine decisions
        result = self._combine_decisions(rule_result, llm_result, bill_data)
        
        return result

    def _combine_decisions(
        self,
        rule_result,
        llm_result,
        bill_data: ExtractedBillData,
    ) -> HybridDecisionResult:
        """Combine rule engine and LLM decisions using weighted logic."""
        
        decision_factors = []
        review_reasons = []
        requires_review = False

        # Weights: Rules 60%, LLM 40%
        RULE_WEIGHT = 0.6
        LLM_WEIGHT = 0.4

        if llm_result and llm_result.confidence > 0:
            # Both engines available
            rule_conf = rule_result.confidence
            llm_conf = llm_result.confidence
            
            # Check for agreement
            if rule_result.decision == llm_result.decision:
                # Full agreement → high confidence
                final_decision = rule_result.decision
                final_confidence = min(
                    rule_conf * RULE_WEIGHT + llm_conf * LLM_WEIGHT + 10,  # Agreement bonus
                    98.0
                )
                decision_factors.append(
                    f"Rule engine and LLM agree: {final_decision.value}"
                )
            
            elif rule_result.decision == ClaimDecision.REJECTED and rule_conf >= 80:
                # Rules strongly reject — override LLM
                final_decision = ClaimDecision.REJECTED
                final_confidence = rule_conf
                decision_factors.append(
                    f"Rule engine strongly rejects (confidence: {rule_conf}%)"
                )
                if llm_result.decision != ClaimDecision.REJECTED:
                    decision_factors.append(
                        f"LLM suggested {llm_result.decision.value} but rules override"
                    )
            
            elif rule_result.decision == ClaimDecision.NEEDS_REVIEW:
                # Rules uncertain → delegate to LLM
                if llm_conf >= self.confidence_threshold:
                    final_decision = llm_result.decision
                    final_confidence = llm_conf * LLM_WEIGHT + rule_conf * RULE_WEIGHT
                    decision_factors.append(
                        f"Rules uncertain, LLM decides: {llm_result.decision.value}"
                    )
                else:
                    final_decision = ClaimDecision.NEEDS_REVIEW
                    final_confidence = max(rule_conf, llm_conf) * 0.5
                    requires_review = True
                    review_reasons.append("Both rule engine and LLM have low confidence")
            
            elif rule_result.decision != llm_result.decision:
                # Disagreement
                if rule_conf > llm_conf + 20:
                    final_decision = rule_result.decision
                    final_confidence = rule_conf * 0.7
                    decision_factors.append(
                        f"Disagreement: Rules ({rule_result.decision.value}) override LLM ({llm_result.decision.value})"
                    )
                elif llm_conf > rule_conf + 20:
                    final_decision = llm_result.decision
                    final_confidence = llm_conf * 0.7
                    decision_factors.append(
                        f"Disagreement: LLM ({llm_result.decision.value}) overrides rules ({rule_result.decision.value})"
                    )
                else:
                    # Close confidence — needs review
                    final_decision = ClaimDecision.NEEDS_REVIEW
                    final_confidence = max(rule_conf, llm_conf) * 0.5
                    requires_review = True
                    review_reasons.append(
                        f"Engines disagree: Rules={rule_result.decision.value} ({rule_conf}%), "
                        f"LLM={llm_result.decision.value} ({llm_conf}%)"
                    )
            else:
                final_decision = rule_result.decision
                final_confidence = rule_conf
        
        else:
            # Only rule engine available
            final_decision = rule_result.decision
            final_confidence = rule_result.confidence
            decision_factors.append("Rule engine only (LLM not available)")
            
            if final_confidence < self.confidence_threshold:
                requires_review = True
                review_reasons.append(
                    f"Low confidence ({final_confidence}%) and LLM reasoning unavailable"
                )

        # Merge item evaluations (prefer LLM's enriched evaluations when available)
        item_evaluations = rule_result.item_evaluations
        if llm_result and llm_result.item_analyses:
            item_evaluations = self._merge_item_evaluations(
                rule_result.item_evaluations,
                llm_result.item_analyses
            )

        # Calculate approved amount based on final decision
        # - REJECTED:           0 (entire claim denied)
        # - APPROVED:           full bill amount
        # - PARTIALLY_APPROVED: sum of per-item approved_amounts
        # - NEEDS_REVIEW:       sum of per-item approved_amounts (best estimate)
        if final_decision == ClaimDecision.REJECTED:
            total_approved = 0.0
            # Zero out all item approved amounts for consistency
            for ev in item_evaluations:
                if ev.decision.value != "COVERED":
                    ev.approved_amount = 0.0
        elif final_decision == ClaimDecision.APPROVED:
            total_approved = bill_data.total_amount
        else:
            total_approved = sum(e.approved_amount for e in item_evaluations)
            # Sanity guard: approved cannot exceed billed
            total_approved = min(total_approved, bill_data.total_amount)

        # Build comprehensive reasoning
        reasoning_parts = [rule_result.reasoning_summary]
        if llm_result and llm_result.reasoning:
            reasoning_parts.append(f"\nLLM Reasoning:\n{llm_result.reasoning}")

        return HybridDecisionResult(
            final_decision=final_decision,
            confidence=round(min(final_confidence, 100), 1),
            rule_engine_result=rule_result,
            llm_result=llm_result,
            item_evaluations=item_evaluations,
            total_approved_amount=round(total_approved, 2),
            total_bill_amount=round(bill_data.total_amount, 2),
            reasoning_summary="\n".join(reasoning_parts),
            decision_factors=decision_factors,
            requires_human_review=requires_review,
            review_reasons=review_reasons,
            rejection_citations=list(rule_result.rejection_citations),
            claim_decision=rule_result.claim_decision,
        )

    def _merge_item_evaluations(
        self,
        rule_items: list[ItemEvaluation],
        llm_items: list[dict],
    ) -> list[ItemEvaluation]:
        """Merge rule engine and LLM item evaluations for richer output."""
        merged = []
        
        # Create lookup from LLM results
        llm_lookup = {}
        for item in llm_items:
            key = item.get("item", "").lower().strip()
            llm_lookup[key] = item

        for rule_item in rule_items:
            # Try to find matching LLM evaluation
            llm_match = llm_lookup.get(rule_item.bill_item.lower().strip())
            
            if llm_match:
                # Enrich with LLM details
                clause_ref = llm_match.get("clause_reference", rule_item.clause_reference) or ""
                page_num = llm_match.get("page_number", rule_item.page_number)
                reason = rule_item.reason
                
                if llm_match.get("reason"):
                    reason = f"{rule_item.reason}. LLM: {llm_match['reason']}"
                
                merged.append(ItemEvaluation(
                    bill_item=rule_item.bill_item,
                    amount=rule_item.amount,
                    approved_amount=rule_item.approved_amount,
                    decision=rule_item.decision,
                    reason=reason,
                    clause_reference=clause_ref,
                    page_number=page_num,
                    rejection_citation=rule_item.rejection_citation,
                ))
            else:
                merged.append(rule_item)

        return merged

