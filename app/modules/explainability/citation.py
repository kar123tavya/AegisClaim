"""
AegisClaim AI - Explainability Citation Engine
Handles precise policy clause citation with page references.
"""
import logging
from typing import Optional

logger = logging.getLogger("aegisclaim.explainability.citation")

from app.modules.policy.schemas import PolicyChunk


class CitationEngine:
    """Manages precise policy clause citations for explainability."""

    @staticmethod
    def format_citation(chunk: PolicyChunk, context: str = "") -> str:
        """Format a policy chunk as a proper citation."""
        section = chunk.section.value if hasattr(chunk.section, 'value') else str(chunk.section)
        citation = f"[Page {chunk.page_number}, Section: {section.title()}]"
        
        if context:
            citation += f" — {context}"
        
        return citation

    @staticmethod
    def find_best_citation(
        query: str,
        chunks: list[PolicyChunk],
    ) -> Optional[PolicyChunk]:
        """Find the most relevant policy chunk for a given query."""
        if not chunks:
            return None
        
        query_words = set(w.lower() for w in query.split() if len(w) > 3)
        best_chunk = None
        best_score = 0
        
        for chunk in chunks:
            chunk_words = set(chunk.text.lower().split())
            overlap = len(query_words & chunk_words)
            
            # Bonus for high relevance score
            score = overlap + (chunk.relevance_score * 5)
            
            if score > best_score:
                best_score = score
                best_chunk = chunk
        
        return best_chunk

    @staticmethod
    def build_citation_trail(chunks: list[PolicyChunk]) -> list[dict]:
        """Build an ordered citation trail from policy chunks."""
        trail = []
        for chunk in chunks:
            section = chunk.section.value if hasattr(chunk.section, 'value') else str(chunk.section)
            trail.append({
                "page": chunk.page_number,
                "section": section,
                "excerpt": chunk.text[:150] + "..." if len(chunk.text) > 150 else chunk.text,
                "relevance_score": round(chunk.relevance_score, 3),
            })
        
        return sorted(trail, key=lambda x: x["page"])
