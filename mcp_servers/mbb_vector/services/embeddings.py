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