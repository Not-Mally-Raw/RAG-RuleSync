"""Unified production facade bridging fast and enhanced rule extraction."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .rule_extraction import (
    ExtractionSummary,
    RuleExtractionPipeline,
    RuleExtractionSettings,
)

try:  # Optional dependency for rich exports
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover - pandas optional
    pd = None  # type: ignore


if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .enhanced_rule_engine import EnhancedConfig  # type: ignore

logger = logging.getLogger(__name__)


class _PipelineRuleEngineFacade:
    """Async-friendly adapter exposing pipeline operations like the legacy engine."""

    def __init__(self, pipeline: RuleExtractionPipeline, validator=None) -> None:
        self._pipeline = pipeline
        self._validator = validator

    @property
    def settings(self) -> RuleExtractionSettings:
        return self._pipeline.settings

    async def extract_rules_from_text(
        self,
        text: str,
        document_name: str = "ad_hoc.txt",
        *,
        max_rules: Optional[int] = None,
    ) -> Dict[str, Any]:
        summary = await self._pipeline.extract_from_text(
            text,
            document_name,
            max_rules=max_rules,
        )
        payload = summary.to_dict()
        if self._validator:
            payload = self._validator(payload)
        return payload

    async def process_document(
        self,
        document_path: str,
        *,
        max_rules: Optional[int] = None,
    ) -> Dict[str, Any]:
        summary = await self._pipeline.process_document(
            document_path,
            max_rules=max_rules,
        )
        payload = summary.to_dict()
        if self._validator:
            payload = self._validator(payload)
        return payload

    async def batch_process(
        self,
        document_paths: Sequence[str],
        *,
        max_rules: Optional[int] = None,
        concurrency: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        summaries = await self._pipeline.batch_process(
            document_paths,
            max_rules=max_rules,
            concurrency=concurrency,
        )
        results = [summary.to_dict() for summary in summaries]
        if self._validator:
            results = [self._validator(payload) for payload in results]
        return results


class ProductionRuleExtractionSystem:
    """High-level orchestrator exposing both fast and enhanced pipelines."""

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        *,
        max_rules: Optional[int] = None,
        use_qdrant: bool = False,
        pipeline_settings: Optional[RuleExtractionSettings] = None,
        enable_enhanced: bool = False,
        enhanced_config: Optional["EnhancedConfig"] = None,
        vector_manager: Optional[Any] = None,
    ) -> None:
        base_settings = pipeline_settings or RuleExtractionSettings()
        settings_data = base_settings.dict()

        if groq_api_key:
            settings_data["groq_api_key"] = groq_api_key
        else:
            settings_data.setdefault("groq_api_key", os.getenv("GROQ_API_KEY", ""))

        if not settings_data.get("groq_api_key"):
            raise ValueError("GROQ_API_KEY missing; set it in the environment or pass explicitly")

        if max_rules is not None:
            settings_data["max_rules_total"] = max_rules

        self.settings = RuleExtractionSettings(**settings_data)
        self.pipeline = RuleExtractionPipeline(self.settings)
        self.max_rules = self.settings.max_rules_total
        self.use_qdrant = use_qdrant

        self._validator = self._apply_validation

        # Legacy compatibility surfaces
        self.rule_engine = _PipelineRuleEngineFacade(self.pipeline, validator=self._validator)
        self.prompt_system = self.pipeline.processor.prompts
        self.llm = self.pipeline.processor._client

        self.enhanced_engine = None
        if enable_enhanced:
            try:  # lazy import to avoid heavy dependencies when unused
                from .enhanced_rule_engine import EnhancedConfig, EnhancedRuleEngine  # type: ignore

                config = enhanced_config or EnhancedConfig(groq_api_key=self.settings.groq_api_key)
                self.enhanced_engine = EnhancedRuleEngine(config=config, vector_manager=vector_manager)
            except Exception as exc:  # pragma: no cover - optional feature
                logger.warning("enhanced_engine_initialization_failed", exc_info=exc)

    # ------------------------------------------------------------------
    # Core processing helpers
    # ------------------------------------------------------------------

    async def process_document_advanced(
        self,
        document_path: str,
        enable_enhancement: bool = False,
        enable_validation: bool = False,
    ) -> Dict[str, Any]:
        """Process a document with optional enhanced enrichment."""

        if enable_enhancement and self.enhanced_engine is not None:
            payload = await self._run_enhanced_path(document_path)
            payload.setdefault("document_context", {"mode": "enhanced"})
            payload = self._apply_validation(payload)
            return payload

        if enable_enhancement and self.enhanced_engine is None:
            logger.info(
                "enhanced_processing_requested_but_engine_unavailable",
                extra={"document_path": document_path},
            )

        summary = await self.pipeline.process_document(
            document_path,
            max_rules=self.max_rules,
        )
        payload = summary.to_dict()
        payload.setdefault("document_context", {"mode": "fast"})
        payload = self._apply_validation(payload)
        return payload

    async def batch_process_documents(
        self,
        document_paths: Sequence[str],
        *,
        concurrency: int = 2,
    ) -> List[Dict[str, Any]]:
        summaries = await self.pipeline.batch_process(
            document_paths,
            max_rules=self.max_rules,
            concurrency=concurrency,
        )
        results = [summary.to_dict() for summary in summaries]
        return [self._apply_validation(payload) for payload in results]

    async def extract_rules_from_text(
        self,
        text: str,
        document_name: str = "ad_hoc.txt",
        *,
        max_rules: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await self.rule_engine.extract_rules_from_text(
            text,
            document_name,
            max_rules=max_rules,
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def export_results(
        self,
        results: Iterable[Union[Dict[str, Any], ExtractionSummary]],
        format: str = "json",
        output_path: Optional[Union[str, Path]] = None,
        include_metadata: bool = True,
        schema: str = "full",
    ) -> str:
        """Export rule extraction results - JSON ONLY (CSV/Excel removed)."""

        documents = [self._apply_validation(self._normalise_result(entry)) for entry in results]
        if not documents:
            raise ValueError("No results provided for export")

        format_normalised = format.lower().strip()
        
        # Only support JSON export
        if format_normalised not in {"json"}:
            raise ValueError(f"Only JSON format is supported. Requested: {format}")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        default_name = f"rule_extraction_{timestamp}.json"

        if output_path:
            path = Path(output_path)
        else:
            path = Path("output") / default_name
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON directly
        payload = {
            "summary": self._build_summary(documents),
            "results": documents,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        logger.info("export_completed", extra={"path": str(path), "format": format_normalised})
        return str(path)

    def consolidate_all_rules(
        self,
        output_dir: Union[str, Path] = "output",
        output_file: Optional[Union[str, Path]] = None,
    ) -> str:
        """Consolidate all individual JSON rule files into a single JSON file.
        
        Args:
            output_dir: Directory containing individual JSON files (default: "output")
            output_file: Path for consolidated file (default: "output/all_rules_consolidated.json")
            
        Returns:
            Path to the consolidated JSON file
        """
        output_dir = Path(output_dir)
        if not output_dir.exists():
            raise ValueError(f"Output directory does not exist: {output_dir}")
        
        # Find all JSON files in output directory
        json_files = list(output_dir.glob("*.json"))
        if not json_files:
            raise ValueError(f"No JSON files found in {output_dir}")
        
        # Collect all rules from all files
        all_documents = []
        total_rules = 0
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Extract rules and metadata
                doc_entry = {
                    "source_pdf": data.get("source_pdf", json_file.stem),
                    "rule_count": data.get("rule_count", len(data.get("rules", []))),
                    "rules": data.get("rules", []),
                    "processing_time": data.get("processing_time", 0),
                    "chunks_processed": data.get("chunks_processed", 0),
                }
                all_documents.append(doc_entry)
                total_rules += doc_entry["rule_count"]
                
            except Exception as e:
                logger.warning(f"Failed to read {json_file}: {e}")
                continue
        
        # Create consolidated output
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        consolidated = {
            "consolidated_at": datetime.utcnow().isoformat(),
            "total_documents": len(all_documents),
            "total_rules": total_rules,
            "documents": all_documents,
        }
        
        # Determine output path
        if output_file:
            output_path = Path(output_file)
        else:
            output_path = output_dir / f"all_rules_consolidated_{timestamp}.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write consolidated file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(consolidated, f, indent=2, ensure_ascii=False)
        
        logger.info(
            "rules_consolidated",
            extra={
                "path": str(output_path),
                "documents": len(all_documents),
                "total_rules": total_rules,
            }
        )
        
        return str(output_path)

    def get_system_stats(self) -> Dict[str, Any]:
        settings = self.settings
        # Minimal counters (can be incremented in future enhancements)
        processing_stats = {
            "documents_processed": 0,
            "rules_extracted": 0,
        }
        return {
            "configuration": {
                "max_rules": self.max_rules,
                "max_concurrent_calls": settings.max_concurrent_calls,
                "throttle_seconds": settings.throttle_seconds,
                "enhanced_engine": bool(self.enhanced_engine),
                "use_qdrant": self.use_qdrant,
                "groq_model": getattr(settings, "groq_model", "unknown"),
            },
            "processing_stats": processing_stats,
        }

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def validate_against_hcl_dataset(self, hcl_csv_path: str) -> Dict[str, Any]:
        """Proxy HCL validation to the enhanced engine when available.

        This provides a stable entry point for UI layers that expect the
        legacy ``validate_against_hcl_dataset`` API on the production system.
        """

        if not self.enhanced_engine:
            raise RuntimeError("Enhanced engine is not enabled; HCL validation is unavailable.")

        return self.enhanced_engine.validate_against_hcl_dataset(hcl_csv_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_enhanced_path(self, document_path: str) -> Dict[str, Any]:
        """Execute the enhanced rule extraction path for a document."""

        assert self.enhanced_engine is not None  # for type checkers

        payload = await self.pipeline.loader.load(Path(document_path))
        filename = payload.metadata.get("filename") or Path(document_path).name

        enhanced_result = await self.enhanced_engine.extract_rules_from_text(
            payload.text,
            filename=filename,
        )

        enhanced_result.setdefault("document_metadata", payload.metadata)
        enhanced_result.setdefault("filename", filename)
        return enhanced_result

    def _normalise_result(
        self,
        result: Union[Dict[str, Any], ExtractionSummary],
    ) -> Dict[str, Any]:
        if isinstance(result, ExtractionSummary):
            payload = result.to_dict()
        else:
            payload = dict(result)

        payload.setdefault("filename", payload.get("document_name", payload.get("filename", "unknown")))
        payload.setdefault("rules", [])
        payload.setdefault("rule_count", len(payload["rules"]))
        payload.setdefault("avg_confidence", 0.0)
        payload.setdefault("status", "success" if payload["rules"] else payload.get("status", "no_rules"))
        return payload

    def _apply_validation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Single-source semantic validation for extracted rules."""

        rules = payload.get("rules") or []
        validated: List[Dict[str, Any]] = []
        stats = {
            "total_rules": len(rules),
            "advisory_rules": 0,
            "enforceable_rules": 0,
            "incomplete_rules": 0,
            "unresolved_compound_constraints": 0,
        }

        for rule in rules:
            updated, flags = self._validate_rule(rule)
            validated.append(updated)
            if updated.get("validation_state") == "ADVISORY_ONLY":
                stats["advisory_rules"] += 1
            if updated.get("validation_state") == "ENFORCEABLE":
                stats["enforceable_rules"] += 1
            if updated.get("validation_state") == "INCOMPLETE":
                stats["incomplete_rules"] += 1
            if flags.get("has_unresolved_compound_constraint"):
                stats["unresolved_compound_constraints"] += 1

        payload = dict(payload)
        payload["rules"] = validated
        payload["rule_count"] = len(validated)
        payload["validation"] = {
            "status": "semantic_validation_applied",
            **stats,
        }
        return payload

    def _validate_rule(self, rule: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, bool]]:
        constraints = rule.get("constraints")
        if constraints is None:
            constraints_list: List[Any] = []
        else:
            constraints_list = constraints if isinstance(constraints, list) else [constraints]
        severity = (
            str(rule.get("severity") or rule.get("rule_severity") or rule.get("suggested_severity") or "")
        ).upper()
        severity = severity or "ADVISORY"

        # Determine presence of constraints, accounting for string expressions
        if isinstance(constraints, str):
            has_constraints = bool(constraints.strip())
            has_unresolved_compound = False
        else:
            has_constraints = bool(constraints_list)
            has_unresolved_compound = any(self._has_unresolved_compound(constraint) for constraint in constraints_list)

        if severity == "ADVISORY":
            validation_state = "ADVISORY_ONLY"
        elif severity == "ENFORCEABLE":
            validation_state = "ENFORCEABLE" if has_constraints and not has_unresolved_compound else "INCOMPLETE"
        else:
            validation_state = "ADVISORY_ONLY"
            severity = "ADVISORY"

        updated = dict(rule)
        updated["severity"] = severity
        updated.setdefault("suggested_severity", severity)
        updated["validation_state"] = validation_state
        updated["has_constraints"] = has_constraints

        return updated, {"has_unresolved_compound_constraint": has_unresolved_compound}

    def _has_unresolved_compound(self, constraint: Any) -> bool:
        """Detect compound constraints that were not resolved into concrete subconditions."""

        if isinstance(constraint, dict):
            for key in ("all_of", "any_of", "conditions", "allOf", "anyOf"):
                if key in constraint:
                    nested = constraint.get(key) or []
                    if not nested:
                        return True
                    return any(self._has_unresolved_compound(item) for item in nested)
            return False
        if isinstance(constraint, list):
            return any(self._has_unresolved_compound(item) for item in constraint)
        return False

    def _build_summary(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_rules = sum(len(doc.get("rules", [])) for doc in documents)
        successful = sum(1 for doc in documents if doc.get("status") == "success")
        failed = sum(1 for doc in documents if doc.get("status") not in {"success", "no_rules"})
        total_processing_time = sum(float(doc.get("processing_time") or 0.0) for doc in documents)
        avg_processing_time = total_processing_time / len(documents) if documents else 0.0
        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "documents": len(documents),
            "successful_documents": successful,
            "failed_documents": failed,
            "total_rules": total_rules,
            "total_processing_seconds": round(total_processing_time, 3),
            "avg_processing_seconds": round(avg_processing_time, 3),
            "average_confidence": (
                sum(doc.get("avg_confidence", 0.0) for doc in documents if doc.get("avg_confidence")) / successful
                if successful
                else 0.0
            ),
        }

    def _flatten_rules(self, documents: List[Dict[str, Any]], *, include_metadata: bool) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for doc in documents:
            base_row = {
                "filename": doc.get("filename"),
                "status": doc.get("status"),
                "rule_count": doc.get("rule_count", 0),
                "avg_confidence": doc.get("avg_confidence", 0.0),
                "chunks_processed": doc.get("chunks_processed"),
                "model_calls": doc.get("model_calls"),
                "processing_time": doc.get("processing_time"),
            }
            if include_metadata:
                if doc.get("document_context"):
                    base_row["document_context"] = self._serialise_field(doc.get("document_context"))
                if doc.get("document_metadata"):
                    base_row["document_metadata"] = self._serialise_field(doc.get("document_metadata"))

            if not doc.get("rules"):
                rows.append(base_row)
                continue

            for idx, rule in enumerate(doc["rules"], start=1):
                row = dict(base_row)
                row["rule_index"] = idx
                for key, value in rule.items():
                    row[key] = self._serialise_field(value)
                rows.append(row)
        return rows

    def _flatten_rules_dfm_strict(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten extraction results into a minimalist Level-1 DFM schema.

        Purpose: produce table-ready rows focused on Level-1 extraction only.
        Drops early-governance columns and keeps only fields needed for review.

        Kept columns:
          - rule_text
          - domain (best-effort)
          - rule_type
          - constraints (readable)
          - applicability_text (process/material/feature/location)
          - severity (ADVISORY|ENFORCEABLE)
          - confidence (0..1)

        Dropped columns: rule_id, extraction_method, source_document, risk, complexity.
        """

        def _norm_text(text: str) -> str:
            return " ".join((text or "").strip().split()).lower()

        def _pick_domain(doc: Dict[str, Any], rule: Dict[str, Any]) -> str:
            filename = (doc.get("filename") or "").strip()
            filename_lower = filename.lower()
            ctx = doc.get("document_context") or {}
            tech_domain = (ctx.get("technical_domain") or "").strip()
            if tech_domain:
                base = tech_domain
            elif "sheet" in filename_lower and "metal" in filename_lower:
                base = "sheet metal"
            else:
                base = (ctx.get("industry_sector") or "general").strip() or "general"

            primary_feature = (rule.get("primary_feature") or "").strip()
            if primary_feature:
                return f"{base} / {primary_feature}"
            return base

        def _priority_from_text(text: str) -> str:
            t = _norm_text(text)
            if any(k in t for k in [" must ", " shall ", " required ", " do not ", " never "]):
                return "high"
            if any(k in t for k in [" should ", " recommended "]):
                return "medium"
            return "low"

        def _risk_from_text(text: str) -> str:
            t = _norm_text(text)
            high_markers = [
                "tolerance",
                "±",
                "minimum",
                "maximum",
                "clearance",
                "interference",
                "thickness",
                "radius",
                "failure",
                "crack",
                "fracture",
                "safety",
                "critical",
            ]
            if any(m in t for m in high_markers):
                return "high"
            # Any numeric constraint usually implies measurable defect risk.
            if any(ch.isdigit() for ch in t):
                return "medium"
            if any(k in t for k in ["avoid", "ensure", "prevent"]):
                return "medium"
            return "low"

        def _format_constraints(rule: Dict[str, Any]) -> str:
            constraints = rule.get("constraints")
            # If the new prompt produced a single string expression
            if isinstance(constraints, str):
                return constraints.strip()
            if not isinstance(constraints, list) or not constraints:
                return ""
            rendered: List[str] = []
            for c in constraints:
                if not isinstance(c, dict):
                    continue
                param = str(c.get("parameter") or c.get("target") or c.get("subject") or "").strip()
                op = str(c.get("operator") or c.get("constraint_type") or c.get("op") or "").strip()
                value = c.get("value")
                expr = c.get("expression")
                units = str(c.get("units") or c.get("unit") or "").strip()
                rhs = ""
                if isinstance(expr, str) and expr.strip():
                    rhs = expr.strip()
                elif isinstance(value, (int, float)):
                    rhs = str(value)
                elif isinstance(value, str):
                    rhs = value.strip()
                elif value is not None:
                    try:
                        rhs = json.dumps(value, ensure_ascii=False)
                    except Exception:
                        rhs = str(value)
                piece = ""
                if param and op and rhs:
                    piece = f"{param} {op} {rhs}"
                elif param and rhs:
                    piece = f"{param}: {rhs}"
                elif rhs:
                    piece = rhs
                if piece and units:
                    piece = f"{piece} {units}"
                if piece:
                    rendered.append(piece)
            # compound_logic hint
            compound = rule.get("compound_logic")
            if isinstance(compound, list) and compound:
                for node in compound:
                    if not isinstance(node, dict):
                        continue
                    fn = str(node.get("function") or "").strip()
                    operands = node.get("operands")
                    if fn and isinstance(operands, list) and operands:
                        op_str = ", ".join(str(o) for o in operands if str(o).strip())
                        if op_str:
                            rendered.append(f"{fn}({op_str})")
            return "; ".join(rendered)

        def _format_applicability(rule: Dict[str, Any]) -> str:
            app = rule.get("applicability_structured")
            if not isinstance(app, dict):
                app_list = rule.get("applicability")
                if isinstance(app_list, list) and app_list and isinstance(app_list[0], dict):
                    app = app_list[0]
            if not isinstance(app, dict):
                app = {}
            parts: List[str] = []
            for key in ("process", "material", "feature", "location", "geometry"):
                val = app.get(key)
                if val is None:
                    continue
                s = str(val).strip()
                if not s or s.lower() in {"unknown", "null"}:
                    continue
                parts.append(f"{key}={s}")
            return "; ".join(parts)

        rows: List[Dict[str, Any]] = []
        for doc in documents:
            rules = doc.get("rules") or []
            if not rules:
                continue
            for rule in rules:
                rule_text = (rule.get("rule_text") or "").strip()
                if not rule_text:
                    continue

                confidence = rule.get("confidence_score", rule.get("confidence"))
                try:
                    confidence_val = float(confidence) if confidence is not None else 0.0
                except Exception:
                    confidence_val = 0.0

                rows.append(
                    {
                        "rule_text": rule_text,
                        "domain": _pick_domain(doc, rule),
                        "rule_type": (rule.get("rule_type") or "").strip() or "general",
                        "constraints": _format_constraints(rule),
                        "applicability_text": _format_applicability(rule),
                        "severity": (str(rule.get("severity") or "").strip() or "ADVISORY").upper(),
                        "confidence": round(max(0.0, min(1.0, confidence_val)), 4),
                    }
                )

        return rows

    @staticmethod
    def _serialise_field(value: Any) -> Any:
        if isinstance(value, set):
            value = sorted(value)
        if isinstance(value, tuple):
            value = list(value)
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return value


__all__ = ["ProductionRuleExtractionSystem"]