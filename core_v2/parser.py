import fitz  # PyMuPDF
from dataclasses import dataclass, field
from typing import List, Dict, Any
from pathlib import Path
import hashlib

@dataclass
class StructuralBlock:
    block_id: str
    text: str
    block_type: str  # "paragraph", "table_row", "list_item", "header"
    page_number: int
    section_title: str
    source_document: str

@dataclass
class DocumentPayload:
    blocks: List[StructuralBlock]
    metadata: Dict[str, Any]

class LayoutAwareParser:
    def parse(self, file_path: Path) -> DocumentPayload:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        ext = file_path.suffix.lower()
        if ext == '.pdf':
            return self._parse_pdf(file_path)
        else:
            raise NotImplementedError(f"Unsupported extension: {ext}")
            
    def _parse_pdf(self, file_path: Path) -> DocumentPayload:
        doc = fitz.open(file_path)
        blocks_out = []
        doc_hash = hashlib.md5(file_path.name.encode()).hexdigest()[:8]
        current_section = "Root"
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # --- 1. SAFE TABLE EXTRACTION ---
            table_bboxes = []
            if hasattr(page, "find_tables"):
                table_finder = page.find_tables()
                if table_finder and table_finder.tables:
                    for t_idx, table in enumerate(table_finder.tables):
                        table_bboxes.append(table.bbox)
                        try:
                            df = table.to_pandas()
                            if not df.empty:
                                # Fallback to CSV if markdown isn't available
                                table_text = df.to_csv(index=False, sep="\t")
                                block_id = f"{doc_hash}_p{page_num+1}_t{t_idx}"
                                blocks_out.append(StructuralBlock(
                                    block_id=block_id,
                                    text=table_text.strip(),
                                    block_type="table",
                                    page_number=page_num + 1,
                                    section_title=current_section,
                                    source_document=file_path.name
                                ))
                        except Exception as e:
                            # If table parsing fails, ignore and let text blocks pick it up
                            pass
            
            # --- 2. TEXT BLOCK EXTRACTION ---
            blocks = page.get_text("dict").get("blocks", [])
            for b_idx, b in enumerate(blocks):
                if b.get("type") == 0:  # 0 means text block
                    bbox = b.get("bbox", [0, 0, 0, 0])
                    
                    # Check if block center is inside a parsed table to prevent duplication
                    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
                    in_table = any(
                        (t[0] <= cx <= t[2] and t[1] <= cy <= t[3])
                        for t in table_bboxes
                    )
                    
                    if in_table:
                        continue
                        
                    text = ""
                    max_font_size = 0
                    is_bold = False
                    
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            text += span.get("text", "") + " "
                            # Track font characteristics
                            size = span.get("size", 0)
                            if size > max_font_size: max_font_size = size
                            # Flag 2**4 is bold in PyMuPDF
                            if span.get("flags", 0) & 16: is_bold = True
                            
                    text = text.strip()
                    if text:
                        # Improved Heuristic for headers vs paragraphs
                        block_type = "paragraph"
                        is_short = len(text.split()) < 10
                        
                        # A header is usually short, bold or large, and doesn't end with a period
                        if is_short and (text.isupper() or max_font_size > 12 or is_bold):
                            if not text.endswith(('.', ':', ',')):
                                block_type = "header"
                                current_section = text
                                
                        block_id = f"{doc_hash}_p{page_num+1}_b{b_idx}"
                        blocks_out.append(StructuralBlock(
                            block_id=block_id,
                            text=text,
                            block_type=block_type,
                            page_number=page_num + 1,
                            section_title=current_section,
                            source_document=file_path.name
                        ))
                        
        metadata = {
            "filename": file_path.name,
            "page_count": len(doc),
            "total_blocks": len(blocks_out)
        }
        return DocumentPayload(blocks=blocks_out, metadata=metadata)
