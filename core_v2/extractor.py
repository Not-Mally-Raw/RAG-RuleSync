import logging
from pathlib import Path
from typing import List, Dict, Any

from core_v2.parser import LayoutAwareParser
from core_v2.windower import SlidingWindowGenerator
from core_v2.truth_store import TruthStore
from core_v2.embeddings import EmbeddingManager
from core_v2.vector_store import VectorStore
from core_v2.dfm_anchors import DFMAnchorClassifier
from core_v2.candidate_assembler import CandidateAssembler
from core_v2.llm_structurer import LLMStructurer, deduplicate_extracted_rules
from core_v2.validator import MultiHopValidator

logger = logging.getLogger("DeterministicExtractor")

class DeterministicExtractor:
    def __init__(
        self,
        parser: LayoutAwareParser,
        windower: SlidingWindowGenerator,
        truth_store: TruthStore,
        embedding_manager: EmbeddingManager,
        vector_store: VectorStore,
        anchor_classifier: DFMAnchorClassifier,
        llm_client: Any
    ):
        self.parser = parser
        self.windower = windower
        self.truth_store = truth_store
        self.embedding_manager = embedding_manager
        self.vector_store = vector_store
        self.anchor_classifier = anchor_classifier
        self.candidate_assembler = CandidateAssembler(context_sentences=2)
        self.structurer = LLMStructurer(llm_client)
        self.validator = MultiHopValidator(llm_client, vector_store, embedding_manager)

    def extract(self, file_path: Path) -> List[Dict[str, Any]]:
        # 1. PARSE
        logger.info(f"Parsing {file_path}")
        payload = self.parser.parse(file_path)

        # 2. WINDOW
        windows = self.windower.generate(payload.blocks)
        
        # 3. INDEX
        self.truth_store.store_document(payload, windows)
        
        window_texts = [w.text for w in windows]
        window_ids = [w.window_id for w in windows]
        
        if not window_texts:
            return []
            
        embeddings = self.embedding_manager.embed(window_texts)
        self.vector_store.add(embeddings, window_ids)
        
        # 4. CLASSIFY
        classifications = self.anchor_classifier.classify_batch(embeddings)
        
        candidate_windows = []
        for i, (is_rule, score) in enumerate(classifications):
            if is_rule:
                candidate_windows.append(windows[i])
        
        logger.info(f"Found {len(candidate_windows)} rule candidate windows out of {len(windows)}")
        
        # 5. COLLAPSE OVERLAPPING WINDOWS, EXTRACT & 6. ANCHOR
        extraction_units = self.candidate_assembler.assemble(candidate_windows)
        logger.info(f"Assembled {len(extraction_units)} extraction units from candidate windows")

        all_extracted_rules = []
        for unit in extraction_units:
            extracted = self.structurer.structure(
                unit.target_text,
                unit.unit_id,
                context_text=unit.context_text,
                source_window_ids=unit.source_window_ids,
            )
            all_extracted_rules.extend(extracted)

        all_extracted_rules = deduplicate_extracted_rules(all_extracted_rules)
            
        logger.info(f"Extracted {len(all_extracted_rules)} distinct rules")
        
        # 7. VALIDATE
        # validated_rules = self.validator.validate(all_extracted_rules, self.truth_store)
        validated_rules = all_extracted_rules
        
        logger.info(f"Final validated rules: {len(validated_rules)}")
        
        # 8. RETURN format
        results = []
        for vr in validated_rules:
            results.append({
                "rule_text": vr.resolved_rule_text,
                "source_windows": vr.source_window_ids
            })
            
        return results
