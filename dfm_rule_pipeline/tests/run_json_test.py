import sys
import json
from pathlib import Path

# Add root directory to sys.path to allow imports from root
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from pipeline import run_pipeline
from llm.client import LLMClient

INPUT_FILE = root_dir / "tests" / "final.json"

def prepare_data(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    rules = []
    for doc in data.get("documents", []):
        for rule in doc.get("rules", []):
            rules.append({
                "rule_text": rule["rule_text"],
                # We intentionally don't pass rule_type (Category) to test the LLM resolver
                # "rule_type": rule.get("rule_type", "General") 
            })
    return rules

def main():
    llm = LLMClient()
    print(f"🚀 Loading rules from: {INPUT_FILE}")
    test_rules = prepare_data(INPUT_FILE)
    print(f"Found {len(test_rules)} rules.")

    print("🔥 Running Pipeline...")
    # This will generate output/dfm_results.csv
    run_pipeline(llm, test_rules) 

    print("✅ Finished!")

if __name__ == "__main__":
    main()
