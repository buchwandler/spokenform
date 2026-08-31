from __future__ import annotations

from spokenform import prepare

THAI_CASES = (
    ("๑๒๓", "หนึ่งร้อยยี่สิบสาม"),
    ("3-5", "สาม ถึง ห้า"),
    ("555 คน", "ห้าร้อยห้าสิบห้า คน"),
    ("฿20", "ยี่สิบ บาท"),
    ("50% + 2 = 52", "ห้าสิบ เปอร์เซ็นต์ บวก สอง เท่ากับ ห้าสิบสอง"),
    ("โทร 0812345678", "โทร ศูนย์ แปด หนึ่ง สอง สาม สี่ ห้า หก เจ็ด แปด"),
    ("12:05", "สิบสอง นาฬิกา ศูนย์ ห้า นาที"),
    ("บ้าน 12/4", "บ้าน หนึ่ง สอง ขีด สี่"),
)


def test_legacy_thai_semantic_pairs() -> None:
    for source, expected in THAI_CASES:
        assert prepare(source, language="th", use_spacy=False).spoken_text == expected, source


def test_thai_source_alignment_covers_the_intended_currency_value() -> None:
    source = "ราคา ๒๐ บาท"
    result = prepare(source, language="th", use_spacy=False)

    assert result.spoken_text == "ราคา ยี่สิบ บาท"
    replacements = [item for item in result.source_replacements if item.source == "๒๐ บาท"]
    assert len(replacements) == 1
    replacement = replacements[0]
    assert source[replacement.source_start : replacement.source_end] == "๒๐ บาท"
    assert "ยี่สิบ" in replacement.replacement
    assert result.spoken_text[replacement.output_start : replacement.output_end] == ("ยี่สิบ บาท")
