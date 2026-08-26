from __future__ import annotations

import ast
from pathlib import Path

import pytest

from spokenform.number_words import (
    cardinal,
    digits,
    number_backend_for_language,
    ordinal,
)


@pytest.mark.parametrize(
    ("language", "backend"),
    [
        ("en", "num2words"),
        ("ja", "num2words"),
        ("ko", "num2words"),
        ("zh", "cn2an"),
        ("zh_CN", "cn2an"),
    ],
)
def test_number_backend_selection(language: str, backend: str) -> None:
    assert number_backend_for_language(language) == backend


@pytest.mark.parametrize(
    ("language", "value", "expected"),
    [
        ("ja", 21, "二十一"),
        ("ko", 21, "이십일"),
        ("zh", 123, "一百二十三"),
        ("zh_CN", -123, "负一百二十三"),
    ],
)
def test_cardinal_rendering(language: str, value: int, expected: str) -> None:
    assert cardinal(value, language) == expected


def test_chinese_decimal_and_digitwise_rendering() -> None:
    assert cardinal("1.23", "zh_CN") == "一点二三"
    assert digits("012", "zh_CN") == ("零", "一", "二")


def test_released_num2words_ordinals_remain_available() -> None:
    assert ordinal(3, "ja") == "三番目"
    assert ordinal(3, "ko") == "세 번째"


def test_chinese_ordinals_fail_closed() -> None:
    with pytest.raises(ValueError, match="Ordinal rendering"):
        ordinal(3, "zh")


def test_num2words_calls_are_confined_to_backend_facade() -> None:
    root = Path(__file__).parents[1] / "spokenform"
    violations: list[str] = []
    for path in root.rglob("*.py"):
        if path.name == "number_words.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(
            isinstance(node.func, ast.Name) and node.func.id == "num2words"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        ):
            violations.append(str(path.relative_to(root.parent)))
        if "from num2words import num2words" in path.read_text(encoding="utf-8"):
            violations.append(str(path.relative_to(root.parent)))
    assert violations == []
