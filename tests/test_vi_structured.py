from __future__ import annotations

import pytest
from abbr2words.units import unit_entries

from spokenform import iter_structured_replacements, prepare
from spokenform.config import (
    NumberPolicy,
    RecognitionDomain,
    RecognitionEvidence,
    number_policy_for_language,
)
from spokenform.language import resolve_abbr2words_language, resolve_num2words_language
from spokenform.number_words import number_backend_for_language
from spokenform.numeric_lexeme import (
    NumericLexeme,
    numeric_punctuation_policy,
    numeric_speech_policy,
    parse_numeric_lexeme,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", "không"),
        ("1", "một"),
        ("2", "hai"),
        ("11", "mười một"),
        ("21", "hai mươi mốt"),
        ("25", "hai mươi lăm"),
        ("100", "một trăm"),
        ("101", "một trăm lẻ một"),
        ("-5", "âm năm"),
        ("+5", "dương năm"),
        ("1,5", "một phẩy năm"),
        ("1,50", "một phẩy năm không"),
        ("0,02", "không phẩy không hai"),
        (",02", "không phẩy không hai"),
    ],
)
def test_vietnamese_plain_numbers(raw: str, expected: str) -> None:
    assert prepare(raw, language="vi", use_spacy=False).spoken_text == expected


@pytest.mark.parametrize("separator", [".", " ", "\u00a0", "\u202f"])
def test_vietnamese_grouping_preserves_numeric_value(separator: str) -> None:
    assert (
        prepare(f"1{separator}234,50", language="vi", use_spacy=False).spoken_text
        == "một nghìn hai trăm ba mươi bốn phẩy năm không"
    )


def test_vietnamese_dot_grouping_is_valid() -> None:
    lexeme = parse_numeric_lexeme("1.234", "vi", context="plain")
    assert isinstance(lexeme, NumericLexeme)
    assert lexeme.integer_digits == "1234"
    assert lexeme.fraction_digits is None


@pytest.mark.parametrize("raw", ["1.5", "1.25", "12.34", "1.2.3", "1.23"])
def test_vietnamese_dot_decimals_fail_closed(raw: str) -> None:
    assert prepare(raw, language="vi", use_spacy=False).spoken_text == raw
    assert parse_numeric_lexeme(raw, "vi", context="plain") is None
    assert parse_numeric_lexeme(raw, "vi", context="quantity") is None


def test_vietnamese_numeric_policies() -> None:
    punctuation = numeric_punctuation_policy("vi-VN")
    assert punctuation.decimal_separator == ","
    assert punctuation.grouping_separators == (".", " ", "\u00a0", "\u202f")
    assert punctuation.alternate_decimal_separators == ()
    assert punctuation.infer_decimal_in_strong_context is False

    speech = numeric_speech_policy("vi")
    assert speech.decimal_word == "phẩy"
    assert speech.fraction_mode == "digitwise"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1 s", "một giây"),
        ("2 min", "hai phút"),
        ("3 h", "ba giờ"),
        ("4 d", "bốn ngày"),
        ("7 m", "bảy mét"),
        ("8 km", "tám kilômét"),
        ("10 L", "mười lít"),
        ("14 kg", "mười bốn kilôgam"),
        ("20 °C", "hai mươi độ Celsius"),
        ("70 °F", "bảy mươi độ Fahrenheit"),
        ("5 m/s", "năm mét trên giây"),
        ("80 km/h", "tám mươi kilômét trên giờ"),
        ("100 kPa", "một trăm kilôpascan"),
        ("2 GB", "hai gigabyte"),
        ("2 m²", "hai mét vuông"),
        ("2 m³", "hai mét khối"),
        ("1,5 km", "một phẩy năm kilômét"),
    ],
)
def test_vietnamese_structured_quantities(source: str, expected: str) -> None:
    assert prepare(source, language="vi", use_spacy=False).spoken_text == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1000 VND", "một nghìn đồng Việt Nam"),
        ("₫1000", "một nghìn đồng Việt Nam"),
        ("1.000 VND", "một nghìn đồng Việt Nam"),
        ("-1000 VND", "âm một nghìn đồng Việt Nam"),
    ],
)
def test_vietnamese_currency(source: str, expected: str) -> None:
    assert prepare(source, language="vi", use_spacy=False).spoken_text == expected


