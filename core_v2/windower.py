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

        # Load the spaCy English model for sentence boundary detection.
        # If it is not installed, raise a clear error with install instructions.
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError(
                "spaCy model 'en_core_web_sm' is not installed.\n"
                "Run the following command to install it:\n\n"
                "    python -m spacy download en_core_web_sm\n"
            )

        # Enable only the components needed for sentence segmentation.
        # 'en_core_web_sm' ships with: tok2vec, tagger, parser, senter, ner, attribute_ruler, lemmatizer
        # We only need sentence boundaries so disable everything except what sents needs.
        available_pipes = self.nlp.pipe_names
        pipes_to_enable = [p for p in ["tok2vec", "parser", "senter"] if p in available_pipes]
        if pipes_to_enable:
            self.nlp.select_pipes(enable=pipes_to_enable)

        # Custom component: prevent sentence splits on engineering abbreviations
        @spacy.Language.component("custom_engineering_sbd")
        def custom_engineering_sbd(doc):
            abbreviations = {
                "in.", "mm.", "approx.", "max.", "min.", "dia.", "rad.",
                "fig.", "e.g.", "i.e.", "note:", "note"
            }
            for i, token in enumerate(doc[:-1]):
                text = token.text.lower()
                if text in abbreviations:
                    doc[i + 1].is_sent_start = False
                # If "NOTE" is followed by ":", keep continuation glued
                if text == "note" and doc[i + 1].text == ":":
                    if i + 2 < len(doc):
                        doc[i + 2].is_sent_start = False
            return doc

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
            doc = self.nlp(block.text)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

            if not sentences:
                continue

            if len(sentences) <= self.window_size:
                # Block is smaller than window size; emit as a single window
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
