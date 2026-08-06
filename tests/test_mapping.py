from spokenform import OffsetMap, Replacement, prepare
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
