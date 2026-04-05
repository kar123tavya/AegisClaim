"""
AegisClaim AI - Explainability Engine
Generates fully-auditable, page-pinned, paragraph-indexed explanations
for every claim decision, with proper citation cards for the frontend.
"""
import logging
import uuid
from typing import Optional

logger = logging.getLogger("aegisclaim.explainability.engine")

from app.modules.decision.schemas import HybridDecisionResult, ItemDecision
from app.modules.policy.schemas import PolicyChunk
from .schemas import ClaimExplanation, ItemExplanation


class ExplainabilityEngine:
    """
    Generates comprehensive, auditable explanations for every claim decision.
    Every explanation cites specific policy clauses with page + paragraph indices.
    """

    def generate_explanation(
        self,
        decision_result: HybridDecisionResult,
        policy_chunks: list[PolicyChunk] = None,
    ) -> ClaimExplanation:
        policy_chunks = policy_chunks or []

        # --- Per-item explanations ---
        item_explanations = []
        for item_eval in decision_result.item_evaluations:
            explanation = self._explain_item(item_eval, policy_chunks, decision_result)
            item_explanations.append(explanation)

        # --- Cited clauses (for Citations tab) ---
        cited_clauses = self._collect_cited_clauses(decision_result, policy_chunks, item_explanations)

        # --- Overall reasoning text ---
        overall_reasoning = self._generate_overall_reasoning(decision_result, item_explanations)

        # --- Recommendations ---
        recommendations = self._generate_recommendations(decision_result)

        # --- Summary HTML ---
        summary_html = self._build_summary_html(decision_result, item_explanations)

        # Normalise confidence to [0, 1]
        confidence = decision_result.confidence
        if confidence > 1.0:
            confidence = confidence / 100.0
        confidence = round(min(max(confidence, 0.0), 1.0), 4)

        return ClaimExplanation(
            claim_id=f"CLM-{uuid.uuid4().hex[:8].upper()}",
            decision=decision_result.final_decision.value,
            confidence=confidence,
            overall_reasoning=overall_reasoning,
            item_explanations=item_explanations,
            cited_clauses=cited_clauses,
            decision_factors=decision_result.decision_factors,
            recommendations=recommendations,
            requires_human_review=decision_result.requires_human_review,
            review_reasons=decision_result.review_reasons,
            total_bill_amount=decision_result.total_bill_amount,
            total_approved_amount=decision_result.total_approved_amount,
            summary_html=summary_html,
        )

    # ── Per-item explanation ───────────────────────────────────────────────
    def _explain_item(
        self,
        item_eval,
        policy_chunks: list[PolicyChunk],
        decision_result: HybridDecisionResult,
    ) -> ItemExplanation:
        best_clause = ""
        best_section = ""
        best_page: Optional[int] = item_eval.page_number
        best_paragraph: Optional[int] = None

        # Priority 1: hard rejection citation (has exact page + paragraph)
        if item_eval.rejection_citation:
            rc = item_eval.rejection_citation
            best_clause = rc.exact_clause_text
            best_page = rc.page
            best_paragraph = getattr(rc, "paragraph", None)
            best_section = "exclusions"

        # Priority 2: clause_reference from rule engine
        elif item_eval.clause_reference:
            best_clause = item_eval.clause_reference

        # Priority 3: LLM item analysis
        if decision_result.llm_result:
            for llm_item in (decision_result.llm_result.item_analyses or []):
                if _name_match(llm_item.get("item", ""), item_eval.bill_item):
                    if llm_item.get("clause_reference"):
                        best_clause = best_clause or llm_item["clause_reference"]
                    if llm_item.get("page_number"):
                        best_page = best_page or int(llm_item["page_number"])
                    break

        # Priority 4: semantic search in policy chunks
        if policy_chunks and not best_clause:
            item_words = {w.lower() for w in item_eval.bill_item.split() if len(w) > 3}
            for chunk in policy_chunks:
                chunk_lower = chunk.text.lower()
                if any(w in chunk_lower for w in item_words):
                    best_clause = chunk.text[:400]
                    best_section = (
                        chunk.section.value if hasattr(chunk.section, "value") else str(chunk.section)
                    )
                    best_page = chunk.page_number
                    # Derive paragraph index from chunk order on page
                    best_paragraph = getattr(chunk, "paragraph_index", None)
                    break

        # Build policy_reference string
        parts = []
        if best_page:
            parts.append(f"Page {best_page}")
        if best_paragraph is not None:
            parts.append(f"Paragraph {best_paragraph}")
        if best_section and best_section not in ("general", ""):
            parts.append(f"Section: {best_section.replace('_', ' ').title()}")
        policy_ref = ", ".join(parts)

        # Reasoning
        reasoning = self._format_item_reasoning(
            item_eval, best_clause, best_page, best_paragraph, best_section
        )

        return ItemExplanation(
            bill_item=item_eval.bill_item,
            amount=item_eval.amount,
            approved_amount=item_eval.approved_amount,
            status=item_eval.decision.value,
            clause_text=best_clause,
            clause_section=best_section,
            page_number=best_page,
            reasoning=reasoning,
            policy_reference=policy_ref,
        )

    # ── Reasoning formatter ────────────────────────────────────────────────
    def _format_item_reasoning(
        self,
        item_eval,
        clause: str,
        page: Optional[int],
        paragraph: Optional[int],
        section: str,
    ) -> str:
        d = item_eval.decision.value
        label = d.replace("_", " ").title()
        amt = item_eval.amount
        approved = item_eval.approved_amount

        lines = [f"{item_eval.bill_item} — ₹{amt:,.2f}  |  Status: {label}"]

        if d == "COVERED":
            lines.append(f"✅ Fully approved. Amount ₹{amt:,.2f} is covered under the policy.")
        elif d == "NOT_COVERED":
            lines.append(f"❌ Not covered. ₹{amt:,.2f} is rejected.")
            if item_eval.rejection_citation:
                rc = item_eval.rejection_citation
                ref = f"Page {rc.page}"
                if rc.paragraph is not None:
                    ref += f", ¶{rc.paragraph}"
                lines.append(f"Policy citation ({ref}): {rc.reasoning}")
            elif item_eval.reason:
                lines.append(f"Reason: {item_eval.reason}")
        elif d == "PARTIALLY_COVERED":
            deduction = amt - approved
            lines.append(
                f"⚠️ Partially covered. Approved ₹{approved:,.2f} of ₹{amt:,.2f}. "
                f"Deduction: ₹{deduction:,.2f}."
            )
            if item_eval.reason:
                lines.append(f"Reason: {item_eval.reason}")
        else:
            lines.append("🔍 Requires manual review.")
            if item_eval.reason:
                lines.append(f"Note: {item_eval.reason}")

        if clause:
            ref_str = f"Policy Reference"
            if page:
                ref_str += f" — Page {page}"
                if paragraph is not None:
                    ref_str += f", ¶{paragraph}"
            lines.append(f'\n{ref_str}:\n"{clause[:300]}{"..." if len(clause) > 300 else ""}"')

        return "\n".join(lines)

    # ── Overall reasoning ──────────────────────────────────────────────────
    def _generate_overall_reasoning(
        self,
        dr: HybridDecisionResult,
        item_explanations: list[ItemExplanation],
    ) -> str:
        decision = dr.final_decision.value
        confidence_pct = dr.confidence * 100 if dr.confidence <= 1.0 else dr.confidence

        lines = [
            f"## Claim Decision: {decision}",
            f"**Confidence:** {confidence_pct:.1f}%",
            f"**Bill Amount:** ₹{dr.total_bill_amount:,.2f}",
            f"**Approved Amount:** ₹{dr.total_approved_amount:,.2f}",
        ]
        if dr.total_bill_amount > 0:
            cov = (dr.total_approved_amount / dr.total_bill_amount) * 100
            lines.append(f"**Coverage:** {cov:.1f}%")

        # Decision factors
        if dr.decision_factors:
            lines += ["", "### Decision Factors"]
            lines += [f"- {f}" for f in dr.decision_factors]

        # Rule engine summary
        if dr.rule_engine_result and dr.rule_engine_result.reasoning_summary:
            lines += ["", "### Rule Engine Analysis"]
            lines.append(dr.rule_engine_result.reasoning_summary)

        # Rejection citations
        if dr.rejection_citations:
            lines += ["", "### Policy Citations (Rejection Grounds)"]
            for c in dr.rejection_citations:
                para = f", ¶{c.paragraph}" if c.paragraph is not None else ""
                lines.append(f"- **Page {c.page}{para}**: {c.reasoning}")
                lines.append(f'  > "{c.exact_clause_text[:300]}{"..." if len(c.exact_clause_text) > 300 else ""}"')

        # LLM reasoning
        if dr.llm_result and dr.llm_result.reasoning:
            lines += ["", "### AI Reasoning"]
            lines.append(dr.llm_result.reasoning)

        # Review flags
        if dr.requires_human_review and dr.review_reasons:
            lines += ["", "### ⚠️ Human Review Required"]
            lines += [f"- {r}" for r in dr.review_reasons]

        return "\n".join(lines)

    # ── Cited clauses (for Citations tab) ─────────────────────────────────
    def _collect_cited_clauses(
        self,
        dr: HybridDecisionResult,
        policy_chunks: list[PolicyChunk],
        item_explanations: list[ItemExplanation],
    ) -> list[dict]:
        clauses: list[dict] = []
        seen: set[str] = set()

        def _add(entry: dict) -> None:
            key = (entry.get("clause_text", "")[:120]).strip()
            if key and key not in seen:
                seen.add(key)
                clauses.append(entry)

        # 1. Rejection citations (highest priority — have page + paragraph)
        for rc in dr.rejection_citations:
            _add({
                "clause_text": rc.exact_clause_text,
                "page": rc.page,
                "paragraph": rc.paragraph,
                "section": "exclusions",
                "relevance": rc.reasoning,
                "citation_type": "rejection",
            })

        # 2. LLM cited clauses (have page number)
        if dr.llm_result:
            for c in (dr.llm_result.cited_clauses or []):
                _add({
                    "clause_text": c.get("clause_text", c.get("text", "")),
                    "page": c.get("page"),
                    "paragraph": c.get("paragraph"),
                    "section": c.get("section", ""),
                    "relevance": c.get("relevance", "Referenced by AI reasoning"),
                    "citation_type": "llm",
                })

        # 3. Item-level citations (from item explanations)
        for ie in item_explanations:
            if ie.clause_text and ie.status != "COVERED":
                _add({
                    "clause_text": ie.clause_text,
                    "page": ie.page_number,
                    "paragraph": None,
                    "section": ie.clause_section,
                    "relevance": f"Cited for: {ie.bill_item} ({ie.status})",
                    "citation_type": "item",
                })

        # 4. Policy chunks (general reference)
        for chunk in policy_chunks[:8]:
            section = chunk.section.value if hasattr(chunk.section, "value") else str(chunk.section)
            _add({
                "clause_text": chunk.text,
                "page": chunk.page_number,
                "paragraph": getattr(chunk, "paragraph_index", None),
                "section": section,
                "relevance": "Retrieved as relevant policy clause during evaluation",
                "citation_type": "rag",
            })

        return clauses[:15]

    # ── Recommendations ────────────────────────────────────────────────────
    def _generate_recommendations(self, dr: HybridDecisionResult) -> list[str]:
        recs = []
        decision = dr.final_decision.value

        if decision == "REJECTED":
            recs.append("Consider filing an appeal with additional supporting documents.")
            recs.append(
                "Verify if rejected items can be claimed under a different policy clause or rider."
            )
            if dr.rejection_citations:
                recs.append(
                    "Review the cited policy clauses carefully — some exclusions may have exceptions."
                )

        if decision == "PARTIALLY_APPROVED":
            diff = dr.total_bill_amount - dr.total_approved_amount
            recs.append(
                f"Out-of-pocket amount: ₹{diff:,.2f}. "
                "Check if a top-up or supplemental policy covers the balance."
            )

        if dr.requires_human_review:
            recs.append("Submit additional supporting documents to expedite the review process.")
            recs.append("Contact the insurer's claims helpline for clarification on flagged items.")

        conf = dr.confidence if dr.confidence <= 1.0 else dr.confidence / 100
        if conf < 0.5:
            recs.append(
                "Decision confidence is low — expert adjudicator review is strongly recommended."
            )

        if not recs:
            recs.append(
                "Claim has been processed. Retain all original bills and discharge summaries for records."
            )

        return recs

    # ── Summary HTML ───────────────────────────────────────────────────────
    def _build_summary_html(
        self,
        dr: HybridDecisionResult,
        item_explanations: list[ItemExplanation],
    ) -> str:
        decision = dr.final_decision.value
        color = {
            "APPROVED": "#10b981",
            "REJECTED": "#ef4444",
            "NEEDS_REVIEW": "#f59e0b",
            "PARTIALLY_APPROVED": "#3b82f6",
        }.get(decision, "#6b7280")

        conf = dr.confidence if dr.confidence <= 1.0 else dr.confidence / 100
        return (
            f'<div class="decision-summary">'
            f'<div class="decision-badge" style="background:{color};">{decision}</div>'
            f'<div>Confidence: {conf:.0%}</div>'
            f'<div>Bill: ₹{dr.total_bill_amount:,.2f} | Approved: ₹{dr.total_approved_amount:,.2f}</div>'
            f"</div>"
        )


# ── Utility ────────────────────────────────────────────────────────────────
def _name_match(a: str, b: str) -> bool:
    """Fuzzy match between two item names."""
    a_words = {w.lower() for w in a.split() if len(w) > 3}
    b_words = {w.lower() for w in b.split() if len(w) > 3}
    return bool(a_words & b_words)
