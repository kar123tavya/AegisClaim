"""
AegisClaim AI - API Router
Combines all API routers into the main router.
"""
from datetime import datetime, timezone
from fastapi import APIRouter

from app.api.v1.claims import router as claims_router
from app.api.v1.policies import router as policies_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.analytics import router as analytics_router

router = APIRouter()

router.include_router(claims_router, prefix="/claims", tags=["claims"])
router.include_router(policies_router, prefix="/policies", tags=["policies"])
router.include_router(evaluation_router, prefix="/evaluation", tags=["evaluation"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])


@router.get("/health", tags=["system"])
async def health_check():
    """System health check — returns status and timestamp."""
    return {
        "status": "healthy",
        "service": "AegisClaim AI",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "ocr": "online",
            "llm": "online",
            "fraud_detection": "online",
            "policy_rag": "online",
        }
    }
