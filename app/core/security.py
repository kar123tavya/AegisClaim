"""
AegisClaim AI - Security & Privacy Module
Handles PII anonymization, safe document handling, and data protection.
"""
import re
import hashlib
import os
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime


class Anonymizer:
    """Anonymizes personally identifiable information (PII) in text and structured data."""
    
    # PII patterns for detection and masking
    PII_PATTERNS = {
        "email": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        "phone": re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
        "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        "aadhaar": re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b'),
        "pan": re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'),
        "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
        "date_of_birth": re.compile(r'\b(?:DOB|Date of Birth|D\.O\.B\.?)\s*:?\s*\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}', re.IGNORECASE),
        "ip_address": re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
    }
    
    MASK_MAP = {
        "email": "[EMAIL_REDACTED]",
        "phone": "[PHONE_REDACTED]",
        "ssn": "[SSN_REDACTED]",
        "aadhaar": "[AADHAAR_REDACTED]",
        "pan": "[PAN_REDACTED]",
        "credit_card": "[CC_REDACTED]",
        "date_of_birth": "[DOB_REDACTED]",
        "ip_address": "[IP_REDACTED]",
    }
    
    @classmethod
    def anonymize_text(cls, text: str, categories: Optional[list[str]] = None) -> str:
        """
        Mask PII in text.
        
        Args:
            text: Input text containing potential PII
            categories: Optional list of PII categories to mask. If None, masks all.
            
        Returns:
            Anonymized text with PII replaced by category markers.
        """
        if not text:
            return text
            
        categories = categories or list(cls.PII_PATTERNS.keys())
        anonymized = text
        
        for category in categories:
            if category in cls.PII_PATTERNS:
                pattern = cls.PII_PATTERNS[category]
                mask = cls.MASK_MAP[category]
                anonymized = pattern.sub(mask, anonymized)
        
        return anonymized
    
    @classmethod
    def anonymize_dict(cls, data: dict, sensitive_keys: Optional[list[str]] = None) -> dict:
        """
        Anonymize sensitive fields in a dictionary.
        
        Args:
            data: Dictionary potentially containing PII
            sensitive_keys: Keys whose values should be fully masked
            
        Returns:
            Dictionary with sensitive values masked
        """
        default_sensitive = {"patient_name", "patient_id", "phone", "email", 
                           "address", "ssn", "aadhaar", "pan_number"}
        keys_to_mask = set(sensitive_keys) if sensitive_keys else default_sensitive
        
        anonymized = {}
        for key, value in data.items():
            if key.lower() in keys_to_mask:
                if isinstance(value, str):
                    anonymized[key] = cls._hash_value(value)
                else:
                    anonymized[key] = "[REDACTED]"
            elif isinstance(value, str):
                anonymized[key] = cls.anonymize_text(value)
            elif isinstance(value, dict):
                anonymized[key] = cls.anonymize_dict(value, sensitive_keys)
            elif isinstance(value, list):
                anonymized[key] = [
                    cls.anonymize_dict(item, sensitive_keys) if isinstance(item, dict)
                    else cls.anonymize_text(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                anonymized[key] = value
        
        return anonymized
    
    @staticmethod
    def _hash_value(value: str) -> str:
        """Create a deterministic but irreversible hash of a value."""
        return f"ANON_{hashlib.sha256(value.encode()).hexdigest()[:12]}"


class SecureDocumentHandler:
    """Handles documents securely with automatic cleanup."""
    
    def __init__(self, upload_dir: str = "./data/uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self._temp_files: list[Path] = []
    
    async def save_upload(self, file_content: bytes, filename: str) -> Path:
        """
        Save an uploaded file securely.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            
        Returns:
            Path to saved file
        """
        # Generate unique filename to prevent overwrites
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\-_.]', '_', filename)
        unique_name = f"{timestamp}_{safe_name}"
        file_path = self.upload_dir / unique_name
        
        file_path.write_bytes(file_content)
        self._temp_files.append(file_path)
        
        return file_path
    
    def cleanup(self):
        """Remove all temporary files created during this session."""
        for file_path in self._temp_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
        self._temp_files.clear()
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """Remove files older than specified age."""
        if not self.upload_dir.exists():
            return
            
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        for file_path in self.upload_dir.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff:
                try:
                    file_path.unlink()
                except Exception:
                    pass
