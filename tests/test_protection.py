import pytest

from spokenform import PreparationConfig, ProtectedSpan, ProtectionError, prepare


def test_config_and_caller_protected_span() -> None:
    result = prepare(
        "Dr. 12 https://example.org/a2",
        config=PreparationConfig(language="en"),
        protected_spans=[(0, 3)],
    )
    assert result.spoken_text.startswith("Dr.")
    assert "twelve" in result.spoken_text
    assert "https://example.org/a2" in result.spoken_text
    assert result.warnings == ()


def test_invalid_protection_warns_or_raises() -> None:
    result = prepare("123", protected_spans=[(-1, 2)])
    assert result.warnings[0].startswith("[PROTECT]")

    with pytest.raises(ProtectionError):
        prepare("123", protected_spans=[(-1, 2)], strict=True)


def test_overlapping_protection_warns_or_raises() -> None:
    result = prepare("123", protected_spans=[(0, 2), (1, 3)])
    assert any("overlapping" in warning for warning in result.warnings)

    with pytest.raises(ProtectionError):
        prepare("123", protected_spans=[(0, 2), (1, 3)], strict=True)


def test_protected_literals_survive_all_semantic_stages() -> None:
    source = "URL https://example.org/Dr.2?x=3 email dev2@example.org v1.2.3 Prof. 2 kg"
    result = prepare(source, language="de", use_spacy=False)

    assert "https://example.org/Dr.2?x=3" in result.spoken_text
    assert "dev2@example.org" in result.spoken_text
    assert "v1.2.3" in result.spoken_text
    assert result.spoken_text.endswith("Professor zwei Kilogramm")
    assert all("\ue000" not in value for value in result.warnings)
    assert all("\ue000" not in value for value in result.to_adapter_dict()["spoken_text"])
    assert all("\ue000" not in str(value) for value in result.to_dict().values())


def test_adjacent_caller_spans_and_maps_are_exact() -> None:
    source = "AA11 BB22 01.01.2024 Dr."
    result = prepare(
        source,
        language="de",
        use_spacy=False,
        protected_spans=(
            ProtectedSpan(0, 4, kind="code"),
            ProtectedSpan(5, 9, kind="code"),
        ),
    )

    assert result.spoken_text.startswith("AA11 BB22")
    assert result.spoken_text.endswith("Doktor")
    assert result.protected_spans[0].kind == "code"
    assert result.map_source_span(0, 4) == (0, 4)
    assert "\ue000" not in result.render_changes()


def test_unicode_normalization_around_protected_placeholder_preserves_offsets() -> None:
    source = "e\u0301 https://example.org/é 2 kg"
    result = prepare(source, language="de", use_spacy=False)
    url_start = source.index("https://")
    url_end = url_start + len("https://example.org/é")
    output_start, output_end = result.map_source_span(url_start, url_end)

    assert result.spoken_text[output_start:output_end] == "https://example.org/é"
    assert result.map_output_span(output_start, output_end) == (url_start, url_end)
