"""
AegisClaim AI - OCR Data Schemas
Pydantic models for structured bill data extraction.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum
from datetime import date

# Literal keeps settlement outcomes aligned with decision.schemas.ClaimDecision without a circular import.
ClaimOutcomeLiteral = Literal["APPROVED", "REJECTED", "NEEDS_REVIEW", "PARTIALLY_APPROVED"]


class BillItemCategory(str, Enum):
    ROOM_CHARGES = "room_charges"
    ICU_CHARGES = "icu_charges"
    PROCEDURE = "procedure"
    SURGERY = "surgery"
    DIAGNOSTIC = "diagnostic"
    LABORATORY = "laboratory"
    MEDICATION = "medication"
    CONSULTATION = "consultation"
    NURSING = "nursing"
    SUPPLIES = "supplies"
    AMBULANCE = "ambulance"
    MISCELLANEOUS = "miscellaneous"
    UNKNOWN = "unknown"


class BillLineItem(BaseModel):
    """A single line item from a hospital bill."""
    description: str = Field(..., description="Item description")
    category: BillItemCategory = Field(default=BillItemCategory.UNKNOWN)
    quantity: Optional[int] = Field(default=1)
    unit_price: Optional[float] = Field(default=None)
    amount: float = Field(..., description="Total amount for this item")
    billing_code: Optional[str] = Field(default=None, description="Medical billing code if present")


class ExtractedBillData(BaseModel):
    """Structured data extracted from a hospital bill."""
    patient_name: Optional[str] = Field(default=None)
    patient_id: Optional[str] = Field(default=None)
    patient_age: Optional[int] = Field(default=None)
    hospital_name: Optional[str] = Field(default=None)
    hospital_address: Optional[str] = Field(default=None)
    bill_number: Optional[str] = Field(default=None)
    bill_date: Optional[str] = Field(default=None)
    admission_date: Optional[str] = Field(default=None)
    discharge_date: Optional[str] = Field(default=None)
    diagnosis: Optional[str] = Field(default=None)
    treating_doctor: Optional[str] = Field(default=None)
    line_items: list[BillLineItem] = Field(default_factory=list)
    subtotal: Optional[float] = Field(default=None)
    tax: Optional[float] = Field(default=None)
    discount: Optional[float] = Field(default=None)
    total_amount: float = Field(default=0.0)
    currency: str = Field(default="INR")
    raw_text: Optional[str] = Field(default=None, description="Raw OCR text")
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    language_detected: Optional[str] = Field(default="eng")
    warnings: list[str] = Field(default_factory=list)

    @property
    def computed_total(self) -> float:
        """Sum of all line items."""
        return sum(item.amount for item in self.line_items)

    @property
    def total_discrepancy(self) -> float:
        """Difference between stated total and computed total."""
        if self.total_amount > 0:
            return abs(self.total_amount - self.computed_total)
        return 0.0


class OCRResult(BaseModel):
    """Full OCR processing result."""
    bill_data: ExtractedBillData
    processing_time_ms: float = 0.0
    ocr_engine: str = "tesseract"
    pages_processed: int = 1
    language_used: str = "eng"
    source_file: Optional[str] = None


class ExtractedTextBlock(BaseModel):
    """A segment of extracted text with stable page and paragraph indices."""
    text: str = Field(..., description="Paragraph or block text")
    page_number: int = Field(..., ge=1, description="1-based page number")
    paragraph_index: int = Field(..., ge=0, description="Paragraph index within the page")


class PolicyDocumentData(BaseModel):
    """Structured policy document content for settlement and retrieval."""
    raw_text: str = Field(..., description="Full text including PAGE_* markers when from PDF")
    blocks: list[ExtractedTextBlock] = Field(default_factory=list)
    total_pages: int = Field(default=0, ge=0)
    source_file: Optional[str] = None


class RejectionCitation(BaseModel):
    """Pinpoints policy language supporting a rejection."""
    page: int = Field(..., ge=1, description="Exact 1-based page number")
    paragraph: int = Field(..., ge=0, description="Paragraph index on that page")
    exact_clause_text: str = Field(..., description="Verbatim policy clause text from the cited block")
    reasoning: str = Field(..., description="Why this citation supports the rejection")


class ClaimDecision(BaseModel):
    """Claim settlement output with mandatory page-level rejection citations."""
    outcome: ClaimOutcomeLiteral = Field(..., description="Final claim disposition")
    rejection_citations: list[RejectionCitation] = Field(default_factory=list)
    reasoning_summary: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
