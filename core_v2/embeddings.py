import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import HashingVectorizer

from dfm_rule_pipeline.config import EMBEDDING_MODEL


class _HashingEmbeddingModel:
    """Small local fallback used when the sentence-transformer model is unavailable."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.vectorizer = HashingVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            n_features=dimension,
            alternate_sign=False,
            norm="l2",
        )

    def get_sentence_embedding_dimension(self) -> int:
        return self.dimension

    def encode(self, texts: List[str], **_) -> np.ndarray:
        return self.vectorizer.transform(texts).astype(np.float32).toarray()


class EmbeddingManager:
    """Manages text embeddings with a deterministic offline fallback."""

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        fallback_model: str | None = None,
        device: str = "cpu",
    ):
        self.model = self._load_model(model_name, device)
        if self.model is None and fallback_model and fallback_model != model_name:
            self.model = self._load_model(fallback_model, device)

        if self.model is None:
            print(f"Warning: Failed to load embedding model {model_name}. Using local hashing fallback.")
            self.model = _HashingEmbeddingModel()

        if hasattr(self.model, "get_embedding_dimension"):
            self.dimension = self.model.get_embedding_dimension()
        else:
            self.dimension = self.model.get_sentence_embedding_dimension()

    def _load_model(self, model_name: str, device: str):
        try:
            return SentenceTransformer(model_name, device=device, local_files_only=True)
        except Exception as e:
            print(f"Warning: Failed to load embedding model {model_name} ({e}).")
            return None

    def embed(self, texts: List[str]) -> np.ndarray:
        """Encode a batch of texts into dense vectors. Returns (N, D) array."""
        return self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    def embed_single(self, text: str) -> np.ndarray:
        """Encode a single text. Returns (D,) array."""
        return self.embed([text])[0]
