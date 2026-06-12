import numpy as np
from typing import Tuple, List
from .embeddings import EmbeddingManager

# Fixed anchor phrases that define what a DFM rule looks like
DFM_ANCHOR_PHRASES = [
    # Dimensional constraints
    "minimum thickness shall be",
    "maximum bend radius",
    "clearance between features must not be less than",
    "tolerance of plus or minus",
    "wall thickness should be at least",
    
    # Manufacturing process rules
    "draft angle for injection molding",
    "sheet metal bend radius requirement",
    "hole diameter to depth ratio",
    "distance between holes shall be",
    
    # Material specifications
    "material thickness requirement",
    "surface finish roughness value",
    "hardness specification",
    
    # General constraint patterns
    "shall not exceed",
    "must be greater than or equal to",
    "recommended value is",
    "ensure that the",
    "the ratio of",
]

# ============================================================================
# FUTURE TAXONOMY-AWARE TRIGGERS (Commented out for now per user request)
# ============================================================================
# In the future, we will transition from the hard-coded anchor phrases above 
# to a hybrid approach using these taxonomy-driven signals to prevent false negatives.
#
# TAXONOMY_OBJECTS = [
#     "Bridge", "Flange", "Emboss", "Boss", "Rib", "Hole", "Tube", "Pocket",
#     "PMI", "Thread", "Washer", "Pin", "Wall", "Clearance", "Gusset"
# ]
#
# QUANTITATIVE_SIGNALS = [
#     "mm", "degree", "ratio", "times", "%", "minimum", "maximum", 
#     "between", "at least", "at most", "less than", "greater than"
# ]
#
# LINGUISTIC_SIGNALS = [
#     "must", "shall", "should", "recommended", "ensure", "avoid", 
#     "check", "conform", "prevent", "allow"
# ]
#
# APPLICABILITY_CONSTRAINTS = [
#     "blind hole", "through hole", "material", "thread class", 
#     "supported wall", "unsupported wall", "6061-t6"
# ]
# ============================================================================


class DFMAnchorClassifier:
    """Binary classifier: is this text block a potential DFM rule?"""
    
    def __init__(self, embedding_manager: EmbeddingManager, threshold: float = 0.25):
        self.threshold = threshold
        self.anchor_embeddings = embedding_manager.embed(DFM_ANCHOR_PHRASES)
        
    def classify(self, block_embedding: np.ndarray) -> Tuple[bool, float]:
        """Returns (is_rule_candidate, max_similarity_score)."""
        # Compute cosine similarity (inner product of normalized vectors)
        similarities = np.dot(self.anchor_embeddings, block_embedding.T)
        max_score = float(np.max(similarities))
        return (max_score >= self.threshold, max_score)
        
    def classify_batch(self, block_embeddings: np.ndarray) -> List[Tuple[bool, float]]:
        """Classify a batch of embeddings."""
        # anchor_embeddings: (M, D)
        # block_embeddings: (N, D)
        # result: (M, N) -> dot product
        similarities = np.dot(self.anchor_embeddings, block_embeddings.T)
        # We want max over anchors (M), so max along axis 0
        max_scores = np.max(similarities, axis=0)
        
        results = []
        for score in max_scores:
            results.append((float(score) >= self.threshold, float(score)))
        return results
