from typing import Any, Dict, List

from .bucket_registry import classify_bucket
from .canonicalizer import canonicalize_envelope_payload
from .domain_normalizer import domain_from_rule_text, is_known_domain, normalize_domain_name
from .grounding import validate_grounding
from .llm_formalizer import TaxonomyJSONParseError, TaxonomyLLMFormalizer
from .models import TaxonomyEnvelope, model_dump_compat
from .repair import TaxonomyRepairer
from .schema_factory import normalize_envelope_payload
from .validator import TaxonomyValidationError, TaxonomyValidator, errors_to_dicts


def _input_to_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return {}


def _decision_from_errors(errors: List[TaxonomyValidationError], repaired: bool) -> str:
    schema_codes = {"schema_root_failed", "schema_attribute_failed"}
    if any(error.code in schema_codes for error in errors):
        return "schema_path_failed"
    if repaired:
        return "repair_failed"
    return "validation_failed"


def _force_domain(payload: Dict[str, Any], domain: str) -> Dict[str, Any]:
    payload["domain"] = domain
    for rule in payload.get("taxonomy_rules", []):
        if isinstance(rule, dict):
            rule["RuleCategory"] = domain
    return payload


class TaxonomyFormalizationService:
    def __init__(self, llm_client: Any):
        self.formalizer = TaxonomyLLMFormalizer(llm_client)
        self.repairer = TaxonomyRepairer(llm_client)
        self.validator = TaxonomyValidator()

    def formalize_rules(self, rules: List[Any]) -> List[Dict[str, Any]]:
        return [self.formalize_rule(rule) for rule in rules]

    def formalize_rule(self, rule_input: Any) -> Dict[str, Any]:
        data = _input_to_dict(rule_input)
        rule_text = str(data.get("rule_text") or "").strip()
        explicit_domain = data.get("rule_type")

        if not rule_text:
            return self._review_response("", "validation_failed", "", "", [{"code": "model_parse_failed", "message": "Rule text is required.", "location": "$.rule_text", "suggestion": ""}])

        explicit_domain_is_valid = is_known_domain(explicit_domain)
        domain = normalize_domain_name(explicit_domain) if explicit_domain_is_valid else domain_from_rule_text(rule_text)
        bucket = classify_bucket(rule_text)

        try:
            raw_payload = self.formalizer.formalize(rule_text, domain, bucket)
        except TaxonomyJSONParseError as exc:
            parse_errors = [
                {
                    "code": "json_parse_failed",
                    "message": str(exc),
                    "location": "$",
                    "suggestion": "Return one complete JSON object with domain, bucket, and taxonomy_rules.",
                }
            ]
            try:
                repaired_payload = self.repairer.recover_json(rule_text, exc.raw_response, parse_errors, domain, bucket)
            except Exception as repair_exc:
                repair_errors = parse_errors + [
                    {
                        "code": "repair_failed",
                        "message": str(repair_exc),
                        "location": "$",
                        "suggestion": "Review the raw model output and prompt the model for JSON only.",
                    }
                ]
                return self._review_response(rule_text, "repair_failed", domain, bucket, repair_errors)

            prepared_repair = self._prepare_payload(
                repaired_payload,
                domain,
                bucket,
                rule_text,
                explicit_domain_is_valid,
            )
            repaired_envelope, repair_errors = self.validator.validate(prepared_repair)
            if repaired_envelope:
                repair_errors.extend(validate_grounding(rule_text, prepared_repair))
            if not repair_errors and repaired_envelope:
                return self._success_response(rule_text, repaired_envelope)

            return self._review_response(
                rule_text,
                _decision_from_errors(repair_errors, repaired=True),
                prepared_repair.get("domain", domain),
                prepared_repair.get("bucket", bucket),
                errors_to_dicts(repair_errors),
            )
        except Exception as exc:
            return self._review_response(
                rule_text,
                "llm_failed",
                domain,
                bucket,
                [{"code": "llm_failed", "message": str(exc), "location": "$", "suggestion": "Check LLM availability and JSON-only response."}],
            )

        prepared_payload = self._prepare_payload(
            raw_payload,
            domain,
            bucket,
            rule_text,
            explicit_domain_is_valid,
        )
        envelope, errors = self.validator.validate(prepared_payload)
        if envelope:
            errors.extend(validate_grounding(rule_text, prepared_payload))
        if not errors and envelope:
            return self._success_response(rule_text, envelope)

        error_dicts = errors_to_dicts(errors)
        try:
            repaired_payload = self.repairer.repair(rule_text, prepared_payload, error_dicts, domain, bucket)
        except Exception as exc:
            repair_errors = error_dicts + [
                {"code": "repair_failed", "message": str(exc), "location": "$", "suggestion": "Review the generated taxonomy JSON manually."}
            ]
            return self._review_response(rule_text, _decision_from_errors(errors, repaired=True), domain, bucket, repair_errors)

        prepared_repair = self._prepare_payload(
            repaired_payload,
            domain,
            bucket,
            rule_text,
            explicit_domain_is_valid,
        )
        repaired_envelope, repair_errors = self.validator.validate(prepared_repair)
        if repaired_envelope:
            repair_errors.extend(validate_grounding(rule_text, prepared_repair))
        if not repair_errors and repaired_envelope:
            return self._success_response(rule_text, repaired_envelope)

        return self._review_response(
            rule_text,
            _decision_from_errors(repair_errors, repaired=True),
            prepared_repair.get("domain", domain),
            prepared_repair.get("bucket", bucket),
            errors_to_dicts(repair_errors),
        )

    def _success_response(self, rule_text: str, envelope: TaxonomyEnvelope) -> Dict[str, Any]:
        return {
            "rule_text": rule_text,
            "status": "Success",
            "decision_code": "formalized",
            "domain": envelope.domain,
            "bucket": envelope.bucket,
            "taxonomy_rules": [model_dump_compat(rule) for rule in envelope.taxonomy_rules],
            "validation_errors": [],
        }

    def _prepare_payload(
        self,
        payload: Any,
        domain: str,
        bucket: str,
        rule_text: str,
        explicit_domain_is_valid: bool,
    ) -> Dict[str, Any]:
        prepared = normalize_envelope_payload(payload, fallback_domain=domain, fallback_bucket=bucket)
        if explicit_domain_is_valid:
            prepared = _force_domain(prepared, domain)
        prepared = canonicalize_envelope_payload(prepared, rule_text)
        if explicit_domain_is_valid:
            prepared = _force_domain(prepared, domain)
        return prepared

    def _review_response(
        self,
        rule_text: str,
        decision_code: str,
        domain: str,
        bucket: str,
        errors: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "rule_text": rule_text,
            "status": "Review Needed",
            "decision_code": decision_code,
            "domain": domain,
            "bucket": bucket,
            "taxonomy_rules": [],
            "validation_errors": errors,
        }
