import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer
from dfm_rule_pipeline.config import EMBEDDING_MODEL

class EmbeddingManager:
    """Manages text embedding using sentence-transformers."""
    
    def __init__(
        self, 
        model_name: str = EMBEDDING_MODEL,
        fallback_model: str = EMBEDDING_MODEL,
        device: str = "cpu",
    ):
        try:
            # Try primary model first
            self.model = SentenceTransformer(model_name, device=device)
            self.dimension = self.model.get_sentence_embedding_dimension()
        except Exception as e:
            print(f"Warning: Failed to load primary model {model_name} ({e}). Using fallback {fallback_model}.")
            self.model = SentenceTransformer(fallback_model, device=device)
            self.dimension = self.model.get_sentence_embedding_dimension()
            
    def embed(self, texts: List[str]) -> np.ndarray:
        """Encode a batch of texts into dense vectors. Returns (N, D) array."""
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings
        
    def embed_single(self, text: str) -> np.ndarray:
        """Encode a single text. Returns (D,) array."""
        embeddings = self.model.encode([text], convert_to_numpy=True, normalize_embeddings=True)
        return embeddings[0]
