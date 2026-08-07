from spokenform import OffsetMap, prepare


def test_structured_mapping_preserves_exact_source_span() -> None:
    source = "A 2 kg, then 2 kg."
    result = prepare(source, language="de", use_spacy=False)
    structured = next(stage for stage in result.stages if stage.name == "structured")
    assert [edit.source for edit in structured.mapped_edits] == ["2 kg", "2 kg"]
    assert [edit.replacement for edit in structured.mapped_edits] == [
        "zwei Kilogramm",
        "zwei Kilogramm",
    ]
    assert all(edit.kind == "structured" for edit in structured.mapped_edits)
    assert all(edit.rule == "de.quantity" for edit in structured.mapped_edits)


def test_public_span_helpers_and_serialization_round_trip() -> None:
    source = "Prof. hat 2 kg."
    result = prepare(source, language="de", use_spacy=False)
    start = source.index("2 kg")
    end = start + len("2 kg")
    output_start, output_end = result.map_source_span(start, end)
    assert result.spoken_text[output_start:output_end] == "zwei Kilogramm"
    assert result.map_output_span(output_start, output_end) == (start, end)
    assert result.source_edits
    assert result.source_edits[0].source_start == source.index("Prof.")
    assert result.source_edits[0].output_start == result.spoken_text.index("Professor")
    quantity_edit = next(edit for edit in result.source_edits if edit.source == "2 kg")
    assert quantity_edit.replacement == "zwei Kilogramm"
    assert quantity_edit.stages == ("structured",)
    restored = OffsetMap.from_dict(result.to_dict()["offset_map"])
    assert restored.source_to_output(len(source)) == len(result.spoken_text)
