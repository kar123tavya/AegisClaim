"""
AegisClaim AI - Policies API Endpoints
"""
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

logger = logging.getLogger("aegisclaim.api.policies")

from app.core.security import SecureDocumentHandler
from app.modules.policy.retriever import PolicyRetriever

router = APIRouter()

_retriever = None
_doc_handler = SecureDocumentHandler()


def get_retriever() -> PolicyRetriever:
    global _retriever
    if _retriever is None:
        _retriever = PolicyRetriever()
    return _retriever


@router.post("/upload")
async def upload_policy(
    policy: UploadFile = File(..., description="Insurance policy PDF"),
):
    """Upload and index an insurance policy for querying."""
    retriever = get_retriever()
    
    try:
        content = await policy.read()
        path = await _doc_handler.save_upload(content, policy.filename)
        
        status = retriever.index_policy(str(path))
        
        metadata = retriever.get_metadata()
        
        return {
            "status": "indexed" if status.is_indexed else "failed",
            "policy_id": status.policy_id,
            "total_chunks": status.total_chunks,
            "metadata": metadata.model_dump() if metadata else None,
        }
    except Exception as e:
        logger.error(f"Policy upload error: {e}")
        raise HTTPException(500, f"Policy indexing failed: {str(e)}")


@router.post("/query")
async def query_policy(
    query: str = Form(..., description="Natural language query about the policy"),
    top_k: int = Form(5, description="Number of results"),
):
    """Semantic query against the indexed policy."""
    retriever = get_retriever()
    
    if not retriever.is_indexed:
        raise HTTPException(400, "No policy indexed. Upload a policy first.")
    
    result = retriever.query(query, top_k)
    
    return {
        "query": result.query,
        "confidence": result.confidence,
        "results": [
            {
                "text": chunk.text,
                "page_number": chunk.page_number,
                "section": chunk.section.value if hasattr(chunk.section, 'value') else str(chunk.section),
                "relevance_score": chunk.relevance_score,
            }
            for chunk in result.relevant_chunks
        ],
    }
