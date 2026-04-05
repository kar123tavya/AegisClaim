"""
AegisClaim AI - Policy PDF Parser
Extracts text from insurance policy PDFs with page tracking and section detection.
"""
import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aegisclaim.policy.parser")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

from .schemas import PolicySection, PolicyMetadata


# Section detection patterns (multilingual)
SECTION_PATTERNS = {
    PolicySection.COVERAGE: [
        r"(?:scope\s+of\s+)?coverage",
        r"what\s+is\s+covered",
        r"covered\s+(?:benefits|services|treatments)",
        r"inclusions",
        r"benefits?\s+(?:covered|schedule|summary)",
        r"कवरेज", r"cobertura", r"couverture",
    ],
    PolicySection.EXCLUSIONS: [
        r"exclusions?",
        r"what\s+is\s+not\s+covered",
        r"not\s+covered",
        r"excluded\s+(?:conditions|treatments|services)",
        r"permanant?\s+exclusions?",
        r"बहिष्करण", r"exclusiones", r"exclusions",
    ],
    PolicySection.LIMITS: [
        r"(?:coverage\s+)?limits?",
        r"(?:sum\s+)?(?:insured|assured)",
        r"maximum\s+(?:benefit|coverage|limit)",
        r"(?:annual|lifetime)\s+limit",
        r"सीमा", r"límites", r"limites",
    ],
    PolicySection.SUB_LIMITS: [
        r"sub[\s\-]?limits?",
        r"room\s+rent\s+(?:limit|cap|ceiling)",
        r"per\s+(?:day|claim)\s+limit",
        r"proportionate\s+deduction",
    ],
    PolicySection.DEFINITIONS: [
        r"definitions?",
        r"glossary",
        r"key\s+terms",
        r"interpretation",
        r"परिभाषाएं", r"definiciones", r"définitions",
    ],
    PolicySection.WAITING_PERIOD: [
        r"waiting\s+period",
        r"initial\s+waiting",
        r"pre[\s\-]?existing\s+(?:disease|condition)",
        r"moratorium\s+period",
        r"प्रतीक्षा अवधि", r"período de espera",
    ],
    PolicySection.COPAY: [
        r"co[\s\-]?pay(?:ment)?",
        r"deductible",
        r"excess",
        r"cost[\s\-]?sharing",
        r"सह-भुगतान", r"copago",
    ],
    PolicySection.CLAIMS_PROCESS: [
        r"claim(?:s)?\s+(?:process|procedure|filing|settlement)",
        r"how\s+to\s+(?:file|make|submit)\s+a?\s*claim",
        r"reimbursement\s+(?:process|procedure)",
        r"दावा प्रक्रिया", r"proceso de reclamación",
    ],
    PolicySection.PRE_AUTHORIZATION: [
        r"pre[\s\-]?auth(?:orization|orisation)?",
        r"prior\s+(?:approval|authorization)",
        r"cashless\s+(?:process|procedure|facility)",
        r"पूर्व-प्राधिकरण", r"preautorización",
    ],
    PolicySection.NETWORK: [
        r"network\s+(?:hospital|provider)",
        r"empanelled\s+hospital",
        r"preferred\s+provider",
        r"tie[\s\-]?up\s+hospital",
        r"नेटवर्क अस्पताल",
    ],
}


