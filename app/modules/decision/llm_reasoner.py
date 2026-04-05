"""
AegisClaim AI - LLM Reasoner
Uses Google Gemini (new google.genai SDK) for complex claim reasoning with clause citation.
Includes retry logic with exponential backoff for quota/rate-limit errors.
"""
import json
import logging
import time
from typing import Optional

logger = logging.getLogger("aegisclaim.decision.llm_reasoner")

# Try new SDK first, fall back to legacy
GENAI_AVAILABLE = False
_genai_client = None

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
    GENAI_SDK = "new"
except ImportError:
    try:
        import google.generativeai as genai_legacy
        GENAI_AVAILABLE = True
        GENAI_SDK = "legacy"
    except ImportError:
        logger.warning("No Google GenAI SDK available")
        GENAI_SDK = "none"

from app.core.config import settings
from app.modules.ocr.schemas import ExtractedBillData
from app.modules.policy.schemas import PolicyChunk, PolicyMetadata
from .schemas import ClaimDecision, LLMReasoningResult


# Models to try in order of preference (higher free-tier limits first)
MODEL_PRIORITY = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


class LLMReasoner:
    """
    LLM-based reasoning engine for complex and ambiguous claim decisions.
    Uses Google Gemini with the new google.genai SDK, with automatic retry
    and model fallback for quota errors.
    """

    def __init__(self):
        self.client = None
        self.model_name = MODEL_PRIORITY[0]
        self._initialize()

    def _initialize(self):
        """Initialize the Gemini client."""
        if not GENAI_AVAILABLE:
            logger.warning("Gemini SDK not available")
            return

        if not settings.google_api_key:
            logger.warning("GOOGLE_API_KEY not set")
            return

        try:
            if GENAI_SDK == "new":
                self.client = genai.Client(api_key=settings.google_api_key)
                logger.info(f"Gemini client initialized (new SDK) — models: {MODEL_PRIORITY}")
            elif GENAI_SDK == "legacy":
                genai_legacy.configure(api_key=settings.google_api_key)
                self.client = genai_legacy.GenerativeModel(self.model_name)
                logger.info(f"Gemini client initialized (legacy SDK) — model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")

    def reason(
        self,
        bill_data: ExtractedBillData,
        policy_chunks: list[PolicyChunk],
        policy_metadata: Optional[PolicyMetadata] = None,
    ) -> LLMReasoningResult:
        """
        Use LLM to reason about a claim decision.
        Retries with exponential backoff on quota errors.
        Falls back to alternative models if primary is exhausted.
        """
        if not self.client or not settings.enable_llm_reasoning:
            return LLMReasoningResult(
                decision=ClaimDecision.NEEDS_REVIEW,
                confidence=0.0,
                reasoning="LLM reasoning not available. Using rule-based evaluation only.",
                model_used="none"
            )

        prompt = self._build_prompt(bill_data, policy_chunks, policy_metadata)

        # Try each model in priority order
        for model_name in MODEL_PRIORITY:
            result = self._try_generate(prompt, model_name)
            if result is not None:
                return result

        # All models failed
        return LLMReasoningResult(
            decision=ClaimDecision.NEEDS_REVIEW,
            confidence=0.0,
            reasoning="LLM reasoning unavailable — all models returned quota errors. Using rule-based evaluation.",
            model_used="none (quota exhausted)"
        )

    def _try_generate(self, prompt: str, model_name: str, max_retries: int = 3) -> Optional[LLMReasoningResult]:
        """Try to generate with a specific model, with retries."""
        for attempt in range(max_retries):
            try:
                if GENAI_SDK == "new":
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            max_output_tokens=4096,
                        ),
                    )
                    text = response.text
                else:
                    # Legacy SDK
                    import google.generativeai as genai_legacy
                    model = genai_legacy.GenerativeModel(model_name)
                    response = model.generate_content(
                        prompt,
                        generation_config=genai_legacy.GenerationConfig(
                            temperature=0.1,
                            max_output_tokens=4096,
                        )
                    )
                    text = response.text

                result = self._parse_response(text)
                result.model_used = model_name
                logger.info(f"LLM reasoning succeeded with {model_name} (attempt {attempt+1})")
                return result

            except Exception as e:
                error_str = str(e)
                is_quota_error = any(kw in error_str.lower() for kw in [
                    "429", "quota", "rate", "resource exhausted", "resourceexhausted"
                ])

                if is_quota_error:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        f"Quota error on {model_name} (attempt {attempt+1}/{max_retries}). "
                        f"Retrying in {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"LLM generation error on {model_name}: {e}")
                    # Non-quota error — return failure
                    return LLMReasoningResult(
                        decision=ClaimDecision.NEEDS_REVIEW,
                        confidence=0.0,
                        reasoning=f"LLM error ({model_name}): {error_str[:500]}",
                        model_used=model_name
                    )

        # All retries exhausted for this model
        logger.warning(f"All retries exhausted for {model_name}")
        return None

    def _build_prompt(
        self,
        bill_data: ExtractedBillData,
        policy_chunks: list[PolicyChunk],
        policy_metadata: Optional[PolicyMetadata],
    ) -> str:
        """Build a structured prompt for the LLM."""

        # Format bill data
        bill_items_str = ""
        for item in bill_data.line_items:
            bill_items_str += f"  - {item.description} ({item.category.value}): ₹{item.amount:,.2f}\n"

        if not bill_items_str:
            bill_items_str = "  No line items extracted\n"

        # Format policy chunks with page numbers
        policy_context = ""
        for i, chunk in enumerate(policy_chunks, 1):
            section = chunk.section.value if hasattr(chunk.section, 'value') else chunk.section
            policy_context += (
                f"\n--- Policy Clause #{i} (Page {chunk.page_number}, Section: {section}) ---\n"
                f"{chunk.text}\n"
            )

        if not policy_context:
            policy_context = "No specific policy clauses retrieved.\n"

        # Format metadata
        metadata_str = "Not available"
        if policy_metadata:
            parts = []
            if policy_metadata.sum_insured:
                parts.append(f"Sum Insured: ₹{policy_metadata.sum_insured:,.2f}")
            if policy_metadata.room_rent_limit_per_day:
                parts.append(f"Room Rent Limit: ₹{policy_metadata.room_rent_limit_per_day:,.0f}/day")
            if policy_metadata.copay_percentage:
                parts.append(f"Co-pay: {policy_metadata.copay_percentage}%")
            if policy_metadata.waiting_period_months:
                parts.append(f"Waiting Period: {policy_metadata.waiting_period_months} months")
            if policy_metadata.pre_existing_waiting_years:
                parts.append(f"Pre-existing Waiting: {policy_metadata.pre_existing_waiting_years} years")
            if parts:
                metadata_str = "\n  ".join(parts)

        prompt = f"""You are an expert insurance claim adjudicator. Analyze the following medical insurance claim and make a decision.

## HOSPITAL BILL DATA
- Patient: {bill_data.patient_name or 'Unknown'}
- Hospital: {bill_data.hospital_name or 'Unknown'}
- Diagnosis: {bill_data.diagnosis or 'Not specified'}
- Bill Date: {bill_data.bill_date or 'Unknown'}
- Admission: {bill_data.admission_date or 'Unknown'}
- Discharge: {bill_data.discharge_date or 'Unknown'}
- Total Amount: ₹{bill_data.total_amount:,.2f}

### Bill Line Items:
{bill_items_str}

## POLICY INFORMATION
### Key Policy Parameters:
  {metadata_str}

### Relevant Policy Clauses (Retrieved from policy document):
{policy_context}

## YOUR TASK
Analyze this claim and respond in the following EXACT JSON format:

{{
    "decision": "APPROVED" or "REJECTED" or "NEEDS_REVIEW" or "PARTIALLY_APPROVED",
    "confidence": <number 0-100>,
    "reasoning": "<detailed natural language explanation of the decision>",
    "item_analyses": [
        {{
            "item": "<bill item description>",
            "amount": <amount>,
            "approved_amount": <approved amount>,
            "status": "COVERED" or "NOT_COVERED" or "PARTIALLY_COVERED",
            "reason": "<why this item is covered/not covered>",
            "clause_reference": "<exact clause text from policy>",
            "page_number": <page number where clause was found>
        }}
    ],
    "cited_clauses": [
        {{
            "clause_text": "<exact text from policy>",
            "page": <page number>,
            "section": "<section name>",
            "relevance": "<how this clause applies to the decision>"
        }}
    ],
    "risk_factors": ["<list of risk factors or concerns>"]
}}

## IMPORTANT RULES:
1. You MUST cite specific policy clauses with page numbers for every decision point
2. Be conservative - if uncertain, recommend NEEDS_REVIEW
3. Consider all bill items individually
4. Check for exclusions, coverage limits, room rent caps, and pre-existing conditions
5. Provide clear, auditable reasoning that could be reviewed by a human adjudicator
6. If policy context is insufficient, state so explicitly and recommend review
7. Calculate approved amounts precisely based on policy sub-limits

Respond ONLY with the JSON object, no additional text."""

        return prompt

    def _parse_response(self, response_text: str) -> LLMReasoningResult:
        """Parse LLM response into structured result."""
        try:
            # Clean response — remove markdown code blocks if present
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])

            data = json.loads(cleaned)

            # Map decision string to enum
            decision_map = {
                "APPROVED": ClaimDecision.APPROVED,
                "REJECTED": ClaimDecision.REJECTED,
                "NEEDS_REVIEW": ClaimDecision.NEEDS_REVIEW,
                "PARTIALLY_APPROVED": ClaimDecision.PARTIALLY_APPROVED,
            }

            return LLMReasoningResult(
                decision=decision_map.get(data.get("decision", "NEEDS_REVIEW"), ClaimDecision.NEEDS_REVIEW),
                confidence=float(data.get("confidence", 50)),
                reasoning=data.get("reasoning", ""),
                item_analyses=data.get("item_analyses", []),
                cited_clauses=data.get("cited_clauses", []),
                risk_factors=data.get("risk_factors", []),
                model_used=""
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            # Extract what we can from the raw text
            decision = ClaimDecision.NEEDS_REVIEW
            if "APPROVED" in response_text.upper():
                decision = ClaimDecision.APPROVED
            elif "REJECTED" in response_text.upper():
                decision = ClaimDecision.REJECTED

            return LLMReasoningResult(
                decision=decision,
                confidence=40.0,
                reasoning=response_text[:2000],
                model_used=""
            )
