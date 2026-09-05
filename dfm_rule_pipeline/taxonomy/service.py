"""
Taxonomy V3 Pipeline Service Orchestrator.

Combines bucket classification, dynamic context prompts, LLM extraction,
deterministic assembly, validation, and targeted repair loops.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from dfm_rule_pipeline.taxonomy.assembler import TaxonomyAssembler
from dfm_rule_pipeline.taxonomy.bucket_classifier import BucketClassifier
from dfm_rule_pipeline.taxonomy.llm_extractor import LLMExtractor
from dfm_rule_pipeline.taxonomy.models import RuleInput, TaxonomyResponse
from dfm_rule_pipeline.taxonomy.prompt_context import PromptContextBuilder
from dfm_rule_pipeline.taxonomy.repair import TaxonomyRepair
from dfm_rule_pipeline.taxonomy.schema_registry import SchemaRegistry
from dfm_rule_pipeline.taxonomy.validator import TaxonomyValidator

logger = logging.getLogger("taxonomy.service")


def _sanitize_rule_text(text: str) -> str:
    """Sanitize raw rule text (stripping LaTeX math delimiters, unescaped braces, and leading list bullets)."""
    if not text:
        return text
    clean = re.sub(r"\\\((.*?)\\\)", r"\1", text)
    clean = re.sub(r"\\\$(.*?)\\\$", r"\1", clean)
    clean = clean.replace("{", "(").replace("}", ")")
    clean = re.sub(r"^\s*(?:[-•*–—]|\(?\d+[\.\)]|\([a-zA-Z]\))\s*", "", clean)
    return clean.strip()


def _split_into_rule_sentences(text: str) -> List[str]:
    """
    Splits multi-sentence paragraphs, bullet points, and numbered lists
    into semantically independent rule chunks.
    
    Preserves rule continuation sentences (e.g. 'otherwise...', 'if the material is superalloy,
    the ratio limit reduces to...') with their parent sentence.
    """
    if not text or not text.strip():
        return []
    
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    
    # 1. Check for newline-delimited rules / bullet points
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) > 1:
        raw_candidates = []
        for line in lines:
            c = _sanitize_rule_text(line)
            if c:
                raw_candidates.append(c)
    else:
        # 2. Check for inline numbered or bullet points: e.g. '1. ... 2. ...' or '- ... - ...'
        inline_marker = re.compile(r'(?:^|(?<=[.!?])\s+|\s+[-•*–—]\s+)(?:[-•*–—]|\(?\d+[\.\)]|\([a-zA-Z]\))\s+')
        parts = [_sanitize_rule_text(p) for p in inline_marker.split(text) if p.strip()]
        if len(parts) > 1:
            raw_candidates = parts
        else:
            # 3. Standard sentence split on period followed by space + capital letter
            sentences = re.split(r'\.(?=\s+[A-Z])', text)
            raw_candidates = [_sanitize_rule_text(s).rstrip('.') + '.' for s in sentences if s.strip()]
    
    # Filter out empty or tiny fragments (< 10 chars)
    candidates = [c.rstrip('.') + '.' if not c.endswith('.') else c for c in raw_candidates if len(c) > 10]
    if len(candidates) <= 1:
        return [text.strip()]
    
    # Continuation indicators that signal SAME rule continuation (e.g. conditional branches)
    _CONTINUATION_RE = re.compile(
        r'(?i)\b(the\s+ratio|the\s+limit|the\s+value|the\s+tolerance|the\s+threshold|'
        r'this\s+value|this\s+ratio|this\s+limit|that\s+value|'
        r'it\s+reduces|it\s+increases|it\s+decreases|it\s+should|it\s+must|'
        r'the\s+same\s+|otherwise|in\s+that\s+case)\b'
    )
    
    groups: List[str] = []
    current = candidates[0]
    for nxt in candidates[1:]:
        if _CONTINUATION_RE.search(nxt):
            # Continuation sentence — merge with current rule
            current = current.rstrip('.') + '. ' + nxt
        else:
            # Standalone independent rule
            groups.append(current)
            current = nxt
    if current:
        groups.append(current)
        
    return groups if groups else [text.strip()]


class TaxonomyFormalizationService:
    """
    Orchestrates the Taxonomy V3 formalization pipeline.
    """

    def __init__(
        self,
        llm_client,
        embedder=None,
        config_path=None,
    ):
        self._llm = llm_client
        self._registry = SchemaRegistry(config_path)
        
        # Instantiate sub-components
        self._classifier = BucketClassifier(self._registry, embedder)
        self._prompt_builder = PromptContextBuilder(self._registry)
        self._extractor = LLMExtractor(self._llm)
        self._assembler = TaxonomyAssembler()
        self._validator = TaxonomyValidator()
        self._repairer = TaxonomyRepair(self._llm, self._registry)

    def formalize_rule(self, rule_input: RuleInput) -> TaxonomyResponse:
        """
        Runs the V3 formalization pipeline on a single rule input or paragraph.
        """
        rule_text = _sanitize_rule_text(rule_input.rule_text)
        if not rule_text:
            return TaxonomyResponse(
                rule_text=rule_text,
                status="Review Needed",
                decision_code="skipped_empty",
                domain="General",
                bucket="SimpleValidation",
                taxonomy_rules=[],
                validation_errors=[],
            )

        # Multi-sentence paragraph pre-segmentation check
        sentences = _split_into_rule_sentences(rule_text)
        if len(sentences) > 1:
            all_rules = []
            all_errors = []
            domains = []
            buckets = []
            
            for sent in sentences:
                sub_input = RuleInput(rule_text=sent, rule_type=rule_input.rule_type)
                sub_res = self._formalize_single_sentence(sub_input)
                all_rules.extend(sub_res.taxonomy_rules)
                all_errors.extend(sub_res.validation_errors)
                domains.append(sub_res.domain)
                buckets.append(sub_res.bucket)
                
            main_domain = max(set(domains), key=domains.count) if domains else "General"
            main_bucket = max(set(buckets), key=buckets.count) if buckets else "SimpleValidation"
            
            return TaxonomyResponse(
                rule_text=rule_text,
                status="Success" if all_rules else "Review Needed",
                decision_code="formalized" if all_rules else "paragraph_processing_failed",
                domain=main_domain,
                bucket=main_bucket,
                taxonomy_rules=all_rules,
                validation_errors=all_errors,
            )

        return self._formalize_single_sentence(rule_input)

    def _formalize_single_sentence(self, rule_input: RuleInput) -> TaxonomyResponse:
        """Helper to formalize a single un-segmented sentence."""
        rule_text = _sanitize_rule_text(rule_input.rule_text)
        try:
            # 1. Bucket and Domain Classification (Tier 0)
            class_res = self._classifier.classify(
                rule_text,
                explicit_domain=rule_input.rule_type,
                llm_client=self._llm,
            )
            domain = class_res.domain
            bucket = class_res.bucket

            # 2. Build Selective Context Prompt (Tier 1)
            prompt = self._prompt_builder.build_prompt(rule_text, domain, bucket)

            # 3. LLM Flat Extraction (Tier 2)
            extraction = self._extractor.extract(prompt)
            if not extraction:
                return TaxonomyResponse(
                    rule_text=rule_text,
                    status="Review Needed",
                    decision_code="llm_failed",
                    domain=domain,
                    bucket=bucket,
                    taxonomy_rules=[],
                    validation_errors=[],
                )

            # Keep classification decisions aligned
            extraction.domain = domain
            extraction.bucket = bucket

            # 4. Deterministic Schema Assembly (Tier 3)
            rule_ast = self._assembler.assemble(extraction, self._registry)

            # 5. Deterministic Validation (Tier 4)
            errors = self._validator.validate(rule_ast, domain, self._registry)

            # Check if any new attributes were auto-registered
            has_new_attr = any(e.code == "new_attribute_registered" for e in errors)
            fatal_errors = [e for e in errors if e.code != "new_attribute_registered"]

            if has_new_attr and not fatal_errors:
                return TaxonomyResponse(
                    rule_text=rule_text,
                    status="Review Needed",
                    decision_code="new_attribute_registered",
                    domain=domain,
                    bucket=bucket,
                    taxonomy_rules=[rule_ast],
                    validation_errors=errors,
                )

            # 6. Targeted Repair Loop (Tier 5) - triggers if errors found
            if errors:
                repaired_extraction = self._repairer.repair(
                    rule_text, extraction, errors, domain
                )
                if repaired_extraction:
                    repaired_extraction.domain = domain
                    repaired_extraction.bucket = bucket
                    
                    # Re-assemble & Re-validate
                    repaired_ast = self._assembler.assemble(repaired_extraction, self._registry)
                    repaired_errors = self._validator.validate(
                        repaired_ast, domain, self._registry
                    )
                    
                    if not repaired_errors:
                        # Repair succeeded!
                        return TaxonomyResponse(
                            rule_text=rule_text,
                            status="Success",
                            decision_code="formalized",
                            domain=domain,
                            bucket=bucket,
                            taxonomy_rules=[repaired_ast],
                            validation_errors=[],
                        )
                    else:
                        # Repair failed to clear all errors
                        return TaxonomyResponse(
                            rule_text=rule_text,
                            status="Review Needed",
                            decision_code="repair_failed",
                            domain=domain,
                            bucket=bucket,
                            taxonomy_rules=[repaired_ast],
                            validation_errors=repaired_errors,
                        )
                else:
                    # Repair request failed or was skipped
                    return TaxonomyResponse(
                        rule_text=rule_text,
                        status="Review Needed",
                        decision_code="validation_failed",
                        domain=domain,
                        bucket=bucket,
                        taxonomy_rules=[rule_ast],
                        validation_errors=errors,
                    )

            # Happy path: validated successfully on first try
            return TaxonomyResponse(
                rule_text=rule_text,
                status="Success",
                decision_code="formalized",
                domain=domain,
                bucket=bucket,
                taxonomy_rules=[rule_ast],
                validation_errors=[],
            )

        except Exception as e:
            logger.error(f"Error processing rule taxonomy formalization: {e}", exc_info=True)
            return TaxonomyResponse(
                rule_text=rule_text,
                status="Review Needed",
                decision_code=f"pipeline_error({str(e)})",
                domain="General",
                bucket="SimpleValidation",
                taxonomy_rules=[],
                validation_errors=[],
            )

    def process_rules(self, rules: List[RuleInput]) -> List[TaxonomyResponse]:
        """
        Runs the V3 formalization pipeline on a batch of rules.
        """
        return [self.formalize_rule(rule) for rule in rules]
