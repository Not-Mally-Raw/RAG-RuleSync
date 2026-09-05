import sys
import logging
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core_v2.parser import LayoutAwareParser
from core_v2.windower import SlidingWindowGenerator
from core_v2.truth_store import TruthStore
from core_v2.embeddings import EmbeddingManager
from core_v2.vector_store import VectorStore
from core_v2.dfm_anchors import DFMAnchorClassifier
from core_v2.extractor import DeterministicExtractor

logging.basicConfig(level=logging.INFO)

class MockLLM:
    def call(self, prompt: str) -> str:
        if "DFM rule text extractor" in prompt:
            # Structurer mock
            if "bend radius is 2mm" in prompt.lower():
                return '[{"rule_text": "The minimum bend radius is 2mm.", "resolved_rule_text": "The minimum bend radius is 2mm."}]'
            if "greater than 3mm" in prompt.lower():
                return '[{"rule_text": "It must be greater than 3mm.", "resolved_rule_text": "The flange height must be greater than 3mm."}]'
            return '[]'
            
        if "rule disambiguation expert" in prompt:
            # Gate mock
            if "bikes" in prompt and "cars" in prompt:
                return '{"action": "SPAWN_NEW_RULE", "reasoning": "different application", "refined_rule_text": null}'
            if "stainless" in prompt:
                return '{"action": "MERGE_AND_REFINE", "reasoning": "modification", "refined_rule_text": "The bend radius must be 2.0mm. For stainless steel, use 3.0mm."}'
            return '{"action": "IRRELEVANT", "reasoning": "not related", "refined_rule_text": null}'
        
        return "{}"

def test_extraction():
    parser = LayoutAwareParser()
    windower = SlidingWindowGenerator(window_size=1, stride=1)
    db_file = Path(".test_tmp") / f"test_truth_store_{uuid.uuid4().hex}.db"
    db_file.parent.mkdir(exist_ok=True)
    if db_file.exists(): db_file.unlink()
    truth_store = TruthStore(db_file)
    from dfm_rule_pipeline.config import EMBEDDING_MODEL
    embedding_manager = EmbeddingManager(model_name=EMBEDDING_MODEL)
    vector_store = VectorStore(dimension=384) 
    anchor_classifier = DFMAnchorClassifier(embedding_manager=embedding_manager, threshold=0.2) # Low threshold for mock text
    llm_client = MockLLM()
    
    extractor = DeterministicExtractor(
        parser=parser,
        windower=windower,
        truth_store=truth_store,
        embedding_manager=embedding_manager,
        vector_store=vector_store,
        anchor_classifier=anchor_classifier,
        llm_client=llm_client
    )
    
    test_text = "The minimum bend radius is 2mm. It must be greater than 3mm for flange height. For stainless steel, use 3.0mm for bend radius. Also, bikes use 1.2mm thickness while cars use 3.4mm thickness."
    
    # Mocking parser payload to bypass PDF requirement
    from core_v2.parser import DocumentPayload, StructuralBlock
    payload = DocumentPayload(
        blocks=[StructuralBlock(block_id="b1", text=test_text, block_type="paragraph", page_number=1, section_title="Test Section", source_document="dummy.pdf")],
        metadata={}
    )
    
    # Override parser.parse to return mock payload
    extractor.parser.parse = lambda x: payload
    
    try:
        results = extractor.extract(Path("dummy.pdf"))
        print("\n=== Extraction Results ===")
        for r in results:
            print(f"- Text: {r['rule_text']}")
            print(f"  Source Windows: {r['source_windows']}")
    finally:
        pass

if __name__ == "__main__":
    test_extraction()
