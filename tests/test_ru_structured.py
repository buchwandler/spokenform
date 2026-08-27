from __future__ import annotations

import pytest
from abbr2words import iter_unit_matches

from spokenform import prepare
from spokenform.config import RecognitionDomain
from spokenform.locales.ru import quantity_category
from spokenform.numbers import normalize_numbers, normalize_plain_numbers
from spokenform.numeric_lexeme import (
    numeric_punctuation_policy,
    numeric_speech_policy,
    parse_numeric_lexeme,
)
from spokenform.structured import iter_structured_replacements


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("0", "ноль"),
        ("1", "один"),
        ("2", "два"),
        ("5", "пять"),
        ("11", "одиннадцать"),
        ("21", "двадцать один"),
        ("22", "двадцать два"),
        ("25", "двадцать пять"),
        ("101", "сто один"),
        ("121", "сто двадцать один"),
        ("122", "сто двадцать два"),
        ("-5", "минус пять"),
        ("+5", "плюс пять"),
        ("1,5", "один запятая пять"),
        ("1,50", "один запятая пять ноль"),
        ("0,02", "ноль запятая ноль два"),
        (",02", "ноль запятая ноль два"),
    ],
)
def test_russian_plain_numbers(source: str, expected: str) -> None:
    assert prepare(source, language="ru", use_spacy=False).spoken_text == expected


@pytest.mark.parametrize("separator", [" ", "\u00a0", "\u202f"])
def test_russian_grouping(separator: str) -> None:
    source = f"1{separator}234,50"
    assert prepare(source, language="ru", use_spacy=False).spoken_text == (
        "одна тысяча двести тридцать четыре запятая пять ноль"
    )


@pytest.mark.parametrize("source", ["1.5", "1.234", "1.2.3"])
def test_russian_period_decimals_are_preserved(source: str) -> None:
    assert prepare(source, language="ru", use_spacy=False).spoken_text == source
    assert parse_numeric_lexeme(source, "ru", context="plain") is None
    assert parse_numeric_lexeme(source, "ru", context="quantity") is None


def test_russian_numeric_policies() -> None:
    punctuation = numeric_punctuation_policy("ru-RU")
    assert punctuation.decimal_separator == ","
    assert punctuation.grouping_separators == (" ", "\u00a0", "\u202f")
    assert punctuation.alternate_decimal_separators == ()
    speech = numeric_speech_policy("ru")
    assert speech.decimal_word == "запятая"
    assert speech.fraction_mode == "digitwise"


@pytest.mark.parametrize(
    ("category", "values"),
    [
        ("one", [1, 21, 31, 101, 121]),
        ("few", [2, 3, 4, 22, 23, 24, 102, 122]),
        ("many", [0, 5, 10, 11, 12, 14, 15, 20, 25, 100, 111]),
    ],
)
def test_russian_quantity_categories(category: str, values: list[int]) -> None:
    for value in values:
        lexeme = parse_numeric_lexeme(str(value), "ru", context="quantity")
        assert lexeme is not None
        assert quantity_category(lexeme) == category


@pytest.mark.parametrize("source", ["0,0", "1,0", "2,0", "1,5", "21,00"])
def test_russian_visible_decimals_are_other(source: str) -> None:
    lexeme = parse_numeric_lexeme(source, "ru", context="quantity")
    assert lexeme is not None
    assert quantity_category(lexeme) == "other"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1 кг", "один килограмм"),
        ("2 кг", "два килограмма"),
        ("5 кг", "пять килограммов"),
        ("11 кг", "одиннадцать килограммов"),
        ("21 кг", "двадцать один килограмм"),
        ("22 кг", "двадцать два килограмма"),
        ("25 кг", "двадцать пять килограммов"),
        ("111 кг", "сто одиннадцать килограммов"),
        ("121 кг", "сто двадцать один килограмм"),
        ("1 мин", "одна минута"),
        ("2 мин", "две минуты"),
        ("5 мин", "пять минут"),
        ("21 мин", "двадцать одна минута"),
        ("22 мин", "двадцать две минуты"),
        ("25 мин", "двадцать пять минут"),
    ],
)
def test_russian_quantity_morphology(source: str, expected: str) -> None:
    assert prepare(source, language="ru", use_spacy=False).spoken_text == expected


