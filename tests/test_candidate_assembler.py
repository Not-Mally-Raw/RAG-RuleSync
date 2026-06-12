from core_v2.candidate_assembler import CandidateAssembler
from core_v2.windower import TextWindow


def _window(window_id, indices, sentences):
    return TextWindow(
        window_id=window_id,
        text=" ".join(sentences[i] for i in indices),
        source_block_ids=["b1"],
        sentence_indices=indices,
        page_number=1,
        section_title="Tabs",
        source_document="sheetmetal.pdf",
        block_sentences=sentences,
    )


def test_assembler_collapses_overlapping_windows_and_adds_context():
    sentences = [
        "Tabs are formed sheet-metal locating features.",
        "The minimum width is equal to two times the material thickness or 3.200 mm, whichever is greater.",
        "The maximum length is five times the width.",
        "The minimum distance between tabs is equal to the material thickness or 1.00 mm, whichever is greater.",
    ]
    windows = [
        _window("b1_w0", [0, 1, 2], sentences),
        _window("b1_w1", [1, 2, 3], sentences),
    ]

    units = CandidateAssembler(context_sentences=1).assemble(windows)

    assert len(units) == 1
    assert units[0].source_window_ids == ["b1_w0", "b1_w1"]
    assert "minimum width" in units[0].target_text
    assert "maximum length" in units[0].target_text
    assert "minimum distance between tabs" in units[0].target_text
    assert "Section: Tabs" in units[0].context_text


def test_assembler_keeps_separate_source_blocks_separate():
    first = _window("b1_w0", [0], ["The minimum bend radius is 2 mm."])
    second = TextWindow(
        window_id="b2_w0",
        text="The minimum hole diameter is 1 mm.",
        source_block_ids=["b2"],
        sentence_indices=[0],
        page_number=1,
        section_title="Holes",
        source_document="sheetmetal.pdf",
        block_sentences=["The minimum hole diameter is 1 mm."],
    )

    units = CandidateAssembler().assemble([second, first])

    assert [u.unit_id for u in units] == ["b1_u0_0", "b2_u0_0"]
