import logging
import json
from google import genai
from google.genai import types

from app.core.config import settings
from app.modules.ocr.schemas import ExtractedBillData, BillLineItem

logger = logging.getLogger("aegisclaim.normalization.language")

class LanguageNormalizer:
    """Detects and translates non-English OCR extractions into standardized English."""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key) if settings.google_api_key else None
        
    def normalize(self, bill_data: ExtractedBillData) -> ExtractedBillData:
        """Translate the bill data to English if it's not already."""
        if not self.client:
            logger.warning("No API key. Skipping language normalization.")
            return bill_data
            
        langs = str(bill_data.language_detected).lower()
        if not langs or "eng" in langs and len(langs) <= 3:
            # Assume it's English only
            return bill_data
            
        logger.info(f"Non-English detected ({langs}). Translating... (Warning: this adds latency)")
        
        # Determine items to translate
        try:
            items_to_translate = []
            for idx, item in enumerate(bill_data.line_items):
                items_to_translate.append(f"Item {idx}: {item.description}")
                
            prompt = f"""
            You are a medical billing translation assistant.
            Translate the following fields and list items from their source language (likely {langs}) to English.
            Retain any medical terminology accurately. Ensure line items match exactly in index.
            
            Format response as JSON:
            {{
                "patient_name": "{bill_data.patient_name}",
                "hospital_name": "{bill_data.hospital_name}",
                "diagnosis": "{bill_data.diagnosis}",
                "treating_doctor": "{bill_data.treating_doctor}",
                "translated_items": [
                    "English translation of item 0",
                    "English translation of item 1"
                ]
            }}
            
            Fields to translate:
            Patient Name: {bill_data.patient_name}
            Hospital Name: {bill_data.hospital_name}
            Diagnosis: {bill_data.diagnosis}
            Doctor: {bill_data.treating_doctor}
            
            Line Items:
            {chr(10).join(items_to_translate)}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            data = json.loads(response.text)
            
            # Create a localized copy
            localized = bill_data.model_copy(deep=True)
            localized.patient_name = data.get("patient_name", localized.patient_name)
            localized.hospital_name = data.get("hospital_name", localized.hospital_name)
            localized.diagnosis = data.get("diagnosis", localized.diagnosis)
            localized.treating_doctor = data.get("treating_doctor", localized.treating_doctor)
            
            translations = data.get("translated_items", [])
            for idx, item in enumerate(localized.line_items):
                if idx < len(translations):
                    # Annotate original language for reference
                    orig = item.description
                    item.description = f"{translations[idx]} [Orig: {orig}]"
                    
            logger.info("Language normalization complete.")
            return localized
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return bill_data
