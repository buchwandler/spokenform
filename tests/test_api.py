import inspect

import pytest

import spokenform
from spokenform import PreparationConfig, prepare


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
