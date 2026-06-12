import sys
from pathlib import Path
import json

sys.path.append(str(Path(__file__).parent.parent))

from core_v2.parser import StructuralBlock, DocumentPayload
from core_v2.windower import SlidingWindowGenerator
from core_v2.truth_store import TruthStore

def test_ingestion():
    # 1. Mock some StructuralBlocks (simulate PyMuPDF output)
    blocks = [
        StructuralBlock(
            block_id="doc1_p1_b1",
            text="The minimum bend radius is an important parameter in sheet metal forming. It should be at least 1.5 times the material thickness.",
            block_type="paragraph",
            page_number=1,
            section_title="Bend Constraints",
            source_document="sheetmetal_guidelines.pdf"
        ),
        StructuralBlock(
            block_id="doc1_p1_b2",
            text="However, for aluminum parts, the minimum bend radius must be 2.0 times the material thickness. Always check the material specs.",
            block_type="paragraph",
            page_number=1,
            section_title="Bend Constraints",
            source_document="sheetmetal_guidelines.pdf"
        )
    ]
    
    payload = DocumentPayload(
        blocks=blocks,
        metadata={"filename": "sheetmetal_guidelines.pdf", "page_count": 1}
    )
    
    # 2. Window Generation
    print("Generating windows...")
    windower = SlidingWindowGenerator(window_size=3, stride=1)
    windows = windower.generate(blocks)
    
    print(f"Generated {len(windows)} windows:")
    for w in windows:
        print(f" - {w.window_id}: {w.text}")
        
    # 3. Truth Store
    print("\nInitializing Truth Store...")
    db_path = Path("test_truth_store.db")
    if db_path.exists():
        db_path.unlink()
        
    store = TruthStore(db_path)
    store.store_document(payload, windows)
    
    # 4. Verify retrieval
    w_text = store.get_window_text(windows[0].window_id)
    print(f"\nRetrieved Window Text: {w_text}")
    assert w_text == windows[0].text, "TruthStore failed to save verbatim text!"
    print("Ingestion pipeline (Windower + TruthStore) works successfully!")
    
if __name__ == "__main__":
    test_ingestion()