@pytest.mark.parametrize(
    ("source", "expected_suffix"),
    [
        ("1,5 кг", "килограмма"),
        ("2,0 кг", "килограмма"),
        ("0,1 м", "метра"),
        ("0,1 м²", "квадратного метра"),
    ],
)
def test_russian_decimal_noun_forms(source: str, expected_suffix: str) -> None:
    assert prepare(source, language="ru", use_spacy=False).spoken_text.endswith(expected_suffix)


@pytest.mark.parametrize(
    "source",
    ["1 °C", "2 °C", "5 °C", "-5 °C", "1,5 °C", "1 °F", "2 °F", "5 °F", "1 K", "2 K", "5 K"],
)
def test_russian_temperatures_are_reviewed(source: str) -> None:
    result = prepare(source, language="ru", use_spacy=False)
    assert "градус" in result.spoken_text or "кельвин" in result.spoken_text


def test_russian_symbol_aliases_share_canonical_identity() -> None:
    for left, right in (("kg", "кг"), ("Hz", "Гц"), ("W", "Вт"), ("V", "В"), ("kPa", "кПа")):
        left_match = next(iter(iter_unit_matches(f"5 {left}", "ru")))
        right_match = next(iter(iter_unit_matches(f"5 {right}", "ru")))
        assert left_match.canonical_id == right_match.canonical_id
        assert (
            prepare(f"5 {left}", language="ru", use_spacy=False).spoken_text
            == prepare(f"5 {right}", language="ru", use_spacy=False).spoken_text
        )


def test_russian_metadata_domain_filters_and_mapping() -> None:
    source = "2 кг"
    replacements = iter_structured_replacements(source, language="ru")
    assert len(replacements) == 1
    replacement = replacements[0]
    assert (replacement.start, replacement.end) == (0, len(source))
    assert replacement.language == "ru"
    assert replacement.rule == "ru.quantity"
    assert replacement.recognition_domain == "quantities"
    assert replacement.recognition_evidence == "intrinsic"
    assert iter_structured_replacements(
        source, language="ru", allowed_domains=frozenset({RecognitionDomain.QUANTITIES})
    )
    assert (
        iter_structured_replacements(
            source, language="ru", disabled_domains=frozenset({RecognitionDomain.QUANTITIES})
        )
        == ()
    )


def test_russian_caller_protected_range() -> None:
    assert iter_structured_replacements("x 2 кг y", language="ru", protected_ranges=((2, 6),)) == ()


def test_russian_repeated_spans_keep_offsets() -> None:
    source = "Откройте https://example.com/v1.2.3, напишите test@example.com и пройдите 2 км. 2 км."
    result = prepare(source, language="ru", use_spacy=False)
    assert "https://example.com/v1.2.3" in result.spoken_text
    assert "test@example.com" in result.spoken_text
    edits = [edit for edit in result.source_replacements if edit.rule == "ru.quantity"]
    assert [(edit.source, edit.source_start, edit.source_end) for edit in edits] == [
        ("2 км", source.index("2 км"), source.index("2 км") + 4),
        ("2 км", source.rindex("2 км"), source.rindex("2 км") + 4),
    ]


def test_russian_guarded_abbreviations_and_caller_managed_structures() -> None:
    assert prepare("стр. 4", language="ru", use_spacy=False).spoken_text == "страница четыре"
    assert prepare("№ 7", language="ru", use_spacy=False).spoken_text == "номер семь"
    assert prepare("рис. 2", language="ru", use_spacy=False).spoken_text == "рисунок два"
    assert prepare("табл. 3", language="ru", use_spacy=False).spoken_text == "таблица три"
    for source in (
        "г. Москва",
        "2026 г.",
        "р. Волга",
        "14.05.2026",
        "2026-05-14",
        "19:10",
        "25:99",
        "100 ₽",
        "100 RUB",
    ):
        assert prepare(source, language="ru", use_spacy=False).spoken_text == source


def test_russian_phone_marker_protection() -> None:
    assert (
        normalize_plain_numbers("тел.: +7 495 123-45-67", language="ru") == "тел.: +7 495 123-45-67"
    )


def test_russian_legacy_number_api_uses_safe_path() -> None:
    assert normalize_numbers("1,50", language="ru") == "один запятая пять ноль"


def test_unknown_russian_canonical_id_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from spokenform.locales import ru

    source = "2 zz"
    match = ru.UnitMatch(0, 4, 0, 1, "2", "zz", "future-unit", "zz", "future", "ru")
    monkeypatch.setattr(ru, "iter_unit_matches", lambda *args, **kwargs: (match,))
    assert ru.iter_replacements(source) == ()
