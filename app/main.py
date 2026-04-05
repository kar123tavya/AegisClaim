"""
AegisClaim AI - FastAPI Main Application
Production-grade Explainable Insurance Claim Decision Engine
"""
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.v1.router import router as api_router

# Setup logging
logger = setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("=" * 60)
    logger.info(f"  {settings.app_name} v{settings.app_version}")
    logger.info(f"  Starting up...")
    logger.info(f"  LLM Reasoning: {'Enabled' if settings.enable_llm_reasoning and settings.google_api_key else 'Disabled'}")
    logger.info(f"  Fraud Detection: {'Enabled' if settings.enable_fraud_detection else 'Disabled'}")
    logger.info(f"  OCR Languages: {settings.ocr_languages}")
    logger.info("=" * 60)
    
    # Ensure directories
    settings.ensure_directories()
    
    # Init DB tables
    from app.core.database import init_db
    init_db()
    
    yield
    
    # Cleanup
    logger.info("Shutting down AegisClaim AI...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Production-grade Explainable Insurance Claim Decision Engine",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API router
app.include_router(api_router, prefix=settings.api_prefix)

# Mount static files for frontend
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


@app.get("/")
async def root():
    """Serve the dashboard."""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api": settings.api_prefix,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "llm_enabled": bool(settings.enable_llm_reasoning and settings.google_api_key),
        "fraud_detection_enabled": settings.enable_fraud_detection,
        "ocr_languages": settings.supported_languages,
    }
