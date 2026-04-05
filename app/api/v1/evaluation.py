"""
AegisClaim AI - Evaluation API Endpoints
"""
import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger("aegisclaim.api.evaluation")

from app.modules.evaluation.runner import EvaluationRunner
from app.modules.evaluation.dataset import generate_synthetic_dataset

router = APIRouter()


@router.post("/run")
async def run_evaluation(num_claims: int = 200):
    """Run the full evaluation pipeline on synthetic data."""
    try:
        runner = EvaluationRunner()
        results = runner.run_evaluation(num_claims=num_claims)
        
        return {
            "status": "completed",
            "accuracy": results["metrics"]["accuracy"],
            "false_rejection_rate": results["metrics"]["false_rejection_rate"],
            "total_claims": results["total_claims"],
            "processing_time_seconds": results["processing_time_seconds"],
            "metrics": results["metrics"],
            "type_breakdown": results["type_breakdown"],
            "report": results["report"],
        }
    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        raise HTTPException(500, f"Evaluation failed: {str(e)}")


@router.post("/generate-dataset")
async def generate_dataset(num_claims: int = 200):
    """Generate a synthetic claims dataset."""
    try:
        claims = generate_synthetic_dataset(num_claims)
        return {
            "status": "generated",
            "total_claims": len(claims),
            "distribution": {
                "valid": sum(1 for c in claims if c["claim_type"] == "valid"),
                "invalid": sum(1 for c in claims if c["claim_type"] == "invalid"),
                "edge_case": sum(1 for c in claims if c["claim_type"] == "edge_case"),
            },
            "sample": claims[:3],
        }
    except Exception as e:
        logger.error(f"Dataset generation error: {e}")
        raise HTTPException(500, f"Dataset generation failed: {str(e)}")
