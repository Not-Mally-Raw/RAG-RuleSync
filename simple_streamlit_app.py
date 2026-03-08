from __future__ import annotations
import asyncio
import os
import tempfile
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
    from dfm_rule_pipeline.schema.feature_schema import features_dict
except ImportError:
    import sys
    sys.path.append(str(Path.cwd() / "dfm_rule_pipeline"))
    try:
        from dfm_rule_pipeline.llm.client import LLMClient
        from dfm_rule_pipeline.pipeline import run_pipeline as run_refinement_pipeline
        from dfm_rule_pipeline.formatter import run_pipeline as run_formatting_pipeline
        from dfm_rule_pipeline.schema.feature_schema import features_dict
    except ImportError:
        st.error("❌ Critical Error: Could not import pipeline modules.")

# ---------------------------------------------------------
# PROMPTS
# ---------------------------------------------------------
CATEGORY_JUDGE_PROMPT = """
You are an expert Manufacturing Systems Engineer. Your task is to analyze a DFM (Design for Manufacturability) rule and route it to the exact schema key required for formalization.

### TARGET DOMAINS (Allowed Keys):
{domain_list}

### DOMAIN FINGERPRINTS (Unique Object/Attribute Identifiers):
- **Injection Moulding**: Look for complex hole attributes like 'DiameterAtTop', 'RadiusAtBot', 'TotalDepth', or 'IsBlind'. Also features like 'Boss', 'Rib', 'Lip', and 'DraftAngle'.
- **Sheetmetal**: Punch features like 'Bridge', 'Spoon', 'Louver', 'Hem', 'Gusset', 'Emboss', 'Dimple'. Look for 'Bend' objects with 'MinRadius' and 'ModuleParams.Thickness'.
- **Die Cast**: Features 'MoldFace', 'MoldWall', and 'WallThickness'. Unique attributes: 'MoldWallThickness', 'MoldClassificationType'.
- **Drill**: Focuses on machined holes. Features 'SimpleHole', 'CBHole', 'CSHole'. Attributes: 'DrillDepth', 'ThreadSize', 'TipAngle', 'BoreDiameter'.
- **Turn**: Lathe operations. Features 'TurnCorner', 'Groove', 'BoredHole'. Attributes: 'MaxOuterDiameter', 'BHRelief', 'StraightnessTolerance'.
- **Mill**: Features 'Pocket', 'Chamfer', and various 'Fillets' (Top, Side, Bot). Attributes: 'MinSideRadius', 'IsBotChamfered', 'Machinability'.
- **Tubing**: Features 'Tube', 'Overlap', 'Straight'. Attributes: 'OuterDiameter', 'IsUniformBendRadius'.
- **Assembly**: High-level relationships. Features 'Fastener', 'Bolt', 'Nut', 'Clearance'. Attributes: 'WrenchFlatDiameter', 'ShankLength', 'IsWasherPresent'.
- **SMForm**: Specialized forming. Features 'SMFace', 'SimpleHole'. Look specifically for 'NormalThickness'.
- **Model**: Global part attributes. Features 'PartBody'. Attributes: 'TightBoxLength', 'SurfaceArea', 'DiagonalLength'.
- **General**: Falling back to 'PMI' (Geometric Tolerances like 'Circularity', 'Concentricity') and 'Thread' units.

### JUDGMENT STEPS (Chain-of-Thought):
1. **Identify Features**: Extract mentioned objects (e.g., "Hole", "Boss").
2. **Verify Context/Fingerprint**: 
   - If "Hole" mentions 'blind/through' and 'ratio' without machining terms (Tap/Thread), it is INJECTION MOULDING.
   - If "Hole" includes machining terms like 'ThreadSize' or 'DrillDepth', it is DRILL.
   - If "Radius" refers to a "Bend", it is likely SHEETMETAL.
   - If "Thickness" is 'NormalThickness', it is strictly SMFORM.
3. **Select Key**: Match the reasoning to exactly one key from the ALLOWED DOMAINS.

### RULE TEXT TO ANALYZE:
"{rule_text}"

### RESPONSE FORMAT (STRICT JSON):
{{
  "analysis": "Step-by-step reasoning based on unique fingerprints found in the text.",
  "judged_category": "Exact Key from Allowed Domains"
}}
"""

