from __future__ import annotations

import pytest

from spokenform import prepare_for_kokorog2p


@pytest.mark.parametrize(
    ("source", "fragment", "rule"),
    [
        ("12:30", "สิบสอง นาฬิกา สาม ศูนย์ นาที", "th.time"),
        ("2.05", "สอง จุด ศูนย์ ห้า", "th.decimal"),
        ("1-3", "หนึ่ง ถึง สาม", "th.range"),
        ("เลขที่ 1234", "เลขที่ หนึ่ง สอง สาม สี่", "th.identifier"),
        ("โทร 081-234", "โทร ศูนย์ แปด หนึ่ง ขีด สอง สาม สี่", "th.identifier"),
        ("555", "ฮ่า ฮ่า ฮ่า", "th.laughter.555"),
        ("555 บาท", "ห้าร้อยห้าสิบห้า บาท", "th.currency"),
        ("เร็วๆ", "เร็ว เร็ว", "th.repetition"),
    ],
)
def test_thai_kokorog2p_semantics_are_structured_and_source_aligned(
    source: str, fragment: str, rule: str
) -> None:
    result = prepare_for_kokorog2p(source, "th")
    assert fragment in result.spoken_text
    matches = [item for item in result.source_replacements if item.rule == rule]
    assert matches
    for item in matches:
        assert source[item.source_start : item.source_end] == item.source


@pytest.mark.parametrize("symbol", ["%", "+", "=", "<", ">", "≤", "≥"])
def test_thai_operator_semantics_are_upstream(symbol: str) -> None:
    result = prepare_for_kokorog2p(f"2 {symbol} 3", "th")
    assert result.spoken_text
    assert any(item.rule == f"th.operator.{symbol}" for item in result.source_replacements)
