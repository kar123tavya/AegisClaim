"""
AegisClaim AI - Core Configuration
Centralized settings management using pydantic-settings.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    google_api_key: str = Field(default="", description="Google Gemini API key")
    
    # Tesseract OCR
    tesseract_path: str = Field(
        default=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        description="Path to Tesseract executable"
    )
    ocr_languages: str = Field(
        default="eng+hin+spa+fra+deu+ara+chi_sim+jpn",
        description="Tesseract language packs (+ separated)"
    )
    
    # File paths
    upload_dir: str = Field(default="./data/uploads")
    vector_store_dir: str = Field(default="./data/vector_store")
    
    # Feature flags
    enable_fraud_detection: bool = Field(default=True)
    enable_llm_reasoning: bool = Field(default=True)
    
    # Thresholds
    confidence_threshold: int = Field(default=60, ge=0, le=100)
    max_upload_size_mb: int = Field(default=50)
    
    # Logging
    log_level: str = Field(default="INFO")
    
    # Application
    app_name: str = "AegisClaim AI"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    
    # FAISS
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 500
    chunk_overlap: int = 100
    retrieval_top_k: int = 5
    
    # DB
    sqlite_db_url: str = Field(default="sqlite:///./data/aegisclaim_analytics.db")
    
    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported OCR languages."""
        return self.ocr_languages.split("+")
    
    @property
    def language_names(self) -> dict[str, str]:
        """Human-readable language names."""
        return {
            "eng": "English",
            "hin": "Hindi",
            "spa": "Spanish",
            "fra": "French",
            "deu": "German",
            "ara": "Arabic",
            "chi_sim": "Chinese (Simplified)",
            "jpn": "Japanese",
            "kor": "Korean",
            "por": "Portuguese",
            "ita": "Italian",
            "tha": "Thai",
            "tam": "Tamil",
            "tel": "Telugu",
            "ben": "Bengali",
            "mar": "Marathi",
        }
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        for dir_path in [self.upload_dir, self.vector_store_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        Path("data/sample_policies").mkdir(parents=True, exist_ok=True)
        Path("data/sample_bills").mkdir(parents=True, exist_ok=True)
        Path("data/synthetic").mkdir(parents=True, exist_ok=True)
        
        # Ensure DB dir exists
        if self.sqlite_db_url.startswith("sqlite:///"):
            db_path = self.sqlite_db_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton settings instance
settings = Settings()
settings.ensure_directories()