class PolicyParser:
    """
    Extracts and structures text from insurance policy PDFs.
    Preserves page numbers and section context.
    """

    @staticmethod
    def parse_pdf(file_path: str) -> tuple[list[dict], PolicyMetadata]:
        """
        Extract text from PDF with page numbers and section detection.
        
        Args:
            file_path: Path to the policy PDF
            
        Returns:
            Tuple of (pages_data, metadata) where pages_data contains
            {'page': int, 'text': str, 'section': str} entries
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Policy file not found: {file_path}")

        pages_data = []
        
        if PDFPLUMBER_AVAILABLE:
            pages_data = PolicyParser._extract_with_pdfplumber(path)
        elif PYPDF2_AVAILABLE:
            pages_data = PolicyParser._extract_with_pypdf2(path)
        else:
            raise RuntimeError("No PDF extraction library available")

        # Detect sections
        pages_with_sections = PolicyParser._assign_sections(pages_data)
        
        # Extract metadata
        all_text = "\n".join(p["text"] for p in pages_with_sections)
        metadata = PolicyParser._extract_metadata(all_text, len(pages_with_sections))

        return pages_with_sections, metadata

    @staticmethod
    def _extract_with_pdfplumber(path: Path) -> list[dict]:
        """Extract using pdfplumber (preserves layout better)."""
        pages = []
        try:
            with pdfplumber.open(str(path)) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    
                    # Also extract tables
                    tables = page.extract_tables()
                    table_text = ""
                    for table in tables:
                        if table:
                            for row in table:
                                cells = [str(c) if c else "" for c in row]
                                table_text += " | ".join(cells) + "\n"
                    
                    full_text = text
                    if table_text:
                        full_text += "\n[TABLE]\n" + table_text
                    
                    pages.append({
                        "page": i + 1,
                        "text": full_text,
                        "section": PolicySection.GENERAL.value
                    })
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
        
        return pages

    @staticmethod
    def _extract_with_pypdf2(path: Path) -> list[dict]:
        """Fallback extraction using PyPDF2."""
        pages = []
        try:
            reader = PdfReader(str(path))
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append({
                    "page": i + 1,
                    "text": text,
                    "section": PolicySection.GENERAL.value
                })
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
        
        return pages

    @staticmethod
    def _assign_sections(pages_data: list[dict]) -> list[dict]:
        """Detect and assign section labels to each page."""
        current_section = PolicySection.GENERAL
        
        for page_data in pages_data:
            text = page_data["text"]
            detected = PolicyParser._detect_section(text)
            if detected:
                current_section = detected
            page_data["section"] = current_section.value
        
        return pages_data

    @staticmethod
    def _detect_section(text: str) -> Optional[PolicySection]:
        """Detect the primary section of a text block."""
        text_lower = text.lower()
        best_section = None
        best_score = 0
        
        for section, patterns in SECTION_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                score += len(matches)
            
            if score > best_score:
                best_score = score
                best_section = section
        
        return best_section if best_score > 0 else None

    @staticmethod
    def _extract_metadata(full_text: str, total_pages: int) -> PolicyMetadata:
        """Extract key policy metadata from the full text."""
        metadata = PolicyMetadata(total_pages=total_pages)
        
        # Sum insured
        sum_patterns = [
            r"sum\s+(?:insured|assured)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?(?:\s*(?:lakhs?|lacs?|crore))?)",
            r"(?:coverage|policy)\s+(?:amount|limit)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?(?:\s*(?:lakhs?|lacs?|crore))?)",
        ]
        for pattern in sum_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(",", "")
                try:
                    value = float(re.match(r'[\d.]+', value_str).group())
                    if 'crore' in value_str.lower():
                        value *= 10_000_000
                    elif 'lakh' in value_str.lower() or 'lac' in value_str.lower():
                        value *= 100_000
                    metadata.sum_insured = value
                except (ValueError, AttributeError):
                    pass
                break

        # Room rent limit
        room_patterns = [
            r"room\s+rent\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+)\s*(?:per\s+day|/\s*day|daily)",
            r"(?:room\s+(?:rent|charge)\s+(?:limit|cap|ceiling))\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d,]+)",
        ]
        for pattern in room_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    metadata.room_rent_limit_per_day = float(match.group(1).replace(",", ""))
                except ValueError:
                    pass
                break

        # Copay
        copay_match = re.search(
            r"co[\-\s]?pay(?:ment)?\s*[:\-]?\s*(\d+)\s*%",
            full_text, re.IGNORECASE
        )
        if copay_match:
            metadata.copay_percentage = float(copay_match.group(1))

        # Waiting period
        waiting_match = re.search(
            r"(?:initial\s+)?waiting\s+period\s*[:\-]?\s*(\d+)\s*(?:months?|days?)",
            full_text, re.IGNORECASE
        )
        if waiting_match:
            metadata.waiting_period_months = int(waiting_match.group(1))

        # Pre-existing waiting
        pre_existing_match = re.search(
            r"pre[\-\s]?existing\s+(?:disease|condition)\s+.*?(\d+)\s*(?:years?|months?)",
            full_text, re.IGNORECASE
        )
        if pre_existing_match:
            val = int(pre_existing_match.group(1))
            if "month" in full_text[pre_existing_match.start():pre_existing_match.end()+10].lower():
                val = val // 12
            metadata.pre_existing_waiting_years = val

        # Policy name
        name_match = re.search(
            r"(?:policy\s+name|plan\s+name|product\s+name)\s*[:\-]?\s*(.+?)(?:\n|$)",
            full_text, re.IGNORECASE
        )
        if name_match:
            metadata.policy_name = name_match.group(1).strip()

        # Insurer name
        insurer_match = re.search(
            r"(?:^|\n)([A-Z][A-Za-z\s]+(?:Insurance|Assurance|Life|Health|General)\s*(?:Company|Corp|Ltd|Limited|Co))",
            full_text
        )
        if insurer_match:
            metadata.insurer_name = insurer_match.group(1).strip()

        return metadata
