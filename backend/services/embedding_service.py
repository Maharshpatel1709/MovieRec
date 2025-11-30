"""
Embedding service for generating text embeddings.
Supports Vertex AI and mock/local fallback.
"""
from typing import List, Optional
import numpy as np
from loguru import logger

from backend.config import settings


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self):
        self._model = None
        self._use_mock = settings.use_mock_embeddings
        self._dimension = settings.embedding_dimension
        self._vertex_client = None
        self._sentence_transformer = None
    
    def _init_vertex_ai(self):
        """Initialize Vertex AI client."""
        try:
            from google.cloud import aiplatform
            from vertexai.language_models import TextEmbeddingModel
            
            aiplatform.init(
                project=settings.google_cloud_project,
                location=settings.vertex_ai_location
            )
            self._vertex_client = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
            logger.info("Vertex AI embedding model initialized")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize Vertex AI: {e}")
            return False
    
    def _init_sentence_transformer(self):
        """Initialize local sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            # Use all-mpnet-base-v2 for 768 dimensions (matches our vector index)
            self._sentence_transformer = SentenceTransformer('all-mpnet-base-v2')
            self._dimension = 768  # mpnet dimension
            logger.info("Sentence transformer model initialized (all-mpnet-base-v2, 768 dim)")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize sentence transformer: {e}")
            return False
    
    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate a deterministic mock embedding based on text."""
        # Create a deterministic hash-based embedding
        np.random.seed(hash(text) % (2**32))
        embedding = np.random.randn(self._dimension).astype(float)
        # Normalize to unit vector
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.tolist()
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Falls back through: Vertex AI -> Sentence Transformer -> Mock
        """
        if not text or not text.strip():
            return [0.0] * self._dimension
        
        # Try Vertex AI first if not using mock
        if not self._use_mock:
            if self._vertex_client is None:
                self._init_vertex_ai()
            
            if self._vertex_client:
                try:
                    embeddings = self._vertex_client.get_embeddings([text])
                    return embeddings[0].values
                except Exception as e:
                    logger.warning(f"Vertex AI embedding failed: {e}")
        
        # Try sentence transformer
        if self._sentence_transformer is None:
            self._init_sentence_transformer()
        
        if self._sentence_transformer:
            try:
                embedding = self._sentence_transformer.encode(text)
                return embedding.tolist()
            except Exception as e:
                logger.warning(f"Sentence transformer embedding failed: {e}")
        
        # Fall back to mock
        logger.debug("Using mock embedding")
        return self._generate_mock_embedding(text)
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Try Vertex AI
            if not self._use_mock and self._vertex_client:
                try:
                    batch_embeddings = self._vertex_client.get_embeddings(batch)
                    embeddings.extend([e.values for e in batch_embeddings])
                    continue
                except Exception as e:
                    logger.warning(f"Batch Vertex AI embedding failed: {e}")
            
            # Try sentence transformer
            if self._sentence_transformer:
                try:
                    batch_embeddings = self._sentence_transformer.encode(batch)
                    embeddings.extend(batch_embeddings.tolist())
                    continue
                except Exception as e:
                    logger.warning(f"Batch sentence transformer failed: {e}")
            
            # Mock fallback
            embeddings.extend([self._generate_mock_embedding(t) for t in batch])
        
        return embeddings
    
    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Compute cosine similarity between two embeddings."""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self._dimension


# Singleton instance
embedding_service = EmbeddingService()

