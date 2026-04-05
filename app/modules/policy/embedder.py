"""
AegisClaim AI - Policy Embedder
Creates embeddings from policy text and stores them in a FAISS vector database.
"""
import logging
import hashlib
import json
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aegisclaim.policy.embedder")

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    logger.warning("sentence-transformers not available")

try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available")

from app.core.config import settings
from .schemas import PolicyChunk, PolicySection


class PolicyEmbedder:
    """
    Embeds policy text chunks using sentence-transformers and indexes them in FAISS.
    Stores metadata (page numbers, sections) alongside vectors.
    """

    def __init__(self):
        self.model = None
        self.index = None
        self.chunks_metadata: list[dict] = []
        self.dimension = 384  # all-MiniLM-L6-v2 dimension
        self._load_model()

    def _load_model(self):
        """Load the embedding model."""
        if ST_AVAILABLE:
            try:
                self.model = SentenceTransformer(settings.embedding_model)
                self.dimension = self.model.get_sentence_embedding_dimension()
                logger.info(f"Loaded embedding model: {settings.embedding_model}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self.model = None

    def chunk_text(
        self,
        pages_data: list[dict],
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> list[PolicyChunk]:
        """
        Split page-level text into overlapping chunks while preserving metadata.
        
        Args:
            pages_data: List of {'page': int, 'text': str, 'section': str}
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between consecutive chunks
            
        Returns:
            List of PolicyChunk objects
        """
        chunk_size = chunk_size or settings.chunk_size
        chunk_overlap = chunk_overlap or settings.chunk_overlap
        chunks = []
        chunk_counter = 0

        for page_data in pages_data:
            text = page_data["text"]
            page = page_data["page"]
            section = page_data.get("section", "general")
            
            if not text or len(text.strip()) < 20:
                continue

            # Split by paragraphs first, then by size
            paragraphs = text.split('\n\n')
            current_chunk = ""
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                if len(current_chunk) + len(para) <= chunk_size:
                    current_chunk += ("\n" + para if current_chunk else para)
                else:
                    if current_chunk:
                        chunk_counter += 1
                        chunks.append(PolicyChunk(
                            text=current_chunk.strip(),
                            page_number=page,
                            section=PolicySection(section) if section in [s.value for s in PolicySection] else PolicySection.GENERAL,
                            section_title=section,
                            chunk_id=f"chunk_{chunk_counter}"
                        ))
                    
                    # Handle paragraphs larger than chunk_size
                    if len(para) > chunk_size:
                        words = para.split()
                        current_chunk = ""
                        for word in words:
                            if len(current_chunk) + len(word) + 1 <= chunk_size:
                                current_chunk += (" " + word if current_chunk else word)
                            else:
                                if current_chunk:
                                    chunk_counter += 1
                                    chunks.append(PolicyChunk(
                                        text=current_chunk.strip(),
                                        page_number=page,
                                        section=PolicySection(section) if section in [s.value for s in PolicySection] else PolicySection.GENERAL,
                                        section_title=section,
                                        chunk_id=f"chunk_{chunk_counter}"
                                    ))
                                # Keep overlap
                                overlap_words = current_chunk.split()[-chunk_overlap // 5:] if current_chunk else []
                                current_chunk = " ".join(overlap_words) + " " + word
                    else:
                        # Keep overlap from previous chunk
                        overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ""
                        current_chunk = overlap_text + "\n" + para if overlap_text else para
            
            # Add remaining text
            if current_chunk.strip():
                chunk_counter += 1
                chunks.append(PolicyChunk(
                    text=current_chunk.strip(),
                    page_number=page,
                    section=PolicySection(section) if section in [s.value for s in PolicySection] else PolicySection.GENERAL,
                    section_title=section,
                    chunk_id=f"chunk_{chunk_counter}"
                ))

        logger.info(f"Created {len(chunks)} chunks from {len(pages_data)} pages")
        return chunks

    def create_index(self, chunks: list[PolicyChunk], policy_id: str = "default") -> bool:
        """
        Create FAISS index from policy chunks.
        
        Args:
            chunks: List of PolicyChunk objects
            policy_id: Unique identifier for the policy
            
        Returns:
            True if successful
        """
        if not self.model or not FAISS_AVAILABLE:
            logger.error("Embedding model or FAISS not available")
            return False

        if not chunks:
            logger.warning("No chunks to index")
            return False

        try:
            # Generate embeddings
            texts = [chunk.text for chunk in chunks]
            embeddings = self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
            embeddings = np.array(embeddings, dtype=np.float32)

            # Create FAISS index (Inner Product for normalized vectors = cosine similarity)
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(embeddings)

            # Store metadata
            self.chunks_metadata = [
                {
                    "text": chunk.text,
                    "page_number": chunk.page_number,
                    "section": chunk.section.value if isinstance(chunk.section, PolicySection) else chunk.section,
                    "section_title": chunk.section_title,
                    "chunk_id": chunk.chunk_id,
                }
                for chunk in chunks
            ]

            # Save to disk
            self._save_index(policy_id)
            
            logger.info(f"Created FAISS index with {len(chunks)} vectors (dim={self.dimension})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False

    def _save_index(self, policy_id: str):
        """Save FAISS index and metadata to disk."""
        store_dir = Path(settings.vector_store_dir) / policy_id
        store_dir.mkdir(parents=True, exist_ok=True)

        if self.index:
            faiss.write_index(self.index, str(store_dir / "index.faiss"))

        meta_path = store_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks_metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved index to {store_dir}")

    def load_index(self, policy_id: str = "default") -> bool:
        """Load a previously saved FAISS index."""
        store_dir = Path(settings.vector_store_dir) / policy_id
        index_path = store_dir / "index.faiss"
        meta_path = store_dir / "metadata.json"

        if not index_path.exists() or not meta_path.exists():
            logger.warning(f"No saved index found for policy: {policy_id}")
            return False

        try:
            self.index = faiss.read_index(str(index_path))
            
            with open(meta_path, "r", encoding="utf-8") as f:
                self.chunks_metadata = json.load(f)
            
            logger.info(f"Loaded index for {policy_id} with {self.index.ntotal} vectors")
            return True
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    def search(self, query: str, top_k: int = None) -> list[PolicyChunk]:
        """
        Search the FAISS index for relevant policy chunks.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            
        Returns:
            List of PolicyChunk objects with relevance scores
        """
        top_k = top_k or settings.retrieval_top_k
        
        if not self.model or not self.index:
            logger.error("Model or index not loaded")
            return []

        try:
            # Encode query
            query_embedding = self.model.encode([query], normalize_embeddings=True)
            query_embedding = np.array(query_embedding, dtype=np.float32)

            # Search
            scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

            # Build results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self.chunks_metadata):
                    continue
                meta = self.chunks_metadata[idx]
                section_val = meta.get("section", "general")
                try:
                    section_enum = PolicySection(section_val)
                except ValueError:
                    section_enum = PolicySection.GENERAL
                    
                chunk = PolicyChunk(
                    text=meta["text"],
                    page_number=meta["page_number"],
                    section=section_enum,
                    section_title=meta.get("section_title", ""),
                    chunk_id=meta.get("chunk_id", ""),
                    relevance_score=float(score)
                )
                results.append(chunk)

            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    @staticmethod
    def generate_policy_id(file_path: str) -> str:
        """Generate a consistent policy ID from file path."""
        return hashlib.md5(Path(file_path).name.encode()).hexdigest()[:12]
