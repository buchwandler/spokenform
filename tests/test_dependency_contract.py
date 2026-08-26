from __future__ import annotations

import pytest
from abbr2words import iter_unit_matches

from spokenform import iter_structured_replacements


@pytest.mark.parametrize(
    ("language", "symbol", "canonical_id"),
    [
        ("cs", "Kč", "currency-czech-koruna"),
        ("de", "EUR", "currency-euro"),
        ("fr", "€", "currency-euro"),
        ("fr", "$", "currency-us-dollar"),
        ("fr", "£", "currency-pound-sterling"),
        ("es", "€", "currency-euro"),
        ("it", "€", "currency-euro"),
        ("pt", "€", "currency-euro"),
        ("ja", "¥", "currency-japanese-yen"),
        ("ko", "₩", "currency-south-korean-won"),
        ("zh_CN", "人民币", "currency-chinese-yuan"),
        ("de", "m³", "volume-cubic-meter"),
        ("de", "km/h", "speed-kilometer-per-hour"),
    ],
)
def test_migrated_locale_uses_canonical_abbr2words_identity(
    language: str, symbol: str, canonical_id: str
) -> None:
    source = f"2 {symbol}"
    matches = list(iter_unit_matches(source, language))
    replacements = iter_structured_replacements(source, language=language)

    assert matches and matches[0].canonical_id == canonical_id
    assert replacements
    assert replacements[0].start == matches[0].start
    assert replacements[0].end == matches[0].end
