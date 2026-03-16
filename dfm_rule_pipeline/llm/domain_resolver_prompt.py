"""
LLM prompt for semantic domain classification.
Sends domain definitions + rule text to gpt-oss-120b and asks
it to pick the best-matching manufacturing domain.
"""

DOMAIN_RESOLVER_PROMPT = """
You are a DFM (Design for Manufacturability) Domain Classifier.

Your task: Given a manufacturing rule, determine which SINGLE domain it belongs to
by matching its MEANING against the domain definitions below. Use semantic understanding,
not just keyword matching.

------------------------------------------------------------
DOMAIN DEFINITIONS
{domain_definitions_block}
------------------------------------------------------------
CLASSIFICATION RULES

1. Match based on the manufacturing PROCESS and FEATURE TYPE the rule describes.
2. If a rule mentions objects that exist in MULTIPLE domains, pick the most SPECIFIC domain.
   For example, "Hole" exists in many domains — use context clues like "drill depth", "thread pitch"
   (Drill), "mold draft" (Die Cast / Injection Moulding), "sheet thickness" (Sheetmetal), etc.
3. If the rule is about GD&T tolerances (flatness, parallelism, runout, etc.) or thread class,
   choose "General".
4. If genuinely ambiguous, choose "General".

------------------------------------------------------------
RULE TEXT:
"{rule_text}"

------------------------------------------------------------
OUTPUT VALID JSON ONLY (no markdown, no comments):

{{
  "domain": "<exact domain name from the list above>",
  "confidence": "high|medium|low",
  "reasoning": "<one-line explanation>"
}}
"""
