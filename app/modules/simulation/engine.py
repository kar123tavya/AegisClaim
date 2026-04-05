"""
AegisClaim AI - What-If Simulation Engine (Enhanced)
Multi-scenario analysis: shows exactly how much more could be approved
under different appeal strategies, with specific monetary recommendations.
"""
from __future__ import annotations
import logging
import json
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from app.services.claim_processor import ClaimProcessingResult

logger = logging.getLogger("aegisclaim.simulation.engine")

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class WhatIfSimulator:
    """
    Multi-scenario What-If simulation engine.
    Computes concrete monetary scenarios for claim improvement.
    """

    def __init__(self):
        self.client = None
        if GENAI_AVAILABLE and settings.google_api_key:
            try:
                self.client = genai.Client(api_key=settings.google_api_key)
            except Exception as e:
                logger.error(f"Failed to init simulation client: {e}")

    def simulate(self, claim_result: "ClaimProcessingResult") -> dict:
        """
        Run multi-scenario simulation on a claim result.
        Always returns a useful result even without LLM.
        """
        if not claim_result.explanation:
            return self._unavailable("No explanation available for simulation.")

        exp = claim_result.explanation
        decision_str = exp.decision if isinstance(exp.decision, str) else getattr(exp.decision, "value", str(exp.decision))

        total_billed   = float(exp.total_bill_amount or 0)
        total_approved = float(exp.total_approved_amount or 0)
        total_rejected = total_billed - total_approved

        # Gather item-level data
        items_data = []
        for ie in exp.item_explanations:
            items_data.append({
                "item":          ie.bill_item,
                "billed":        ie.amount,
                "approved":      ie.approved_amount,
                "status":        ie.status,
                "reasoning":     (ie.reasoning or "")[:250],
                "clause_text":   (ie.clause_text  or "")[:200],
                "page_number":   ie.page_number,
                "policy_ref":    ie.policy_reference or "",
            })

        rejected_items  = [i for i in items_data if i["status"] == "NOT_COVERED"]
        partial_items   = [i for i in items_data if i["status"] == "PARTIALLY_COVERED"]
        covered_items   = [i for i in items_data if i["status"] == "COVERED"]

        rejected_amount = sum(i["billed"]             for i in rejected_items)
        partial_gap     = sum(i["billed"] - i["approved"] for i in partial_items)

        # Always compute rule-based scenarios (no LLM needed)
        scenarios = self._build_rule_scenarios(
            rejected_items, partial_items, covered_items,
            total_billed, total_approved,
            claim_result
        )

        # Enrich with LLM if available
        if self.client and (rejected_items or partial_items):
            llm_scenarios = self._llm_enrich(
                decision_str, items_data, total_billed, total_approved,
                claim_result
            )
            if llm_scenarios:
                # Merge LLM scenarios, avoiding duplicates
                existing_titles = {s["title"] for s in scenarios}
                for s in llm_scenarios:
                    if s.get("title") not in existing_titles:
                        scenarios.append(s)

        # Sort by potential gain descending
        scenarios.sort(key=lambda s: s.get("potential_additional_approval", 0), reverse=True)

        # Best-case projection
        best_case = min(total_billed, total_approved + rejected_amount + partial_gap)
        best_case_pct = (best_case / total_billed * 100) if total_billed > 0 else 0

        return {
            "status":                   "success",
            "decision":                 decision_str,
            "total_billed":             round(total_billed, 2),
            "currently_approved":       round(total_approved, 2),
            "total_rejected":           round(total_rejected, 2),
            "best_case_approval":       round(best_case, 2),
            "best_case_coverage_pct":   round(best_case_pct, 1),
            "rejected_item_count":      len(rejected_items),
            "partially_covered_count":  len(partial_items),
            "scenarios":                scenarios[:5],  # top 5
            "appeal_priority":          self._appeal_priority(rejected_items, partial_items),
        }

    # ── Rule-based scenarios (always runs) ────────────────────────────────
    def _build_rule_scenarios(
        self,
        rejected: list[dict],
        partial: list[dict],
        covered: list[dict],
        total_billed: float,
        total_approved: float,
        claim_result,
    ) -> list[dict]:
        scenarios = []

        # Scenario 1: Remove excluded items entirely
        if rejected:
            excluded_amount = sum(i["billed"] for i in rejected)
            rebilled = total_billed - excluded_amount
            new_approved = total_approved  # partial approvals stay the same
            scenarios.append({
                "title":                       "Remove Excluded Items",
                "description":                 (
                    f"Remove {len(rejected)} excluded item(s) from the bill. "
                    f"This reduces the bill to ₹{rebilled:,.0f} and eliminates "
                    f"₹{excluded_amount:,.0f} in disputed charges."
                ),
                "potential_additional_approval": 0.0,  # just eliminates friction
                "new_total_bill":              round(rebilled, 2),
                "new_approved_amount":         round(new_approved, 2),
                "action_items":               [
                    f"Remove '{i['item']}' (₹{i['billed']:,.0f}) — {i['reasoning'][:120]}"
                    for i in rejected[:4]
                ],
                "type": "exclusion_removal",
                "difficulty": "easy",
            })

        # Scenario 2: Appeal partial items with medical necessity letter
        if partial:
            partial_gap = sum(i["billed"] - i["approved"] for i in partial)
            scenarios.append({
                "title":                       "Appeal Partial Approvals",
                "description":                 (
                    f"Submit a medical necessity letter for {len(partial)} partially approved item(s). "
                    f"Potential additional recovery: ₹{partial_gap:,.0f}."
                ),
                "potential_additional_approval": round(partial_gap, 2),
                "new_approved_amount":         round(total_approved + partial_gap, 2),
                "action_items": [
                    f"Get medical justification for '{i['item']}' — gap: ₹{i['billed']-i['approved']:,.0f}"
                    for i in partial[:4]
                ],
                "type": "appeal_partial",
                "difficulty": "medium",
            })

        # Scenario 3: Policy upgrade analysis
        pm = getattr(claim_result, "policy_metadata", None)
        if pm and getattr(pm, "room_rent_limit_per_day", None):
            limit = pm.room_rent_limit_per_day
            room_items = [
                i for i in covered + partial + rejected
                if "room" in i["item"].lower() and i["billed"] > limit
            ]
            if room_items:
                extra = sum(i["billed"] for i in room_items) - limit * len(room_items)
                scenarios.append({
                    "title":                       "Upgrade to Higher Room Rent Policy",
                    "description":                 (
                        f"Your current policy allows ₹{limit:,.0f}/day room rent. "
                        f"Upgrading to a plan with ₹{limit*2:,.0f}/day could recover ₹{extra:,.0f}."
                    ),
                    "potential_additional_approval": round(extra, 2),
                    "new_approved_amount":         round(total_approved + extra, 2),
                    "action_items": [
                        f"Request room-rent upgrade rider from insurer",
                        f"Consider a top-up policy covering ₹{extra:,.0f}+ excess room charges",
                    ],
                    "type": "policy_upgrade",
                    "difficulty": "hard",
                })

        # Scenario 4: Resubmit with complete documentation
        has_warnings = bool(getattr(claim_result, "warnings", []))
        if has_warnings:
            scenarios.append({
                "title":                       "Resubmit with Complete Documentation",
                "description":                 (
                    "Warnings were detected during processing. "
                    "Resubmitting with complete discharge summary, doctor's notes, "
                    "and original prescriptions may improve approval."
                ),
                "potential_additional_approval": round(total_billed * 0.05, 2),  # conservative 5%
                "new_approved_amount":         round(total_approved + total_billed * 0.05, 2),
                "action_items": [
                    "Attach original discharge summary with diagnosis codes (ICD-10)",
                    "Provide prescriptions for all medications listed in the bill",
                    "Include pre-authorization reference number if surgery was planned",
                ],
                "type": "documentation",
                "difficulty": "easy",
            })

        return scenarios

    # ── LLM enrichment ────────────────────────────────────────────────────
    def _llm_enrich(
        self,
        decision_str: str,
        items: list[dict],
        total_billed: float,
        total_approved: float,
        claim_result,
    ) -> list[dict]:
        try:
            pm = getattr(claim_result, "policy_metadata", None)
            policy_limits = ""
            if pm:
                parts = []
                if getattr(pm, "sum_insured", None):
                    parts.append(f"Sum Insured: ₹{pm.sum_insured:,.0f}")
                if getattr(pm, "room_rent_limit_per_day", None):
                    parts.append(f"Room Rent Cap: ₹{pm.room_rent_limit_per_day:,.0f}/day")
                if getattr(pm, "copay_percentage", None):
                    parts.append(f"Co-pay: {pm.copay_percentage}%")
                if getattr(pm, "waiting_period_months", None):
                    parts.append(f"Waiting Period: {pm.waiting_period_months} months")
                policy_limits = " | ".join(parts)

            prompt = (
                f"You are an expert insurance appeal advisor. A claim was {decision_str}.\n"
                f"Bill: ₹{total_billed:,.0f} | Currently Approved: ₹{total_approved:,.0f}\n"
                f"Policy Limits: {policy_limits or 'Not specified'}\n\n"
                "Line items:\n"
                + json.dumps([{k: v for k, v in i.items() if k != "reasoning"} for i in items], indent=1)
                + "\n\nGenerate 2 SPECIFIC, actionable appeal scenarios not already obvious "
                "from the data above. Each must show exact rupee amounts recoverable.\n\n"
                "Respond ONLY as JSON array:\n"
                '[\n'
                '  {\n'
                '    "title": "Scenario Name",\n'
                '    "description": "What to do and why",\n'
                '    "potential_additional_approval": <number>,\n'
                '    "action_items": ["Step 1", "Step 2"],\n'
                '    "difficulty": "easy|medium|hard"\n'
                '  }\n'
                ']'
            )

            response = self.client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.4,
                ),
            )

            data = json.loads(response.text)
            if isinstance(data, dict):
                data = [data]
            if not isinstance(data, list):
                return []

            enriched = []
            for s in data:
                if isinstance(s, dict) and s.get("title"):
                    enriched.append({
                        "title":                       s.get("title", "LLM Scenario"),
                        "description":                 s.get("description", ""),
                        "potential_additional_approval": float(s.get("potential_additional_approval", 0)),
                        "new_approved_amount":         round(total_approved + float(s.get("potential_additional_approval", 0)), 2),
                        "action_items":                s.get("action_items", []),
                        "type":                        "llm_generated",
                        "difficulty":                  s.get("difficulty", "medium"),
                    })
            return enriched

        except Exception as e:
            logger.warning(f"LLM enrichment failed: {e}")
            return []

    # ── Appeal priority ranking ────────────────────────────────────────────
    @staticmethod
    def _appeal_priority(rejected: list[dict], partial: list[dict]) -> list[dict]:
        """Rank rejected/partial items by appeal worthiness."""
        candidates = []
        for item in rejected:
            candidates.append({
                "item":       item["item"],
                "amount":     item["billed"],
                "reason":     "Fully rejected — high priority for appeal",
                "page_ref":   item.get("policy_ref", ""),
                "priority":   "HIGH",
            })
        for item in partial:
            gap = item["billed"] - item["approved"]
            if gap > 500:
                candidates.append({
                    "item":     item["item"],
                    "amount":   gap,
                    "reason":   f"Partially approved — ₹{gap:,.0f} gap worth disputing",
                    "page_ref": item.get("policy_ref", ""),
                    "priority": "MEDIUM",
                })
        # Sort by amount descending
        candidates.sort(key=lambda x: x["amount"], reverse=True)
        return candidates[:6]

    @staticmethod
    def _unavailable(msg: str) -> dict:
        return {"status": "unavailable", "message": msg, "scenarios": [], "appeal_priority": []}