def test_fractional_vnd_fails_closed() -> None:
    assert prepare("1,5 VND", language="vi", use_spacy=False).spoken_text == "1,5 VND"


def test_vietnamese_runtime_and_dependency_routing() -> None:
    assert number_policy_for_language("vi") is NumberPolicy.STRUCTURED_AND_PLAIN
    assert number_backend_for_language("vi") == "num2words"
    assert number_backend_for_language("vi-VN") == "num2words"
    assert resolve_num2words_language("vi-VN") == "vi"
    assert resolve_abbr2words_language("vi-VN") == "vi"


def test_vietnamese_dependency_units_have_renderable_contract() -> None:
    entries = unit_entries("vi")
    assert entries
    assert all(entry.canonical_id and entry.expansion for entry in entries)
    assert {entry.category for entry in entries} <= {"unit", "currency"}


def test_vietnamese_abbreviation_and_quantity_integration() -> None:
    result = prepare("TP. Hà Nội có 2 kg hàng.", language="vi", use_spacy=False)
    assert result.spoken_text == "thành phố Hà Nội có hai kilôgam hàng."
    assert any(edit.rule == "vi.quantity" for edit in result.source_replacements)


def test_vietnamese_phone_marker_does_not_claim_phone_number() -> None:
    assert (
        prepare("SĐT: 0914.858.982", language="vi", use_spacy=False).spoken_text
        == "số điện thoại: 0914.858.982"
    )


@pytest.mark.parametrize("source", ["UBND", "HĐND", "QĐ-TTg", "Số 30/2020/NĐ-CP"])
def test_vietnamese_legal_identifiers_fail_closed(source: str) -> None:
    assert prepare(source, language="vi", use_spacy=False).spoken_text == source


def test_vietnamese_ordinals_dates_and_times_remain_caller_managed() -> None:
    for source in ("3. mục", "12:34", "14.05.2026", "2026-05-14"):
        assert prepare(source, language="vi", use_spacy=False).spoken_text == source


def test_vietnamese_source_mapping_preserves_repeated_quantity_spans() -> None:
    source = "TP. Hà Nội có 2 kg. 2 kg."
    result = prepare(source, language="vi", use_spacy=False)
    quantity_edits = [edit for edit in result.source_replacements if edit.rule == "vi.quantity"]
    first = source.index("2 kg")
    second = source.index("2 kg", first + 1)
    assert [(edit.source_start, edit.source_end, edit.source) for edit in quantity_edits] == [
        (first, first + 4, "2 kg"),
        (second, second + 4, "2 kg"),
    ]


def test_vietnamese_caller_protected_ranges_and_metadata() -> None:
    source = "x 2 kg y"
    assert iter_structured_replacements(source, language="vi", protected_ranges=((2, 6),)) == ()
    replacement = iter_structured_replacements(source, language="vi")[0]
    assert replacement.language == "vi"
    assert replacement.rule == "vi.quantity"
    assert replacement.recognition_domain == RecognitionDomain.QUANTITIES.value
    assert replacement.recognition_evidence == RecognitionEvidence.INTRINSIC.value


def test_vietnamese_domain_filters() -> None:
    assert iter_structured_replacements(
        "2 kg", language="vi", allowed_domains=frozenset({RecognitionDomain.QUANTITIES})
    )
    assert not iter_structured_replacements(
        "2 kg", language="vi", disabled_domains=frozenset({RecognitionDomain.QUANTITIES})
    )
    assert iter_structured_replacements(
        "1000 VND", language="vi", allowed_domains=frozenset({RecognitionDomain.FINANCE})
    )
    assert not iter_structured_replacements(
        "1000 VND", language="vi", disabled_domains=frozenset({RecognitionDomain.FINANCE})
    )
