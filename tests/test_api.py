import inspect

import pytest

import spokenform
from spokenform import NumberPolicy, PreparationConfig, prepare, prepare_for_kokorog2p


def test_german_readable_pipeline() -> None:
    result = prepare(
        "Prof. Klein bringt am 14.05.2026 um 18:20 Uhr 2 kg mit.",
        language="de",
    )

    assert result.language == "de"
    assert "Professor Klein" in result.spoken_text
    assert "vierzehnten Mai" in result.spoken_text
    assert "achtzehn Uhr zwanzig" in result.spoken_text
    assert "zwei Kilogramm" in result.spoken_text
    assert [stage.name for stage in result.stages] == [
        "structured",
        "abbreviations",
        "numbers",
        "whitespace",
    ]
    assert result.changed
    assert result.edits


def test_disable_stages() -> None:
    result = prepare(
        "Prof. Klein hat 2 kg.",
        language="de",
        expand_abbreviations=False,
        expand_structured=False,
        expand_numbers=False,
        normalize_whitespace=False,
    )
    assert result.spoken_text == "Prof. Klein hat 2 kg."
    assert result.stages == ()


def test_language_is_explicit_and_source_is_not_parsed_as_markup() -> None:
    source = '[Bonjour]{lang="fr"} 2 tests.'
    result = prepare(
        source,
        language="en",
        expand_abbreviations=False,
        expand_numbers=False,
        normalize_whitespace=False,
    )
    assert result.language == "en"
    assert result.clean_text == source
    assert result.spoken_text == source
    assert "language_spans" not in result.to_dict()
    assert "semantic_spans" not in result.to_dict()


def test_spacing_is_last_and_reviewable() -> None:
    result = prepare(
        "  Hello\u00a0  world  ",
        language="en",
        expand_abbreviations=False,
        expand_numbers=False,
    )
    assert result.spoken_text == "Hello world"
    assert result.stages[-1].name == "whitespace"
    assert result.stages[-1].changed


def test_unicode_normalization_is_independent_from_whitespace() -> None:
    decomposed = "e\u0301"
    preserved = prepare(
        decomposed,
        expand_abbreviations=False,
        expand_structured=False,
        expand_numbers=False,
        normalize_whitespace=False,
        normalize_unicode=False,
        use_spacy=False,
    )
    normalized = prepare(
        decomposed,
        expand_abbreviations=False,
        expand_structured=False,
        expand_numbers=False,
        normalize_whitespace=False,
        normalize_unicode=True,
        use_spacy=False,
    )

    assert preserved.spoken_text == decomposed
    assert normalized.spoken_text == "é"


def test_whitespace_controls_are_independent() -> None:
    source = "  a\t\u00a0b \n\n\n c  "
    result = prepare(
        source,
        config=PreparationConfig(
            language="en",
            expand_abbreviations=False,
            expand_structured=False,
            expand_numbers=False,
            normalize_unicode=False,
            strip_outer_whitespace=False,
            collapse_horizontal_whitespace=False,
            normalize_line_whitespace=False,
            collapse_blank_lines=False,
            use_spacy=False,
        ),
    )

    assert result.spoken_text == source


def test_kokorog2p_profile_preserves_outer_run_spaces() -> None:
    result = prepare(
        "  Hallo  ",
        config=PreparationConfig.for_kokorog2p("de"),
        expand_abbreviations=False,
        expand_structured=False,
        expand_numbers=False,
    )

    assert result.spoken_text == "  Hallo  "


def test_kokorog2p_profile_keeps_model_punctuation_downstream() -> None:
    result = prepare(
        "Hallo!",
        config=PreparationConfig(language="de", model_punctuation=True),
        expand_abbreviations=False,
        expand_structured=False,
        expand_numbers=False,
    )
    assert result.spoken_text == "Hallo!"
    assert any("model punctuation remains downstream" in warning for warning in result.warnings)


def test_kokorog2p_adapter_projection_is_complete_and_serializable() -> None:
    result = prepare_for_kokorog2p("Prof. 2 kg", "de")
    projection = result.to_adapter_dict()
    serialized = result.to_dict()

    assert projection["spoken_text"] == result.spoken_text
    assert projection["language"] == "de"
    assert projection["source_replacements"]
    assert projection["offset_map"]["source_length"] == len(result.source_text)  # type: ignore[index]
    assert "stage_report" in projection
    assert serialized["source_edits"] == serialized["source_replacements"]


def test_kokorog2p_number_policy_is_explicit_by_language() -> None:
    german = prepare_for_kokorog2p("2 kg", "de")
    english = prepare_for_kokorog2p("2", "en")
    disabled = prepare(
        "2",
        config=PreparationConfig(
            language="de",
            number_policy=NumberPolicy.NONE,
            expand_abbreviations=False,
            use_spacy=False,
        ),
    )

    assert "zwei Kilogramm" in german.spoken_text
    assert english.spoken_text == "2"
    assert any("caller-managed" in warning for warning in english.warnings)
    assert disabled.spoken_text == "2"
    assert any("unsupported number policy" in warning for warning in disabled.warnings)


def test_removed_api_arguments_and_exports_are_absent() -> None:
    parameters = inspect.signature(prepare).parameters
    for removed in (
        "detect_language",
        "detector",
        "allowed_languages",
        "language_spans",
        "markup",
        "render_language_marks",
    ):
        assert removed not in parameters

    for removed in (
        "LanguageDetector",
        "lingua_detector",
        "LanguageSpan",
        "SemanticSpan",
        "ParsedMarkup",
        "SSMDParseError",
    ):
        assert not hasattr(spokenform, removed)


def test_preparation_config_requires_a_non_empty_language() -> None:
    with pytest.raises(TypeError, match="language must be a string"):
        PreparationConfig(language=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="language must not be empty"):
        PreparationConfig(language="  ")


def test_removed_prepare_arguments_fail_with_type_error() -> None:
    with pytest.raises(TypeError):
        prepare("hello", language="en", detect_language=True)  # type: ignore[call-arg]


def test_preparation_config_validates_spacy_options() -> None:
    with pytest.raises(TypeError, match="use_spacy"):
        PreparationConfig(language="en", use_spacy="yes")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="spacy_model"):
        PreparationConfig(language="en", spacy_model="  ")
