import json
import os
import sys

# --- IMPORT LLM CLIENT ---
try:
    from llm.client import LLMClient
except ImportError:
    print("❌ Critical Error: Could not import 'LLMClient' from 'llm.llm_client'.")
    sys.exit(1)

from pipeline import run_pipeline

# Configuration
INPUT_FILE = r"dfm_rule_pipeline\tests\testing.json"

def load_rules(filepath):
    """
    Robust JSON loader that FLATTENS nested structures.
    Handles: { "documents": [ { "rules": [...] } ] }
    """
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return []
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    all_rules = []

    # CASE 1: Root is a Dict
    if isinstance(data, dict):
        # Nested Structure (The one you pasted)
        if "documents" in data:
            print("📦 Detected nested 'documents' structure. Flattening...")
            for doc in data["documents"]:
                if "rules" in doc:
                    all_rules.extend(doc["rules"])
        
        # Flat "rules" key
        elif "rules" in data:
            all_rules.extend(data["rules"])
            
        # Single Rule Object
        elif "rule_text" in data:
            all_rules.append(data)

    # CASE 2: Root is a List
    elif isinstance(data, list):
        # List of rules?
        all_rules.extend(data)
            
    return all_rules

def main():
    print("🚀 DFM Rule Pipeline - Production Mode")
    print("========================================")
    
    # 1. INITIALIZE LLM
    print("🔌 Initializing LLM Client...")
    try:
        llm = LLMClient() 
    except Exception as e:
        print(f"❌ Error initializing LLMClient: {e}")
        return

    # 2. LOAD DATA
    print(f"📂 Loading rules from: {INPUT_FILE}")
    rules_data = load_rules(INPUT_FILE)
    
    if not rules_data:
        print("❌ No rules found (Check JSON structure).")
        return

    # 3. RUN PIPELINE
    # The pipeline.py now has the safety check for 'llm', so this is safe.
    run_pipeline(llm, rules_data)

if __name__ == "__main__":
    main()