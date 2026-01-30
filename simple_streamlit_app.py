from __future__ import annotations
import asyncio
import os
import tempfile
import glob
import json
import time
import shutil
import pandas as pd
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# --- Internal Core Imports ---
from core.enhanced_rule_engine import EnhancedConfig
from core.production_system import ProductionRuleExtractionSystem
from core.rule_extraction import RuleExtractionSettings

# --- Pipeline Imports ---
try:
    from dfm_rule_pipeline.llm.client import LLMClient
    from dfm_rule_pipeline.pipeline import run_pipeline as run_refinement_pipeline
    from dfm_rule_pipeline.formatter import run_pipeline as run_formatting_pipeline
except ImportError:
    import sys
    sys.path.append(str(Path.cwd() / "dfm_rule_pipeline"))
    try:
        from dfm_rule_pipeline.llm.client import LLMClient
        from dfm_rule_pipeline.pipeline import run_pipeline as run_refinement_pipeline
        from dfm_rule_pipeline.formatter import run_pipeline as run_formatting_pipeline
    except ImportError:
        st.error("❌ Critical Error: Could not import pipeline modules.")

# ---------------------------------------------------------
# UI Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="RAG-RuleSync | Enterprise DFM Compiler",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished look
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0rem; }
    .stStatus { border: 1px solid #E2E8F0; border-radius: 8px; background-color: #F8FAFC; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; color: #0F172A; }
    div[data-testid="stDataFrame"] { border: 1px solid #E2E8F0; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

load_dotenv(override=False)

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2083/2083236.png", width=50) 
    st.title("Settings")
    
    st.markdown("### 🛑 Safety & Cost Cap")
    rule_limit = st.slider("Max Processing Cap", 5, 200, 20, help="Strictly limits the number of rules sent to the LLM.")
    
    st.markdown("### Extraction Profile")
    profile = st.selectbox("Scan Depth", ["Fast Scan (Draft)", "Balanced", "Deep Inspection"], index=1)
    high_recall = st.toggle("High Recall Mode", value=True)
    
    st.markdown("---")
    if os.getenv("GROQ_API_KEY"):
        st.success("✅ Groq API Connected")
    else:
        st.error("❌ Groq API Key Missing")

# ---------------------------------------------------------
# System Setup
# ---------------------------------------------------------
@st.cache_resource
def get_system():
    key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "gpt-oss-20b-latest")
    return ProductionRuleExtractionSystem(
        groq_api_key=key,
        pipeline_settings=RuleExtractionSettings(groq_api_key=key, groq_model=model),
        enable_enhanced=True,
        enhanced_config=EnhancedConfig(groq_api_key=key, recall_mode=high_recall),
    )

system = get_system()

# ---------------------------------------------------------
# Helpers & Cleanup
# ---------------------------------------------------------
def force_cleanup(output_dir):
    """
    CRITICAL FIX: Aggressively deletes old results files before starting.
    This prevents the 'appending' bug where old rules mixed with new ones.
    """
    output_path = Path(output_dir)
    targets = [
        output_path / "dfm_results.csv",
        output_path / "extracted_rules.csv"
    ]
    for target in targets:
        if target.exists():
            try:
                os.remove(target)
            except Exception:
                pass # Ignore if file is locked

def normalize_headers(csv_path):
    """Ensures intermediate CSV has correct headers for the formatter."""
    try:
        df = pd.read_csv(csv_path)
        rename_map = {"rule": "rule_text", "Rule": "rule_text", "text": "rule_text", "Status": "status"}
        df.rename(columns=rename_map, inplace=True)
        df.to_csv(csv_path, index=False)
    except Exception:
        pass

def orchestrate_pipeline(doc_path, progress_container, max_rules):
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    doc_stem = Path(doc_path).stem
    
    # 1. CLEANUP OLD FILES (The Fix for Appending Bug)
    force_cleanup(output_dir)
    
    # --- Step 1: Raw Extraction ---
    progress_container.write(f"📄 **Step 1/3:** Scanning PDF...")
    raw_result = asyncio.run(system.process_document_advanced(doc_path, enable_enhancement=True))
    
    all_rules = raw_result.get("rules", [])
    if not all_rules: return None

    # Limit Logic
    if len(all_rules) > max_rules:
        rules_to_process = all_rules[:max_rules]
        progress_container.warning(f"⚠️ Cap Active: Processing {max_rules} of {len(all_rules)} candidates.")
    else:
        rules_to_process = all_rules
        progress_container.info(f"✅ Processing all {len(all_rules)} candidates.")

    # --- Step 2: LLM Refinement ---
    progress_container.write(f"🤖 **Step 2/3:** AI Refinement...")
    try:
        llm_client = LLMClient()
    except Exception as e:
        st.error(f"LLM Error: {e}")
        return None

    # Run Pipeline (Produces generic 'output/dfm_results.csv')
    run_refinement_pipeline(llm_client, rules_to_process)
    
    # --- Step 2.5: ATOMIC RENAME ---
    generic_output = output_dir / "dfm_results.csv"
    temp_unique_csv = output_dir / f"TEMP_{doc_stem}_{int(time.time())}.csv"
    
    time.sleep(1.5) # Wait for file write
    
    if generic_output.exists():
        shutil.move(str(generic_output), str(temp_unique_csv))
        normalize_headers(str(temp_unique_csv))
    else:
        st.error("❌ Pipeline did not generate results file.")
        return None

    # --- Step 3: Formatting ---
    progress_container.write(f"✨ **Step 3/3:** Applying DFM Schema...")
    final_csv_path = output_dir / f"{doc_stem}_FINAL_FORMATTED.csv"
    
    try:
        run_formatting_pipeline(str(temp_unique_csv), str(final_csv_path))
    except Exception as e:
        st.error(f"Formatting failed: {e}")
        return None
    
    # --- Step 4: CLEANUP ---
    if temp_unique_csv.exists():
        os.remove(temp_unique_csv)

    return final_csv_path

# ---------------------------------------------------------
# Main UI
# ---------------------------------------------------------
st.markdown('<p class="main-header">RAG-RuleSync Compiler</p>', unsafe_allow_html=True)

uploaded = st.file_uploader("Drop your DFM Specification PDF here", type=["pdf"])
doc_path = ""

if uploaded:
    tmp_path = Path(tempfile.gettempdir()) / uploaded.name
    tmp_path.write_bytes(uploaded.getbuffer())
    doc_path = str(tmp_path)
    st.info(f"📂 File loaded: **{uploaded.name}**")

if st.button("🚀 Start Production Pipeline", type="primary", disabled=not bool(doc_path), use_container_width=True):
    
    if "final_df" in st.session_state: del st.session_state["final_df"]
        
    with st.status("🏗️ Orchestrating Extraction Pipeline...", expanded=True) as status:
        start_time = time.time()
        final_csv = orchestrate_pipeline(doc_path, status, rule_limit)
        
        if final_csv and os.path.exists(final_csv):
            elapsed = time.time() - start_time
            status.update(label=f"✅ Completed in {elapsed:.1f}s", state="complete", expanded=False)
            
            # Load Data and Convert JSON strings to Dicts for the UI
            df = pd.read_csv(final_csv)
            # Try parsing the JSON column so the JsonColumn component can render it
            try:
                df["dfm_json"] = df["dfm_json"].apply(lambda x: json.loads(x) if isinstance(x, str) and x.strip() else None)
            except:
                pass 
                
            st.session_state["final_df"] = df
            st.session_state["final_csv_path"] = str(final_csv)
            st.session_state["doc_name"] = uploaded.name
        else:
            status.update(label="❌ Pipeline Failed", state="error")

# ---------------------------------------------------------
# Results
# ---------------------------------------------------------
if "final_df" in st.session_state:
    df = st.session_state["final_df"]
    
    st.markdown("---")
    st.subheader("📊 Extraction Analytics")
    
    # Logic for Metrics
    cad_ready_count = df['dfm_json'].notna().sum()
    advisory_count = len(df[df['DecisionCode'].astype(str).str.contains("advisory|Failure", case=False, regex=True)])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Processed", len(df))
    m2.metric("CAD Ready", cad_ready_count)
    m3.metric("Advisory / Skipped", advisory_count)
    
    # --- FILTERS (New Feature) ---
    filter_option = st.radio(
        "View Mode:", 
        ["All Rules", "CAD Ready Only", "Issues/Advisory"], 
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # Apply Filter
    df_display = df.copy()
    if filter_option == "CAD Ready Only":
        df_display = df[df['dfm_json'].notna()]
    elif filter_option == "Issues/Advisory":
        df_display = df[df['dfm_json'].isna()]

    # --- ENHANCED TABLE ---
    st.dataframe(
        df_display, 
        use_container_width=True, 
        column_config={
            "dfm_json": st.column_config.JsonColumn("Structured JSON", help="Click to expand"),
            "Status": st.column_config.TextColumn("Status"),
            "DecisionCode": st.column_config.TextColumn("Decision"),
            "RuleText": st.column_config.TextColumn("Original Rule", width="large"),
        },
        hide_index=True
    )
    
    # Download Button
    with open(st.session_state["final_csv_path"], "rb") as f:
        st.download_button(
            label="📥 Download Final CSV",
            data=f,
            file_name=f"{Path(st.session_state['doc_name']).stem}_DFM_Rules.csv",
            mime="text/csv",
            type="primary"
        )

st.markdown("---")
st.markdown("<div style='text-align: center; color: #94A3B8; font-size: 0.8rem;'>RAG-RuleSync System v2.2.0 | © 2026 Engineering Dept</div>", unsafe_allow_html=True)