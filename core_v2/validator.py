import json
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
from core_v2.llm_structurer import ExtractedRule

logger = logging.getLogger("MultiHopValidator")

@dataclass
class ValidatedRule:
    resolved_rule_text: str
    source_window_ids: List[str]

GATE_PROMPT = """You are a rule disambiguation expert. You have:

EXISTING RULE:
{existing_rule_text}

NEW RELATED TEXT:
{new_block_text}

Determine if the new text:
A) MODIFIES the existing rule (adds exception, refines condition, provides additional context)
B) Is a SEPARATE INDEPENDENT RULE (different application, material, feature, or threshold)
C) Is IRRELEVANT (not related to the existing rule)

CRITICAL: If the new text specifies a DIFFERENT application context (e.g., different material,
different part type, different manufacturing process), you MUST choose B.

Respond with ONLY a JSON: 
{{
    "action": "MERGE_AND_REFINE" | "SPAWN_NEW_RULE" | "IRRELEVANT", 
    "reasoning": "...",
    "refined_rule_text": "If MERGE_AND_REFINE, provide the combined resolved rule text here. Otherwise null."
}}
"""

class ApplicabilityGate:
    def __init__(self, llm_client):
        self.llm = llm_client

    def gate(self, existing_rule_text: str, new_block_text: str) -> Dict[str, Any]:
        prompt = GATE_PROMPT.format(
            existing_rule_text=existing_rule_text,
            new_block_text=new_block_text
        )
        try:
            raw_response = self.llm.call(prompt)
            if "```" in raw_response:
                raw_response = raw_response.split("```")[1]
                if raw_response.startswith("json"):
                    raw_response = raw_response[4:]
            return json.loads(raw_response.strip())
        except Exception as e:
            if "LLM Error" in str(e) or "Groq Failed" in str(e) or "Rate limit" in str(e):
                logger.error(f"Fatal API error in ApplicabilityGate: {e}")
                raise e
            logger.warning(f"ApplicabilityGate JSON failed: {e}. Defaulting to IRRELEVANT.")
            return {"action": "IRRELEVANT", "reasoning": "Error", "refined_rule_text": None}

class MultiHopValidator:
    def __init__(self, llm_client, vector_store, embedding_manager):
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
        self.gate = ApplicabilityGate(llm_client)

    def validate(self, rules: List[ExtractedRule], truth_store) -> List[ValidatedRule]:
        validated_rules = []
        
        for rule in rules:
            current_text = rule.resolved_rule_text
            used_windows = list(rule.source_window_ids or [rule.source_window_id])
            
            # Embed rule text
            query_emb = self.embedding_manager.embed_single(current_text)
            
            # Search related
            results = self.vector_store.search_all_above_threshold(query_emb, threshold=0.5)
            
            spawned_rules = []
            
            for res in results:
                if res.window_id in used_windows:
                    continue
                
                new_text = truth_store.get_window_text(res.window_id)
                decision = self.gate.gate(current_text, new_text)
                action = decision.get("action")
                
                if action == "MERGE_AND_REFINE":
                    refined_text = decision.get("refined_rule_text")
                    if refined_text:
                        current_text = refined_text
                    used_windows.append(res.window_id)
                elif action == "SPAWN_NEW_RULE":
                    spawned_rules.append(ValidatedRule(resolved_rule_text=new_text, source_window_ids=[res.window_id]))
                    used_windows.append(res.window_id)
                    
            validated_rules.append(ValidatedRule(resolved_rule_text=current_text, source_window_ids=used_windows))
            validated_rules.extend(spawned_rules)
            
        return validated_rules
