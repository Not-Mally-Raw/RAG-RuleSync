from __future__ import annotations
from typing import Optional, Callable, Iterable, List, Dict, Any
import importlib
from .interfaces import DocumentMeta, Rule, ITextLoader, IChunker, IRuleExtractor, IExporter

def _resolve_callable(module_name: str, attr: str) -> Callable:
    """Lazy import helper — returns callable or raises ImportError with guidance."""
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        raise ImportError(f"Could not import module '{module_name}': {e}") from e
    try:
        fn = getattr(mod, attr)
    except AttributeError as e:
        raise ImportError(f"Module '{module_name}' has no attribute '{attr}'") from e
    if not callable(fn):
        raise TypeError(f"Resolved attribute {module_name}.{attr} is not callable")
    return fn

class TextLoaderAdapter(ITextLoader):
    """
    Adapter that delegates to an existing loader function.
    Provide 'impl' as either a callable or as tuple (module_name, func_name).
    """
    def __init__(self, impl: Optional[object] = None):
        self._impl = impl

    def _get_impl(self):
        if callable(self._impl):
            return self._impl
        if isinstance(self._impl, tuple) and len(self._impl) == 2:
            return _resolve_callable(self._impl[0], self._impl[1])
        # default: try common legacy locations (safe lazy lookup)
        return _resolve_callable("core.document_loader", "load_document")

    def load(self, path: str) -> DocumentMeta:
        fn = self._get_impl()
        result = fn(path)  # expected to return DocumentMeta-like dict or object
        if isinstance(result, DocumentMeta):
            return result
        # if legacy returns dict, coerce to DocumentMeta (non-invasive)
        if isinstance(result, dict):
            return DocumentMeta(path=path, pages=result.get("pages"), text=result.get("text"), extras=result)
        return result

class ChunkerAdapter(IChunker):
    def __init__(self, impl: Optional[object] = None):
        self._impl = impl

    def _get_impl(self):
        if callable(self._impl):
            return self._impl
        if isinstance(self._impl, tuple) and len(self._impl) == 2:
            return _resolve_callable(self._impl[0], self._impl[1])
        return _resolve_callable("core.chunking", "chunk_text")

    def chunk(self, document: DocumentMeta) -> Iterable[str]:
        fn = self._get_impl()
        return fn(document)

class RuleExtractorAdapter(IRuleExtractor):
    def __init__(self, impl: Optional[object] = None):
        self._impl = impl

    def _get_impl(self):
        if callable(self._impl):
            return self._impl
        if isinstance(self._impl, tuple) and len(self._impl) == 2:
            return _resolve_callable(self._impl[0], self._impl[1])
        return _resolve_callable("core.rule_extraction", "extract_rules_from_chunk")

    def extract(self, chunk: str, context: Optional[Dict[str, Any]] = None) -> List[Rule]:
        fn = self._get_impl()
        raw = fn(chunk, context) if context is not None else fn(chunk)
        # If legacy returns dicts, coerce
        if isinstance(raw, list) and raw and isinstance(raw[0], dict):
            return [Rule(id=r.get("id"), text=r.get("text") or r.get("rule"), category=r.get("category"), confidence=r.get("confidence"), meta=r) for r in raw]
        return raw  # assume already List[Rule] or compatible

class ExporterAdapter(IExporter):
    def __init__(self, impl: Optional[object] = None):
        self._impl = impl

    def _get_impl(self):
        if callable(self._impl):
            return self._impl
        if isinstance(self._impl, tuple) and len(self._impl) == 2:
            return _resolve_callable(self._impl[0], self._impl[1])
        return _resolve_callable("core.exporter", "export_rules")

    def export(self, rules: Iterable[Rule], output_path: str) -> None:
        fn = self._get_impl()
        fn(rules, output_path)
