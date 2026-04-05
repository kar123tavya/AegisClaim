from __future__ import annotations
import logging
from typing import TYPE_CHECKING
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from app.services.claim_processor import ClaimProcessingResult

logger = logging.getLogger("aegisclaim.analytics")


class AnalyticsEngine:
    """Records and aggregates telemetry and tracking for claims processing."""
    
    def __init__(self, db_session):
        self.db = db_session
        
    def log_claim(self, claim_result: "ClaimProcessingResult"):
        """Log a complete claim result to the database."""
        try:
            from app.modules.analytics.models import ProcessedClaimInfo, FraudLog

            # explanation.decision is a plain string, NOT an enum
            exp = claim_result.explanation
            if exp:
                decision = exp.decision if isinstance(exp.decision, str) else getattr(exp.decision, 'value', str(exp.decision))
                conf = exp.confidence if isinstance(exp.confidence, float) else float(exp.confidence or 0)
                app_amt = float(exp.total_approved_amount or 0)
            else:
                decision = "ERROR"
                conf = 0.0
                app_amt = 0.0

            bill = claim_result.ocr_result.bill_data if claim_result.ocr_result else None

            db_claim = ProcessedClaimInfo(
                claim_id=claim_result.claim_id,
                patient_name=bill.patient_name if bill else None,
                hospital_name=bill.hospital_name if bill else None,
                bill_amount=float(bill.total_amount) if bill else 0.0,
                language_detected=bill.language_detected if bill else "unknown",
                decision_status=decision,
                confidence=conf,
                approved_amount=app_amt,
                processing_time_ms=float(claim_result.processing_time_ms or 0),
            )
            self.db.add(db_claim)

            if claim_result.fraud_analysis:
                fa = claim_result.fraud_analysis
                fraud = FraudLog(
                    claim_id=claim_result.claim_id,
                    risk_score=float(fa.fraud_risk_score or 0),
                    risk_level=fa.risk_level if isinstance(fa.risk_level, str) else str(fa.risk_level),
                    flags=[
                        {"type": f.flag_type, "severity": f.severity, "desc": f.description}
                        for f in fa.flags
                    ],
                )
                self.db.add(fraud)

            self.db.commit()
            logger.info(f"Logged claim {claim_result.claim_id} to analytics DB.")
        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            logger.error(f"Failed to log claim {claim_result.claim_id}: {e}")
            
    def save_feedback(self, claim_id: str, new_decision: str, comments: str, user: str = "human_reviewer"):
        """Save manual override feedback to improve rules/AI over time."""
        try:
            from app.modules.analytics.models import ProcessedClaimInfo, FeedbackLog

            # Get original
            original_claim = self.db.query(ProcessedClaimInfo).filter(ProcessedClaimInfo.claim_id == claim_id).first()
            orig_decision = original_claim.decision_status if original_claim else "UNKNOWN"
            
            feedback = FeedbackLog(
                claim_id=claim_id,
                user_id=user,
                original_decision=orig_decision,
                new_decision=new_decision,
                comments=comments
            )
            self.db.add(feedback)
            
            if original_claim:
                original_claim.decision_status = new_decision  # override
                
            self.db.commit()
            return True
        except Exception as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            logger.error(f"Failed saving feedback for {claim_id}: {e}")
            return False

    def get_dashboard_stats(self):
        """Aggregate data for industry dashboard."""
        try:
            from app.modules.analytics.models import ProcessedClaimInfo, FraudLog
            from sqlalchemy import func

            total_claims = self.db.query(func.count(ProcessedClaimInfo.id)).scalar() or 0
            
            # Approval rate
            approved = self.db.query(func.count(ProcessedClaimInfo.id)).filter(
                ProcessedClaimInfo.decision_status.in_(["APPROVED", "PARTIALLY_APPROVED"])
            ).scalar() or 0
            
            approval_rate = (approved / total_claims * 100) if total_claims > 0 else 0
            
            # Total processed amount
            total_billed = self.db.query(func.sum(ProcessedClaimInfo.bill_amount)).scalar() or 0
            total_approved = self.db.query(func.sum(ProcessedClaimInfo.approved_amount)).scalar() or 0
            savings = total_billed - total_approved
            
            # Avg processing time
            avg_time = self.db.query(func.avg(ProcessedClaimInfo.processing_time_ms)).scalar() or 0
            
            # Flagged fraud
            fraud_flags = self.db.query(func.count(FraudLog.id)).filter(
                FraudLog.risk_level.in_(["HIGH", "CRITICAL"])
            ).scalar() or 0
            
            # Languages Breakdown
            lang_counts = self.db.query(
                ProcessedClaimInfo.language_detected, 
                func.count(ProcessedClaimInfo.id)
            ).group_by(ProcessedClaimInfo.language_detected).order_by(func.count(ProcessedClaimInfo.id).desc()).limit(5).all()
            
            lang_stats = {lang or 'unknown': count for lang, count in lang_counts}
            
            return {
                "total_claims": total_claims,
                "approval_rate": round(approval_rate, 1),
                "total_billed": round(total_billed, 2),
                "total_approved": round(total_approved, 2),
                "total_savings": round(savings, 2),
                "avg_processing_time_ms": round(avg_time, 1),
                "high_fraud_flags": fraud_flags,
                "language_distribution": lang_stats
            }
        except Exception as e:
            logger.error(f"Error generating dashboard stats: {e}")
            return {
                "total_claims": 0,
                "approval_rate": 0,
                "total_billed": 0,
                "total_approved": 0,
                "total_savings": 0,
                "avg_processing_time_ms": 0,
                "high_fraud_flags": 0,
                "language_distribution": {}
            }
