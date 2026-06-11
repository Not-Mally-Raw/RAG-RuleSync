import sqlite3
import json
from pathlib import Path
from typing import List, Optional
from .parser import StructuralBlock, DocumentPayload
from .windower import TextWindow

class TruthStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    filename TEXT PRIMARY KEY,
                    metadata JSON
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    block_id TEXT PRIMARY KEY,
                    text TEXT,
                    block_type TEXT,
                    page_number INTEGER,
                    section_title TEXT,
                    source_document TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS windows (
                    window_id TEXT PRIMARY KEY,
                    text TEXT,
                    source_block_ids JSON,
                    sentence_indices JSON,
                    page_number INTEGER,
                    section_title TEXT,
                    source_document TEXT
                )
            """)
            conn.commit()

    def store_document(self, payload: DocumentPayload, windows: List[TextWindow]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT OR IGNORE INTO documents (filename, metadata) VALUES (?, ?)",
                (payload.metadata.get("filename", "unknown"), json.dumps(payload.metadata))
            )
            
            for b in payload.blocks:
                cursor.execute(
                    """INSERT OR IGNORE INTO blocks 
                       (block_id, text, block_type, page_number, section_title, source_document) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (b.block_id, b.text, b.block_type, b.page_number, b.section_title, b.source_document)
                )
                
            for w in windows:
                cursor.execute(
                    """INSERT OR IGNORE INTO windows 
                       (window_id, text, source_block_ids, sentence_indices, page_number, section_title, source_document) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (w.window_id, w.text, json.dumps(w.source_block_ids), json.dumps(w.sentence_indices),
                     w.page_number, w.section_title, w.source_document)
                )
            conn.commit()

    def get_window_text(self, window_id: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT text FROM windows WHERE window_id = ?", (window_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_block_text(self, block_id: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT text FROM blocks WHERE block_id = ?", (block_id,))
            row = cursor.fetchone()
            return row[0] if row else None
