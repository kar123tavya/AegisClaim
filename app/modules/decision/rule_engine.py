"""
AegisClaim AI - Deterministic Rule Engine
Applies hard business rules to evaluate insurance claims against policy terms.
"""
import logging
from collections import defaultdict
from typing import Optional, Union

logger = logging.getLogger("aegisclaim.decision.rule_engine")

from app.modules.ocr.schemas import (
    BillItemCategory,
    ExtractedBillData,
    ExtractedTextBlock,
    RejectionCitation,
    ClaimDecision as SettlementClaimDecision,
)
from app.modules.policy.schemas import PolicyChunk, PolicyMetadata
from .schemas import (
    ClaimDecision,
    ItemDecision,
    RuleViolation,
    ItemEvaluation,
    RuleEngineResult,
)


class RuleEngine:
    """
    Deterministic rule engine for clear-cut claim decisions.
    Applies policy rules: coverage limits, room rent caps, exclusions, waiting periods.
    """

    # Known exclusion keywords
    EXCLUSION_KEYWORDS = [
        "cosmetic", "aesthetic", "beauty", "hair transplant", "lasik",
        "dental", "orthodontic", "infertility", "ivf", "weight loss",
        "bariatric", "obesity", "experimental", "investigational",
        "self-inflicted", "suicide", "alcohol", "drug abuse", "substance",
        "war", "nuclear", "adventure sports", "hazardous activity",
        "congenital", "genetic", "pre-existing",
        # Hindi
        "कॉस्मेटिक", "सौंदर्य", "बांझपन",
        # Spanish
        "cosmético", "estético", "infertilidad",
    ]

    EXCLUSION_CONTEXT_MARKERS = (
        "exclusion", "not covered", "excluded", "exclude", "not payable",
        "permanent exclusion", "general exclusion",
    )

    # Pre-existing condition indicators
    PRE_EXISTING_INDICATORS = [
        "diabetes", "hypertension", "high blood pressure", "heart disease",
        "cardiac", "asthma", "copd", "cancer", "hiv", "aids", "hepatitis",
        "kidney disease", "renal failure", "thyroid", "epilepsy",
        "मधुमेह", "उच्च रक्तचाप",
    ]

    @staticmethod
    def _normalize_policy_chunk(
        chunk: Union[PolicyChunk, ExtractedTextBlock, tuple],
    ) -> tuple[object, str, int, Optional[int]]:
        """Unpack tuple-wrapped policy chunks and read metadata safely."""
        if isinstance(chunk, tuple):
            chunk = chunk[0]

        if hasattr(chunk, "metadata") and chunk.metadata is not None:
            page_number = chunk.metadata.get("page_number") or getattr(chunk, "page_number", None) or 1
            paragraph_index = chunk.metadata.get("paragraph_index")
        else:
            page_number = getattr(chunk, "page_number", None) or 1
            paragraph_index = getattr(chunk, "paragraph_index", None)

        if hasattr(chunk, "text"):
            text = chunk.text
        elif isinstance(chunk, dict):
            text = chunk.get("text", "")
        else:
            text = ""

        return chunk, text, page_number, paragraph_index

    def _normalize_policy_blocks(
        self,  # ADDED SELF HERE
        policy_chunks: Optional[list[Union[PolicyChunk, ExtractedTextBlock]]],
    ) -> list[ExtractedTextBlock]:
        """Convert PolicyChunk or ExtractedTextBlock inputs into ExtractedTextBlock with paragraph_index."""
        if not policy_chunks:
            return []
            
        from collections import defaultdict # Ensure this is available
        page_seq: defaultdict[int, int] = defaultdict(int)
        blocks: list[ExtractedTextBlock] = []
        
        for c in policy_chunks:
            # This handles unpacking the 'tuple' error we saw earlier
            c, text, p, paragraph_index = self._normalize_policy_chunk(c)
            
            if isinstance(c, ExtractedTextBlock):
                blocks.append(c)
                continue
                
            if paragraph_index is None:
                paragraph_index = page_seq[p]
                page_seq[p] += 1
                
            blocks.append(
                ExtractedTextBlock(
                    text=text,
                    page_number=p,
                    paragraph_index=paragraph_index,
                )
            )
        return blocks

    @staticmethod
    def _normalize_confidence(confidence: float) -> float:
        """Ensure confidence is returned as a decimal between 0.0 and 1.0."""
        if confidence is None:
            return 0.0
        if confidence > 1.0:
            confidence = confidence / 100.0
        return max(0.0, min(confidence, 1.0))

    def _find_block_for_keyword(
        self, blocks: list[ExtractedTextBlock], keyword: str
    ) -> Optional[ExtractedTextBlock]:
        kw = keyword.lower().strip()
        if not kw:
            return None
        for b in blocks:
            if kw in b.text.lower():
                return b
        return None

    def _find_block_exclusion_context(
        self, blocks: list[ExtractedTextBlock], keyword: str
    ) -> Optional[ExtractedTextBlock]:
        """Prefer a block that mentions the keyword within exclusion-style language."""
        kw = keyword.lower().strip()
        if not kw:
            return None
        best: Optional[ExtractedTextBlock] = None
        for b in blocks:
            bl = b.text.lower()
            if kw not in bl:
                continue
            if any(m in bl for m in self.EXCLUSION_CONTEXT_MARKERS):
                return b
            best = best or b
        return best

    def _find_fallback_exclusion_block(
        self, blocks: list[ExtractedTextBlock]
    ) -> Optional[ExtractedTextBlock]:
        """Any chunk that reads like an exclusions clause."""
        for b in blocks:
            bl = b.text.lower()
            if any(m in bl for m in self.EXCLUSION_CONTEXT_MARKERS):
                return b
        return blocks[0] if blocks else None

    def _build_citation(
        self, block: ExtractedTextBlock, reasoning: str
    ) -> RejectionCitation:
        return RejectionCitation(
            page=block.page_number,
            paragraph=block.paragraph_index,
            exact_clause_text=block.text.strip(),
            reasoning=reasoning,
        )

    def _citation_for_exclusion_match(
        self,
        blocks: list[ExtractedTextBlock],
        matched_needles: list[str],
        bill_item_description: str,
    ) -> Optional[RejectionCitation]:
        """
        Resolve a RejectionCitation from policy blocks for matched exclusion needles.
        Tries exclusion-context blocks first, then any block containing a needle, then a general exclusions chunk.
        """
        if not blocks:
            return None
        for needle in matched_needles:
            block = self._find_block_exclusion_context(blocks, needle)
            if block:
                return self._build_citation(
                    block,
                    reasoning=(
                        f"Bill line matches excluded term '{needle}'; cited policy block aligns this service "
                        f"with exclusions (item: {bill_item_description[:120]})."
                    ),
                )
        for needle in matched_needles:
            block = self._find_block_for_keyword(blocks, needle)
            if block:
                return self._build_citation(
                    block,
                    reasoning=(
                        f"Policy text contains the same excluded term '{needle}' as the bill line "
                        f"({bill_item_description[:120]})."
                    ),
                )
        fb = self._find_fallback_exclusion_block(blocks)
        if fb and matched_needles:
            return self._build_citation(
                fb,
                reasoning=(
                    f"Bill item matches exclusion trigger ({', '.join(matched_needles[:5])}); "
                    f"general exclusions clause applies (item: {bill_item_description[:120]})."
                ),
            )
        return None

    def evaluate(
        self,
        bill_data: ExtractedBillData,
        policy_metadata: Optional[PolicyMetadata],
        policy_chunks: Optional[list[Union[PolicyChunk, ExtractedTextBlock]]] = None,
    ) -> RuleEngineResult:
        """
        Evaluate a claim against policy rules.

        Args:
            bill_data: Structured data from the hospital bill
            policy_metadata: Extracted policy metadata (limits, copay, etc.)
            policy_chunks: Relevant policy text blocks (PolicyChunk or ExtractedTextBlock)

        Returns:
            RuleEngineResult including structured claim_decision and RejectionCitation entries
        """
        violations: list[RuleViolation] = []
        item_evaluations: list[ItemEvaluation] = []
        policy_chunks = policy_chunks or []
        blocks = self._normalize_policy_blocks(policy_chunks)

        policy_text = "\n".join(b.text for b in blocks).lower()

        rejection_citations: list[RejectionCitation] = []

        def _add_citation(c: RejectionCitation) -> None:
            key = (c.page, c.paragraph, c.exact_clause_text[:240])
            if not any(
                (x.page, x.paragraph, x.exact_clause_text[:240]) == key
                for x in rejection_citations
            ):
                rejection_citations.append(c)

        # === Rule 1: Total Amount vs Sum Insured ===
        if policy_metadata and policy_metadata.sum_insured:
            violation = self._check_sum_insured(bill_data.total_amount, policy_metadata.sum_insured)
            violations.append(violation)

        # === Rule 2: Room Rent Cap ===
        if policy_metadata and policy_metadata.room_rent_limit_per_day:
            room_violations = self._check_room_rent(
                bill_data.line_items, policy_metadata.room_rent_limit_per_day
            )
            violations.extend(room_violations)

        # === Rule 3: Exclusions (policy block citations required when flagged) ===
        exclusion_violations, exclusion_cites = self._check_exclusions(bill_data, blocks)
        violations.extend(exclusion_violations)
        for c in exclusion_cites:
            _add_citation(c)

        # === Rule 4: Pre-existing Conditions ===
        pre_existing_violations = self._check_pre_existing(
            bill_data, policy_metadata, policy_text
        )
        violations.extend(pre_existing_violations)

        # === Rule 5: Bill Completeness ===
        completeness_violations = self._check_completeness(bill_data)
        violations.extend(completeness_violations)

        # === Evaluate Individual Items ===
        for item in bill_data.line_items:
            eval_result, item_cites = self._evaluate_item(
                item, policy_metadata, blocks
            )
            item_evaluations.append(eval_result)
            for c in item_cites:
                _add_citation(c)

        # === Calculate approved amount ===
        total_approved = sum(e.approved_amount for e in item_evaluations)

        # Apply copay if applicable
        if policy_metadata and policy_metadata.copay_percentage:
            copay_factor = 1 - (policy_metadata.copay_percentage / 100)
            total_approved *= copay_factor

        # === Determine overall decision ===
        critical_violations = [v for v in violations if v.severity == "critical" and not v.passed]
        high_violations = [v for v in violations if v.severity == "high" and not v.passed]
        failed_violations = [v for v in violations if not v.passed]

        if critical_violations:
            decision = ClaimDecision.REJECTED
            confidence = 0.90
        elif high_violations:
            decision = ClaimDecision.REJECTED
            confidence = 0.75
        elif len(failed_violations) > len(violations) * 0.5 and failed_violations:
            decision = ClaimDecision.REJECTED
            confidence = 0.65
        elif not failed_violations:
            decision = ClaimDecision.APPROVED
            confidence = 0.80
        elif total_approved > 0 and total_approved < bill_data.total_amount:
            decision = ClaimDecision.PARTIALLY_APPROVED
            confidence = 0.60
        else:
            decision = ClaimDecision.NEEDS_REVIEW
            confidence = 0.40

        confidence = self._normalize_confidence(confidence)

        reasons = []
        for v in violations:
            if not v.passed:
                reasons.append(f"❌ {v.rule_name}: {v.details}")
            else:
                reasons.append(f"✅ {v.rule_name}: {v.details}")

        claim_decision = SettlementClaimDecision(
            outcome=decision.value,
            rejection_citations=list(rejection_citations),
            reasoning_summary="\n".join(reasons),
            confidence=confidence,
        )

        return RuleEngineResult(
            decision=decision,
            violations=violations,
            item_evaluations=item_evaluations,
            total_approved_amount=round(total_approved, 2),
            total_bill_amount=bill_data.total_amount,
            confidence=confidence,
            reasoning_summary="\n".join(reasons),
            rejection_citations=rejection_citations,
            claim_decision=claim_decision,
        )

    def _check_sum_insured(self, bill_amount: float, sum_insured: float) -> RuleViolation:
        """Check if bill amount exceeds sum insured."""
        passed = bill_amount <= sum_insured
        return RuleViolation(
            rule_name="Sum Insured Limit",
            rule_description="Total bill amount must not exceed sum insured",
            passed=passed,
            details=(
                f"Bill amount (₹{bill_amount:,.2f}) is within sum insured (₹{sum_insured:,.2f})"
                if passed else
                f"Bill amount (₹{bill_amount:,.2f}) exceeds sum insured (₹{sum_insured:,.2f}) by ₹{bill_amount - sum_insured:,.2f}"
            ),
            severity="critical" if not passed else "low"
        )

    def _check_room_rent(self, line_items, daily_limit: float) -> list[RuleViolation]:
        """Check room rent against daily cap."""
        violations = []
        for item in line_items:
            if item.category in (BillItemCategory.ROOM_CHARGES, BillItemCategory.ICU_CHARGES):
                days = item.quantity or 1
                daily_rate = item.amount / max(days, 1)

                passed = daily_rate <= daily_limit
                violations.append(RuleViolation(
                    rule_name=f"Room Rent Cap - {item.description}",
                    rule_description=f"Daily room rent must not exceed ₹{daily_limit:,.0f}/day",
                    passed=passed,
                    details=(
                        f"Room rate ₹{daily_rate:,.0f}/day is within limit of ₹{daily_limit:,.0f}/day"
                        if passed else
                        f"Room rate ₹{daily_rate:,.0f}/day exceeds cap of ₹{daily_limit:,.0f}/day. "
                        f"Excess: ₹{(daily_rate - daily_limit) * days:,.0f} over {days} days"
                    ),
                    severity="high" if not passed else "low"
                ))
        return violations

    def _check_exclusions(
        self, bill_data: ExtractedBillData, blocks: list[ExtractedTextBlock]
    ) -> tuple[list[RuleViolation], list[RejectionCitation]]:
        """Check bill items against exclusion list; each rejection uses RejectionCitation from policy blocks."""
        violations: list[RuleViolation] = []
        citations: list[RejectionCitation] = []

        for item in bill_data.line_items:
            desc_lower = item.description.lower()
            matched: list[str] = []
            for kw in self.EXCLUSION_KEYWORDS:
                if kw in desc_lower:
                    matched.append(kw)

            if policy_text := "\n".join(b.text for b in blocks).lower():
                if "exclusion" in policy_text or "not covered" in policy_text:
                    for tok in desc_lower.split():
                        if len(tok) <= 3:
                            continue
                        if tok in policy_text:
                            idx = policy_text.find(tok)
                            context = policy_text[max(0, idx - 200):idx + 200]
                            if any(ex in context for ex in ("exclusion", "not covered", "excluded", "exclude")):
                                tag = f"policy-term:{tok}"
                                if tag not in matched:
                                    matched.append(tag)

            if not matched:
                continue

            needles: list[str] = []
            for m in matched:
                if m.startswith("policy-term:"):
                    needles.append(m.replace("policy-term:", "", 1))
                else:
                    needles.append(m)
            cite = self._citation_for_exclusion_match(blocks, needles, item.description)
            if cite is None:
                continue

            citations.append(cite)
            violations.append(RuleViolation(
                rule_name=f"Exclusion Check - {item.description}",
                rule_description="Item matches policy exclusion list",
                passed=False,
                details=cite.exact_clause_text,
                severity="critical"
            ))

        return violations, citations

    def _check_pre_existing(
        self, bill_data: ExtractedBillData,
        policy_metadata: Optional[PolicyMetadata],
        policy_text: str
    ) -> list[RuleViolation]:
        """Check for pre-existing condition indicators."""
        violations = []
        diagnosis = (bill_data.diagnosis or "").lower()

        for indicator in self.PRE_EXISTING_INDICATORS:
            if indicator in diagnosis:
                waiting_years = (
                    policy_metadata.pre_existing_waiting_years
                    if policy_metadata and policy_metadata.pre_existing_waiting_years
                    else 4
                )
                violations.append(RuleViolation(
                    rule_name=f"Pre-existing Condition - {indicator.title()}",
                    rule_description=f"Pre-existing conditions have a {waiting_years}-year waiting period",
                    passed=False,
                    details=(
                        f"Diagnosis mentions '{indicator}' which may be a pre-existing condition. "
                        f"Waiting period: {waiting_years} years. "
                        f"Requires verification of policy start date and condition history."
                    ),
                    severity="high"
                ))

        return violations

    def _check_completeness(self, bill_data: ExtractedBillData) -> list[RuleViolation]:
        """Check if bill data is complete enough for processing."""
        violations = []

        if bill_data.extraction_confidence < 0.3:
            violations.append(RuleViolation(
                rule_name="Document Quality",
                rule_description="Bill extraction confidence must be adequate",
                passed=False,
                details=f"Low extraction confidence ({bill_data.extraction_confidence:.0%}). Document may be illegible.",
                severity="high"
            ))

        if not bill_data.line_items:
            violations.append(RuleViolation(
                rule_name="Line Items Missing",
                rule_description="Bill must have identifiable line items",
                passed=False,
                details="No line items could be extracted from the bill",
                severity="high"
            ))

        if bill_data.total_amount <= 0:
            violations.append(RuleViolation(
                rule_name="Total Amount Missing",
                rule_description="Bill must have a valid total amount",
                passed=False,
                details="Could not determine total bill amount",
                severity="medium"
            ))

        return violations

    def _evaluate_item(
        self,
        item,
        policy_metadata: Optional[PolicyMetadata],
        blocks: list[ExtractedTextBlock],
    ) -> tuple[ItemEvaluation, list[RejectionCitation]]:
        """Evaluate a single bill item; NOT_COVERED requires a RejectionCitation from policy blocks."""
        desc_lower = item.description.lower()
        cites: list[RejectionCitation] = []

        matched_kws = [kw for kw in self.EXCLUSION_KEYWORDS if kw in desc_lower]
        if matched_kws:
            cite = self._citation_for_exclusion_match(blocks, matched_kws, item.description)
            if cite is None:
                return (
                    ItemEvaluation(
                        bill_item=item.description,
                        amount=item.amount,
                        approved_amount=0.0,
                        decision=ItemDecision.NEEDS_REVIEW,
                        reason="",
                        clause_reference="",
                        page_number=None,
                        rejection_citation=None,
                    ),
                    [],
                )
            cites.append(cite)
            return (
                ItemEvaluation(
                    bill_item=item.description,
                    amount=item.amount,
                    approved_amount=0.0,
                    decision=ItemDecision.NOT_COVERED,
                    reason="",
                    clause_reference=cite.exact_clause_text[:200],
                    page_number=cite.page,
                    rejection_citation=cite,
                ),
                cites,
            )

        if item.category in (BillItemCategory.ROOM_CHARGES, BillItemCategory.ICU_CHARGES):
            if policy_metadata and policy_metadata.room_rent_limit_per_day:
                days = item.quantity or 1
                daily_rate = item.amount / max(days, 1)
                if daily_rate > policy_metadata.room_rent_limit_per_day:
                    approved = policy_metadata.room_rent_limit_per_day * days
                    cap_block = self._find_block_for_keyword(blocks, "room") or self._find_fallback_exclusion_block(blocks)
                    clause_ref = (cap_block.text[:200] + "...") if cap_block else ""
                    return (
                        ItemEvaluation(
                            bill_item=item.description,
                            amount=item.amount,
                            approved_amount=approved,
                            decision=ItemDecision.PARTIALLY_COVERED,
                            reason="",
                            clause_reference=clause_ref,
                            page_number=(cap_block.page_number if cap_block else None),
                            rejection_citation=None,
                        ),
                        [],
                    )

        if policy_metadata and policy_metadata.sum_insured:
            if item.amount > policy_metadata.sum_insured:
                si_block = self._find_block_for_keyword(blocks, "sum insured") or self._find_block_for_keyword(blocks, "insured")
                clause_ref = (si_block.text[:200] + "...") if si_block else ""
                return (
                    ItemEvaluation(
                        bill_item=item.description,
                        amount=item.amount,
                        approved_amount=policy_metadata.sum_insured,
                        decision=ItemDecision.PARTIALLY_COVERED,
                        reason="",
                        clause_reference=clause_ref,
                        page_number=(si_block.page_number if si_block else None),
                        rejection_citation=None,
                    ),
                    [],
                )

        clause_ref = ""
        page_num = None
        for chunk in blocks:
            chunk_lower = chunk.text.lower()
            item_words = [w for w in desc_lower.split() if len(w) > 3]
            if any(w in chunk_lower for w in item_words):
                clause_ref = chunk.text[:100] + "..."
                page_num = chunk.page_number
                break

        return (
            ItemEvaluation(
                bill_item=item.description,
                amount=item.amount,
                approved_amount=item.amount,
                decision=ItemDecision.COVERED,
                reason="",
                clause_reference=clause_ref,
                page_number=page_num,
                rejection_citation=None,
            ),
            [],
        )
