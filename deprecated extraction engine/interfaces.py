from __future__ import annotations
from typing import Protocol, Iterable, List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class DocumentMeta:
    path: str
    pages: Optional[int] = None
    text: Optional[str] = None
    extras: Optional[Dict[str, Any]] = None

@dataclass
class Rule:
    id: Optional[str]
    text: str
    category: Optional[str] = None
    confidence: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None

class ITextLoader(Protocol):
    """Load a document and return metadata + text."""
    def load(self, path: str) -> DocumentMeta:
        ...

class IChunker(Protocol):
    """Turn DocumentMeta into iterable chunks (strings)."""
    def chunk(self, document: DocumentMeta) -> Iterable[str]:
        ...

class IRuleExtractor(Protocol):
    """Extract structured rules from a text chunk."""
    def extract(self, chunk: str, context: Optional[Dict[str, Any]] = None) -> List[Rule]:
        ...

class IExporter(Protocol):
    """Export collected rules to storage (CSV/DB)."""
    def export(self, rules: Iterable[Rule], output_path: str) -> None:
        ...
