from __future__ import annotations

import ast
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import numeralform
import pytest

from spokenform.language import base_language, supported_languages
from spokenform.language_support import language_support
from spokenform.number_words import (
    cardinal,
    currency,
    decimal,
    digits,
    number_backend_for_language,
    ordinal,
    year,
)


@pytest.mark.parametrize(
    ("language", "backend"),
    [
        ("en", "numeralform"),
        ("ja", "numeralform"),
        ("ko", "numeralform"),
        ("vi", "numeralform"),
        ("th", "numeralform"),
        ("vi-VN", "numeralform"),
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
        ("th", 0, "ศูนย์"),
        ("th", 21, "ยี่สิบเอ็ด"),
        ("th", 101, "หนึ่งร้อยเอ็ด"),
    ],
)
def test_cardinal_rendering(language: str, value: int, expected: str) -> None:
    assert cardinal(value, language) == expected


def test_cardinal_contract_covers_representative_numeralform_locales() -> None:
    assert cardinal(101, "en") == "one hundred and one"
    assert cardinal(21, "de") == "einundzwanzig"
    assert cardinal(71, "fr") == "soixante et onze"
    assert cardinal(80, "fr-CH") == "huitante"
    assert cardinal(118, "it") == "centodiciotto"
    assert cardinal(42, "sv") == "fyrtiotvå"
    assert cardinal(21, "vi") == "hai mươi mốt"
    assert cardinal(21, "kk") == "жиырма бір"
    assert cardinal(21, "hi") == "इक्कीस"
    assert cardinal(21, "hy") == "քսանմեկ"
    assert cardinal(21, "mn") == "хорин нэг"


@pytest.mark.parametrize(
    "language",
    [
        language
        for language in supported_languages(include_locales=True)
        if base_language(language) != "zh" and language_support(language).plain_cardinals
    ],
)
def test_claimed_numeralform_backend_has_cardinal_capability(language: str) -> None:
    support = language_support(language)
    assert support.number_backend == "numeralform"
    assert support.number_language is not None
    assert numeralform.supports(support.number_language, form="cardinal", value=0)


def test_numeralform_decimal_and_currency_contracts() -> None:
    assert decimal(Decimal("1.20"), "en") == "one point two zero"
    assert currency(Decimal("12.80"), "en", "EUR") == "twelve euros and eighty cents"


def test_chinese_decimal_and_digitwise_rendering() -> None:
    assert cardinal("1.23", "zh_CN") == "一点二三"
    assert digits("012", "zh_CN") == ("零", "一", "二")
    assert digits("012", "th") == ("ศูนย์", "หนึ่ง", "สอง")


def test_numeralform_ordinals_and_years_remain_available() -> None:
    assert ordinal(3, "en") == "third"
    assert ordinal(3, "ja") == "三番目"
    assert ordinal(3, "ko") == "세 번째"
    assert year(2024, "en") == "twenty twenty-four"


def test_chinese_ordinals_fail_closed() -> None:
    with pytest.raises(ValueError, match="Ordinal rendering"):
        ordinal(3, "zh")


def test_numeralform_errors_are_translated_at_facade_boundary() -> None:
    with pytest.raises(ValueError, match="Cannot render ordinal"):
        ordinal(3, "th")


@pytest.mark.parametrize("value", [1.5, object(), None])
def test_numeric_facade_rejects_unsupported_runtime_types(value: object) -> None:
    with pytest.raises(TypeError):
        cardinal(value, "en")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        currency(value, "en", "EUR")  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["", " ", "abc", "--1"])
def test_numeric_facade_rejects_invalid_strings(value: str) -> None:
    with pytest.raises(ValueError):
        cardinal(value, "en")


def test_numeric_facade_rejects_non_finite_decimal() -> None:
    with pytest.raises(ValueError, match="finite"):
        cardinal(Decimal("NaN"), "en")


def test_upstream_num2words_is_not_used_in_spokenform_runtime() -> None:
    root = Path(__file__).parents[1] / "spokenform"
    violations: list[str] = []
    for path in root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "num2words" or alias.name.startswith("numeralform.compat"):
                        violations.append(str(path.relative_to(root.parent)))
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "num2words" or module.startswith("numeralform.compat"):
                    violations.append(str(path.relative_to(root.parent)))
            if isinstance(node, ast.Attribute):
                parts: list[str] = []
                current: ast.expr = node
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                dotted = ".".join(reversed(parts))
                if dotted.startswith("numeralform.compat") or dotted.startswith("num2words"):
                    violations.append(str(path.relative_to(root.parent)))
            if isinstance(node, ast.Name) and node.id == "CONVERTER_CLASSES":
                violations.append(str(path.relative_to(root.parent)))
        if 'package_version("num2words")' in source:
            violations.append(str(path.relative_to(root.parent)))
    assert violations == []


def test_importing_spokenform_does_not_import_upstream_num2words() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import spokenform; assert 'num2words' not in sys.modules",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stderr == ""
