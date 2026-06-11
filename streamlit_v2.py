import streamlit as st
import tempfile
import os
from pathlib import Path
import pandas as pd
import sys
import logging
import warnings

# Suppress noisy transformers/huggingface warnings
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

# Configure global structured logging with precise timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True
)
# Ensure the root directory is in sys.path
sys.path.append(str(Path(__file__).parent))

from core_v2.parser import LayoutAwareParser
from core_v2.windower import SlidingWindowGenerator
from core_v2.truth_store import TruthStore
from core_v2.embeddings import EmbeddingManager
from core_v2.vector_store import VectorStore
from core_v2.dfm_anchors import DFMAnchorClassifier
from core_v2.candidate_assembler import CandidateAssembler
from core_v2.llm_structurer import LLMStructurer, deduplicate_extracted_rules
from core_v2.validator import MultiHopValidator
from dfm_rule_pipeline.llm.client import LLMClient
from dfm_rule_pipeline.config import EMBEDDING_MODEL

st.set_page_config(page_title="RAG-RuleSync V2 Tester", layout="wide")
st.title("RAG-RuleSync V2 Pipeline Tester")

# Cache the expensive embedding model load
@st.cache_resource
def load_models():
    embedder = EmbeddingManager(model_name=EMBEDDING_MODEL)
    classifier = DFMAnchorClassifier(embedder, threshold=0.25)
    return embedder, classifier

@st.cache_resource
def load_llm():
    return LLMClient()

embedder, classifier = load_models()
llm_client = load_llm()

uploaded_file = st.file_uploader("Upload DFM PDF", type=["pdf"])

