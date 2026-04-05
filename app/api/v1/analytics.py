"""
AegisClaim AI - Analytics API Endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.modules.analytics.engine import AnalyticsEngine

logger = logging.getLogger("aegisclaim.api.analytics")

router = APIRouter()

class FeedbackRequest(BaseModel):
    claim_id: str
    new_decision: str
    comments: str

@router.get("/stats")
def get_analytics_dashboard(db: Session = Depends(get_db)):
    """Get aggregated analytics stats for the dashboard."""
    try:
        engine = AnalyticsEngine(db)
        stats = engine.get_dashboard_stats()
        return stats
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")

@router.post("/feedback")
def submit_feedback(feedback: FeedbackRequest, db: Session = Depends(get_db)):
    """Submit human override/feedback for a claim."""
    try:
        engine = AnalyticsEngine(db)
        success = engine.save_feedback(
            claim_id=feedback.claim_id,
            new_decision=feedback.new_decision,
            comments=feedback.comments
        )
        if success:
            return {"status": "success", "message": "Feedback saved successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to save feedback (claim not found or db error)")
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))
