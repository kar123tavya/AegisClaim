"""
AegisClaim AI - Table & Line Item Extractor
Extracts structured table data and line items from raw OCR text.
Fixes: deduplication, double-counting subtotals, currency-symbol-only rows,
       amount vs quantity confusion, and declared-total trust.
"""
import re
import logging
from typing import Optional
from .schemas import BillLineItem, BillItemCategory

logger = logging.getLogger("aegisclaim.ocr.table_extractor")


# ── Category classification keywords (multilingual) ─────────────────────────
CATEGORY_KEYWORDS = {
    BillItemCategory.ROOM_CHARGES: [
        "room", "ward", "bed", "accommodation", "room rent", "general ward",
        "private room", "semi-private", "deluxe", "suite",
        "कमरा", "habitación", "chambre", "zimmer",
    ],
    BillItemCategory.ICU_CHARGES: [
        "icu", "intensive care", "critical care", "ccu", "nicu", "picu",
        "hdu", "high dependency", "आईसीयू", "cuidados intensivos",
    ],
    BillItemCategory.SURGERY: [
        "surgery", "operation", "surgical", "o.t.", "ot charges",
        "theatre", "operative", "laparoscopy", "appendectomy",
        "cholecystectomy", "सर्जरी", "cirugía", "chirurgie",
    ],
    BillItemCategory.PROCEDURE: [
        "procedure", "endoscopy", "colonoscopy", "biopsy", "catheter",
        "dialysis", "chemotherapy", "radiation", "physiotherapy", "stent",
        "प्रक्रिया", "procedimiento",
    ],
    BillItemCategory.DIAGNOSTIC: [
        "mri", "ct scan", "x-ray", "xray", "ultrasound", "usg", "ecg",
        "eeg", "echo", "scan", "imaging", "radiology", "pet scan",
        "एमआरआई", "radiografía",
    ],
    BillItemCategory.LABORATORY: [
        "lab", "laboratory", "blood test", "cbc", "urinalysis", "pathology",
        "culture", "sensitivity", "hemoglobin", "lipid", "liver function",
        "renal", "thyroid", "hba1c", "प्रयोगशाला", "laboratorio",
    ],
    BillItemCategory.MEDICATION: [
        "medicine", "medication", "drug", "tablet", "injection", "iv fluid",
        "antibiotic", "pharmacy", "capsule", "syrup", "ointment", "insulin",
        "दवा", "medicamento", "médicament",
    ],
    BillItemCategory.CONSULTATION: [
        "consultation", "consult", "visit", "opinion", "doctor fee",
        "specialist", "physician", "surgeon fee", "anesthetist",
        "परामर्श", "consulta", "beratung",
    ],
    BillItemCategory.NURSING: [
        "nursing", "nurse", "care charge", "attendant", "नर्सिंग", "enfermería",
    ],
    BillItemCategory.SUPPLIES: [
        "supplies", "consumable", "disposable", "gloves", "syringe",
        "implant", "prosthesis", "bandage", "dressing", "आपूर्ति",
    ],
    BillItemCategory.AMBULANCE: [
        "ambulance", "transport", "emergency transport", "एम्बुलेंस",
    ],
}

# ── Lines that are guaranteed NOT individual bill items ─────────────────────
# (summary/header/tax/discount lines) — kept comprehensive to avoid double-count
SKIP_KEYWORDS = frozenset([
    # English summary terms
    "total", "subtotal", "sub total", "sub-total", "grand total",
    "net amount", "net payable", "net total", "amount due", "amount payable",
    "balance due", "balance payable", "balance amount",
    "advance", "deposit", "security deposit", "advance paid",
    "discount", "concession", "rebate", "waiver",
    "tax", "gst", "cgst", "sgst", "igst", "vat", "service tax",
    "cess", "surcharge",
    # Table headers
    "serial", "sr.no", "sl.no", "s.no", "no.", "description",
    "particular", "particulars", "item", "charges", "amount",
    "quantity", "qty", "rate", "unit", "price", "per",
    "approved", "covered", "payable",
    # Hindi
    "कुल", "उप-योग", "छूट", "कर", "अग्रिम",
    # Spanish/French
    "total general", "sous-total", "montant total",
    # Insurance-specific aggregates
    "room charges total", "icu total", "pharmacy total",
    "diagnostic total", "surgery total", "procedure total",
    "lab total", "total charges", "total bill", "total amount",
    "claim amount", "admissible amount", "approved amount",
])

