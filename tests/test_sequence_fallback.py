from __future__ import annotations

import pytest

from spokenform import PreparationConfig, SequenceFallbackMode, prepare
from spokenform.language import SUPPORTED_BASE_LANGUAGES


def test_sequence_fallback_preserve_is_default() -> None:
    implicit = prepare("AAPL", language="en", use_spacy=False)
    explicit = prepare("AAPL", language="en", use_spacy=False, sequence_fallback_mode="preserve")
    assert implicit.spoken_text == explicit.spoken_text == "AAPL"
    assert PreparationConfig().sequence_fallback_mode is SequenceFallbackMode.PRESERVE


def test_unknown_uppercase_is_spelled_by_opt_in_fallback() -> None:
    result = prepare("AAPL", language="en", use_spacy=False, sequence_fallback_mode="spell")
    assert result.spoken_text == "A A P L"
    assert [item.rule for item in result.source_replacements] == ["fallback.sequence"]


def test_mixed_alphanumeric_and_identifier_punctuation_are_spelled() -> None:
    assert prepare("XJ9", use_spacy=False, sequence_fallback_mode="spell").spoken_text == (
        "X J nine"
    )
    result = prepare(
        "AB-12", use_spacy=False, sequence_fallback_mode="spell", disabled_domains={"identifiers"}
    )
    assert result.spoken_text == "A B hyphen one two"
    assert all(item.rule != "sequence.product" for item in result.source_replacements)
    assert any(item.rule == "fallback.sequence" for item in result.source_replacements)


def test_fallback_does_not_spell_ordinary_words() -> None:
    source = "hello TravelTips LaCrosse McGill VanRullen"
    result = prepare(source, use_spacy=False, sequence_fallback_mode="spell")
    assert result.spoken_text == source
    assert not result.source_replacements


def test_caller_protection_is_absolute() -> None:
    result = prepare(
        "H2O", use_spacy=False, sequence_fallback_mode="spell", protected_spans=[(0, 3)]
    )
    assert result.spoken_text == "H2O"
    assert not result.source_replacements


def test_disabled_chemistry_can_use_orthographic_fallback() -> None:
    preserved = prepare("H2O", use_spacy=False, disabled_domains={"chemistry"})
    spelled = prepare(
        "H2O", use_spacy=False, disabled_domains={"chemistry"}, sequence_fallback_mode="spell"
    )
    assert preserved.spoken_text == "H2O"
    assert spelled.spoken_text == "H two O"
    assert all(item.rule != "sequence.formula" for item in spelled.source_replacements)
    assert any(item.rule == "fallback.sequence" for item in spelled.source_replacements)


def test_surface_suppression_and_fallback_remain_separate() -> None:
    result = prepare(
        "final 3-2",
        use_spacy=False,
        interpretation_mode="surface",
        sequence_fallback_mode="spell",
    )
    assert result.spoken_text == "final three hyphen two"
    assert all(item.rule != "sequence.sports" for item in result.source_replacements)
    assert any(item.rule == "fallback.sequence" for item in result.source_replacements)


def test_auto_protected_literals_are_not_spelled() -> None:
    result = prepare("See https://example.org/a2", use_spacy=False, sequence_fallback_mode="spell")
    assert result.spoken_text == "See https://example.org/a2"
    assert not any(item.rule == "fallback.sequence" for item in result.source_replacements)


def test_literal_promotion_precedes_fallback() -> None:
    result = prepare(
        "See https://example.org/a2",
        use_spacy=False,
        normalize_literals=True,
        sequence_fallback_mode="spell",
    )
    assert any(item.rule == "sequence.url" for item in result.source_replacements)
    assert not any(item.rule == "fallback.sequence" for item in result.source_replacements)


@pytest.mark.parametrize("language", sorted(SUPPORTED_BASE_LANGUAGES))
def test_fallback_is_total_and_mapped_in_every_supported_language(language: str) -> None:
    result = prepare("XJ9", language=language, use_spacy=False, sequence_fallback_mode="spell")
    assert result.spoken_text
    replacement = next(
        item for item in result.source_replacements if item.rule == "fallback.sequence"
    )
    assert replacement.source == "XJ9"
    assert result.map_source_span(replacement.source_start, replacement.source_end) == (
        replacement.output_start,
        replacement.output_end,
    )
    assert result.map_output_span(replacement.output_start, replacement.output_end) == (
        replacement.source_start,
        replacement.source_end,
    )
