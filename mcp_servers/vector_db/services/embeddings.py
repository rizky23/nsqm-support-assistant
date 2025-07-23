from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
from shared.utils.logger import log

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
    
    async def initialize(self):
        """Initialize the embedding model"""
        try:
            log.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            log.info("Embedding model loaded successfully")
            return True
        except Exception as e:
            log.error(f"Failed to load embedding model: {e}")
            return False
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts"""
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        embeddings = self.model.encode([text1, text2])
        similarity = np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
        )
        return float(similarity)