# Patterns that indicate a line is a totalling row (ends with a number
# but describes a category sum rather than an individual item)
TOTALLING_RE = re.compile(
    r'\b(?:total|sub[\s\-]?total|grand|net|sum|कुल|totale|総計)\b',
    re.IGNORECASE,
)

# ── Amount extraction ─────────────────────────────────────────────────────────
_CURRENCY_RE = re.compile(
    r'(?:Rs\.?|INR|₹|USD|\$|€|£|¥|AED|SGD)',
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r'([\d,]+\.?\d{0,2})')


def _parse_amount(text: str) -> Optional[float]:
    """Parse a monetary value from a string; return None if not parseable."""
    text = _CURRENCY_RE.sub('', text).strip()
    m = _NUMBER_RE.search(text)
    if m:
        try:
            v = float(m.group(1).replace(',', ''))
            if 0.01 < v < 100_000_000:
                return v
        except ValueError:
            pass
    return None


# ── Date patterns ─────────────────────────────────────────────────────────────
DATE_PATTERNS = [
    re.compile(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'),
    re.compile(r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b'),
    re.compile(
        r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4})\b',
        re.IGNORECASE,
    ),
]


class TableExtractor:
    """Extracts structured line items and metadata from raw OCR text."""

    # ── Category classification ────────────────────────────────────────────
    @staticmethod
    def classify_category(description: str) -> BillItemCategory:
        desc_lower = description.lower()
        best, best_score = BillItemCategory.UNKNOWN, 0
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in desc_lower)
            if score > best_score:
                best_score = score
                best = category
        return best

    # ── Helper: should this line be skipped? ──────────────────────────────
    @staticmethod
    def _is_skip_line(line: str) -> bool:
        ll = line.lower().strip()
        # Exact or partial match against skip keywords
        if any(kw == ll or ll.startswith(kw + ' ') or ll.endswith(' ' + kw)
               or (' ' + kw + ' ') in ll for kw in SKIP_KEYWORDS):
            return True
        # Regex check for totalling phrases
        if TOTALLING_RE.search(ll):
            return True
        # Lines that are ONLY a number (bare numeric rows = totals)
        stripped = _CURRENCY_RE.sub('', ll).strip()
        if re.fullmatch(r'[\d,]+\.?\d{0,2}', stripped):
            return True
        return False

    # ── Metadata extraction ────────────────────────────────────────────────
    @staticmethod
    def extract_field(text: str, field_patterns: list[str]) -> Optional[str]:
        for pat_str in field_patterns:
            m = re.search(pat_str, text, re.IGNORECASE | re.MULTILINE)
            if m:
                v = m.group(1).strip()
                if v:
                    return v
        return None

    @classmethod
    def extract_metadata(cls, raw_text: str) -> dict:
        metadata = {}

        metadata["patient_name"] = cls.extract_field(raw_text, [
            r"(?:patient\s*(?:name)?|name\s*of\s*patient)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.]{2,40})(?:\n|$|\s{2,}|age)",
            r"(?:रोगी का नाम|नाम)\s*[:\-]?\s*(.+?)(?:\n|$)",
            r"(?:nombre del paciente|nombre)\s*[:\-]?\s*(.+?)(?:\n|$)",
            r"(?:mr\.|mrs\.|ms\.|master)\s+([A-Za-z][A-Za-z\s\.]{2,40})(?:\n|$|,)",
        ])

        metadata["patient_id"] = cls.extract_field(raw_text, [
            r"(?:patient\s*id|uhid|mr\s*no|mrn|registration\s*(?:no|number))\s*[:\-]?\s*([A-Za-z0-9\-/]+)",
            r"(?:रोगी आईडी|पंजीयन)\s*[:\-]?\s*([A-Za-z0-9\-]+)",
        ])

        metadata["hospital_name"] = cls.extract_field(raw_text, [
            r"^([A-Z][A-Za-z\s&\.]{3,}(?:Hospital|Medical|Healthcare|Clinic|Centre|Center|Institute|Trust))",
            r"(?:hospital|clinic|centre|center)\s*(?:name)?\s*[:\-]?\s*(.+?)(?:\n|$)",
        ])

        metadata["bill_number"] = cls.extract_field(raw_text, [
            r"(?:bill\s*(?:no\.?|number|#)|invoice\s*(?:no\.?|number|#)|receipt\s*no\.?)\s*[:\-]?\s*([A-Za-z0-9\-/]+)",
            r"(?:बिल नंबर|चालान नंबर)\s*[:\-]?\s*([A-Za-z0-9\-/]+)",
        ])

        metadata["diagnosis"] = cls.extract_field(raw_text, [
            r"(?:diagnosis|provisional\s*diagnosis|final\s*diagnosis|icd\s*code)\s*[:\-]?\s*(.+?)(?:\n|$)",
            r"(?:निदान)\s*[:\-]?\s*(.+?)(?:\n|$)",
            r"(?:admitted\s*for|reason\s*for\s*admission)\s*[:\-]?\s*(.+?)(?:\n|$)",
        ])

        metadata["treating_doctor"] = cls.extract_field(raw_text, [
            r"(?:(?:treating|attending|consulting)\s*(?:doctor|physician|surgeon|consultant))\s*[:\-]?\s*(Dr\.?\s*[A-Za-z\s\.]+?)(?:\n|$|\s{3,})",
            r"(?:Dr\.)\s+([A-Za-z][A-Za-z\s\.]{2,40})(?:\n|$|,|\s{3,})",
            r"(?:डॉक्टर)\s*[:\-]?\s*(.+?)(?:\n|$)",
        ])

        metadata["patient_age"] = cls.extract_field(raw_text, [
            r"(?:age|आयु|edad)\s*[:\-]?\s*(\d{1,3})\s*(?:years?|yrs?|yr\.?|Y)?",
            r"(\d{1,3})\s*(?:years?|yrs?)\s*(?:old)?",
        ])
        if metadata.get("patient_age"):
            try:
                metadata["patient_age"] = int(metadata["patient_age"])
            except ValueError:
                metadata.pop("patient_age", None)

        # Extract dates
        all_dates = []
        for pat in DATE_PATTERNS:
            all_dates.extend(pat.findall(raw_text))
        # Remove duplicates while preserving order
        seen_dates = []
        for d in all_dates:
            if d not in seen_dates:
                seen_dates.append(d)
        if seen_dates:
            metadata["bill_date"] = seen_dates[0]
            if len(seen_dates) > 1:
                metadata["admission_date"] = seen_dates[1]
            if len(seen_dates) > 2:
                metadata["discharge_date"] = seen_dates[2]

        return {k: v for k, v in metadata.items() if v is not None}

    # ── Line item extraction ───────────────────────────────────────────────
    @classmethod
    def extract_line_items(cls, raw_text: str) -> list[BillLineItem]:
        """
        Extract line items robustly.
        Strategy:
          1. Strip page markers.
          2. Skip known summary/header lines.
          3. Try to parse a line as: description + [qty] + [unit] + amount.
          4. Deduplicate items with identical description+amount.
          5. Prune items whose amounts account for >40% of the sum of
             all other items (likely sub-totals that slipped through).
        """
        # Strip page markers inserted by OCR engine
        clean_text = re.sub(r'\[PAGE_\d+_(?:START|END)\]', '', raw_text)
        lines = clean_text.split('\n')

        # Pattern A: desc | qty | unit_price | amount  (pipe-separated table)
        pipe_pattern = re.compile(
            r'^(?:\d+[\.\)]\s*)?'
            r'(.{3,60}?)'                       # description
            r'\s*\|\s*(\d+)\s*\|\s*'            # | qty |
            r'(?:Rs\.?|INR|₹|USD|\$|€|£)?\s*([\d,]+\.?\d{0,2})\s*\|\s*'  # unit
            r'(?:Rs\.?|INR|₹|USD|\$|€|£)?\s*([\d,]+\.?\d{0,2})\s*$',     # total
            re.IGNORECASE,
        )
        # Pattern B: desc [qty] [unit_price] amount  (space-separated)
        space_qty_pattern = re.compile(
            r'^(?:\d+[\.\)]\s*)?'
            r'(.{3,80}?)\s+'
            r'(\d{1,4})\s+'
            r'(?:Rs\.?|INR|₹|USD|\$|€|£)?\s*([\d,]+\.?\d{0,2})\s+'
            r'(?:Rs\.?|INR|₹|USD|\$|€|£)?\s*([\d,]+\.?\d{0,2})\s*$',
            re.IGNORECASE,
        )
        # Pattern C: desc amount  (simple)
        simple_pattern = re.compile(
            r'^(?:\d+[\.\)]\s*)?'
            r'(.{3,100}?)\s+'
            r'(?:Rs\.?|INR|₹|USD|\$|€|£)?\s*([\d,]+\.?\d{0,2})\s*$',
            re.IGNORECASE,
        )

        raw_items: list[BillLineItem] = []
        seen_key: set[tuple] = set()

        for raw_line in lines:
            line = raw_line.strip()
            if not line or len(line) < 4:
                continue
            if cls._is_skip_line(line):
                continue

            item: Optional[BillLineItem] = None

            # --- Try Pattern A (pipe table) ---
            m = pipe_pattern.match(line)
            if m:
                desc, qty_s, unit_s, amt_s = m.groups()
                try:
                    amt = float(amt_s.replace(',', ''))
                    qty = int(qty_s)
                    unit = float(unit_s.replace(',', ''))
                    if amt > 0 and len(desc.strip()) > 2:
                        item = BillLineItem(
                            description=desc.strip(),
                            category=cls.classify_category(desc),
                            quantity=qty,
                            unit_price=unit,
                            amount=amt,
                        )
                except (ValueError, TypeError):
                    pass

            # --- Try Pattern B (space-separated with qty) ---
            if item is None:
                m = space_qty_pattern.match(line)
                if m:
                    desc, qty_s, unit_s, amt_s = m.groups()
                    try:
                        amt = float(amt_s.replace(',', ''))
                        qty = int(qty_s)
                        unit = float(unit_s.replace(',', ''))
                        # Sanity: qty * unit should be close to amt
                        if amt > 0 and len(desc.strip()) > 2:
                            expected = qty * unit
                            ratio = min(expected, amt) / max(expected, amt) if max(expected, amt) > 0 else 0
                            if ratio > 0.5:  # reasonable match
                                item = BillLineItem(
                                    description=desc.strip(),
                                    category=cls.classify_category(desc),
                                    quantity=qty,
                                    unit_price=unit,
                                    amount=amt,
                                )
                    except (ValueError, TypeError):
                        pass

            # --- Try Pattern C (simple description + amount) ---
            if item is None:
                m = simple_pattern.match(line)
                if m:
                    desc, amt_s = m.groups()
                    try:
                        amt = float(amt_s.replace(',', ''))
                        desc_clean = desc.strip()
                        # Additional guard: description must have actual words
                        word_count = len([w for w in desc_clean.split() if len(w) > 1])
                        if amt > 0 and word_count >= 1 and len(desc_clean) > 2:
                            # Skip if desc itself looks like a totalling phrase
                            if not cls._is_skip_line(desc_clean):
                                item = BillLineItem(
                                    description=desc_clean,
                                    category=cls.classify_category(desc_clean),
                                    amount=amt,
                                )
                    except (ValueError, TypeError):
                        pass

            if item is not None:
                key = (item.description.lower()[:40], round(item.amount, 2))
                if key not in seen_key:
                    seen_key.add(key)
                    raw_items.append(item)

        # ── Post-processing: prune likely sub-totals that slipped through ──
        if len(raw_items) > 1:
            total_sum = sum(i.amount for i in raw_items)
            # If any single item is >60% of total and not the only item,
            # it's probably an erroneous sub-total row
            pruned = [
                i for i in raw_items
                if not (len(raw_items) > 2 and i.amount / total_sum > 0.6)
            ]
            if pruned:
                raw_items = pruned

        return raw_items

    # ── Total extraction ───────────────────────────────────────────────────
    @classmethod
    def extract_total(cls, raw_text: str) -> Optional[float]:
        """
        Extract the declared bill total.
        Preference: grand total > net payable > total amount > total.
        Returns the most specific declared value found.
        """
        # Ordered by specificity (most specific first)
        patterns = [
            re.compile(
                r'(?:grand\s*total|final\s*(?:bill|amount))\s*[:\-]?\s*'
                r'(?:Rs\.?|INR|₹|USD|\$|€|£)?\s*([\d,]+\.?\d{0,2})',
                re.IGNORECASE,
            ),
            re.compile(
                r'(?:net\s*(?:payable|amount|total)|amount\s*(?:due|payable))\s*[:\-]?\s*'
                r'(?:Rs\.?|INR|₹|USD|\$|€|£)?\s*([\d,]+\.?\d{0,2})',
                re.IGNORECASE,
            ),
            re.compile(
                r'(?:total\s*amount|amount\s*total|bill\s*total|bill\s*amount)\s*[:\-]?\s*'
                r'(?:Rs\.?|INR|₹|USD|\$|€|£)?\s*([\d,]+\.?\d{0,2})',
                re.IGNORECASE,
            ),
            re.compile(
                r'(?:कुल\s*राशि|कुल\s*देय|कुल)\s*[:\-]?\s*(?:₹|Rs\.?)?\s*([\d,]+\.?\d{0,2})',
                re.IGNORECASE,
            ),
            re.compile(
                r'(?:total|monto\s*total|montant\s*total)\s*[:\-]?\s*'
                r'(?:Rs\.?|INR|₹|USD|\$|€|£)?\s*([\d,]+\.?\d{0,2})',
                re.IGNORECASE,
            ),
        ]

        # Clean page markers
        clean_text = re.sub(r'\[PAGE_\d+_(?:START|END)\]', '', raw_text)

        for pat in patterns:
            matches = pat.findall(clean_text)
            best = 0.0
            for m in matches:
                try:
                    v = float(m.replace(',', ''))
                    if v > best:
                        best = v
                except ValueError:
                    continue
            if best > 0:
                return best

        return None

    # ── Reconcile total vs line items ──────────────────────────────────────
    @staticmethod
    def reconcile_total(
        line_items: list[BillLineItem],
        declared_total: Optional[float],
    ) -> tuple[list[BillLineItem], float]:
        """
        When there is a significant discrepancy between declared total and
        sum of extracted line items, trust the declared total.

        Returns (possibly pruned items, authoritative total).
        """
        if not declared_total or declared_total <= 0:
            return line_items, sum(i.amount for i in line_items)

        if not line_items:
            return line_items, declared_total

        computed = sum(i.amount for i in line_items)
        if computed <= 0:
            return line_items, declared_total

        discrepancy_ratio = abs(computed - declared_total) / max(computed, declared_total)

        # If discrepancy is > 15%, try to prune subtotal items
        if discrepancy_ratio > 0.15:
            logger.warning(
                f"Discrepancy detected: computed={computed:.2f}, declared={declared_total:.2f} "
                f"({discrepancy_ratio:.0%}). Attempting reconciliation."
            )
            # Remove items that are themselves the difference or a sum of others
            pruned = [
                item for item in line_items
                if abs(item.amount - declared_total) > 1.0  # not equal to total
                and item.amount < declared_total            # not larger than total
            ]
            if pruned:
                new_computed = sum(i.amount for i in pruned)
                new_ratio = abs(new_computed - declared_total) / max(new_computed, declared_total)
                if new_ratio < discrepancy_ratio:
                    logger.info(f"Reconciled: {len(line_items)} → {len(pruned)} items, new sum={new_computed:.2f}")
                    line_items = pruned

        return line_items, declared_total
