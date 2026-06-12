from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .windower import TextWindow


@dataclass
class ExtractionUnit:
    unit_id: str
    target_text: str
    context_text: str
    source_window_ids: List[str]
    page_number: int
    section_title: str
    source_document: str


class CandidateAssembler:
    """
    Collapses overlapping rule-candidate windows into block-level extraction units.

    Sliding windows are excellent for recall, but they should not be the unit sent
    to the structuring LLM. This assembles the union of candidate sentence spans
    from the same source block and attaches nearby context for subject resolution.
    """

    def __init__(self, context_sentences: int = 2):
        self.context_sentences = context_sentences

    def assemble(self, candidate_windows: Sequence[TextWindow]) -> List[ExtractionUnit]:
        grouped: Dict[Tuple[str, Tuple[str, ...]], List[TextWindow]] = {}
        for window in candidate_windows:
            key = (window.source_document, tuple(window.source_block_ids))
            grouped.setdefault(key, []).append(window)

        units: List[ExtractionUnit] = []
        for (_, block_ids), windows in grouped.items():
            ordered = sorted(windows, key=lambda w: (min(w.sentence_indices), w.window_id))
            sentences = self._sentences_for_group(ordered)
            if not sentences:
                continue

            covered_indices = sorted({
                idx
                for window in ordered
                for idx in window.sentence_indices
                if 0 <= idx < len(sentences)
            })
            if not covered_indices:
                continue

            start, end = covered_indices[0], covered_indices[-1]
            context_start = max(0, start - self.context_sentences)
            context_end = min(len(sentences) - 1, end + self.context_sentences)

            target_text = " ".join(sentences[start:end + 1]).strip()
            context_parts = []
            if ordered[0].section_title and ordered[0].section_title != "Root":
                context_parts.append(f"Section: {ordered[0].section_title}")
            prefix = " ".join(sentences[context_start:start]).strip()
            suffix = " ".join(sentences[end + 1:context_end + 1]).strip()
            if prefix:
                context_parts.append(f"Previous context: {prefix}")
            if suffix:
                context_parts.append(f"Following context: {suffix}")

            unit_window_ids = [w.window_id for w in ordered]
            unit_id = f"{'_'.join(block_ids)}_u{start}_{end}"
            units.append(ExtractionUnit(
                unit_id=unit_id,
                target_text=target_text,
                context_text="\n".join(context_parts),
                source_window_ids=unit_window_ids,
                page_number=ordered[0].page_number,
                section_title=ordered[0].section_title,
                source_document=ordered[0].source_document,
            ))

        return sorted(units, key=lambda u: (u.page_number, u.unit_id))

    @staticmethod
    def _sentences_for_group(windows: Iterable[TextWindow]) -> List[str]:
        for window in windows:
            if window.block_sentences:
                return window.block_sentences
        return []
