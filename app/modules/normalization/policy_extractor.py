import logging
import json
from google import genai
from google.genai import types

from app.core.config import settings
from app.modules.policy.schemas import PolicyMetadata

logger = logging.getLogger("aegisclaim.normalization.policy_extractor")

class PolicyNormalizer:
    """Extracts definitive structured rules (limits, sublimits) from raw policy text."""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key) if settings.google_api_key else None
        
    def extract_structured_metadata(self, policy_text_sample: str, current_metadata: PolicyMetadata) -> PolicyMetadata:
        """
        Uses an LLM to extract definitive caps and limits from the policy text.
        Typically, feeding the first 3-4 pages is enough to extract the core schedule of benefits.
        """
        if not self.client:
            logger.warning("No API key. Skipping policy normalization.")
            return current_metadata
            
        logger.info("Extracting structured policy limits via LLM...")
        try:
            prompt = f"""
            Analyze the following insurance policy text (schedule of benefits) and extract hard limits.
            If a value is not explicitly stated or found, output null for it.
            
            Format response as JSON EXACTLY as follows:
            {{
                "sum_insured": <number or null>,
                "room_rent_limit_per_day": <number or null>,
                "copay_percentage": <number (0 to 100) or null>,
                "waiting_period_months": <number or null>,
                "pre_existing_waiting_years": <number or null>
            }}
            
            Policy Text Sample:
            {policy_text_sample}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-lite", # use lite for long text upfront 
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            
            data = json.loads(response.text)

            # Guard: LLM may return a list instead of a dict in edge cases
            if isinstance(data, list):
                data = data[0] if data and isinstance(data[0], dict) else {}
            if not isinstance(data, dict):
                logger.warning("LLM returned unexpected JSON structure; skipping normalization.")
                return current_metadata

            # Apply to metadata
            if data.get("sum_insured") is not None:
                current_metadata.sum_insured = float(data["sum_insured"])
            if data.get("room_rent_limit_per_day") is not None:
                current_metadata.room_rent_limit_per_day = float(data["room_rent_limit_per_day"])
            if data.get("copay_percentage") is not None:
                current_metadata.copay_percentage = float(data["copay_percentage"])
            if data.get("waiting_period_months") is not None:
                current_metadata.waiting_period_months = int(data["waiting_period_months"])
            if data.get("pre_existing_waiting_years") is not None:
                current_metadata.pre_existing_waiting_years = int(data["pre_existing_waiting_years"])

            logger.info("Successfully extracted structured policy metadata limits.")
            return current_metadata

        except Exception as e:
            logger.error(f"Policy structured extraction failed: {e}")
            return current_metadata
