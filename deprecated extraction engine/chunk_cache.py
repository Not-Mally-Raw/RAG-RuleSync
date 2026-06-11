"""Chunk-level persistence for resumable rule extraction.

This module intentionally has a single responsibility: store and retrieve
per-chunk extraction outputs so expensive LLM calls can be resumed safely
after rate limits or interruptions.

Design notes (SOLID):
- `ChunkCache` is a small interface (DIP).
- `FileChunkCache` is one implementation (SRP).
- The enhanced engine depends on the interface, not the implementation.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Protocol


class ChunkCache(Protocol):
    def get(self, *, document_id: str, chunk_index: int) -> Optional[Dict[str, Any]]:
        """Return cached payload for a chunk, or None if missing."""

    def set(self, *, document_id: str, chunk_index: int, payload: Dict[str, Any]) -> None:
        """Persist payload for a chunk."""


@dataclass(frozen=True)
class FileChunkCache:
    """File-backed chunk cache.

    Layout:
      <base_dir>/<document_id>/chunk_<chunk_index>.json

    Files are written atomically to avoid corruption on interruption.
    """

    base_dir: Path

    def _path_for(self, *, document_id: str, chunk_index: int) -> Path:
        safe_doc = document_id.strip().replace(os.sep, "_")
        return self.base_dir / safe_doc / f"chunk_{chunk_index}.json"

    def get(self, *, document_id: str, chunk_index: int) -> Optional[Dict[str, Any]]:
        path = self._path_for(document_id=document_id, chunk_index=chunk_index)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            # Treat unreadable cache as a miss (caller can overwrite).
            return None

    def set(self, *, document_id: str, chunk_index: int, payload: Dict[str, Any]) -> None:
        path = self._path_for(document_id=document_id, chunk_index=chunk_index)
        path.parent.mkdir(parents=True, exist_ok=True)

        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
