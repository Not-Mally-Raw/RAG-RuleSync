import re
from typing import Dict, Optional

from .knowledge import (
    DISAMBIGUATION_PATTERNS,
    DOMAIN_ALIASES,
    DOMAIN_PROFILES,
    LATEST_DOMAINS,
    TAXONOMY_TO_SCHEMA_DOMAIN,
)


SCHEMA_TO_TAXONOMY_DOMAIN = {value: key for key, value in TAXONOMY_TO_SCHEMA_DOMAIN.items()}
SCHEMA_TO_TAXONOMY_DOMAIN["Model"] = "General"


def _alias_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def normalize_domain_name(value: Optional[str]) -> str:
    if not value:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""
    if raw in LATEST_DOMAINS:
        return raw
    if raw in SCHEMA_TO_TAXONOMY_DOMAIN:
        return SCHEMA_TO_TAXONOMY_DOMAIN[raw]
    return DOMAIN_ALIASES.get(_alias_key(raw), raw)


def is_known_domain(value: Optional[str]) -> bool:
    return normalize_domain_name(value) in LATEST_DOMAINS


def schema_domain_key(value: Optional[str]) -> str:
    normalized = normalize_domain_name(value)
    return TAXONOMY_TO_SCHEMA_DOMAIN.get(normalized, normalized or "General")


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = phrase.lower()
    if "." in normalized_phrase:
        return normalized_phrase in text
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])", text) is not None


def _matches_any(text: str, terms: list[str]) -> bool:
    return any(_contains_phrase(text, term) for term in terms)


def _disambiguated_domain(text: str) -> Optional[str]:
    for domain, required_terms, excluded_terms in DISAMBIGUATION_PATTERNS:
        if _matches_any(text, required_terms) and not _matches_any(text, excluded_terms):
            return domain
    return None


def _domain_scores(text: str) -> Dict[str, int]:
    scores: Dict[str, int] = {}
    for domain, profile in DOMAIN_PROFILES.items():
        score = 0
        score += sum(3 for term in profile.get("primary", []) if _contains_phrase(text, term))
        score += sum(1 for term in profile.get("secondary", []) if _contains_phrase(text, term))
        if score:
            scores[domain] = score
    return scores


def domain_from_rule_text(rule_text: str) -> str:
    text = f" {rule_text.lower()} "

    disambiguated = _disambiguated_domain(text)
    if disambiguated:
        return disambiguated

    scores = _domain_scores(text)
    if scores:
        # Ordered tie-breaks follow the taxonomy's disambiguation priority.
        priority = {domain: idx for idx, (domain, _, _) in enumerate(DISAMBIGUATION_PATTERNS)}
        return max(scores, key=lambda domain: (scores[domain], -priority.get(domain, 999)))

    return "General"
