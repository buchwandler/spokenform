from __future__ import annotations

import pytest

from spokenform import prepare

_FORBIDDEN = {
    "point",
    "minus",
    "plus",
    "percent",
    "and",
    "to",
    "dollar",
    "cents",
    "slash",
    "hyphen",
    "underscore",
    "open parenthesis",
    "close parenthesis",
}


@pytest.mark.parametrize("language", ["ja", "ko", "zh_CN"])
def test_generated_cjk_replacements_do_not_use_english_fallback_words(language: str) -> None:
    result = prepare("1.23 -3 +3 5% 1/2 3-5 5 km", language=language, use_spacy=False)
    generated = " ".join(item.replacement.casefold() for item in result.source_replacements)
    assert not any(token in generated.split() for token in _FORBIDDEN)
    assert "point" not in generated
    assert "minus" not in generated
    assert "plus" not in generated
    assert "percent" not in generated
    assert "slash" not in generated
    assert "hyphen" not in generated


@pytest.mark.parametrize("language", ["ja", "ko", "zh_CN"])
def test_unknown_cjk_adjacent_identifiers_remain_unchanged(language: str) -> None:
    result = prepare("OpenAI AIGC A320 H100 AAPL NASA", language=language, use_spacy=False)
    assert result.spoken_text == "OpenAI AIGC A320 H100 AAPL NASA"
