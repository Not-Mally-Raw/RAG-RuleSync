import json
from typing import Any

from .prompt_context import build_taxonomy_prompt


class TaxonomyJSONParseError(ValueError):
    def __init__(self, message: str, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response


def _strip_markdown_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _balanced_json_slice(text: str) -> str:
    start_positions = [idx for idx in (text.find("{"), text.find("[")) if idx >= 0]
    if not start_positions:
        raise ValueError("No JSON object or array found in LLM response.")
    start = min(start_positions)
    opening = text[start]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escape = False

    for idx in range(start, len(text)):
        char = text[idx]
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    raise ValueError("LLM response contains unbalanced JSON.")


def extract_json_payload(raw: str) -> Any:
    text = _strip_markdown_fence(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return json.loads(_balanced_json_slice(text))
        except Exception as exc:
            raise TaxonomyJSONParseError(str(exc), raw) from exc
    except Exception as exc:
        raise TaxonomyJSONParseError(str(exc), raw) from exc


class TaxonomyLLMFormalizer:
    def __init__(self, llm_client: Any):
        self.llm_client = llm_client

    def formalize(self, rule_text: str, domain: str, bucket: str) -> Any:
        prompt = build_taxonomy_prompt(rule_text, domain, bucket)
        raw = self.llm_client.call(prompt, json_mode=True)
        return extract_json_payload(raw)
