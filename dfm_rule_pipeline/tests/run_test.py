import sys
import os
import pandas as pd
from pathlib import Path

# Add root directory to sys.path to allow imports from root
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from pipeline import run_pipeline
from formatter import run_pipeline as run_formatter
from llm.client import LLMClient

# File Paths
INPUT_TEST_CSV = root_dir / "tests" / "Testing.xlsx"
PIPELINE_OUT = root_dir / "output" / "dfm_results.csv"
FINAL_OUT = root_dir / "output" / "test_results_final.csv"

def prepare_data(csv_path):
    df = pd.read_excel(csv_path)
    return [{"rule_text": r["Rule Text"], "rule_type": r["Category"]} for _, r in df.iterrows()]

def main():
    llm = LLMClient()
    print(f"🚀 Loading rules from: {INPUT_TEST_CSV}")
    test_rules = prepare_data(INPUT_TEST_CSV)

    print("🔥 Stage 1: Running Pipeline...")
    run_pipeline(llm, test_rules) # Generates raw CSV

    print("🛠️ Stage 2: Formatting & Normalizing...")
    run_formatter(str(PIPELINE_OUT), str(FINAL_OUT)) # Normalizes variables

    print(f"✅ Finished! Results in: {FINAL_OUT}")

if __name__ == "__main__":
    main()