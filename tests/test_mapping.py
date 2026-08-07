from spokenform import (
    MappedEdit,
    OffsetMap,
    PreparationStage,
    Replacement,
    TextEdit,
    compose_source_replacements,
    prepare,
)
from spokenform.mapping import apply_replacements


def test_replacement_map_supports_expansion_and_bias() -> None:
    output, edits, mapping = apply_replacements(
        "abcd", (Replacement(1, 2, "XYZ", kind="word"),), stage="words"
    )
    assert output == "aXYZcd"
    assert edits[0].output_start == 1
    assert edits[0].output_end == 4
    assert mapping.source_to_output(1, bias="left") == 1
    assert mapping.source_to_output(1, bias="right") == 4
    assert mapping.source_to_output(2) == 4
    assert mapping.map_source_span(1, 2) == (1, 4)
    assert mapping.output_to_source(1, bias="left") == 1
    assert mapping.output_to_source(1, bias="right") == 2
    assert mapping.output_to_source(4) == 2


def test_insertion_deletion_and_collapse_maps_are_bounded() -> None:
    for replacement, expected in (
        (Replacement(1, 1, "XYZ"), "aXYZbcd"),
        (Replacement(1, 3, ""), "ad"),
        (Replacement(1, 3, "Q"), "aQd"),
    ):
        output, _, mapping = apply_replacements("abcd", (replacement,), stage="test")
        assert output == expected
        assert all(0 <= value <= len(output) for value in mapping.source_left)
        assert all(0 <= value <= len("abcd") for value in mapping.output_left)
        assert list(mapping.source_left) == sorted(mapping.source_left)
        assert list(mapping.source_right) == sorted(mapping.source_right)


def test_composed_preparation_map_and_serialization() -> None:
    result = prepare("Prof. has 2 kg.", language="de")
    assert isinstance(result.offset_map, OffsetMap)
    assert result.offset_map.source_length == len(result.clean_text)
    assert result.offset_map.output_length == len(result.spoken_text)
    assert result.offset_map.source_to_output(0) == 0
    assert result.offset_map.source_to_output(len(result.clean_text)) == len(result.spoken_text)
    serialized = result.to_dict()
    assert serialized["offset_map"]["source_length"] == len(result.clean_text)
    assert serialized["mapped_edits"]
    restored = OffsetMap.from_dict(serialized["offset_map"])
    assert restored.source_to_output(len(result.clean_text)) == len(result.spoken_text)


def test_source_replacements_merge_edits_inside_generated_text() -> None:
    first = PreparationStage(
        name="first",
        before="a",
        after="abc",
        edits=(TextEdit(0, 1, "a", "abc", "first"),),
        mapped_edits=(MappedEdit(0, 1, 0, 3, "a", "abc", "first"),),
    )
    second = PreparationStage(
        name="second",
        before="abc",
        after="axc",
        edits=(TextEdit(1, 2, "b", "x", "second"),),
        mapped_edits=(MappedEdit(1, 2, 1, 2, "b", "x", "second"),),
    )
    maps = (
        OffsetMap.from_replacements(1, (Replacement(0, 1, "abc"),), output_length=3),
        OffsetMap.from_replacements(3, (Replacement(1, 2, "x"),), output_length=3),
    )

    replacements = compose_source_replacements("a", "axc", (first, second), maps)

    assert replacements == (replacements[0],)
    assert replacements[0].source_start == 0
    assert replacements[0].source_end == 1
    assert replacements[0].output_start == 0
    assert replacements[0].output_end == 3
    assert replacements[0].source == "a"
    assert replacements[0].replacement == "axc"
    assert replacements[0].stages == ("first", "second")


def test_source_replacements_are_ordered_non_overlapping_and_reconstructable() -> None:
    source = "1 kWh, 12,50 EUR"
    result = prepare(source, language="de", use_spacy=False)
    edits = result.source_replacements
    assert list(edits) == sorted(edits, key=lambda item: (item.source_start, item.output_start))
    assert all(
        left.source_end <= right.source_start for left, right in zip(edits, edits[1:], strict=False)
    )
    assert all(source[item.source_start : item.source_end] == item.source for item in edits)
    assert all(
        result.spoken_text[item.output_start : item.output_end] == item.replacement
        for item in edits
    )
    assert [(item.source, item.replacement) for item in edits] == [
        ("1 kWh", "eine Kilowattstunde"),
        ("12,50 EUR", "zwölf Euro fünfzig Cent"),
    ]
