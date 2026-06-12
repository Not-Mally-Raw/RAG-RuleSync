from __future__ import annotations
from typing import Iterable, List, Optional
from .interfaces import ITextLoader, IChunker, IRuleExtractor, IExporter, DocumentMeta, Rule
from .adapters import TextLoaderAdapter, ChunkerAdapter, RuleExtractorAdapter, ExporterAdapter

class ProductionRuleExtractionSystem:
    """
    Small orchestrator that composes loader, chunker, extractor and exporter.
    Accepts dependency-injected components implementing the Protocols in core.interfaces.
    This is intentionally a thin coordinator to avoid changing existing logic.
    """
    def __init__(
        self,
        loader: Optional[ITextLoader] = None,
        chunker: Optional[IChunker] = None,
        extractor: Optional[IRuleExtractor] = None,
        exporter: Optional[IExporter] = None,
    ):
        # default adapters delegate to the legacy implementations lazily
        self.loader: ITextLoader = loader or TextLoaderAdapter()
        self.chunker: IChunker = chunker or ChunkerAdapter()
        self.extractor: IRuleExtractor = extractor or RuleExtractorAdapter()
        self.exporter: IExporter = exporter or ExporterAdapter()

    def process_document(self, path: str, export_path: Optional[str] = None) -> List[Rule]:
        """
        Load document, chunk it, extract rules from each chunk and optionally export.
        Returns the list of Rule objects collected.
        """
        doc_meta: DocumentMeta = self.loader.load(path)
        chunks = self.chunker.chunk(doc_meta)
        collected: List[Rule] = []
        for chunk in chunks:
            rules = self.extractor.extract(chunk, {"document": doc_meta})
            # preserve existing behavior: if extractor returns None, skip
            if not rules:
                continue
            collected.extend(rules)
        if export_path:
            # exporter expected to accept iterable of Rule and path
            self.exporter.export(collected, export_path)
        return collected

def default_production_system() -> ProductionRuleExtractionSystem:
    """
    Convenience factory that wires the system with default adapters.
    Use this when you want behavior identical to the legacy pipeline but with DI.
    """
    return ProductionRuleExtractionSystem(
        loader=TextLoaderAdapter(),
        chunker=ChunkerAdapter(),
        extractor=RuleExtractorAdapter(),
        exporter=ExporterAdapter(),
    )
