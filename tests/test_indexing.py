import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from core_v2.embeddings import EmbeddingManager
from core_v2.vector_store import VectorStore
from core_v2.dfm_anchors import DFMAnchorClassifier

def test_indexing():
    print("Loading Embedding Manager...")
    # Use the lighter fallback model    print("Running Indexing Test...")
    from dfm_rule_pipeline.config import EMBEDDING_MODEL
    embedder = EmbeddingManager(model_name=EMBEDDING_MODEL)
    vstore = VectorStore(dimension=embedder.dimension)
    
    # 1. Test DFM Anchor Classifier
    print("\nTesting DFM Anchor Classifier...")
    classifier = DFMAnchorClassifier(embedder, threshold=0.25)
    
    test_blocks = [
        "The minimum bend radius for sheet metal is 2.0mm.",
        "Welcome to the engineering guidelines document.",
        "Table of contents is located on page 4."
    ]
    
    block_embeddings = embedder.embed(test_blocks)
    results = classifier.classify_batch(block_embeddings)
    
    for text, (is_rule, score) in zip(test_blocks, results):
        print(f"'{text}' -> Rule? {is_rule} (Score: {score:.3f})")
        
    assert results[0][0] is True, "Failed to classify obvious rule"
    
    # 2. Test Vector Store
    print("\nTesting Vector Store...")
    vstore = VectorStore(dimension=embedder.dimension)
    
    window_ids = ["w1", "w2", "w3"]
    vstore.add(block_embeddings, window_ids)
    
    # Search for something related to bend radius
    query_emb = embedder.embed_single("What is the bend radius requirement?")
    search_res = vstore.search(query_emb, top_k=1)
    
    print(f"Top search result for 'bend radius requirement': {search_res[0].window_id} (Score: {search_res[0].score:.3f})")
    assert search_res[0].window_id == "w1", "Vector search failed to find the right window"
    
    print("\nIndexing pipeline (Embeddings + VectorStore + Classifier) works successfully!")
    
if __name__ == "__main__":
    test_indexing()
