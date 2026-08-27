from __future__ import annotations

import pytest
from abbr2words import iter_unit_matches

from spokenform import prepare
from spokenform.config import RecognitionDomain
from spokenform.language import resolve_abbr2words_language, resolve_num2words_language
from spokenform.numbers import normalize_numbers
from spokenform.numeric_lexeme import (
    NumericLexeme,
    numeric_punctuation_policy,
    numeric_speech_policy,
    parse_numeric_lexeme,
)
from spokenform.structured import iter_structured_replacements


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", "noll"),
        ("1", "ett"),
        ("2", "två"),
        ("11", "elva"),
        ("21", "tjugoett"),
        ("100", "etthundra"),
        ("101", "etthundraett"),
        ("-5", "minus fem"),
        ("+5", "plus fem"),
        ("1,5", "ett komma fem"),
        ("1,50", "ett komma fem noll"),
        ("0,02", "noll komma noll två"),
        (",02", "noll komma noll två"),
    ],
)
def test_swedish_plain_numbers(raw: str, expected: str) -> None:
    assert prepare(raw, language="sv", use_spacy=False).spoken_text == expected


@pytest.mark.parametrize("separator", [" ", "\u00a0", "\u202f"])
def test_swedish_grouping_preserves_numeric_value(separator: str) -> None:
    assert prepare(f"1{separator}000", language="sv", use_spacy=False).spoken_text == "etttusen"
    assert (
        prepare(f"1{separator}234,50", language="sv", use_spacy=False).spoken_text
        == "etttusen tvåhundratrettiofyra komma fem noll"
    )


def test_swedish_dot_decimals_are_preserved() -> None:
    for raw in ("1.5", "1.234", "1.2.3"):
        assert prepare(raw, language="sv", use_spacy=False).spoken_text == raw
        assert parse_numeric_lexeme(raw, "sv", context="plain") is None
        assert parse_numeric_lexeme(raw, "sv", context="quantity") is None


def test_swedish_numeric_policies() -> None:
    punctuation = numeric_punctuation_policy("sv-SE")
    assert punctuation.decimal_separator == ","
    assert punctuation.grouping_separators == (" ", "\u00a0", "\u202f")
    assert punctuation.alternate_decimal_separators == ()
    assert numeric_speech_policy("sv").decimal_word == "komma"
    assert numeric_speech_policy("sv").fraction_mode == "digitwise"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1 s", "en sekund"),
        ("2 s", "två sekunder"),
        ("1 min", "en minut"),
        ("2 min", "två minuter"),
        ("1 h", "en timme"),
        ("2 h", "två timmar"),
        ("1 m", "en meter"),
        ("2 m", "två meter"),
        ("1 km", "en kilometer"),
        ("2 km", "två kilometer"),
        ("1 kg", "ett kilogram"),
        ("2 kg", "två kilogram"),
        ("1,5 km", "ett komma fem kilometer"),
        ("0,5 l", "noll komma fem liter"),
        ("1 °C", "en grad Celsius"),
        ("2 °C", "två grader Celsius"),
        ("1 °F", "en grad Fahrenheit"),
        ("4 m²", "fyra kvadratmeter"),
        ("3 m3", "tre kubikmeter"),
        ("20 km/h", "tjugo kilometer per timme"),
        ("5 m/s", "fem meter per sekund"),
        ("2 kWh", "två kilowattimmar"),
    ],
)
def test_swedish_structured_quantities(source: str, expected: str) -> None:
    assert prepare(source, language="sv", use_spacy=False).spoken_text == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1 kr", "en krona"),
        ("2 kr", "två kronor"),
        ("SEK 1", "en krona"),
        ("SEK 2", "två kronor"),
        ("12,8 kr", "tolv kronor och åttio öre"),
        ("12,80 kr", "tolv kronor och åttio öre"),
        ("12,08 kr", "tolv kronor och åtta öre"),
        ("12,00 kr", "tolv kronor"),
        ("-2 kr", "minus två kronor"),
    ],
)
def test_swedish_currency(source: str, expected: str) -> None:
    assert prepare(source, language="sv", use_spacy=False).spoken_text == expected


