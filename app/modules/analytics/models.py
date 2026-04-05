from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON
from datetime import datetime

from app.core.database import Base

class ProcessedClaimInfo(Base):
    __tablename__ = "processed_claims"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Patient & Bill Info
    patient_name = Column(String, nullable=True)
    hospital_name = Column(String, index=True, nullable=True)
    bill_amount = Column(Float, default=0.0)
    language_detected = Column(String, nullable=True)
    
    # Decision Info
    decision_status = Column(String, index=True) # APPROVED, REJECTED, NEEDS_REVIEW, PARTIALLY_APPROVED
    confidence = Column(Float, default=0.0)
    approved_amount = Column(Float, default=0.0)
    model_used = Column(String, nullable=True)
    
    # Policy Info
    policy_id = Column(String, nullable=True)
    
    # processing timings
    processing_time_ms = Column(Float, default=0)
    
    # Store essential full JSON blob for future retrieval/analysis without needing huge tables
    full_result_json = Column(JSON, nullable=True)

class FraudLog(Base):
    __tablename__ = "fraud_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String) # LOW, MEDIUM, HIGH, CRITICAL
    
    # Store list of flags as JSON
    flags = Column(JSON, nullable=True)

class FeedbackLog(Base):
    __tablename__ = "feedback_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user_id = Column(String, default="system_user")
    original_decision = Column(String)
    new_decision = Column(String)
    comments = Column(Text, nullable=True)
