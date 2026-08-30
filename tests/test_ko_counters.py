from __future__ import annotations

import pytest

from spokenform import prepare_for_kokorog2p
from spokenform.locales.ko import process_num


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", "영"),
        ("1", "한"),
        ("2", "두"),
        ("3", "세"),
        ("10", "열"),
        ("18", "열여덟"),
        ("20", "스무"),
        ("123", "백이십삼"),
    ],
)
def test_korean_native_and_sino_number_forms(value: str, expected: str) -> None:
    assert process_num(value, sino=False) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("3시", "세시"),
        ("10분", "십분"),
        ("3개", "세개"),
        ("2명", "두명"),
        ("20살", "스무살"),
        ("123개", "백이십삼개"),
        ("18시 20분", "열여덟시 이십분"),
    ],
)
def test_korean_counter_preparation_matches_g2pk_forms(source: str, expected: str) -> None:
    assert prepare_for_kokorog2p(source, "ko").spoken_text == expected


def test_korean_counter_protection_is_source_aligned() -> None:
    source = "3개 4개"
    result = prepare_for_kokorog2p(source, "ko", protected_spans=[(0, 2)])
    assert result.spoken_text == "3개 네개"
    assert all(item.source != "3개" for item in result.source_replacements)
