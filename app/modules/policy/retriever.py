"""
AegisClaim AI - Policy RAG Retriever
Retrieves relevant policy clauses for claim evaluation using semantic search.
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aegisclaim.policy.retriever")

from .parser import PolicyParser
from .embedder import PolicyEmbedder
from .schemas import PolicyChunk, PolicyMetadata, PolicyQueryResult, PolicyIndexStatus


class PolicyRetriever:
    """
    RAG-based policy retrieval engine.
    Indexes policy documents and retrieves relevant clauses for claim evaluation.
    """

    def __init__(self):
        self.embedder = PolicyEmbedder()
        self.parser = PolicyParser()
        self.metadata: Optional[PolicyMetadata] = None
        self.policy_id: str = ""
        self._indexed = False
        
        from app.modules.normalization.policy_extractor import PolicyNormalizer
        self.normalizer = PolicyNormalizer()

    def index_policy(self, file_path: str) -> PolicyIndexStatus:
        """
        Parse and index a policy PDF for semantic retrieval.
        
        Args:
            file_path: Path to the insurance policy PDF
            
        Returns:
            PolicyIndexStatus with indexing details
        """
        # Generate policy ID
        self.policy_id = PolicyEmbedder.generate_policy_id(file_path)

        # Try loading existing index first
        if self.embedder.load_index(self.policy_id):
            self._indexed = True
            
            # Since we loaded from disk, parsing wasn't run, so we don't have self.metadata loaded yet
            # In a real app, PolicyMetadata should be saved/loaded alongside the index. We will stub it for now
            # if it hasn't been loaded.
            if not self.metadata:
                self.metadata = PolicyMetadata(policy_name=Path(file_path).name, total_pages=0)
                
            return PolicyIndexStatus(
                is_indexed=True,
                policy_id=self.policy_id,
                policy_name=file_path,
                total_chunks=len(self.embedder.chunks_metadata),
                embedding_model=self.embedder.model.__class__.__name__ if self.embedder.model else "none",
                index_path=f"data/vector_store/{self.policy_id}"
            )

        # Parse PDF
        pages_data, self.metadata = self.parser.parse_pdf(file_path)
        
        if not pages_data:
            return PolicyIndexStatus(
                is_indexed=False,
                policy_id=self.policy_id,
                policy_name=file_path
            )

        # Chunk and embed
        chunks = self.embedder.chunk_text(pages_data)
        
        # --- NORMALIZE USING LLM ---
        # Get the first ~3000 chars of text (approx first few pages)
        sample_text = "\n".join(c.text for c in chunks[:5])
        self.metadata = self.normalizer.extract_structured_metadata(sample_text, self.metadata)
        
        success = self.embedder.create_index(chunks, self.policy_id)

        if success:
            self.metadata.total_chunks = len(chunks)
            self._indexed = True

        return PolicyIndexStatus(
            is_indexed=success,
            policy_id=self.policy_id,
            policy_name=self.metadata.policy_name or file_path,
            total_chunks=len(chunks),
            embedding_model=self.embedder.model.__class__.__name__ if self.embedder.model else "none",
            index_path=f"data/vector_store/{self.policy_id}"
        )

    def query(self, query: str, top_k: int = 5) -> PolicyQueryResult:
        """
        Query the policy for relevant clauses.
        
        Args:
            query: Natural language query about the policy
            top_k: Number of results to return
            
        Returns:
            PolicyQueryResult with relevant chunks
        """
        if not self._indexed:
            logger.warning("No policy indexed. Call index_policy first.")
            return PolicyQueryResult(
                query=query,
                relevant_chunks=[],
                confidence=0.0
            )

        # Generate multiple query variations for better recall
        queries = self._generate_query_variations(query)
        
        all_chunks = []
        seen_ids = set()
        
        for q in queries:
            chunks = self.embedder.search(q, top_k=top_k)
            for chunk in chunks:
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    all_chunks.append(chunk)

        # Sort by relevance and take top-k
        all_chunks.sort(key=lambda c: c.relevance_score, reverse=True)
        top_chunks = all_chunks[:top_k]

        avg_confidence = (
            sum(c.relevance_score for c in top_chunks) / len(top_chunks) 
            if top_chunks else 0.0
        )

        return PolicyQueryResult(
            query=query,
            relevant_chunks=top_chunks,
            confidence=min(avg_confidence, 1.0)
        )

    def get_coverage_clauses(self, bill_item_description: str) -> list[PolicyChunk]:
        """Get policy clauses relevant to a specific bill item."""
        queries = [
            f"Is {bill_item_description} covered under the policy?",
            f"coverage for {bill_item_description}",
            f"exclusion for {bill_item_description}",
            f"limit for {bill_item_description}",
        ]
        
        all_chunks = []
        seen_ids = set()
        
        for q in queries:
            result = self.query(q, top_k=3)
            for chunk in result.relevant_chunks:
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    all_chunks.append(chunk)
        
        all_chunks.sort(key=lambda c: c.relevance_score, reverse=True)
        return all_chunks[:5]

    def get_policy_limits(self) -> list[PolicyChunk]:
        """Retrieve policy limit and sub-limit clauses."""
        return self.query(
            "policy coverage limits sub-limits room rent maximum amount sum insured",
            top_k=5
        ).relevant_chunks

    def get_exclusions(self) -> list[PolicyChunk]:
        """Retrieve policy exclusion clauses."""
        return self.query(
            "exclusions not covered excluded conditions treatments",
            top_k=5
        ).relevant_chunks

    def _generate_query_variations(self, query: str) -> list[str]:
        """Generate query variations for better recall."""
        variations = [query]
        
        # Add domain-specific reformulations
        lower = query.lower()
        
        if "cover" in lower:
            variations.append(query.replace("covered", "included in benefits"))
            variations.append(query.replace("cover", "benefit"))
        
        if "icu" in lower:
            variations.append(query.replace("ICU", "intensive care unit"))
        
        if "room" in lower:
            variations.append(query + " room rent limit cap ceiling per day")
        
        if "surgery" in lower or "operation" in lower:
            variations.append(query + " surgical procedure operative")
        
        if "exclude" in lower or "reject" in lower:
            variations.append(query + " not covered exclusion permanent")
        
        return variations[:3]  # Max 3 variations to avoid too many searches

    @property
    def is_indexed(self) -> bool:
        return self._indexed

    def get_metadata(self) -> Optional[PolicyMetadata]:
        return self.metadata
