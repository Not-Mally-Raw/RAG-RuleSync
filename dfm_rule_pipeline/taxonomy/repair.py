from typing import Any

from .llm_formalizer import extract_json_payload
from .prompt_context import build_json_recovery_prompt, build_repair_prompt


class TaxonomyRepairer:
    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    def repair(self, rule_text: str, invalid_payload: Any, errors: Any, domain: str, bucket: str) -> Any:
        prompt = build_repair_prompt(rule_text, invalid_payload, errors, domain, bucket)
        raw = self.llm_client.call(prompt, json_mode=True)
        return extract_json_payload(raw)

    def recover_json(self, rule_text: str, raw_response: str, errors: Any, domain: str, bucket: str) -> Any:
        prompt = build_json_recovery_prompt(rule_text, raw_response, errors, domain, bucket)
        raw = self.llm_client.call(prompt, json_mode=True)
        return extract_json_payload(raw)
