"""
AegisClaim AI - OCR Engine
Multi-language OCR engine with Tesseract + PDF fallback.
"""
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aegisclaim.ocr.engine")

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

from app.core.config import settings
from .preprocessor import ImagePreprocessor
from .table_extractor import TableExtractor
from .schemas import ExtractedBillData, OCRResult, BillLineItem


class OCREngine:
    """
    Multi-language OCR engine using Tesseract with intelligent fallback.
    
    Supports: English, Hindi, Spanish, French, German, Arabic, 
    Chinese (Simplified), Japanese, and more via Tesseract language packs.
    """

    def __init__(self):
        if TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path
        self.supported_languages = settings.supported_languages
        self.preprocessor = ImagePreprocessor()

    def process_document(
        self, 
        file_path: str, 
        language: Optional[str] = None
    ) -> OCRResult:
        """
        Process a bill document (image or PDF) and extract structured data.
        
        Args:
            file_path: Path to the document file
            language: Specific language code (e.g., 'eng', 'hin', 'spa')
                     If None, auto-detects or uses all configured languages
        
        Returns:
            OCRResult with structured bill data
        """
        start_time = time.time()
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        suffix = path.suffix.lower()
        
        if suffix == '.pdf':
            raw_text, pages = self._process_pdf(path, language)
        elif suffix in ('.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.webp'):
            raw_text = self._process_image(path, language)
            pages = 1
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        # Determine language used
        lang_used = language or self._detect_language(raw_text)

        # Extract structured data
        bill_data = self._extract_structured_data(raw_text)
        
        processing_time = (time.time() - start_time) * 1000

        return OCRResult(
            bill_data=bill_data,
            processing_time_ms=round(processing_time, 2),
            ocr_engine="tesseract" if TESSERACT_AVAILABLE else "pdfplumber",
            pages_processed=pages,
            language_used=lang_used,
            source_file=str(path.name)
        )

    @staticmethod
    def _page_markers(page_num: int, body: str) -> str:
        """Wrap page content with strict markers so downstream can resolve exact page numbers."""
        return f"\n[PAGE_{page_num}_START]\n{body}\n[PAGE_{page_num}_END]\n"

    def _process_pdf(self, path: Path, language: Optional[str] = None) -> tuple[str, int]:
        """Process PDF document — tries text extraction first, falls back to OCR."""
        page_chunks: list[str] = []
        pages = 0

        # First try: direct text extraction with pdfplumber (for digital PDFs)
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(str(path)) as pdf:
                    pages = len(pdf.pages)
                    for page_num, page in enumerate(pdf.pages, start=1):
                        parts: list[str] = []
                        text = page.extract_text() or ""
                        if text.strip():
                            parts.append(text)

                        tables = page.extract_tables()
                        for table in tables:
                            if table:
                                for row in table:
                                    row_text = " | ".join(
                                        str(cell) if cell else "" for cell in row
                                    )
                                    parts.append(row_text)

                        body = "\n".join(parts) if parts else ""
                        page_chunks.append(self._page_markers(page_num, body))
            except Exception as e:
                logger.warning(f"pdfplumber extraction failed: {e}")

        joined = "\n".join(page_chunks) if page_chunks else ""
        if page_chunks and len(joined.strip()) > 100:
            return joined, pages

        # Fallback: OCR via pdf2image + tesseract
        if PDF2IMAGE_AVAILABLE and TESSERACT_AVAILABLE:
            try:
                images = convert_from_path(str(path), dpi=300)
                pages = len(images)
                page_chunks = []
                lang = language or settings.ocr_languages
                for page_num, img in enumerate(images, start=1):
                    img_path = str(path.parent / "_temp_page.png")
                    img.save(img_path)
                    try:
                        processed = self.preprocessor.preprocess(img_path, lang.split("+")[0])
                        text = pytesseract.image_to_string(processed, lang=lang)
                    finally:
                        Path(img_path).unlink(missing_ok=True)
                    body = text or ""
                    page_chunks.append(self._page_markers(page_num, body))
                return "\n".join(page_chunks), pages
            except Exception as e:
                logger.error(f"PDF OCR failed: {e}")

        if not page_chunks:
            return "Unable to extract text from PDF", 0
        return "\n".join(page_chunks), pages

    def _process_image(self, path: Path, language: Optional[str] = None) -> str:
        """Process image file with OCR."""
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("Tesseract is not available for image OCR")

        lang = language or settings.ocr_languages
        
        try:
            # Preprocess image
            processed = self.preprocessor.preprocess(str(path), lang.split('+')[0])
            
            # Run OCR with configured languages
            text = pytesseract.image_to_string(
                processed, 
                lang=lang,
                config='--oem 3 --psm 6'  # LSTM engine, assume block of text
            )
            
            return text
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            # Try without preprocessing
            try:
                img = Image.open(str(path))
                return pytesseract.image_to_string(img, lang=lang)
            except Exception as e2:
                logger.error(f"Fallback OCR also failed: {e2}")
                return ""

    def _detect_language(self, text: str) -> str:
        """Simple language detection based on character ranges."""
        if not text:
            return "eng"
        
        # Check for specific scripts
        devanagari = sum(1 for c in text if '\u0900' <= c <= '\u097F')
        arabic = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        cjk = sum(1 for c in text if '\u4E00' <= c <= '\u9FFF')
        japanese = sum(1 for c in text if '\u3040' <= c <= '\u309F' or '\u30A0' <= c <= '\u30FF')
        tamil = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
        telugu = sum(1 for c in text if '\u0C00' <= c <= '\u0C7F')
        bengali = sum(1 for c in text if '\u0980' <= c <= '\u09FF')
        
        total = len(text)
        threshold = 0.1  # 10% of characters
        
        if devanagari / max(total, 1) > threshold:
            return "hin"
        elif arabic / max(total, 1) > threshold:
            return "ara"
        elif cjk / max(total, 1) > threshold:
            return "chi_sim"
        elif japanese / max(total, 1) > threshold:
            return "jpn"
        elif tamil / max(total, 1) > threshold:
            return "tam"
        elif telugu / max(total, 1) > threshold:
            return "tel"
        elif bengali / max(total, 1) > threshold:
            return "ben"
        
        return "eng"

    def _extract_structured_data(self, raw_text: str) -> ExtractedBillData:
        """Convert raw OCR text into structured bill data."""
        warnings = []

        if not raw_text or len(raw_text.strip()) < 20:
            warnings.append("Very little text extracted — document may be low quality")
            return ExtractedBillData(
                raw_text=raw_text,
                extraction_confidence=0.1,
                warnings=warnings
            )

        # Extract metadata
        metadata = TableExtractor.extract_metadata(raw_text)

        # Extract line items (pre-filtered)
        line_items = TableExtractor.extract_line_items(raw_text)

        # Extract declared total
        declared_total = TableExtractor.extract_total(raw_text)

        # Reconcile: if discrepancy, prune subtotal rows and use declared total
        line_items, authoritative_total = TableExtractor.reconcile_total(line_items, declared_total)

        # Final total: use declared > reconciled sum
        total = authoritative_total or sum(i.amount for i in line_items)

        # Re-check for warnings after reconciliation
        if not line_items:
            warnings.append("No line items could be extracted")
        if not declared_total:
            warnings.append("Total amount not explicitly stated in document")
        else:
            computed = sum(i.amount for i in line_items)
            ratio = abs(computed - declared_total) / max(declared_total, 1)
            if ratio > 0.15:
                warnings.append(
                    f"Residual discrepancy after reconciliation: "
                    f"items sum ₹{computed:,.2f} vs declared ₹{declared_total:,.2f}"
                )
        if not metadata.get("patient_name"):
            warnings.append("Patient name not found in document")
        if not metadata.get("hospital_name"):
            warnings.append("Hospital name not found in document")

        # Calculate confidence
        confidence = self._calculate_confidence(metadata, line_items, total, raw_text)

        # Build patient_age safely
        patient_age = metadata.get("patient_age")
        if isinstance(patient_age, str):
            try:
                patient_age = int(patient_age)
            except ValueError:
                patient_age = None

        return ExtractedBillData(
            patient_name=metadata.get("patient_name"),
            patient_id=metadata.get("patient_id"),
            patient_age=patient_age,
            hospital_name=metadata.get("hospital_name"),
            hospital_address=metadata.get("hospital_address"),
            bill_number=metadata.get("bill_number"),
            bill_date=metadata.get("bill_date"),
            admission_date=metadata.get("admission_date"),
            discharge_date=metadata.get("discharge_date"),
            diagnosis=metadata.get("diagnosis"),
            treating_doctor=metadata.get("treating_doctor"),
            line_items=line_items,
            total_amount=round(total, 2),
            raw_text=raw_text,
            extraction_confidence=confidence,
            language_detected=self._detect_language(raw_text),
            warnings=warnings
        )


    def _calculate_confidence(
        self,
        metadata: dict,
        line_items: list[BillLineItem],
        total: Optional[float],
        raw_text: str
    ) -> float:
        """Calculate extraction confidence score (0.0 - 1.0)."""
        score = 0.0
        max_score = 0.0

        # Metadata completeness (40%)
        key_fields = ["patient_name", "hospital_name", "bill_number", "bill_date", "diagnosis"]
        for field in key_fields:
            max_score += 8
            if metadata.get(field):
                score += 8

        # Line items (30%)
        max_score += 30
        if line_items:
            score += min(30, len(line_items) * 5)

        # Total amount (10%)
        max_score += 10
        if total and total > 0:
            score += 10

        # Total validation (10%): reward small discrepancy
        max_score += 10
        if line_items and total and total > 0:
            computed = sum(item.amount for item in line_items)
            if computed > 0:
                ratio = min(computed, total) / max(computed, total)
                score += ratio * 10

        # Text quality (10%)
        max_score += 10
        if raw_text:
            if len(raw_text) > 200:
                score += 5
            if '\n' in raw_text and len(raw_text.split('\n')) > 5:
                score += 5

        return round(min(score / max(max_score, 1), 1.0), 2)
