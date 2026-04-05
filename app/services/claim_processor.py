"""
AegisClaim AI - Claim Processor Service
Orchestrates the full pipeline: OCR → RAG → Decision → Explanation → Fraud.
"""
import logging
import time
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aegisclaim.services.claim_processor")

from app.core.config import settings
from app.core.security import Anonymizer, SecureDocumentHandler
from app.modules.ocr.engine import OCREngine
from app.modules.ocr.schemas import OCRResult, ExtractedBillData
from app.modules.policy.retriever import PolicyRetriever
from app.modules.policy.schemas import PolicyMetadata
from app.modules.decision.hybrid_engine import HybridDecisionEngine
from app.modules.explainability.engine import ExplainabilityEngine
from app.modules.fraud.detector import FraudDetector
from app.modules.fraud.schemas import FraudAnalysisResult
from app.modules.explainability.schemas import ClaimExplanation
from app.modules.normalization.language import LanguageNormalizer
from app.modules.simulation.engine import WhatIfSimulator
# NOTE: AnalyticsEngine and get_db are imported lazily to avoid circular imports


class ClaimProcessingResult:
    """Complete result from end-to-end claim processing."""
    def __init__(self):
        self.claim_id: str = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        self.ocr_result: Optional[OCRResult] = None
        self.policy_metadata: Optional[PolicyMetadata] = None
        self.explanation: Optional[ClaimExplanation] = None
        self.fraud_analysis: Optional[FraudAnalysisResult] = None
        self.simulation_result: Optional[dict] = None
        self.processing_time_ms: float = 0
        self.errors: list[str] = []
        self.warnings: list[str] = []
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for API response — matches frontend schema."""
        result = {
            "claim_id": self.claim_id,
            "processing_time_ms": self.processing_time_ms,
            "errors": self.errors,
            "warnings": self.warnings,
        }

        # --- OCR result ---
        if self.ocr_result:
            bill = self.ocr_result.bill_data
            result["ocr_result"] = {
                "ocr_engine": self.ocr_result.ocr_engine,
                "processing_time_ms": self.ocr_result.processing_time_ms,
                "pages_processed": self.ocr_result.pages_processed,
                "language_used": self.ocr_result.language_used,
                "bill_data": {
                    "patient_name": bill.patient_name,
                    "patient_id": bill.patient_id,
                    "patient_age": bill.patient_age,
                    "hospital_name": bill.hospital_name,
                    "hospital_address": bill.hospital_address,
                    "bill_number": bill.bill_number,
                    "bill_date": bill.bill_date,
                    "admission_date": bill.admission_date,
                    "discharge_date": bill.discharge_date,
                    "diagnosis": bill.diagnosis,
                    "treating_doctor": bill.treating_doctor,
                    "line_items": [
                        {
                            "description": item.description,
                            "category": item.category.value if hasattr(item.category, 'value') else item.category,
                            "amount": item.amount,
                            "quantity": item.quantity,
                            "unit_price": item.unit_price,
                            "billing_code": item.billing_code,
                        }
                        for item in bill.line_items
                    ],
                    "subtotal": bill.subtotal,
                    "tax": bill.tax,
                    "discount": bill.discount,
                    "total_amount": bill.total_amount,
                    "currency": bill.currency,
                    "extraction_confidence": bill.extraction_confidence,
                    "language_detected": bill.language_detected,
                    "warnings": bill.warnings,
                    "raw_text": bill.raw_text,  # ← important for OCR display
                },
            }

        # --- Policy metadata ---
        if self.policy_metadata:
            result["policy_metadata"] = {
                "policy_name": self.policy_metadata.policy_name,
                "insurer_name": self.policy_metadata.insurer_name,
                "plan_type": self.policy_metadata.plan_type,
                "sum_insured": self.policy_metadata.sum_insured,
                "room_rent_limit_per_day": self.policy_metadata.room_rent_limit_per_day,
                "copay_percentage": self.policy_metadata.copay_percentage,
                "waiting_period_months": self.policy_metadata.waiting_period_months,
                "pre_existing_waiting_years": self.policy_metadata.pre_existing_waiting_years,
                "total_pages": self.policy_metadata.total_pages,
                "total_chunks": self.policy_metadata.total_chunks,
                "language": self.policy_metadata.language,
            }


        # --- Explanation (with citations) ---
        if self.explanation:
            result["explanation"] = {
                "claim_id": self.explanation.claim_id,
                "decision": self.explanation.decision,
                "confidence": self.explanation.confidence,
                "overall_reasoning": self.explanation.overall_reasoning,
                "total_bill_amount": self.explanation.total_bill_amount,
                "total_approved_amount": self.explanation.total_approved_amount,
                "requires_human_review": self.explanation.requires_human_review,
                "review_reasons": self.explanation.review_reasons,
                "recommendations": self.explanation.recommendations,
                "decision_factors": self.explanation.decision_factors,
                "summary_html": self.explanation.summary_html,
                "item_explanations": [
                    {
                        "bill_item": ie.bill_item,
                        "amount": ie.amount,
                        "approved_amount": ie.approved_amount,
                        "status": ie.status,
                        "reasoning": ie.reasoning,
                        "clause_text": ie.clause_text,
                        "clause_section": ie.clause_section,
                        "page_number": ie.page_number,
                        "policy_reference": ie.policy_reference,
                    }
                    for ie in self.explanation.item_explanations
                ],
                "cited_clauses": self.explanation.cited_clauses,
            }

        # --- Fraud analysis ---
        if self.fraud_analysis:
            result["fraud_analysis"] = {
                "fraud_risk_score": self.fraud_analysis.fraud_risk_score,
                "risk_level": self.fraud_analysis.risk_level,
                "anomalies_detected": self.fraud_analysis.anomalies_detected,
                "summary": self.fraud_analysis.summary,
                "recommendation": self.fraud_analysis.recommendation,
                "flags": [
                    {
                        "flag_type": f.flag_type,
                        "severity": f.severity,
                        "description": f.description,
                        "score": f.score,
                        "evidence": f.evidence,
                    }
                    for f in self.fraud_analysis.flags
                ],
            }

        # --- What-If simulation ---
        result["simulation"] = self.simulation_result

        return result

class ClaimProcessor:
    """
    Main pipeline orchestrator.
    Executes: OCR → Policy RAG → Hybrid Decision → Explanation → Fraud Detection
    """

    def __init__(self):
        self.ocr_engine = OCREngine()
        self.lang_normalizer = LanguageNormalizer()
        self.policy_retriever = PolicyRetriever()
        self.decision_engine = HybridDecisionEngine()
        self.explainability_engine = ExplainabilityEngine()
        self.fraud_detector = FraudDetector()
        self.simulator = WhatIfSimulator()
        self.doc_handler = SecureDocumentHandler()
        self._policy_indexed = False

    async def process_claim(
        self,
        bill_path: str,
        policy_path: str,
        language: Optional[str] = None,
    ) -> ClaimProcessingResult:
        """
        Process a complete insurance claim.
        
        Args:
            bill_path: Path to the hospital bill (image or PDF)
            policy_path: Path to the insurance policy PDF
            language: OCR language override
            
        Returns:
            ClaimProcessingResult with all pipeline outputs
        """
        result = ClaimProcessingResult()
        start_time = time.time()

        try:
            # === Step 1: OCR - Extract bill data ===
            logger.info("Step 1/5: OCR - Extracting bill data...")
            try:
                result.ocr_result = self.ocr_engine.process_document(bill_path, language)
                
                # --- Step 1b: Language Normalization ---
                logger.info("Language Normalization Check...")
                result.ocr_result.bill_data = self.lang_normalizer.normalize(result.ocr_result.bill_data)
                
                result.warnings.extend(result.ocr_result.bill_data.warnings)
                logger.info(
                    f"OCR complete: {len(result.ocr_result.bill_data.line_items)} items, "
                    f"total: ₹{result.ocr_result.bill_data.total_amount:,.2f}, "
                    f"confidence: {result.ocr_result.bill_data.extraction_confidence:.0%}"
                )
            except Exception as e:
                result.errors.append(f"OCR failed: {str(e)}")
                logger.error(f"OCR failed: {e}")
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result

            # === Step 2: Policy RAG - Index and retrieve ===
            logger.info("Step 2/5: Policy RAG - Indexing and retrieving...")
            try:
                if not self._policy_indexed or self.policy_retriever.policy_id != self.policy_retriever.embedder.generate_policy_id(policy_path):
                    index_status = self.policy_retriever.index_policy(policy_path)
                    self._policy_indexed = index_status.is_indexed
                    logger.info(f"Policy indexed: {index_status.total_chunks} chunks")
                
                result.policy_metadata = self.policy_retriever.get_metadata()
                
                # Retrieve relevant clauses for each bill item
                all_chunks = []
                for item in result.ocr_result.bill_data.line_items:
                    chunks = self.policy_retriever.get_coverage_clauses(item.description)
                    all_chunks.extend(chunks)
                
                # Also get general limits and exclusions
                all_chunks.extend(self.policy_retriever.get_policy_limits())
                all_chunks.extend(self.policy_retriever.get_exclusions())
                
                # Deduplicate
                seen_ids = set()
                unique_chunks = []
                for chunk in all_chunks:
                    if chunk.chunk_id not in seen_ids:
                        seen_ids.add(chunk.chunk_id)
                        unique_chunks.append(chunk)
                
                policy_chunks = unique_chunks[:15]  # Cap at 15 most relevant
                logger.info(f"Retrieved {len(policy_chunks)} relevant policy chunks")
                
            except Exception as e:
                result.warnings.append(f"Policy RAG warning: {str(e)}")
                logger.warning(f"Policy RAG issue: {e}")
                policy_chunks = []

            # === Step 3: Hybrid Decision ===
            logger.info("Step 3/5: Making decision...")
            try:
                decision_result = self.decision_engine.evaluate(
                    result.ocr_result.bill_data,
                    policy_chunks,              # ← 2nd arg = policy_chunks (list[PolicyChunk])
                    result.policy_metadata,     # ← 3rd arg = policy_metadata (Optional[PolicyMetadata])
                )
                # Normalize confidence to [0, 1] range
                if decision_result.confidence > 1.0:
                    decision_result.confidence = decision_result.confidence / 100.0
                decision_result.confidence = min(max(decision_result.confidence, 0.0), 1.0)
                logger.info(
                    f"Decision: {decision_result.final_decision.value} "
                    f"(confidence: {decision_result.confidence:.0%})"
                )
            except Exception as e:
                result.errors.append(f"Decision engine failed: {str(e)}")
                logger.error(f"Decision failed: {e}")
                result.processing_time_ms = (time.time() - start_time) * 1000
                return result

            # === Step 4: Explainability ===
            logger.info("Step 4/5: Generating explanation...")
            try:
                result.explanation = self.explainability_engine.generate_explanation(
                    decision_result, policy_chunks
                )
                result.explanation.claim_id = result.claim_id
            except Exception as e:
                result.warnings.append(f"Explanation generation warning: {str(e)}")
                logger.warning(f"Explanation issue: {e}")

            # === Step 5: Fraud Detection ===
            if settings.enable_fraud_detection:
                logger.info("Step 5/6: Fraud analysis...")
                try:
                    result.fraud_analysis = self.fraud_detector.analyze(
                        result.ocr_result.bill_data
                    )
                    logger.info(
                        f"Fraud risk: {result.fraud_analysis.fraud_risk_score:.1f}/100 "
                        f"({result.fraud_analysis.risk_level})"
                    )
                except Exception as e:
                    result.warnings.append(f"Fraud detection warning: {str(e)}")
                    logger.warning(f"Fraud detection issue: {e}")

            # === Step 6: What-If Simulation ===
            logger.info("Step 6/6: What-If Simulation...")
            try:
                result.simulation_result = self.simulator.simulate(result)
            except Exception as e:
                result.warnings.append(f"Simulation warning: {str(e)}")
                
        except Exception as e:
            result.errors.append(f"Pipeline error: {str(e)}")
            logger.error(f"Pipeline error: {e}")

        result.processing_time_ms = round((time.time() - start_time) * 1000, 2)
        
        # === Step 7: Analytics Persistence ===
        try:
            from app.core.database import get_db
            from app.modules.analytics.engine import AnalyticsEngine
            db_gen = get_db()
            db_session = next(db_gen)
            analytics = AnalyticsEngine(db_session)
            analytics.log_claim(result)
            db_session.close()
        except Exception as e:
            logger.error(f"Analytics persistence failed: {e}")
            
        logger.info(f"Claim processing complete in {result.processing_time_ms:.0f}ms")
        
        return result

    def process_bill_only(self, file_path: str, language: Optional[str] = None) -> OCRResult:
        """Process only the bill (OCR extraction)."""
        return self.ocr_engine.process_document(file_path, language)

    def cleanup(self):
        """Clean up temporary files."""
        self.doc_handler.cleanup()
