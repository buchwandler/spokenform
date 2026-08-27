from __future__ import annotations

import pytest

from spokenform import iter_structured_replacements, prepare
from spokenform.config import RecognitionDomain


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("0", "ศูนย์"),
        ("1", "หนึ่ง"),
        ("2", "สอง"),
        ("11", "สิบเอ็ด"),
        ("21", "ยี่สิบเอ็ด"),
        ("25", "ยี่สิบห้า"),
        ("100", "หนึ่งร้อย"),
        ("101", "หนึ่งร้อยเอ็ด"),
        ("-5", "ติดลบห้า"),
        ("+5", "บวกห้า"),
        ("1.5", "หนึ่งจุดห้า"),
        ("1.50", "หนึ่งจุดห้าศูนย์"),
        (".05", "ศูนย์จุดศูนย์ห้า"),
        ("-0.05", "ติดลบศูนย์จุดศูนย์ห้า"),
    ],
)
def test_th_plain_numbers(source: str, expected: str) -> None:
    assert prepare(source, language="th", use_spacy=False).spoken_text == expected


@pytest.mark.parametrize("source", ["1,234", "1 234", "1\u00a0234", "1\u202f234"])
def test_th_grouping(source: str) -> None:
    assert prepare(source, language="th", use_spacy=False).spoken_text == "หนึ่งพันสองร้อยสามสิบสี่"


def test_th_decimal_punctuation_and_precision() -> None:
    assert (
        prepare("1,234.50", language="th", use_spacy=False).spoken_text
        == "หนึ่งพันสองร้อยสามสิบสี่จุดห้าศูนย์"
    )
    assert prepare("1.234", language="th", use_spacy=False).spoken_text == "หนึ่งจุดสองสามสี่"
    assert prepare("1,5", language="th", use_spacy=False).spoken_text == "1,5"


@pytest.mark.parametrize("source", ["๒๑", "๑๐๑", "๑.๐๕", "๑,๒๓๔.๕๐"])
def test_th_digits_match_latin_equivalents(source: str) -> None:
    latin = source.translate(str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789"))
    assert (
        prepare(source, language="th", use_spacy=False).spoken_text
        == prepare(latin, language="th", use_spacy=False).spoken_text
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("5 กม.", "ห้า กิโลเมตร"),
        ("5 km", "ห้า กิโลเมตร"),
        ("10 ซม.", "สิบ เซนติเมตร"),
        ("2 กก.", "สอง กิโลกรัม"),
        ("250 ก.", "สองร้อยห้าสิบ กรัม"),
        ("2 ล.", "สอง ลิตร"),
        ("3 ชม.", "สาม ชั่วโมง"),
        ("25 ตร.ม.", "ยี่สิบห้า ตารางเมตร"),
        ("4 ลบ.ม.", "สี่ ลูกบาศก์เมตร"),
        ("30 °C", "สามสิบ องศาเซลเซียส"),
        ("5 kPa", "ห้า กิโลปาสกาล"),
        ("2 GB", "สอง กิกะไบต์"),
    ],
)
def test_th_quantities(source: str, expected: str) -> None:
    assert prepare(source, language="th", use_spacy=False).spoken_text == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("฿100", "หนึ่งร้อย บาท"),
        ("100 ฿", "หนึ่งร้อย บาท"),
        ("THB 100", "หนึ่งร้อย บาท"),
        ("100 THB", "หนึ่งร้อย บาท"),
        ("12.50 THB", "สิบสอง บาท ห้าสิบ สตางค์"),
        ("1.5 THB", "หนึ่ง บาท ห้าสิบ สตางค์"),
        ("0.25 THB", "ยี่สิบห้า สตางค์"),
        ("-12.50 THB", "ติดลบสิบสอง บาท ห้าสิบ สตางค์"),
    ],
)
def test_th_baht(source: str, expected: str) -> None:
    assert prepare(source, language="th", use_spacy=False).spoken_text == expected


def test_th_baht_precision_fails_closed() -> None:
    assert prepare("1.234 THB", language="th", use_spacy=False).spoken_text == "1.234 THB"


@pytest.mark.parametrize("source", ["นพ.", "พญ.", "ทพ.", "ทพญ.", "รศ.", "ผศ.", "ดร."])
def test_th_reviewed_abbreviations_expand(source: str) -> None:
    assert prepare(source, language="th", use_spacy=False).spoken_text != source


def test_th_ambiguous_abbreviation_stays_literal() -> None:
    assert prepare("ม.เชียงใหม่", language="th", use_spacy=False).spoken_text == "ม.เชียงใหม่"
    assert prepare("XYZ.", language="th", use_spacy=False).spoken_text == "XYZ."


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("27 ส.ค. 2569", "27 สิงหาคม 2569"),
        ("๒๗ ส.ค. ๒๕๖๙", "๒๗ สิงหาคม ๒๕๖๙"),
        ("พ.ศ. 2569", "พุทธศักราช 2569"),
        ("ค.ศ. 2026", "คริสต์ศักราช 2026"),
        ("05:00 น.", "05:00 นาฬิกา"),
        ("27/08/2569", "27/08/2569"),
        ("2569-08-27", "2569-08-27"),
        ("05:00", "05:00"),
    ],
)
def test_th_calendar_and_time_bodies_are_caller_managed(source: str, expected: str) -> None:
    assert prepare(source, language="th", use_spacy=False).spoken_text == expected


def test_th_mapping_and_domain_filtering() -> None:
    source = "ระยะ 2 กม. และ 2 กม. ราคา 100 THB"
    result = prepare(source, language="th", use_spacy=False)
    assert result.spoken_text == "ระยะ สอง กิโลเมตร และ สอง กิโลเมตร ราคา หนึ่งร้อย บาท"
    quantity_edits = [edit for edit in result.source_replacements if edit.rule == "th.quantity"]
    assert len(quantity_edits) == 2
    first = source.index("2 กม.")
    second = source.index("2 กม.", first + 1)
    assert [(edit.source_start, edit.source_end) for edit in quantity_edits] == [
        (first, first + len("2 กม.")),
        (second, second + len("2 กม.")),
    ]

    replacement = iter_structured_replacements("2 กม.", language="th")[0]
    assert replacement.rule == "th.quantity"
    assert replacement.recognition_domain == RecognitionDomain.QUANTITIES.value
    assert replacement.recognition_evidence == "intrinsic"
    assert iter_structured_replacements("2 กม.", language="th", protected_ranges=((0, 4),)) == ()
    assert not iter_structured_replacements(
        "2 กม.", language="th", disabled_domains=frozenset({RecognitionDomain.QUANTITIES})
    )
    assert not iter_structured_replacements(
        "100 THB", language="th", disabled_domains=frozenset({RecognitionDomain.FINANCE})
    )
    assert iter_structured_replacements(
        "100 THB", language="th", allowed_domains=frozenset({RecognitionDomain.FINANCE})
    )
