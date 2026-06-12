from dataclasses import dataclass, field
from typing import List
import spacy
from .parser import StructuralBlock

@dataclass
class TextWindow:
    window_id: str
    text: str
    source_block_ids: List[str]
    sentence_indices: List[int]
    page_number: int
    section_title: str
    source_document: str
    block_sentences: List[str] = field(default_factory=list)

class SlidingWindowGenerator:
    def __init__(self, window_size: int = 3, stride: int = 1):
        self.window_size = window_size
        self.stride = stride
        # Load English tokenizer, tagger, parser, NER and word vectors
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            from spacy.cli import download
            download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
            
        # We only need sentence segmentation
        self.nlp.select_pipes(enable=["tok2vec", "parser", "senter"])
        
        @spacy.Language.component("custom_engineering_sbd")
        def custom_engineering_sbd(doc):
            for i, token in enumerate(doc[:-1]):
                text = token.text.lower()
                # Prevent split after abbreviations and "NOTE:"
                if text in ("in.", "mm.", "approx.", "max.", "min.", "dia.", "rad.", "fig.", "e.g.", "i.e.", "note:", "note"):
                    doc[i + 1].is_sent_start = False
                # If the token is 'NOTE' and next is ':', prevent split after ':'
                if text == "note" and doc[i + 1].text == ":":
                    if i + 2 < len(doc):
                        doc[i + 2].is_sent_start = False
            return doc
            
        # Add the custom component before parser
        if "custom_engineering_sbd" not in self.nlp.pipe_names:
            if "parser" in self.nlp.pipe_names:
                self.nlp.add_pipe("custom_engineering_sbd", before="parser")
            elif "senter" in self.nlp.pipe_names:
                self.nlp.add_pipe("custom_engineering_sbd", before="senter")
            else:
                self.nlp.add_pipe("custom_engineering_sbd")

    def generate(self, blocks: List[StructuralBlock]) -> List[TextWindow]:
        windows = []
        
        for block in blocks:
            # We treat headers as context, but usually don't window them
            # For now we'll window everything that is text
            doc = self.nlp(block.text)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            
            if not sentences:
                continue
                
            if len(sentences) <= self.window_size:
                # Block is smaller than window size; emit entire block
                windows.append(TextWindow(
                    window_id=f"{block.block_id}_w0",
                    text=" ".join(sentences),
                    source_block_ids=[block.block_id],
                    sentence_indices=list(range(len(sentences))),
                    page_number=block.page_number,
                    section_title=block.section_title,
                    source_document=block.source_document,
                    block_sentences=sentences
                ))
            else:
                # Sliding window within the block
                for i in range(0, len(sentences) - self.window_size + 1, self.stride):
                    window_sents = sentences[i:i + self.window_size]
                    windows.append(TextWindow(
                        window_id=f"{block.block_id}_w{i}",
                        text=" ".join(window_sents),
                        source_block_ids=[block.block_id],
                        sentence_indices=list(range(i, i + self.window_size)),
                        page_number=block.page_number,
                        section_title=block.section_title,
                        source_document=block.source_document,
                        block_sentences=sentences
                    ))
                    
        return windows