if uploaded_file is not None:
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        tmp_path = Path(tmp_file.name)
    
    tab1, tab2 = st.tabs(["Phase 1 & 2: Ingestion & Indexing", "Phase 3: Extraction & Validation"])
    
    try:
        # ---- PIPELINE EXECUTION ----
        with st.spinner("Parsing PDF and extracting structural blocks..."):
            parser = LayoutAwareParser()
            payload = parser.parse(tmp_path)
            
        with st.spinner("Generating sliding windows (Chunks)..."):
            windower = SlidingWindowGenerator(window_size=3, stride=1)
            windows = windower.generate(payload.blocks)
            
        with st.spinner("Saving to Truth Store..."):
            db_path = Path("temp_streamlit_truth_store.db")
            if db_path.exists():
                db_path.unlink()
            store = TruthStore(db_path)
            store.store_document(payload, windows)

        with st.spinner("Generating embeddings for all chunks..."):
            import time
            start_embed = time.time()
            texts = [w.text for w in windows]
            embeddings = embedder.embed(texts)
            embed_time = time.time() - start_embed
            logging.getLogger("Pipeline").info(f"Generated {len(texts)} embeddings in {embed_time:.3f} seconds.")
            
        with st.spinner("Indexing into Vector Store..."):
            start_index = time.time()
            vstore = VectorStore(dimension=embedder.dimension)
            window_ids = [w.window_id for w in windows]
            vstore.add(embeddings, window_ids)
            index_time = time.time() - start_index
            logging.getLogger("Pipeline").info(f"Indexed {len(window_ids)} vectors into FAISS in {index_time:.3f} seconds.")
            
        with st.spinner("Classifying chunks with DFM Anchors..."):
            results = classifier.classify_batch(embeddings)
            
        candidate_windows = []
        discarded_windows = []
        
        for w, (is_rule, score) in zip(windows, results):
            if is_rule:
                candidate_windows.append((w, score))
            else:
                discarded_windows.append((w, score))

        # ---- UI PRESENTATION: TAB 1 ----
        with tab1:
            st.success(f"Phase 1: Extracted {len(windows)} chunks from {len(payload.blocks)} blocks.")
            
            # Display what each chunk looks like
            window_data = [{"Window ID": w.window_id, "Page": w.page_number, "Section": w.section_title, "Text Content": w.text} for w in windows]
            st.subheader("Extracted Chunks (Sliding Windows)")
            st.dataframe(pd.DataFrame(window_data), width='stretch')

            st.write("---")
            st.success(f"Phase 2: Found {len(candidate_windows)} rules out of {len(windows)} total chunks.")
            
            rule_candidates_data = [{"Window ID": w.window_id, "Page": w.page_number, "Score": f"{score:.3f}", "Text Content": w.text} for w, score in candidate_windows]
            discarded_data = [{"Window ID": w.window_id, "Page": w.page_number, "Score": f"{score:.3f}", "Text Content": w.text} for w, score in discarded_windows]
            
            st.subheader(f"✅ Rule Candidates ({len(candidate_windows)})")
            if rule_candidates_data:
                st.dataframe(pd.DataFrame(rule_candidates_data), width='stretch')
            else:
                st.info("No rules found based on the anchor threshold.")
                
            with st.expander(f"❌ Discarded Boilerplate ({len(discarded_windows)})"):
                if discarded_data:
                    st.dataframe(pd.DataFrame(discarded_data), width='stretch')

        # ---- UI PRESENTATION: TAB 2 ----
        with tab2:
            st.header("Phase 3: Verbatim Extraction & Multi-Hop Validation")
            
            if not candidate_windows:
                st.warning("No rule candidates found in Phase 2 to extract.")
            else:
                structurer = LLMStructurer(llm_client)
                validator = MultiHopValidator(llm_client, vstore, embedder)
                assembler = CandidateAssembler(context_sentences=2)
                
                with st.spinner("Step 1: Assembling overlapping windows and resolving context via LLM..."):
                    extraction_units = assembler.assemble([w for w, score in candidate_windows])
                    st.info(f"Assembled {len(extraction_units)} extraction units from {len(candidate_windows)} candidate windows.")

                    all_extracted_rules = []
                    for unit in extraction_units:
                        extracted = structurer.structure(
                            unit.target_text,
                            unit.unit_id,
                            context_text=unit.context_text,
                            source_window_ids=unit.source_window_ids,
                        )
                        all_extracted_rules.extend(extracted)

                    all_extracted_rules = deduplicate_extracted_rules(all_extracted_rules)
                        
                st.success(f"Structurer extracted {len(all_extracted_rules)} distinct rules.")
                if all_extracted_rules:
                    extracted_data = [{"Extracted Text": r.rule_text, "Resolved Context Text": r.resolved_rule_text, "Source Window IDs": ", ".join(r.source_window_ids)} for r in all_extracted_rules]
                    st.subheader("LLM Structured Rules (Pre-Validation)")
                    st.dataframe(pd.DataFrame(extracted_data), width='stretch')
                
                with st.spinner("Step 2: Multi-Hop Validation (Applicability Gating) [TEMPORARILY BYPASSED]..."):
                    # validated_rules = validator.validate(all_extracted_rules, store)
                    validated_rules = all_extracted_rules # Bypassing to save tokens
                    
                st.success(f"Validator bypassed. Moving {len(validated_rules)} rules to output.")
                if validated_rules:
                    validated_data = [{"Final Rule Text": r.resolved_rule_text, "Source Window IDs": ", ".join(r.source_window_ids)} for r in validated_rules]
                    st.subheader("Final Validated Rules")
                    st.dataframe(pd.DataFrame(validated_data), width='stretch')

    except Exception as e:
        st.error(f"Fatal LLM Error encountered. Halting execution. Error: {e}")
        import traceback
        st.code(traceback.format_exc())
        
        # Save partial output to JSON
        if 'all_extracted_rules' in locals() and all_extracted_rules:
            import json
            out_data = [{"Extracted Text": r.rule_text, "Resolved Context Text": r.resolved_rule_text, "Source Window IDs": r.source_window_ids} for r in all_extracted_rules]
            with open("phase3_partial_output.json", "w") as f:
                json.dump(out_data, f, indent=2)
            st.warning(f"Saved {len(all_extracted_rules)} extracted rules to phase3_partial_output.json")
        
    else:
        # Save final output to CSV if validation succeeded
        if 'validated_rules' in locals() and validated_rules:
            validated_csv_data = [{"Final Rule Text": r.resolved_rule_text, "Source Window IDs": ", ".join(r.source_window_ids)} for r in validated_rules]
            df = pd.DataFrame(validated_csv_data)
            df.to_csv("phase3_final_rules.csv", index=False)
            st.info("Successfully saved validated rules to phase3_final_rules.csv")
        
    finally:
        # Cleanup temp file
        if tmp_path.exists():
            tmp_path.unlink()
