"""
AegisClaim AI - Claims API Endpoints
"""
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

logger = logging.getLogger("aegisclaim.api.claims")

from app.core.config import settings
from app.core.security import SecureDocumentHandler
from app.services.claim_processor import ClaimProcessor

router = APIRouter()

# Global processor instance
_processor = None
_doc_handler = SecureDocumentHandler()


def get_processor() -> ClaimProcessor:
    global _processor
    if _processor is None:
        _processor = ClaimProcessor()
    return _processor


@router.post("/process")
async def process_claim(
    bill: UploadFile = File(..., description="Hospital bill (PDF/image)"),
    policy: UploadFile = File(..., description="Insurance policy PDF"),
    language: Optional[str] = Form(None, description="OCR language code (e.g., eng, hin, spa)"),
):
    """
    Process a complete insurance claim.
    Upload a hospital bill and insurance policy to get a decision with full explanation.
    """
    processor = get_processor()
    
    try:
        # Save uploaded files
        bill_content = await bill.read()
        policy_content = await policy.read()
        
        # Validate file sizes
        max_size = settings.max_upload_size_mb * 1024 * 1024
        if len(bill_content) > max_size:
            raise HTTPException(400, f"Bill file too large (max {settings.max_upload_size_mb}MB)")
        if len(policy_content) > max_size:
            raise HTTPException(400, f"Policy file too large (max {settings.max_upload_size_mb}MB)")
        
        bill_path = await _doc_handler.save_upload(bill_content, bill.filename)
        policy_path = await _doc_handler.save_upload(policy_content, policy.filename)
        
        # Process claim
        result = await processor.process_claim(
            str(bill_path), str(policy_path), language
        )
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Claim processing error: {e}")
        raise HTTPException(500, f"Processing failed: {str(e)}")
    finally:
        _doc_handler.cleanup()


@router.post("/ocr")
async def extract_bill_data(
    bill: UploadFile = File(..., description="Hospital bill (PDF/image)"),
    language: Optional[str] = Form(None, description="OCR language code"),
):
    """Extract structured data from a hospital bill using OCR."""
    processor = get_processor()
    
    try:
        bill_content = await bill.read()
        bill_path = await _doc_handler.save_upload(bill_content, bill.filename)
        
        result = processor.process_bill_only(str(bill_path), language)
        
        return {
            "bill_data": result.bill_data.model_dump(),
            "ocr_engine": result.ocr_engine,
            "processing_time_ms": result.processing_time_ms,
            "language_used": result.language_used,
            "pages_processed": result.pages_processed,
        }
    except Exception as e:
        logger.error(f"OCR error: {e}")
        raise HTTPException(500, f"OCR failed: {str(e)}")
    finally:
        _doc_handler.cleanup()


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported OCR languages."""
    return {
        "supported_languages": settings.supported_languages,
        "language_names": settings.language_names,
        "configured": settings.ocr_languages,
    }