# ---------------------------------------------------------
# UI Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="RAG-RuleSync | Enterprise DFM Compiler",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
# AI Judge Logic
# ---------------------------------------------------------
def judge_rule_category(llm_client, rule_text):
    """Uses LLM to determine category strictly from features_dict."""
    domain_list = ", ".join(features_dict.keys())
    schema_summary = "\n".join([f"- {k}: {v[:100]}..." for k, v in features_dict.items()])
    
    prompt = CATEGORY_JUDGE_PROMPT.format(
        domain_list=domain_list,
        schema_summary=schema_summary,
        rule_text=rule_text
    )
    
    try:
        # 1. Use .call() instead of .ask()
        # 2. Removed json_mode=True as it is not supported by your call method
        response = llm_client.call(prompt) 
        
        # 3. Clean and parse the response
        # Since call() returns a raw string, we must parse it to get the category
        data = json.loads(response) if isinstance(response, str) else response
        category = data.get("judged_category", "General")
        
        print(f"DEBUG: Rule: {rule_text[:50]}... | Allotted Category: {category}")
        return category
    except Exception as e:
        print(f"DEBUG: Category Judging Failed: {e}")
        return "General"

# ---------------------------------------------------------
# Helpers & Orchestration
# ---------------------------------------------------------
def force_cleanup(output_dir):
    output_path = Path(output_dir)
    targets = [output_path / "dfm_results.csv", output_path / "extracted_rules.csv"]
    for target in targets:
        if target.exists():
            try: os.remove(target)
            except: pass

def normalize_headers(csv_path):
    try:
        df = pd.read_csv(csv_path)
        rename_map = {"rule": "rule_text", "Rule": "rule_text", "text": "rule_text", "Status": "status"}
        df.rename(columns=rename_map, inplace=True)
        df.to_csv(csv_path, index=False)
    except: pass

def orchestrate_pipeline(doc_path, manual_text, progress_container, max_rules):
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    doc_stem = Path(doc_path).stem if doc_path else "Direct_Input"
    force_cleanup(output_dir)
    
    rules_to_process = []
    llm_client = LLMClient()

    # --- Step 1: Input Handling (Fast-Track vs RAG) ---
    if doc_path:
        progress_container.write(f"📄 **Step 1/3:** Scanning PDF (RAG Pipeline)...")
        raw_result = asyncio.run(system.process_document_advanced(doc_path, enable_enhancement=True))
        rules_to_process = raw_result.get("rules", [])
    elif manual_text:
        progress_container.write(f"🧠 **Step 1/3:** AI Judging Categories (Fast-Track)...")
        lines = [line.strip() for line in manual_text.split('\n') if line.strip()]
        for line in lines:
            category = judge_rule_category(llm_client, line)
            rules_to_process.append({"rule_text": line, "rule_type": category})
        
    if not rules_to_process:
        st.error("❌ No rules found to process.")
        return None

    # Limit Logic
    if len(rules_to_process) > max_rules:
        rules_to_process = rules_to_process[:max_rules]
        progress_container.warning(f"⚠️ Cap Active: Processing {len(rules_to_process)} candidates.")

    # --- Step 2: Formalization ---
    progress_container.write(f"🤖 **Step 2/3:** AI Refinement & Formalization...")
    try:
        run_refinement_pipeline(llm_client, rules_to_process)
    except Exception as e:
        st.error(f"LLM Error: {e}")
        return None

    # --- Step 2.5: Rename ---
    generic_output = output_dir / "dfm_results.csv"
    temp_unique_csv = output_dir / f"TEMP_{doc_stem}_{int(time.time())}.csv"
    time.sleep(1.2) 
    
    if generic_output.exists():
        shutil.move(str(generic_output), str(temp_unique_csv))
        normalize_headers(str(temp_unique_csv))
    else:
        st.error("❌ Pipeline did not generate results file.")
        return None

    # --- Step 3: Formatting ---
    progress_container.write(f"✨ **Step 3/3:** Applying DFM Schema & Normalization...")
    final_csv_path = output_dir / f"{doc_stem}_FINAL_FORMATTED.csv"
    try:
        run_formatting_pipeline(str(temp_unique_csv), str(final_csv_path))
    except Exception as e:
        st.error(f"Formatting failed: {e}")
        return None
    
    if temp_unique_csv.exists(): os.remove(temp_unique_csv)
    return final_csv_path

