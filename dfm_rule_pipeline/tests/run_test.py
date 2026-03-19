import sys
import os
import json
import pandas as pd
from pathlib import Path

# Add root directory to sys.path to allow imports from root
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

# Updated imports based on your pipeline structure
try:
    from dfm_rule_pipeline.pipeline import run_pipeline
    from dfm_rule_pipeline.formatter import run_pipeline as run_formatter
    from dfm_rule_pipeline.llm.client import LLMClient
except ImportError:
    # Fallback for different folder structures
    from pipeline import run_pipeline
    from formatter import run_pipeline as run_formatter
    from llm.client import LLMClient

# File Paths
INPUT_JSON = root_dir / "tests" / "testing.json"
PIPELINE_OUT = root_dir / "output" / "dfm_results.csv"
FINAL_OUT = root_dir / "output" / "performance_test_final.csv"

def prepare_data_from_json(json_path):
    """Loads JSON and prepares it for the pipeline."""
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # We map rule_category to 'rule_type' for the pipeline 
    # so it triggers the correct manufacture schema (Mill, InjectionMolding, etc.)
    # We keep the logic type (Attribute, Relational) as 'logic_style' for reporting.
    formatted_rules = []
    for r in data:
        formatted_rules.append({
            "rule_text": r["rule_text"],
            "rule_type": r["rule_category"], # Domain needed for schema
            "logic_style": r["rule_type"]    # For post-test metrics
        })
    return formatted_rules

def main():
    llm = LLMClient()
    
    if not INPUT_JSON.exists():
        print(f"❌ Error: Could not find {INPUT_JSON}")
        return

    print(f"🚀 Loading 89 rules from: {INPUT_JSON}")
    test_rules = prepare_data_from_json(INPUT_JSON)

    print(f"🔥 Stage 1: Running Refinement Pipeline on {len(test_rules)} rules...")
    # run_pipeline will generate 'output/dfm_results.csv'
    run_pipeline(llm, test_rules) 

    print("🛠️ Stage 2: Formatting & Normalizing into DFM Schema...")
    # run_formatter takes the raw extraction and applies the final CSV formatting
    run_formatter(str(PIPELINE_OUT), str(FINAL_OUT)) 

    # --- Post-Processing: Re-attach logic styles for metrics ---
    print("📊 Stage 3: Syncing Logic Styles for Metrics...")
    final_df = pd.read_csv(FINAL_OUT)
    original_map = {r["rule_text"]: r["logic_style"] for r in test_rules}
    final_df["LogicStyle"] = final_df["RuleText"].map(original_map)
    final_df.to_csv(FINAL_OUT, index=False)

    print(f"✅ Finished! Detailed results generated at: {FINAL_OUT}")

if __name__ == "__main__":
    main()