def test_swedish_abbr2words_integration_and_canonical_ids() -> None:
    assert resolve_num2words_language("sv-SE") == "sv"
    assert resolve_abbr2words_language("sv-SE") == "sv"
    match = next(iter(iter_unit_matches("2 km", "sv")))
    assert match.canonical_id == "length-kilometer"
    result = prepare("t.ex. 2 kg", language="sv", use_spacy=False)
    assert result.spoken_text == "till exempel två kilogram"
    assert any(edit.rule == "abbr:t.ex." for edit in result.source_replacements)
    quantity = next(edit for edit in result.source_replacements if edit.rule == "sv.quantity")
    assert quantity.source == "2 kg"
    assert quantity.source_start == 6
    assert quantity.source_end == 10


def test_swedish_guarded_abbreviations_remain_guarded() -> None:
    assert prepare("kl. snart", language="sv", use_spacy=False).spoken_text == "kl. snart"
    assert (
        prepare("kap. avslutas här", language="sv", use_spacy=False).spoken_text
        == "kap. avslutas här"
    )
    assert prepare("CA-123", language="sv", use_spacy=False).spoken_text == "CA-123"


def test_swedish_time_and_date_forms_are_caller_managed() -> None:
    for source in ("19.10", "19:10", "25.99", "25:99", "14.05.2026", "2026-05-14"):
        assert prepare(source, language="sv", use_spacy=False).spoken_text == source
    assert prepare("kl. 19.10", language="sv", use_spacy=False).spoken_text == "klockan 19.10"


def test_swedish_protection_and_repeated_source_spans() -> None:
    source = "Besök https://example.com/v1.2.3, mejla test@example.com och gå 2 km. 2 km."
    result = prepare(source, language="sv", use_spacy=False)
    assert result.spoken_text == (
        "Besök https://example.com/v1.2.3, mejla test@example.com och gå två kilometer. två kilometer."
    )
    quantity_edits = [edit for edit in result.source_replacements if edit.rule == "sv.quantity"]
    assert [(edit.source_start, edit.source_end, edit.source) for edit in quantity_edits] == [
        (64, 68, "2 km"),
        (70, 74, "2 km"),
    ]


def test_swedish_caller_protected_ranges_and_metadata() -> None:
    source = "x 2 km y"
    assert iter_structured_replacements(source, language="sv", protected_ranges=((2, 6),)) == ()
    replacements = iter_structured_replacements("x 2 km y", language="sv")
    assert len(replacements) == 1
    replacement = replacements[0]
    assert (replacement.start, replacement.end) == (2, 6)
    assert replacement.language == "sv"
    assert replacement.rule == "sv.quantity"
    assert replacement.recognition_domain == "quantities"
    assert replacement.recognition_evidence == "intrinsic"


def test_swedish_domain_filters() -> None:
    source = "2 km"
    assert iter_structured_replacements(
        source, language="sv", allowed_domains=frozenset({RecognitionDomain.QUANTITIES})
    )
    assert (
        iter_structured_replacements(
            source, language="sv", disabled_domains=frozenset({RecognitionDomain.QUANTITIES})
        )
        == ()
    )


def test_swedish_sentence_punctuation_is_not_part_of_lexeme() -> None:
    result = prepare("Det tog 1,5 sekunder.", language="sv", use_spacy=False)
    assert result.spoken_text == "Det tog ett komma fem sekunder."
    assert result.source_replacements[0].source == "1,5"
    assert result.source_replacements[0].source_end == len("Det tog 1,5")


def test_swedish_numeric_lexeme_grouping() -> None:
    lexeme = parse_numeric_lexeme("1\u202f234,50", "sv")
    assert isinstance(lexeme, NumericLexeme)
    assert lexeme.integer_digits == "1234"
    assert lexeme.fraction_digits == "50"
    assert lexeme.decimal_separator == ","


def test_swedish_legacy_number_api_uses_structured_safe_path() -> None:
    assert normalize_numbers("1 000", language="sv") == "etttusen"
    assert normalize_numbers("1 234,50", language="sv") == (
        "etttusen tvåhundratrettiofyra komma fem noll"
    )
    assert normalize_numbers("19.10", language="sv") == "19.10"
