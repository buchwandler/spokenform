from __future__ import annotations

import builtins
import inspect

import pytest

from spokenform import (
    PreparationConfig,
    TokenAnnotation,
    prepare,
    prepare_for_kokorog2p,
    prepare_language,
)


def test_prepare_language_requires_explicit_language_and_matches_config() -> None:
    parameter = inspect.signature(prepare_language).parameters["language"]
    assert parameter.default is inspect.Parameter.empty
    assert prepare_language("2", language="en", use_spacy=False).spoken_text == "two"
    assert prepare("2", use_spacy=False).spoken_text == "two"

    with pytest.raises(ValueError, match="config language"):
        prepare_language(
            "2",
            language="en",
            config=PreparationConfig.for_speech("de"),
        )


def test_generic_speech_preset_is_not_kokoro_specific() -> None:
    config = PreparationConfig.for_speech("de")
    assert config.language == "de"
    assert config == PreparationConfig(language="de")
    result = prepare("2 kg", config=config, use_spacy=False)
    assert result.spoken_text == "zwei Kilogramm"
    assert "kokoro" not in type(config).__module__.casefold()


def test_injected_annotations_do_not_resolve_spacy_or_leak_source_pos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_loader(*args: object, **kwargs: object) -> object:
        raise AssertionError("internal spaCy resolution must not run")

    monkeypatch.setattr("spokenform.api.load_spacy_model", fail_loader)
    annotation = TokenAnnotation(start=0, end=1, text="2", pos="NUM", tag="CD")
    result = prepare_language(
        "2",
        language="en",
        annotations=(annotation,),
        use_spacy=True,
    )

    assert result.spoken_text == "two"
    assert not hasattr(result, "annotations")
    assert result.mapped_edits[0].source == "2"
    assert result.mapped_edits[0].replacement == "two"


def test_provenance_keeps_semantic_metadata_and_offsets() -> None:
    source = "in 1989 and 2 kg"
    result = prepare_language(source, language="en", use_spacy=False)

    year = next(item for item in result.source_replacements if item.rule == "sequence.year")
    assert year.recognition_domain == "temporal"
    assert year.recognition_evidence == "contextual"
    assert result.source_text[year.source_start : year.source_end] == year.source
    assert result.spoken_text[year.output_start : year.output_end] == year.replacement
    assert result.map_source_span(year.source_start, year.source_end) == (
        year.output_start,
        year.output_end,
    )


def test_protected_spans_remain_literal_for_generic_consumers() -> None:
    source = "Use 2 kg and 3 kg"
    result = prepare_language(
        source,
        language="de",
        protected_spans=[(4, 8)],
        use_spacy=False,
    )

    assert result.spoken_text == "Use 2 kg and drei Kilogramm"
    assert result.spoken_text[4:8] == "2 kg"
    assert any(item.source == "3 kg" for item in result.source_replacements)


def test_generic_preparation_does_not_import_kokorog2p(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def reject_kokoro(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith(("kokorog2p", "pykokoro")):
            raise AssertionError("generic preparation must not import a TTS engine")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_kokoro)
    result = prepare_language("2", language="de", use_spacy=False)
    assert result.spoken_text == "zwei"
    assert prepare_for_kokorog2p("2", "de", use_spacy=False).spoken_text == "zwei"


def test_optional_lexical_evidence_keeps_core_normalization_available() -> None:
    result = prepare_language("2 kg", language="de", use_spacy=False, lexical_evidence=None)
    assert result.spoken_text == "zwei Kilogramm"
    assert any(item.rule == "de.quantity" for item in result.source_replacements)
