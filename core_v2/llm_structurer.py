import json
import logging
import re
from typing import List
from dataclasses import dataclass, field

logger = logging.getLogger("LLMStructurer")

STRUCTURING_PROMPT = """You are an expert Design-for-Manufacturability (DFM) rule extractor.
You will be provided with a TARGET TEXT block and its SURROUNDING CONTEXT (Section title and neighboring sentences).

Your objective is to extract distinct, quantifiable, and deterministic design constraints from the TARGET TEXT and format them into a precise JSON array.

### CORE EXTRACTION RULES:
1. ONLY extract deterministic design rules (e.g., limits, dimensions, minimums, maximums, required distances, material conditions).
2. DO NOT extract advisory statements, best practices without limits, or purely informational facts (e.g., "Lap-welded joints trap plating solutions", "Avoid large sheet metal parts").
3. DO NOT extract rules that appear ONLY in the SURROUNDING CONTEXT. The context is only there to help you understand the TARGET TEXT.
4. If the TARGET TEXT contains MULTIPLE distinct constraints, extract them as SEPARATE rule objects.

### CONTEXT RESOLUTION (CRITICAL):
Often, the TARGET TEXT is written in shorthand and inherits its subject from the Section Title or Previous Context. 
For example, if the Section is "Countersinks" and the TARGET TEXT says "The maximum depth is 3.5 times the material thickness", the subject is missing.
- rule_text: "The maximum depth is 3.5 times the material thickness"
- resolved_rule_text: "The maximum depth of a countersink is 3.5 times the material thickness"

You MUST resolve pronouns ("it", "they") and missing subjects ("The minimum radius...") by looking at the SURROUNDING CONTEXT and replacing them with the explicit feature name in `resolved_rule_text`. If no resolution is needed, `resolved_rule_text` should perfectly match `rule_text`.

SURROUNDING CONTEXT:
{context_text}

TARGET TEXT:
{text_block}

Respond ONLY with a valid JSON array of objects matching this exact schema. Do not use placeholders.
[
  {{
    "rule_text": "The maximum depth is 3.5 times the material thickness.",
    "resolved_rule_text": "The maximum depth of a countersink is 3.5 times the material thickness."
  }}
]
"""

@dataclass
class ExtractedRule:
    rule_text: str
    resolved_rule_text: str
    source_window_id: str = ""
    source_window_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.source_window_ids and self.source_window_id:
            self.source_window_ids = [self.source_window_id]
        if not self.source_window_id and self.source_window_ids:
            self.source_window_id = self.source_window_ids[0]

class LLMStructurer:
    """Sends pre-identified rule blocks to LLM for rule text extraction and context resolution."""
    
    def __init__(self, llm_client):
        self.llm = llm_client

    def structure(
        self,
        text_block: str,
        source_window_id: str,
        context_text: str = "",
        source_window_ids: List[str] | None = None,
    ) -> List[ExtractedRule]:
        prompt = STRUCTURING_PROMPT.format(
            text_block=text_block,
            context_text=context_text or "None"
        )
        try:
            raw_response = self.llm.call(prompt)
            # Basic cleanup for markdown fences
            if "```" in raw_response:
                raw_response = raw_response.split("```")[1]
                if raw_response.startswith("json"):
                    raw_response = raw_response[4:]
            
            parsed_rules = json.loads(raw_response.strip())
            
            if not isinstance(parsed_rules, list):
                if isinstance(parsed_rules, dict):
                    parsed_rules = [parsed_rules]
                else:
                    raise ValueError("LLM did not return a JSON array or object.")
            
            extracted = []
            for r in parsed_rules:
                rule_text = r.get("rule_text", "").strip()
                resolved = r.get("resolved_rule_text", rule_text).strip()
                
                if not rule_text:
                    continue
                
                # Check verbatim
                if rule_text not in text_block:
                    logger.warning(f"Extracted rule_text '{rule_text}' not a pure substring. Accepting resolved text anyway.")
                
                extracted.append(ExtractedRule(
                    rule_text=rule_text,
                    resolved_rule_text=resolved,
                    source_window_id=source_window_id,
                    source_window_ids=source_window_ids or [source_window_id]
                ))
            return extracted
            
        except Exception as e:
            # If the error came from the LLM client (e.g. rate limit), bubble it up
            if "LLM Error" in str(e) or "Groq Failed" in str(e) or "Rate limit" in str(e):
                logger.error(f"Fatal API error: {e}")
                raise e
            # If it's just a JSON parsing error for this specific chunk, skip it and continue
            logger.warning(f"Failed to structure rule block (JSON error): {e}. Skipping this chunk.")
            return []


def deduplicate_extracted_rules(rules: List[ExtractedRule]) -> List[ExtractedRule]:
    """Remove exact and partial duplicates produced by overlapping extraction units."""
    unique: List[ExtractedRule] = []

    for rule in rules:
        candidate_key = _canonical_rule_text(rule.resolved_rule_text)
        if not candidate_key:
            continue

        merged = False
        for idx, existing in enumerate(unique):
            existing_key = _canonical_rule_text(existing.resolved_rule_text)

            if candidate_key == existing_key:
                existing.source_window_ids = _merge_ids(existing.source_window_ids, rule.source_window_ids)
                merged = True
                break

            if candidate_key in existing_key or existing_key in candidate_key:
                keep_new = len(candidate_key) > len(existing_key)
                keeper = rule if keep_new else existing
                keeper.source_window_ids = _merge_ids(existing.source_window_ids, rule.source_window_ids)
                unique[idx] = keeper
                merged = True
                break

        if not merged:
            unique.append(rule)

    return unique


def _canonical_rule_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" .;,")
    return text


def _merge_ids(left: List[str], right: List[str]) -> List[str]:
    seen = set()
    merged = []
    for window_id in [*left, *right]:
        if window_id and window_id not in seen:
            merged.append(window_id)
            seen.add(window_id)
    return merged
