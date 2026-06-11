import faiss
import numpy as np
import json
from pathlib import Path
from typing import List, Tuple, Optional

class SearchResult:
    def __init__(self, window_id: str, score: float):
        self.window_id = window_id
        self.score = score

class VectorStore:
    """FAISS-backed vector store with UUID metadata."""
    
    def __init__(self, dimension: int, index_path: Optional[Path] = None):
        self.dimension = dimension
        # Use inner product (cosine similarity since vectors are normalized)
        self.index = faiss.IndexFlatIP(dimension)
        self.window_ids: List[str] = []
        
        if index_path and index_path.exists():
            self.load(index_path)
            
    def add(self, embeddings: np.ndarray, window_ids: List[str]):
        """Add vectors with associated window IDs."""
        if len(embeddings) != len(window_ids):
            raise ValueError("Number of embeddings must match number of window IDs")
        
        if len(embeddings) == 0:
            return
            
        self.index.add(embeddings)
        self.window_ids.extend(window_ids)
        
    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> List[SearchResult]:
        if self.index.ntotal == 0:
            return []
            
        # Ensure 2D array
        if len(query_embedding.shape) == 1:
            query_embedding = np.expand_dims(query_embedding, axis=0)
            
        scores, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                results.append(SearchResult(self.window_ids[idx], float(score)))
                
        return results
        
    def search_all_above_threshold(self, query_embedding: np.ndarray, threshold: float = 0.25) -> List[SearchResult]:
        """Returns ALL results above a threshold. For deterministic coverage."""
        if self.index.ntotal == 0:
            return []
            
        # To get all above threshold, we can search all (ntotal) and filter
        if len(query_embedding.shape) == 1:
            query_embedding = np.expand_dims(query_embedding, axis=0)
            
        scores, indices = self.index.search(query_embedding, self.index.ntotal)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and score >= threshold:
                results.append(SearchResult(self.window_ids[idx], float(score)))
                
        return results
        
    def save(self, path: Path):
        faiss.write_index(self.index, str(path.with_suffix('.index')))
        with open(path.with_suffix('.json'), 'w') as f:
            json.dump({"dimension": self.dimension, "window_ids": self.window_ids}, f)
            
    def load(self, path: Path):
        self.index = faiss.read_index(str(path.with_suffix('.index')))
        with open(path.with_suffix('.json'), 'r') as f:
            data = json.load(f)
            self.dimension = data["dimension"]
            self.window_ids = data["window_ids"]
