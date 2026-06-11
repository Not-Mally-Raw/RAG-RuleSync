"""Async document processing helpers built on the fast pipeline loader."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Dict, List

from .rule_extraction import DocumentLoader


logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Thin async facade that reuses the cached :class:`DocumentLoader`."""

    def __init__(self, *, cache_size: int = 16) -> None:
        self.loader = DocumentLoader(cache_size=cache_size)

    async def process_document(self, file_path: str) -> Dict[str, object]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        payload = await self.loader.load(path)
        info = dict(payload.metadata)
        info["text"] = payload.text
        info.setdefault("errors", [])
        word_count = max(1, int(info.get("word_count") or 0))
        keywords = info.get("manufacturing_keywords", [])
        info["manufacturing_density"] = len(keywords) / word_count
        logger.debug("processed_document", extra={"filename": info.get("filename")})
        return info

    async def process_multiple_documents(self, file_paths: List[str]) -> List[Dict[str, object]]:
        tasks = [self.process_document(path) for path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed: List[Dict[str, object]] = []
        for original_path, result in zip(file_paths, results):
            if isinstance(result, Exception):
                processed.append(
                    {
                        "filename": Path(original_path).name,
                        "file_path": original_path,
                        "text": "",
                        "errors": [str(result)],
                        "processing_failed": True,
                    }
                )
            else:
                processed.append(result)
        return processed


def get_document_processor() -> DocumentProcessor:
    return DocumentProcessor()


async def test_document_processing() -> None:  # pragma: no cover - smoke helper
    processor = DocumentProcessor()
    # Basic sanity check on a tiny inline string by writing temp file
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
        handle.write("Test manufacturing rule: maintain 5 mm tolerance.")
        temp_path = handle.name

    result = await processor.process_document(temp_path)
    print("Processed", result["filename"], "words", result.get("word_count"))


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(test_document_processing())