# ---------------------------------------------------------
# Sidebar & System Init
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2083/2083236.png", width=50) 
    st.title("Settings")
    rule_limit = st.slider("Max Processing Cap", 5, 200, 20)
    profile = st.selectbox("Scan Depth", ["Fast Scan (Draft)", "Balanced", "Deep Inspection"], index=1)
    high_recall = st.toggle("High Recall Mode", value=True)

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
# Main UI
# ---------------------------------------------------------
st.markdown('<p class="main-header">RAG-RuleSync Compiler</p>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📄 PDF Specification", "✍️ Raw Text Input"])
doc_path, manual_text = None, None

with tab1:
    uploaded = st.file_uploader("Drop DFM Spec PDF here", type=["pdf"])
    if uploaded:
        tmp_path = Path(tempfile.gettempdir()) / uploaded.name
        tmp_path.write_bytes(uploaded.getbuffer())
        doc_path = str(tmp_path)

with tab2:
    manual_text = st.text_area("Paste rules directly (one per line)", height=250)

input_ready = bool(doc_path) or (bool(manual_text) and manual_text.strip() != "")

if st.button("🚀 Start Production Pipeline", type="primary", disabled=not input_ready, use_container_width=True):
    if "final_df" in st.session_state: del st.session_state["final_df"]
    with st.status("🏗️ Orchestrating Extraction Pipeline...", expanded=True) as status:
        start_time = time.time()
        final_csv = orchestrate_pipeline(doc_path, manual_text, status, rule_limit)
        
        if final_csv and os.path.exists(final_csv):
            status.update(label=f"✅ Completed in {time.time() - start_time:.1f}s", state="complete")
            df = pd.read_csv(final_csv)
            try:
                df["dfm_json"] = df["dfm_json"].apply(lambda x: json.loads(x) if isinstance(x, str) and x.strip() else None)
            except: pass 
            st.session_state["final_df"] = df
            st.session_state["final_csv_path"] = str(final_csv)
            
            # --- FIXED NONE-TYPE CRASH HERE ---
            if uploaded:
                st.session_state["doc_name"] = uploaded.name
            else:
                st.session_state["doc_name"] = "Direct_Text_Input.pdf"
        else:
            status.update(label="❌ Pipeline Failed", state="error")

# ---------------------------------------------------------
# Results View
# ---------------------------------------------------------
if "final_df" in st.session_state:
    df = st.session_state["final_df"]
    st.markdown("---")
    st.subheader("📊 Extraction Analytics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Processed", len(df))
    c2.metric("CAD Ready", df['dfm_json'].notna().sum())
    c3.metric("Advisory/Issues", len(df[df['dfm_json'].isna()]))
    
    st.dataframe(df, use_container_width=True, column_config={
        "dfm_json": st.column_config.JsonColumn("Structured JSON"),
        "RuleText": st.column_config.TextColumn("Original Rule", width="large"),
    }, hide_index=True)
    
    with open(st.session_state["final_csv_path"], "rb") as f:
        st.download_button("📥 Download Final CSV", f, file_name=f"{Path(st.session_state['doc_name']).stem}_Rules.csv", mime="text/csv")